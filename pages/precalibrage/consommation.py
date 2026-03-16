
import pandas as pd
import numpy as np
import streamlit as st
import folium
from streamlit_folium import st_folium
from utils.helpers import get_coordinates_from_postal_code
from services.geolocation import get_coordinates_from_address
from services.curve_processing import process_curve
from services.curve_processing.alignment import align_curve_to_reference_year, CalendarAlignmentError, find_max_common_calendar_range
import html
import re
from geopy.distance import geodesic
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_map_with_radius(points: list, radius_km: float = 10, zoom: int = 12):
    """
    Crée une carte avec cercle de rayon et centroïde optimisé.
    
    Cherche le centroïde qui maximise le nombre de points à l'intérieur du rayon.
    Si plusieurs centroïdes donnent le même nombre de points inside,
    choisit celui minimisant la somme totale des distances.
    
    Args:
        points: list of dicts {'name', 'lat', 'lon'}
        radius_km: rayon du cercle en km
        zoom: niveau de zoom folium
    
    Retourne : (folium.Map, (center_lat, center_lon), inside_list, outside_list)
        - inside_list / outside_list: list of tuples (name, distance_km)
    """
    if not points:
        raise ValueError("La liste de points est vide")

    # Centroïde initial (moyenne simple)
    def _lon(p):
        return p.get("lon", p.get("lng"))

    # Filter out points missing coordinates
    valid_points = [p for p in points if p.get("lat") is not None and _lon(p) is not None]
    if not valid_points:
        raise ValueError("La liste de points est vide ou invalide")

    orig_lat = sum(p["lat"] for p in valid_points) / len(valid_points)
    orig_lon = sum(_lon(p) for p in valid_points) / len(valid_points)

    def compute_lists(center_lat, center_lon):
        inside = []
        outside = []
        for p in valid_points:
            d = geodesic((center_lat, center_lon), (p["lat"], _lon(p))).km
            if d <= radius_km:
                inside.append((p.get("name", p.get("nom", "")), round(d, 2)))
            else:
                outside.append((p.get("name", p.get("nom", "")), round(d, 2)))
        return inside, outside

    # Calcul initial
    inside, outside = compute_lists(orig_lat, orig_lon)

    # Si des points sont en dehors, rechercher un centre candidat
    center_lat, center_lon = orig_lat, orig_lon
    if outside:
        candidates = [(p["lat"], _lon(p)) for p in valid_points]
        candidates.append((orig_lat, orig_lon))

        def total_distance(center_lat, center_lon):
            return sum(
                geodesic((center_lat, center_lon), (p["lat"], _lon(p))).km
                for p in valid_points
            )

        best_center = (orig_lat, orig_lon)
        best_inside, best_outside = inside, outside
        best_count = len(inside)
        best_total_dist = total_distance(orig_lat, orig_lon)

        for cand_lat, cand_lon in candidates:
            in_c, out_c = compute_lists(cand_lat, cand_lon)
            count = len(in_c)
            if count > best_count:
                best_count = count
                best_center = (cand_lat, cand_lon)
                best_inside, best_outside = in_c, out_c
                best_total_dist = total_distance(cand_lat, cand_lon)
            elif count == best_count:
                td = total_distance(cand_lat, cand_lon)
                if td < best_total_dist:
                    best_center = (cand_lat, cand_lon)
                    best_inside, best_outside = in_c, out_c
                    best_total_dist = td

        center_lat, center_lon = best_center
        inside, outside = best_inside, best_outside

    # Construire la carte centrée sur le centre choisi
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    names_inside = {name for name, _ in inside}
    for p in valid_points:
        actor_name = p.get("name", p.get("nom", ""))
        color = "green" if actor_name in names_inside else "red"
        # Build richer popup if optional fields are present
        popup_html = f"""
        <b>{actor_name}</b><br>
        Type: {p.get('type', 'N/A')}<br>
        Segment: {p.get('segment', 'N/A')}<br>
        Puissance: {p.get('puissance', 'N/A')}<br>
        """
        folium.Marker(
            location=[p["lat"], _lon(p)],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=actor_name,
            icon=folium.Icon(color=color)
        ).add_to(m)

    # Cercle gris
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_km * 1000,
        color="gray",
        fill=True,
        fill_opacity=0.15,
    ).add_to(m)

    return m, (center_lat, center_lon), inside, outside


def cercle(coords: dict, map_object: folium.Map, radius_km: float = 2.0, 
           color: str = "blue", fill_opacity: float = 0.15, **kwargs) -> None:
    """
    Ajoute un cercle sur une carte Folium.
    
    Args:
        coords: dict avec keys 'lat' et 'lng'
        map_object: objet folium.Map
        radius_km: rayon du cercle en kilomètres
        color: couleur du cercle
        fill_opacity: opacité du remplissage
        **kwargs: arguments supplémentaires pour folium.Circle
    """
    if not coords or not coords.get('lat') or not coords.get('lng'):
        logger.warning("Coordonnées invalides pour le cercle")
        return
    
    folium.Circle(
        location=[coords['lat'], coords['lng']],
        radius=radius_km * 1000,  # Convert km to meters
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=fill_opacity,
        opacity=0.5,
        **kwargs
    ).add_to(map_object)


def extract_distance_km(distance_str: str) -> float:
    """Extract numeric distance value from strings like '2 km', '2km', '2.5', or return float inputs."""
    if isinstance(distance_str, (int, float)):
        return float(distance_str)
    if not isinstance(distance_str, str):
        return 2.0
    match = re.search(r"(\d+(?:[\.,]\d+)?)", distance_str)
    if match:
        return float(match.group(1).replace(",", "."))
    return 2.0


def render():
    """Render the Points de soutirage page with two-tab structure."""
    st.title("Points de soutirage")

    # Initialize soutirage points list if not exists
    if "points_soutirage" not in st.session_state:
        st.session_state["points_soutirage"] = []

    # Create two tabs
    tab1, tab2 = st.tabs(["📊 Gestion des points", "🗺️ Vérification des contraintes"])

    with tab1:
        
        # Full-width layout: Table + Form (no map)
        st.subheader("Points de soutirage")
        
        points = st.session_state["points_soutirage"]
        
        # Initialize confirmation state if not exists
        if "confirm_delete_soutirage" not in st.session_state:
            st.session_state["confirm_delete_soutirage"] = None
        
        # Section 1: Custom HTML table with action buttons
        if "edit_soutirage_idx" not in st.session_state:
            st.session_state["edit_soutirage_idx"] = None
        if "edit_soutirage_form" not in st.session_state:
            st.session_state["edit_soutirage_form"] = None
        if len(points) > 0:
            # Custom CSS for fixed table layout
            st.markdown("""
            <style>
            .soutirage-table {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                background-color: transparent;
            }
            .soutirage-table th {
                background-color: rgba(240, 242, 246, 0.1);
                padding: 10px 8px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid rgba(128, 128, 128, 0.3);
                font-size: 14px;
            }
            .soutirage-table td {
                padding: 12px 8px;
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
                font-size: 14px;
            }
            .soutirage-table tr:hover {
                background-color: rgba(128, 128, 128, 0.1);
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Table header
            table_html = """
            <table class="soutirage-table">
                <thead>
                    <tr>
                        <th style="width: 8%;">Actif</th>
                        <th style="width: 18%;">Nom</th>
                        <th style="width: 12%;">Segment</th>
                        <th style="width: 22%;">Adresse</th>
                        <th style="width: 12%;">ACI</th>
                        <th style="width: 15%;">Actions</th>
                    </tr>
                </thead>
            </table>
            """
            st.markdown(table_html, unsafe_allow_html=True)
            
            for idx, point in enumerate(points):
                highlight = (st.session_state["edit_soutirage_idx"] == idx)
                is_active = point.get("active", True)
                
                if highlight:
                    row_style = "background-color:#e3f0ff; color:#1565c0; font-weight:bold; border-radius:6px;"
                elif not is_active:
                    row_style = "color:#9e9e9e; text-decoration: line-through; opacity: 0.6;"
                else:
                    row_style = ""
                    
                cols = st.columns([0.08, 0.18, 0.12, 0.22, 0.12, 0.15])

                with cols[0]:
                    if f"active_sout_{idx}" not in st.session_state:
                         st.session_state[f"active_sout_{idx}"] = is_active
                    new_active = st.checkbox("Actif", key=f"active_sout_{idx}", label_visibility="collapsed")
                    if new_active != is_active:
                        st.session_state["points_soutirage"][idx]["active"] = new_active
                        if st.session_state.get("project_id"):
                            from services.database import save_project
                            from services.state_serializer import serialize_state
                            save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                        st.rerun()
                with cols[1]:
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{point['nom']}</div>", unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{point['segment']}</div>", unsafe_allow_html=True)
                with cols[3]:
                    adresse_display = point.get('adresse', 'N/A')
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{adresse_display}</div>", unsafe_allow_html=True)
                with cols[4]:
                    aci_text = f"✅ {point['aci_partenaire']}" if point['aci'] else "❌"
                    st.markdown(f"<div style='padding: 4px 0;'>{aci_text}</div>", unsafe_allow_html=True)
                with cols[5]:
                    action_cols = st.columns([1, 1, 1], gap="small")
                    with action_cols[0]:
                        if st.button("✏️", key=f"edit_s_{idx}", help="Modifier", use_container_width=True):
                            st.session_state["edit_soutirage_idx"] = idx
                            st.session_state["edit_soutirage_form"] = point.copy()
                            st.rerun()
                    with action_cols[1]:
                        if st.button("📋", key=f"dup_s_{idx}", help="Dupliquer", use_container_width=True):
                            duplicated_point = point.copy()
                            duplicated_point["nom"] = f"{point['nom']} (copie)"
                            st.session_state["points_soutirage"].append(duplicated_point)
                            if st.session_state.get("project_id"):
                                from services.database import save_project
                                from services.state_serializer import serialize_state
                                save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                            st.success(f"✅ Point '{point['nom']}' dupliqué!")
                            st.rerun()
                    with action_cols[2]:
                        if st.session_state["confirm_delete_soutirage"] == idx:
                            # Show both confirm and cancel buttons
                            col_confirm, col_cancel = st.columns([1, 1])
                            with col_confirm:
                                if st.button("✓", key=f"confirm_s_{idx}", help="Confirmer la suppression", use_container_width=True):
                                    st.session_state["points_soutirage"].pop(idx)
                                    st.session_state["confirm_delete_soutirage"] = None
                                    if st.session_state.get("project_id"):
                                        from services.database import save_project
                                        from services.state_serializer import serialize_state
                                        save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                                    st.success("Point supprimé")
                                    st.rerun()
                            with col_cancel:
                                if st.button("✗", key=f"cancel_s_{idx}", help="Annuler la suppression", use_container_width=True):
                                    st.session_state["confirm_delete_soutirage"] = None
                                    st.rerun()
                        else:
                            if st.button("🗑️", key=f"delete_s_{idx}", help="Supprimer", use_container_width=True):
                                st.session_state["confirm_delete_soutirage"] = idx
                                st.rerun()
                if st.session_state["confirm_delete_soutirage"] == idx:
                    st.warning(f"⚠️ Confirmer ou annuler la suppression de '{point['nom']}'")
                if idx < len(points) - 1:
                    st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

            # Afficher le formulaire de modification sous la table si une ligne est sélectionnée
            if st.session_state["edit_soutirage_idx"] is not None and st.session_state["edit_soutirage_form"] is not None:
                st.markdown("---")
                st.subheader("Modifier le point de soutirage")
                edit_state = st.session_state["edit_soutirage_form"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    edit_state["nom"] = st.text_input("Nom *", value=edit_state["nom"], key="edit_sout_nom")
                    edit_state["segment"] = st.text_input("Segment", value=edit_state["segment"], key="edit_sout_segment")
                
                with col2:
                    edit_state["adresse"] = st.text_input("Adresse", value=edit_state["adresse"], key="edit_sout_adresse")
                    
                    # Auto-géolocalisation si adresse remplie et changée
                    if edit_state["adresse"] and edit_state["adresse"] != edit_state.get("last_geocoded_address", ""):
                        with st.spinner("Géolocalisation..."):
                            coords = get_coordinates_from_address(edit_state["adresse"])
                            if coords and coords.get("lat") and coords.get("lng"):
                                edit_state["coords"] = coords
                                edit_state["manual_lat"] = coords["lat"]
                                edit_state["manual_lng"] = coords["lng"]
                                # Mettre à jour les widgets directement
                                st.session_state["edit_sout_lat"] = coords["lat"]
                                st.session_state["edit_sout_lng"] = coords["lng"]
                                edit_state["last_geocoded_address"] = edit_state["adresse"]
                    
                    # Initialiser les coordonnées manuelles si nécessaire
                    if "manual_lat" not in edit_state:
                        edit_state["manual_lat"] = (edit_state.get("coords") or {}).get("lat", 0.0)
                    if "manual_lng" not in edit_state:
                        edit_state["manual_lng"] = (edit_state.get("coords") or {}).get("lng", 0.0)
                    
                    # Initialiser les widgets dans session_state pour éviter le warning
                    if "edit_sout_lat" not in st.session_state:
                        st.session_state["edit_sout_lat"] = float(edit_state["manual_lat"])
                    if "edit_sout_lng" not in st.session_state:
                        st.session_state["edit_sout_lng"] = float(edit_state["manual_lng"])
                    
                    # Afficher lat/lon éditables
                    col_lat_edit, col_lng_edit = st.columns(2)
                    with col_lat_edit:
                        edit_state["manual_lat"] = st.number_input(
                            "Latitude", 
                            format="%.6f",
                            step=0.001,
                            key="edit_sout_lat"
                        )
                    with col_lng_edit:
                        edit_state["manual_lng"] = st.number_input(
                            "Longitude", 
                            format="%.6f",
                            step=0.001,
                            key="edit_sout_lng"
                        )
                    
                    # Mettre à jour coords avec les valeurs manuelles
                    if edit_state["manual_lat"] != 0.0 or edit_state["manual_lng"] != 0.0:
                        edit_state["coords"] = {"lat": edit_state["manual_lat"], "lng": edit_state["manual_lng"]}
                
                with col3:
                    edit_state["point_livraison"] = st.text_input("Point de livraison", value=edit_state.get("point_livraison", ""), key="edit_sout_pdl")
                    edit_state["aci"] = st.checkbox("Contrat ACI", value=edit_state["aci"], key="edit_sout_aci")
                    injection_points = st.session_state.get("points_injection", [])
                    injection_names = [p["nom"] for p in injection_points]
                    edit_state["aci_partenaire"] = st.selectbox("Partenaire ACI", ["Aucun"] + injection_names, 
                        index=( ["Aucun"] + injection_names ).index(edit_state["aci_partenaire"] ) if edit_state["aci_partenaire"] in (["Aucun"] + injection_names) else 0,
                        disabled=not edit_state["aci"], key="edit_sout_aci_partenaire")

                # --- Gestion de la courbe de consommation dans l'édition ---
                st.markdown("---")
                st.markdown("**Courbe de consommation**")
                
                # Extract the actual dataframe or data dictionary from the 'courbe_consommation' wrapper structure if it exists
                current_curve_source = edit_state.get("courbe_consommation")
                has_curve = current_curve_source is not None
                
                if has_curve:
                    st.success("✅ Une courbe est actuellement attachée à ce point.")
                    
                    df_to_show = None
                    if isinstance(current_curve_source, dict) and "df" in current_curve_source:
                        df_to_show = current_curve_source["df"]
                    elif isinstance(current_curve_source, pd.DataFrame):
                        df_to_show = current_curve_source
                        
                    if df_to_show is not None and not df_to_show.empty:
                        # Display a small preview of the current curve
                        if "value" in df_to_show.columns:
                            st.line_chart(df_to_show["value"], height=200, use_container_width=True)
                        else:
                            st.line_chart(df_to_show, height=200, use_container_width=True)
                    
                    if st.button("🗑️ Supprimer et remplacer cette courbe", key="delete_curve_consommation"):
                        # Remove the curve to expose the uploader
                        edit_state["courbe_consommation"] = None
                        edit_state["curve_data"] = None 
                        st.session_state["points_soutirage"][st.session_state["edit_soutirage_idx"]] = edit_state
                        st.rerun()
                else:
                    # Provide the uploader logic exactly as in the add section if no curve is present
                    st.info("Aucune courbe actuelle. Téléversez-en une nouvelle ci-dessous.")
                    uploaded_file = st.file_uploader("Charger CSV/XLS/XLSX", type=["csv", "xls", "xlsx"], key="edit_upload_curve_sout")
                    if uploaded_file:
                        try:
                            name = uploaded_file.name.lower()
                            if name.endswith(".csv"):
                                curve_df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8-sig')
                                curve_df.columns = [str(col).strip().lstrip('\ufeff') for col in curve_df.columns]
                            else:
                                curve_df = pd.read_excel(uploaded_file)
                            edit_state["curve_data"] = curve_df
                            st.success("✅ Fichier chargé, prêt à être enregistré.")
                        except Exception as e:
                            st.error(f"⚠️ Erreur lecture fichier: {e}")
                            edit_state["curve_data"] = None

                st.markdown("<br>", unsafe_allow_html=True)

                # Boutons verticaux : Enregistrer puis Annuler en dessous
                st.markdown("<div style='width: 220px;'>", unsafe_allow_html=True)
                if st.button("💾 Enregistrer les modifications", key="save_edit_soutirage", type="primary"):
                    # If we added a new curve_data in the edit form, process it and replace the formal wrapper
                    if not has_curve and edit_state.get("curve_data") is not None:
                        processed = None
                        try:
                            processed = process_curve(edit_state["curve_data"])
                        except Exception as e:
                            st.error(f"Erreur traitement: {e}")
                        
                        edit_state["courbe_consommation"] = (
                            {"df": processed.get("df"), "metadata": processed.get("metadata"), "impute_report": processed.get("impute_report")}
                            if processed and processed.get("success") else edit_state["curve_data"]
                        )
                        
                        # Trigger db auto-save for the raw dataset if attached to a project
                        project_id = st.session_state.get("project_id")
                        if project_id:
                            try:
                                from services.database import save_dataset
                                save_dataset(
                                    project_id=project_id,
                                    name=f"{edit_state['nom']}_curve.json",
                                    type="consumption_curve",
                                    data=edit_state["curve_data"],
                                    metadata={"original_name": edit_state["nom"], "address": edit_state["adresse"]},
                                )
                            except Exception as e:
                                st.error(f"Erreur DB dataset: {e}")
                    
                    # Ensure we drop the raw curve_data key from st.session_state representation
                    if "curve_data" in edit_state:
                         del edit_state["curve_data"]
                         
                    idx = st.session_state["edit_soutirage_idx"]
                    st.session_state["points_soutirage"][idx] = edit_state.copy()
                    if st.session_state.get("project_id"):
                        from services.database import save_project
                        from services.state_serializer import serialize_state
                        save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                    st.success(f"✅ Point '{edit_state['nom']}' modifié avec succès!")
                    st.session_state["edit_soutirage_idx"] = None
                    st.session_state["edit_soutirage_form"] = None
                    st.rerun()
                if st.button("❌ Annuler", key="cancel_edit_soutirage"):
                    st.session_state["edit_soutirage_idx"] = None
                    st.session_state["edit_soutirage_form"] = None
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                st.info("✏️ Mode édition actif : le formulaire d'ajout est masqué.")
        else:
            st.info("Aucun point de soutirage configuré. Ajoutez-en un ci-dessous.")

        st.divider()

        # Section 2: Add form (simple form with direct curve display)
        st.subheader("Ajouter un point de soutirage")
        
        # Initialize form state if needed
        if "sout_form_state" not in st.session_state:
            st.session_state["sout_form_state"] = {
                "nom": "", "point_livraison": "", "segment": "",
                "aci": False,
                "adresse": "",
                "curve_data": None, "coords": None
            }
        
        state = st.session_state["sout_form_state"]
        
        # Input form
        col1, col2, col3 = st.columns(3)
        
        with col1:
            state["nom"] = st.text_input("Nom *", value=state["nom"], placeholder="Bâtiment municipal")
            state["segment"] = st.text_input("Segment", value=state["segment"], placeholder="C5")
        
        with col2:
            state["adresse"] = st.text_input("Adresse", value=state["adresse"], placeholder="123 Rue de la Ville, 75001 Paris")
            
            # Auto-géolocalisation si adresse remplie
            if state["adresse"] and state["adresse"] != state.get("last_geocoded_address", ""):
                with st.spinner("Géolocalisation..."):
                    coords = get_coordinates_from_address(state["adresse"])
                    if coords and coords.get("lat") and coords.get("lng"):
                        state["coords"] = coords
                        state["manual_lat"] = coords["lat"]
                        state["manual_lng"] = coords["lng"]
                        # Mettre à jour les widgets directement
                        st.session_state["sout_lat"] = coords["lat"]
                        st.session_state["sout_lng"] = coords["lng"]
                        state["last_geocoded_address"] = state["adresse"]
                    else:
                        st.warning("⚠️ Géolocalisation impossible pour cette adresse")
            
            # Initialiser les coordonnées manuelles si nécessaire
            if "manual_lat" not in state:
                state["manual_lat"] = (state.get("coords") or {}).get("lat", 0.0)
            if "manual_lng" not in state:
                state["manual_lng"] = (state.get("coords") or {}).get("lng", 0.0)
            
            # Initialiser les widgets dans session_state pour éviter le warning
            if "sout_lat" not in st.session_state:
                st.session_state["sout_lat"] = float(state["manual_lat"])
            if "sout_lng" not in st.session_state:
                st.session_state["sout_lng"] = float(state["manual_lng"])
            
            # Afficher lat/lon éditables
            col_lat, col_lng = st.columns(2)
            with col_lat:
                state["manual_lat"] = st.number_input(
                    "Latitude", 
                    format="%.6f",
                    step=0.001,
                    key="sout_lat"
                )
            with col_lng:
                state["manual_lng"] = st.number_input(
                    "Longitude", 
                    format="%.6f",
                    step=0.001,
                    key="sout_lng"
                )
            
            # Mettre à jour coords avec les valeurs manuelles
            if state["manual_lat"] != 0.0 or state["manual_lng"] != 0.0:
                state["coords"] = {"lat": state["manual_lat"], "lng": state["manual_lng"]}
        
        with col3:
            state["point_livraison"] = st.text_input("Point de livraison", value=state.get("point_livraison", ""), placeholder="12345678901234")
            
            # Get list of injection points for ACI partner dropdown
            injection_points = st.session_state.get("points_injection", [])
            injection_names = [p["nom"] for p in injection_points]
            
            # Get already used ACI partners from existing soutirage points
            used_aci_partners = {
                p["aci_partenaire"] 
                for p in st.session_state.get("points_soutirage", []) 
                if p.get("aci") and p.get("aci_partenaire")
            }
            
            # Filter out already used injection points
            available_injection_names = [name for name in injection_names if name not in used_aci_partners]
            
            # Disable ACI checkbox if no injection points available
            has_available_injection_points = len(available_injection_names) > 0
            if not has_available_injection_points:
                state["aci"] = False  # Force ACI to False if no injection points available
            
            # Determine help message
            if len(injection_names) == 0:
                aci_help = "Nécessite au moins un point d'injection"
            elif not has_available_injection_points:
                aci_help = "Tous les points d'injection sont déjà en ACI"
            else:
                aci_help = None
            
            state["aci"] = st.checkbox(
                "Contrat ACI", 
                value=state["aci"], 
                disabled=not has_available_injection_points,
                help=aci_help
            )
            
            if has_available_injection_points:
                current_index = 0
                if state.get("aci_partenaire") in available_injection_names:
                    current_index = available_injection_names.index(state.get("aci_partenaire"))
                state["aci_partenaire"] = st.selectbox(
                    "Partenaire ACI", 
                    available_injection_names, 
                    index=current_index,
                    disabled=not state["aci"]
                )
            else:
                placeholder = "Aucun point d'injection" if len(injection_names) == 0 else "Tous les points d'injection sont déjà en ACI"
                st.selectbox("Partenaire ACI", [placeholder], disabled=True)
                state["aci_partenaire"] = None
        
        # Curve upload
        st.markdown("**Courbe de consommation**")
        
        # Two-column layout: upload on left, preview on right
        col_curve1, col_curve2 = st.columns([1, 1])
        
        with col_curve1:
            uploaded_file = st.file_uploader(
                "Charger CSV/XLS/XLSX",
                type=["csv", "xls", "xlsx"],
                key="upload_curve_sout",
            )
            if uploaded_file:
                try:
                    name = uploaded_file.name.lower()
                    if name.endswith(".csv"):
                        # Use sep=None with python engine for auto-detection of separator (handles ; or ,)
                        curve_df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8-sig')
                        # Clean column names (remove BOM and whitespace)
                        curve_df.columns = [str(col).strip().lstrip('\ufeff') for col in curve_df.columns]
                    else:
                        curve_df = pd.read_excel(uploaded_file)
                    state["curve_data"] = curve_df
                    st.success("✅ Fichier chargé")
                except Exception as e:
                    st.error(f"⚠️ Erreur lecture fichier: {e}")
                    state["curve_data"] = None
        
        with col_curve2:
            # Display curve preview if available
            if state["curve_data"] is not None:
                st.markdown("**📊 Aperçu**")
                try:
                    result = process_curve(state["curve_data"]) if state.get("curve_data") is not None else {"success": False}

                    if result.get('success') and result.get('df') is not None and len(result['df']) > 0:
                        norm_df = result['df']
                        # Plot only the numeric 'value' series if present
                        if 'value' in norm_df.columns:
                            st.line_chart(norm_df['value'], use_container_width=True, height=300)
                        else:
                            st.line_chart(norm_df, use_container_width=True, height=300)

                        st.caption(f"Colonnes: {', '.join(norm_df.columns.astype(str))} — Lignes: {len(norm_df)}")

                        # Calculer le volume consommé
                        if 'value' in norm_df.columns:
                            volume_total = norm_df['value'].sum()
                            volume_mwh = volume_total / 1000.0
                            st.metric("Volume consommé estimé", f"{volume_mwh:.2f} MWh", help=f"{volume_total:.0f} kWh sur la période")
                    else:
                        st.warning("⚠️ Courbe non exploitable pour l'affichage.")
                        if result.get('errors'):
                            st.error(f"Erreurs: {result['errors']}")
                        validation = result.get('validation') or {}
                        if validation.get('errors'):
                            st.error(f"Validation: {validation['errors']}")
                except Exception as e:
                    st.warning(f"⚠️ Erreur lors de la normalisation: {e}")
            else:
                st.info("↖️ Chargez un fichier pour voir l'aperçu")
        
        st.divider()
        
        # Validation button (always visible)
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        
        with col_btn1:
            if st.button("✅ Valider et ajouter le point", use_container_width=True, type="primary"):
                # Validate all required fields
                if not state["nom"]:
                    st.error("⚠️ Le champ Nom est obligatoire")
                elif state["curve_data"] is None:
                    st.error("⚠️ Une courbe de consommation est obligatoire")
                else:
                    # Get coordinates if not already done
                    if not state["coords"]:
                        # Try geocoding from address if provided
                        if state["adresse"]:
                            coords = get_coordinates_from_address(state["adresse"])
                            if coords and coords.get("lat") and coords.get("lng"):
                                state["coords"] = coords
                        # Otherwise check if manual lat/lon are provided
                        elif state["manual_lat"] != 0.0 and state["manual_lng"] != 0.0:
                            state["coords"] = {"lat": state["manual_lat"], "lng": state["manual_lng"]}
                    
                    # Final validation: coords must be set
                    if not state["coords"] or not state["coords"].get("lat") or not state["coords"].get("lng"):
                        st.error("⚠️ Coordonnées GPS manquantes. Renseignez l'adresse ou la latitude/longitude")
                        state["coords"] = None
                    
                    if state["coords"]:
                        # Process uploaded curve and store processing result
                        processed = None
                        try:
                            processed = process_curve(state["curve_data"]) if state.get("curve_data") is not None else None
                        except Exception as e:
                            st.error(f"Erreur traitement courbe: {e}")

                        # Create and add point (store processed result dict so aggregation can read it)
                        new_point = {
                            "nom": state["nom"],
                            "point_livraison": state.get("point_livraison", ""),
                            "segment": state["segment"],
                            "aci": state["aci"],
                            "aci_partenaire": state["aci_partenaire"] if state["aci"] else "Aucun",
                            "adresse": state["adresse"],
                            "active": True,
                            # Store either raw df or processed dict; processed preferred
                            "courbe_consommation": (
                                {"df": processed.get("df"), "metadata": processed.get("metadata"), "impute_report": processed.get("impute_report")} 
                                if processed and processed.get("success") else state.get("curve_data")
                            ),
                            "lat": state["coords"]["lat"],
                            "lng": state["coords"]["lng"]
                        }
                        st.session_state["points_soutirage"].append(new_point)
                        
                        # Auto-save Dataset
                        project_id = st.session_state.get("project_id")
                        if project_id and state.get("curve_data") is not None:
                            try:
                                from services.database import save_dataset
                                save_dataset(
                                    project_id=project_id,
                                    name=f"{state['nom']}_curve.json",
                                    type="consumption_curve",
                                    data=state["curve_data"],
                                    metadata={"original_name": state["nom"], "address": state["adresse"]},
                                )
                            except Exception as e:
                                st.error(f"⚠️ Erreur sauvegarde auto dataset: {e}")
                        
                        # Auto-save Project
                        if project_id:
                            from services.database import save_project
                            from services.state_serializer import serialize_state
                            save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), project_id)
                        
                        st.success(f"✅ Point '{state['nom']}' ajouté et sauvegardé avec succès!")
                        
                        # Reset form state
                        st.session_state["sout_form_state"] = {
                            "nom": "", "point_livraison": "", "segment": "",
                            "aci": False, "aci_partenaire": "Aucun",
                            "adresse": "",
                            "curve_data": None, "coords": None
                        }
                        st.rerun()
        
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state["sout_form_state"] = {
                    "nom": "", "point_livraison": "", "segment": "",
                    "aci": False, "aci_partenaire": "Aucun",
                    "adresse": "",
                    "curve_data": None, "coords": None
                }
                st.rerun()

    with tab2:
        st.subheader("Vérification des contraintes de distance")
        
        points_soutirage = st.session_state["points_soutirage"]
        points_injection = st.session_state.get("points_injection", [])
        
        if len(points_soutirage) == 0 and len(points_injection) == 0:
            st.info("Aucun point à afficher. Ajoutez des points d'injection ou de soutirage.")
        else:
            col_legend1, col_legend2, col_legend3, col_legend4 = st.columns(4)
            def _has_valid_curve_conso(p):
                """Retourne True si le point a une courbe consommation avec au moins 8736h consécutives."""
                courbe = p.get("courbe_consommation")
                if isinstance(courbe, dict) and "df" in courbe:
                    df = courbe["df"]
                elif isinstance(courbe, pd.DataFrame):
                    df = courbe
                else:
                    return False
                if not isinstance(df.index, pd.DatetimeIndex):
                    if "datetime" in df.columns:
                        df = df.set_index("datetime")
                if not isinstance(df.index, pd.DatetimeIndex) or "value" not in df.columns:
                    return False
                df_sorted = df.sort_index()
                src_year = df_sorted.index[0].year
                full_range = pd.date_range(start=f"{src_year}-01-01 00:00:00", end=f"{src_year}-12-31 23:00:00", freq='H')
                df_full = df_sorted.reindex(full_range)
                max_len = 0
                current_len = 0
                for val in df_full['value']:
                    if not pd.isna(val):
                        current_len += 1
                        max_len = max(max_len, current_len)
                    else:
                        current_len = 0
                return max_len >= 8736

            with col_legend1:
                active_inj_count = sum(1 for p in points_injection if p.get("active", True))
                st.metric("Points d'injection", active_inj_count)
            with col_legend2:
                active_conso_valid_count = sum(
                    1 for p in points_soutirage if p.get("active", True) and _has_valid_curve_conso(p)
                )
                st.metric("Points de soutirage", active_conso_valid_count)
            with col_legend3:
                distance_constraint_str = st.session_state.get("distance_constraint", "2 km")
                st.metric("Contrainte de distance", distance_constraint_str)
            with col_legend4:
                postal_code = st.session_state.get("postal_code", "N/A")
                st.metric("Code postal centre", postal_code)

            st.divider()

            # Determine radius in km (EPCI deferred: show notice and fallback)
            distance_constraint_str = st.session_state.get("distance_constraint", "2 km")
            if isinstance(distance_constraint_str, str) and distance_constraint_str.strip().upper() == "EPCI":
                st.warning("Mode EPCI non pris en charge pour l'instant — utilisation d'un rayon par défaut.")
            distance_km = extract_distance_km(distance_constraint_str)

            # Prepare all points for centroid map (injection + soutirage)
            all_points = []
            
            # Add injection points
            for p in points_injection:
                all_points.append({
                    "name": f"[INJ] {p.get('nom', '')}",
                    "lat": p.get("lat"),
                    "lon": p.get("lng"),
                    "type": f"Injection - {p.get('type', 'N/A')}",
                    "segment": p.get("segment"),
                    "puissance": int(p.get("puissance", 0)) if p.get("puissance") is not None else None,
                })
            
            # Add soutirage points
            for p in points_soutirage:
                all_points.append({
                    "name": f"[SOU] {p.get('nom', '')}",
                    "lat": p.get("lat"),
                    "lon": p.get("lng"),
                    "type": "Soutirage",
                    "segment": p.get("segment"),
                    "puissance": None,
                })

            # Build centroid circle map with inside/outside classification (guard invalid coords)
            valid_points = [pp for pp in all_points if pp["lat"] is not None and pp["lon"] is not None]
            
            if len(valid_points) == 0:
                st.info("Aucun point avec coordonnées valides pour afficher la carte.")
            else:
                try:
                    m, (center_lat, center_lon), inside, outside = show_map_with_radius(valid_points, radius_km=distance_km, zoom=12)
                    
                    # Display map
                    st.subheader("Carte de vérification")
                    
                    import streamlit.components.v1 as components
                    map_html = m._repr_html_()
                    components.html(map_html, height=600, scrolling=True)
                    
                except Exception as e:
                    import traceback
                    st.error(f"Erreur affichage carte: {e}")
                    st.code(traceback.format_exc())

            st.divider()
            st.subheader("Aperçu des données retenues (Points Actifs)")
            st.info("💡 Les points décochés dans l'onglet 'Gestion des points' n'apparaîtront pas ici et seront ignorés lors de la génération du scénario.")
            
            # --- Création du DataFrame croisé consommateurs (datetime en index, noms en colonnes, valeurs = consommation) ---

            try:
                dfs = []
                reference_year = st.session_state.get("reference_year")
                plages_valides = []
                noms_valides = []
                courbes_valides = []
                for p in points_soutirage:
                    if p.get("active", True):
                        courbe = p.get("courbe_consommation")
                        nom = p.get("nom", "Consommateur")
                        if isinstance(courbe, dict) and "df" in courbe:
                            df = courbe["df"]
                        elif isinstance(courbe, pd.DataFrame):
                            df = courbe
                        else:
                            continue
                        if not isinstance(df.index, pd.DatetimeIndex):
                            if "datetime" in df.columns:
                                df = df.set_index("datetime")
                        if not isinstance(df.index, pd.DatetimeIndex):
                            continue
                        if "value" not in df.columns:
                            continue
                        # Recherche de la plus longue plage consécutive >= 8736h
                        df_sorted = df.sort_index()
                        # Toujours étendre sur l'année source complète (01/01 00:00 → 31/12 23:00)
                        # pour que les heures supprimées à l'import soient présentes avec NaN
                        src_year = df_sorted.index[0].year
                        full_range = pd.date_range(
                            start=f"{src_year}-01-01 00:00:00",
                            end=f"{src_year}-12-31 23:00:00",
                            freq='H'
                        )
                        df_full = df_sorted.reindex(full_range)
                        max_len = 0
                        best_start = None
                        best_end = None
                        current_start = None
                        current_len = 0
                        for ts, val in df_full['value'].items():
                            if not pd.isna(val):
                                if current_start is None:
                                    current_start = ts
                                    current_len = 1
                                else:
                                    current_len += 1
                                if current_len > max_len:
                                    max_len = current_len
                                    best_start = current_start
                                    best_end = ts
                            else:
                                current_start = None
                                current_len = 0
                        if max_len >= 8736:
                            plages_valides.append((best_start, best_end))
                            noms_valides.append(nom)
                            courbes_valides.append(df_full)
                        else:
                            st.error(f"{nom} : courbe trop courte (max {max_len}h consécutives, minimum requis : 8736h)")
                if courbes_valides:
                    if len(courbes_valides) == 1:
                        # Un seul consommateur : pas d'intersection, juste alignement
                        nom = noms_valides[0]
                        df_full = courbes_valides[0]
                        if not isinstance(df_full.index, pd.DatetimeIndex):
                            try:
                                df_full.index = pd.to_datetime(df_full.index)
                            except Exception as e:
                                st.error(f"Impossible de convertir l'index en DatetimeIndex : {e}")
                                df_conso = None
                                st.session_state["df_conso"] = df_conso
                                return
                        if reference_year is None:
                            reference_year = df_full.index[0].year
                            st.session_state["reference_year"] = reference_year

                        # Index cible : année de référence sans 29 fév si bissextile
                        is_leap_ref = (reference_year % 4 == 0 and (reference_year % 100 != 0 or reference_year % 400 == 0))
                        target_index = pd.date_range(start=f"{reference_year}-01-01 00:00:00", end=f"{reference_year}-12-31 23:00:00", freq="H")
                        if is_leap_ref:
                            target_index = target_index[~((target_index.month == 2) & (target_index.day == 29))]

                        start = df_full.index.min()
                        if start.year == reference_year:
                            df_aligned = df_full.reindex(target_index)
                        else:
                            try:
                                df_aligned = align_curve_to_reference_year(df_full, reference_year)
                                df_aligned = df_aligned.reindex(target_index)
                            except CalendarAlignmentError as err:
                                st.error(f"Erreur d'alignement calendaire pour {nom} : {err}")
                                df_conso = None
                                st.session_state["df_conso"] = df_conso
                                return

                        missing_datetimes = [dt for dt in target_index if pd.isna(df_aligned.loc[dt, 'value'])]
                        missing_count = len(missing_datetimes)
                        df_crop = df_aligned.copy()
                        if missing_count > 0:
                            st.warning(f"{nom} : {missing_count} heure(s) manquante(s) sur l'année civile {reference_year}. Heures manquantes : {[dt.strftime('%d/%m %Hh') for dt in missing_datetimes[:10]]}{' ...' if len(missing_datetimes)>10 else ''}")
                            option = st.selectbox(
                                f"Comment remplir les {missing_count} valeurs manquantes pour {nom} ?",
                                ["Laisser manquant (NaN)", "Remplir par zéro", "Saisir manuellement"],
                                key=f"missing_option_{nom}"
                            )
                            if option == "Remplir par zéro":
                                for dt in missing_datetimes:
                                    df_crop.loc[dt, "value"] = 0.0
                                df_crop = df_crop.sort_index()
                            elif option == "Saisir manuellement":
                                manual_vals = {}
                                for dt in missing_datetimes:
                                    val = st.number_input(f"{nom} - {dt.strftime('%d/%m %Hh')}", min_value=0.0, step=0.1, key=f"manual_{nom}_{dt}")
                                    manual_vals[dt] = val
                                for dt, val in manual_vals.items():
                                    df_crop.loc[dt, "value"] = val
                                df_crop = df_crop.sort_index()
                        df_named = df_crop[["value"]].rename(columns={"value": nom})
                        if not isinstance(df_named.index, pd.DatetimeIndex):
                            df_named.index = pd.to_datetime(df_named.index)
                        st.session_state["df_conso"] = df_named
                        if df_named is not None and not df_named.empty:
                            st.dataframe(df_named, use_container_width=True)
                            st.info(f"Année de référence pour l'alignement calendaire : {reference_year}")
                        else:
                            st.warning("⚠️ DataFrame vide après traitement.")
                    else:
                        # Plusieurs consommateurs : intersection calendaire
                        best_start, best_end, mask_dict = find_max_common_calendar_range(courbes_valides)
                        if best_start is not None and best_end is not None:
                            reference_year = st.session_state.get("reference_year")
                            if reference_year is None:
                                reference_year = courbes_valides[0].index[0].year
                                st.session_state["reference_year"] = reference_year
                            is_leap_ref = (reference_year % 4 == 0 and (reference_year % 100 != 0 or reference_year % 400 == 0))
                            target_index = pd.date_range(start=f"{reference_year}-01-01 00:00:00", end=f"{reference_year}-12-31 23:00:00", freq="H")
                            if is_leap_ref:
                                target_index = target_index[~((target_index.month == 2) & (target_index.day == 29))]
                            for i, df_full in enumerate(courbes_valides):
                                nom = noms_valides[i]
                                mask = mask_dict[i]
                                df_crop = df_full[mask].copy()
                                missing_datetimes = [dt for dt in target_index if dt not in df_crop.index or pd.isna(df_crop.loc[dt, 'value'] if dt in df_crop.index else np.nan)]
                                missing_count = len(missing_datetimes)
                                if missing_count > 0:
                                    st.warning(f"{nom} : {missing_count} heure(s) manquante(s) sur l'année civile. Heures manquantes : {[dt.strftime('%d/%m %Hh') for dt in missing_datetimes[:10]]}{' ...' if len(missing_datetimes)>10 else ''}")
                                    option = st.selectbox(
                                        f"Comment remplir les {missing_count} valeurs manquantes pour {nom} ?",
                                        ["Laisser manquant (NaN)", "Remplir par zéro", "Saisir manuellement"],
                                        key=f"missing_option_{nom}"
                                    )
                                    if option == "Remplir par zéro":
                                        for dt in missing_datetimes:
                                            df_crop.loc[dt, "value"] = 0.0
                                        df_crop = df_crop.sort_index()
                                    elif option == "Saisir manuellement":
                                        manual_vals = {}
                                        for dt in missing_datetimes:
                                            val = st.number_input(f"{nom} - {dt.strftime('%d/%m %Hh')}", min_value=0.0, step=0.1, key=f"manual_{nom}_{dt}")
                                            manual_vals[dt] = val
                                        for dt, val in manual_vals.items():
                                            df_crop.loc[dt, "value"] = val
                                        df_crop = df_crop.sort_index()
                                # Reindex direct si même année, sinon alignement calendaire
                                src_year_crop = df_crop.index[0].year if len(df_crop) > 0 else None
                                if src_year_crop == reference_year:
                                    df_aligned = df_crop.reindex(target_index)
                                else:
                                    try:
                                        df_aligned = align_curve_to_reference_year(df_crop, reference_year)
                                        df_aligned = df_aligned.reindex(target_index)
                                    except CalendarAlignmentError as err:
                                        st.error(f"Erreur d'alignement calendaire pour {nom} : {err}")
                                        continue
                                df_named = df_aligned[["value"]].rename(columns={"value": nom})
                                if not isinstance(df_named.index, pd.DatetimeIndex):
                                    df_named.index = pd.to_datetime(df_named.index)
                                dfs.append(df_named)
                            if dfs:
                                if len(dfs) == 1:
                                    df_conso = dfs[0]
                                    if df_conso.columns[0] != noms_valides[0]:
                                        df_conso.columns = [noms_valides[0]]
                                else:
                                    df_conso = pd.concat(dfs, axis=1)
                                st.session_state["df_conso"] = df_conso
                                st.dataframe(df_conso, use_container_width=True)
                                st.info(f"Année de référence pour l'alignement calendaire : {reference_year}")
                            else:
                                st.warning("⚠️ Aucun point de soutirage actif avec des données valides.")
                        else:
                            st.warning("⚠️ Pas de plage calendaire commune entre les courbes retenues.")
                else:
                    df_conso = None
                    st.session_state["df_conso"] = df_conso
                    st.warning("⚠️ Aucun point de soutirage actif avec des données valides.")
            except Exception as e:
                df_conso = None
                st.session_state["df_conso"] = df_conso
                st.error(f"Erreur création DataFrame croisé consommateurs : {e}")

        # Nettoyage : suppression des st.write() de debug
