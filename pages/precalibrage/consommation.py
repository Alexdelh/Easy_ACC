import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from utils.helpers import get_coordinates_from_postal_code
from services.geolocation import get_coordinates_from_address
from services.curve_standardizer import CurveStandardizer
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
                        <th style="width: 16%;">Nom</th>
                        <th style="width: 10%;">Segment</th>
                        <th style="width: 13%;">Tarif réf. (c€/kWh)</th>
                        <th style="width: 14%;">ACI</th>
                        <th style="width: 9%;">TVA</th>
                        <th style="width: 13%;">Structure tarifaire</th>
                        <th style="width: 11%;">Tarif complément</th>
                        <th style="width: 14%;">Actions</th>
                    </tr>
                </thead>
            </table>
            """
            st.markdown(table_html, unsafe_allow_html=True)
            
            # Display each point with action buttons
            for idx, point in enumerate(points):
                # Create columns for data display and action buttons
                cols = st.columns([0.16, 0.10, 0.13, 0.14, 0.09, 0.13, 0.11, 0.14])
                
                with cols[0]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['nom']}</div>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['segment']}</div>", unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['tarif_reference']}</div>", unsafe_allow_html=True)
                with cols[3]:
                    aci_text = f"Oui ({point['aci_partenaire']})" if point['aci'] else "Non"
                    st.markdown(f"<div style='padding: 4px 0;'>{aci_text}</div>", unsafe_allow_html=True)
                with cols[4]:
                    tva_status = "✅" if point.get('tva', False) else "❌"
                    st.markdown(f"<div style='padding: 4px 0;'>{tva_status}</div>", unsafe_allow_html=True)
                with cols[5]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['structure_tarifaire']}</div>", unsafe_allow_html=True)
                with cols[6]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['tarif_complement']}</div>", unsafe_allow_html=True)
                with cols[7]:
                    # Action buttons with emojis
                    action_cols = st.columns([1, 1, 1], gap="small")
                    
                    with action_cols[0]:
                        if st.button("✏️", key=f"edit_s_{idx}", help="Modifier", use_container_width=True):
                            st.info("Fonction de modification à venir")
                    
                    with action_cols[1]:
                        if st.button("📋", key=f"dup_s_{idx}", help="Dupliquer", use_container_width=True):
                            # Duplicate the point
                            duplicated_point = point.copy()
                            duplicated_point["nom"] = f"{point['nom']} (copie)"
                            st.session_state["points_soutirage"].append(duplicated_point)
                            st.success(f"✅ Point '{point['nom']}' dupliqué!")
                            st.rerun()
                    
                    with action_cols[2]:
                        # Two-step deletion with confirmation
                        if st.session_state["confirm_delete_soutirage"] == idx:
                            if st.button("✓", key=f"confirm_s_{idx}", help="Confirmer la suppression", use_container_width=True):
                                st.session_state["points_soutirage"].pop(idx)
                                st.session_state["confirm_delete_soutirage"] = None
                                st.success("Point supprimé")
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"delete_s_{idx}", help="Supprimer", use_container_width=True):
                                st.session_state["confirm_delete_soutirage"] = idx
                                st.rerun()
                
                # Show confirmation message
                if st.session_state["confirm_delete_soutirage"] == idx:
                    st.warning(f"⚠️ Cliquez sur ✓ pour confirmer la suppression de '{point['nom']}'")
                
                # Add separator between rows
                if idx < len(points) - 1:
                    st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
        else:
            st.info("Aucun point de soutirage configuré. Ajoutez-en un ci-dessous.")

        st.divider()

        # Section 2: Add form (simple form with direct curve display)
        st.subheader("Ajouter un point de soutirage")
        
        # Initialize form state if needed
        if "sout_form_state" not in st.session_state:
            st.session_state["sout_form_state"] = {
                "nom": "", "segment": "", "tarif_reference": 0.0,
                "apply_tva": False, "structure_tarifaire": "Base",
                "aci": False, "aci_partenaire": "Aucun",
                "tarif_complement": 0.0, "adresse": "",
                "curve_data": None, "coords": None
            }
        
        state = st.session_state["sout_form_state"]
        
        # Input form
        col1, col2, col3 = st.columns(3)
        
        with col1:
            state["nom"] = st.text_input("Nom *", value=state["nom"], placeholder="Bâtiment municipal")
            state["segment"] = st.text_input("Segment", value=state["segment"], placeholder="C5")
            state["adresse"] = st.text_input("Adresse *", value=state["adresse"], placeholder="123 Rue de la Ville, 75001 Paris")
        
        with col2:
            state["tarif_reference"] = st.number_input("Tarif d'achat de référence (c€/kWh)", min_value=0.0, step=0.01, value=state["tarif_reference"], format="%.2f")
            state["apply_tva"] = st.checkbox("Récupération de TVA", value=state["apply_tva"])
            state["structure_tarifaire"] = st.selectbox("Structure tarifaire", ["Base", "Heures pleines / Heures creuses", "4 quadrants"], 
                                                        index=["Base", "Heures pleines / Heures creuses", "4 quadrants"].index(state["structure_tarifaire"]))
        
        with col3:
            state["aci"] = st.checkbox("Contrat ACI", value=state["aci"])
            # Get list of injection points for ACI partner dropdown
            injection_points = st.session_state.get("points_injection", [])
            injection_names = [p["nom"] for p in injection_points]
            state["aci_partenaire"] = st.selectbox("Partenaire ACI", ["Aucun"] + injection_names, 
                                                   index=(["Aucun"] + injection_names).index(state["aci_partenaire"]),
                                                   disabled=not state["aci"])
            state["tarif_complement"] = st.number_input("Tarif de complément (c€/kWh)", min_value=0.0, step=0.01, value=state["tarif_complement"], format="%.2f")
        
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
                    standardizer = CurveStandardizer(prm_id=state.get("nom", "temp"))
                    result = standardizer.process(state["curve_data"])
                    
                    if result['success'] and standardizer.parsed_df is not None and len(standardizer.parsed_df) > 0:
                        norm_df = standardizer.parsed_df
                        st.line_chart(norm_df, use_container_width=True, height=300)
                        st.caption(f"Colonnes: {', '.join(norm_df.columns.astype(str))} — Lignes: {len(norm_df)}")
                        
                        # Calculer le volume consommé
                        if 'value' in norm_df.columns:
                            volume_total = norm_df['value'].sum()
                            volume_mwh = volume_total / 1000.0  # Conversion kWh -> MWh
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
                if not state["nom"] or not state["adresse"]:
                    st.error("⚠️ Les champs Nom et Adresse sont obligatoires")
                elif state["curve_data"] is None:
                    st.error("⚠️ Une courbe de consommation est obligatoire")
                else:
                    # Get coordinates if not already done
                    if not state["coords"]:
                        coords = get_coordinates_from_address(state["adresse"])
                        if coords and coords.get("lat") and coords.get("lng"):
                            state["coords"] = coords
                        else:
                            st.error("⚠️ Impossible de géolocaliser l'adresse")
                            state["coords"] = None
                    
                    if state["coords"]:
                        # Create and add point
                        new_point = {
                            "nom": state["nom"],
                            "segment": state["segment"],
                            "tarif_reference": state["tarif_reference"],
                            "aci": state["aci"],
                            "aci_partenaire": state["aci_partenaire"] if state["aci"] else "Aucun",
                            "tva": state["apply_tva"],
                            "structure_tarifaire": state["structure_tarifaire"],
                            "tarif_complement": state["tarif_complement"],
                            "adresse": state["adresse"],
                            "courbe_consommation": state["curve_data"],
                            "lat": state["coords"]["lat"],
                            "lng": state["coords"]["lng"]
                        }
                        st.session_state["points_soutirage"].append(new_point)
                        st.success(f"✅ Point '{state['nom']}' ajouté avec succès!")
                        
                        # Reset form state
                        st.session_state["sout_form_state"] = {
                            "nom": "", "segment": "", "tarif_reference": 0.0,
                            "apply_tva": False, "structure_tarifaire": "Base",
                            "aci": False, "aci_partenaire": "Aucun",
                            "tarif_complement": 0.0, "adresse": "",
                            "curve_data": None, "coords": None
                        }
                        st.rerun()
        
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state["sout_form_state"] = {
                    "nom": "", "segment": "", "tarif_reference": 0.0,
                    "apply_tva": False, "structure_tarifaire": "Base",
                    "aci": False, "aci_partenaire": "Aucun",
                    "tarif_complement": 0.0, "adresse": "",
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
            with col_legend1:
                st.metric("Points d'injection", len(points_injection))
            with col_legend2:
                st.metric("Points de soutirage", len(points_soutirage))
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
