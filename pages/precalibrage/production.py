
import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
from utils.helpers import get_coordinates_from_postal_code
from services.geolocation import get_coordinates_from_address
from services.pvgis import compute_pv_curve
from services.curve_processing import process_curve
from services.curve_processing.alignment import align_curve_to_reference_year, CalendarAlignmentError, find_max_common_calendar_range
import html
import re
import logging
from geopy.distance import geodesic
from services.database import save_dataset, list_datasets, load_dataset

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


def normalize_curve_df(df: pd.DataFrame) -> pd.DataFrame | None:
    """Normalize an uploaded or modeled curve DataFrame for plotting.

    - Tries to set a datetime index if a suitable column exists
    - Selects numeric columns and drops all-null columns
    - Sorts by datetime index when present
    Returns a numeric DataFrame or None if unusable.
    """
    try:
        if df is None:
            return None
        df = df.copy()
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Ensure datetime index if possible
        if not isinstance(df.index, pd.DatetimeIndex):
            datetime_col = None
            for c in df.columns:
                lc = c.lower()
                if ("date" in lc) or ("time" in lc) or ("horodate" in lc) or ("datetime" in lc):
                    datetime_col = c
                    break
            if datetime_col is None and len(df.columns) > 0:
                c0 = df.columns[0]
                try:
                    dt_try = pd.to_datetime(df[c0], errors="raise")
                    datetime_col = c0
                except Exception:
                    datetime_col = None
            if datetime_col:
                try:
                    dt = pd.to_datetime(df[datetime_col], errors="coerce")
                    mask = dt.notna()
                    df = df.loc[mask]
                    df.index = dt[mask]
                    # Drop the original datetime column if we used it
                    if datetime_col in df.columns:
                        df = df.drop(columns=[datetime_col])
                except Exception:
                    pass

        # Sort if datetime index
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        # Prefer known PV column then fallback to numeric selection
        if "P_ac_kW" in df.columns:
            df["P_ac_kW"] = pd.to_numeric(df["P_ac_kW"], errors="coerce")

        num_df = df.select_dtypes(include=["number"]).dropna(how="all")
        if num_df.empty:
            # Try coercing common columns
            for candidate in ["W", "kW", "kWh", "P_ac_kW"]:
                if candidate in df.columns:
                    df[candidate] = pd.to_numeric(df[candidate], errors="coerce")
            num_df = df.select_dtypes(include=["number"]).dropna(how="all")

        if num_df.empty:
            return None
        return num_df
    except Exception:
        return None


def render():
    """Render the Points d'injection page with two-tab structure."""
    st.title("Points d'injection")

    # Initialize injection points list if not exists
    if "points_injection" not in st.session_state:
        st.session_state["points_injection"] = []

    # Ensure edit state keys exist to avoid KeyError when accessed later
    if "edit_injection_idx" not in st.session_state:
        st.session_state["edit_injection_idx"] = None
    if "edit_injection_form" not in st.session_state:
        st.session_state["edit_injection_form"] = None
    # Create two tabs
    tab1, tab2 = st.tabs(["📊 Gestion des points", "🗺️ Vérification des contraintes"])

    with tab1:
        # Full-width layout: Table + Form (no map)
        st.subheader("Points d'injection")
        
        points = st.session_state["points_injection"]
        
        # Initialize form and confirmation states if not exists
        if "confirm_delete_injection" not in st.session_state:
            st.session_state["confirm_delete_injection"] = None
        if "edit_injection_idx" not in st.session_state:
            st.session_state["edit_injection_idx"] = None
        if "edit_injection_form" not in st.session_state:
            st.session_state["edit_injection_form"] = None
        
        # Section 1: Custom HTML table with action buttons
        if len(points) > 0:
            # Custom CSS for fixed table layout
            st.markdown("""
            <style>
            .injection-table {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                background-color: transparent;
            }
            .injection-table th {
                background-color: rgba(240, 242, 246, 0.1);
                padding: 10px 8px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid rgba(128, 128, 128, 0.3);
                font-size: 14px;
            }
            .injection-table td {
                padding: 12px 8px;
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
                font-size: 14px;
            }
            .injection-table tr:hover {
                background-color: rgba(128, 128, 128, 0.1);
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Table header
            table_html = """
            <table class="injection-table">
                <thead>
                    <tr>
                        <th style="width: 8%;">Actif</th>
                        <th style="width: 15%;">Nom</th>
                        <th style="width: 10%;">Type</th>
                        <th style="width: 20%;">Segment</th>
                        <th style="width: 20%;">Puissance (kW)</th>
                        <th style="width: 20%;">Actions</th>
                    </tr>
                </thead>
            </table>
            """
            st.markdown(table_html, unsafe_allow_html=True)
            
            # Display each point with action buttons
            for idx, point in enumerate(points):
                highlight = (st.session_state["edit_injection_idx"] == idx)
                is_active = point.get("active", True)
                
                if highlight:
                    row_style = "background-color:#e3f0ff; color:#1565c0; font-weight:bold; border-radius:6px;"
                elif not is_active:
                    row_style = "color:#9e9e9e; text-decoration: line-through; opacity: 0.6;"
                else:
                    row_style = ""
                    
                cols = st.columns([0.08, 0.15, 0.10, 0.10, 0.12, 0.10, 0.15, 0.20])
                with cols[0]:
                    if f"active_inj_{idx}" not in st.session_state:
                        st.session_state[f"active_inj_{idx}"] = is_active
                    new_active = st.checkbox("Actif", key=f"active_inj_{idx}", label_visibility="collapsed")
                    if new_active != is_active:
                        st.session_state["points_injection"][idx]["active"] = new_active
                        if st.session_state.get("project_id"):
                            from services.database import save_project
                            from services.state_serializer import serialize_state
                            save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                        st.rerun()
                with cols[1]:
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{point['nom']}</div>", unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{point['type']}</div>", unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{point['segment']}</div>", unsafe_allow_html=True)
                with cols[4]:
                    st.markdown(f"<div style='padding: 4px 0; {row_style}'>{int(point['puissance'])}</div>", unsafe_allow_html=True)
                with cols[7]:
                    action_cols = st.columns([1, 1, 1], gap="small")
                    with action_cols[0]:
                        if st.button("✏️", key=f"edit_{idx}", help="Modifier", use_container_width=True):
                            st.session_state["edit_injection_idx"] = idx
                            st.session_state["edit_injection_form"] = point.copy()
                            st.rerun()
                    with action_cols[1]:
                        if st.button("📋", key=f"dup_{idx}", help="Dupliquer", use_container_width=True):
                            duplicated_point = point.copy()
                            duplicated_point["nom"] = f"{point['nom']} (copie)"
                            st.session_state["points_injection"].append(duplicated_point)
                            if st.session_state.get("project_id"):
                                from services.database import save_project
                                from services.state_serializer import serialize_state
                                save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                            st.success(f"✅ Point '{point['nom']}' dupliqué!")
                            st.rerun()
                    with action_cols[2]:
                        if st.session_state["confirm_delete_injection"] == idx:
                            if st.button("✓", key=f"confirm_{idx}", help="Confirmer la suppression", use_container_width=True):
                                st.session_state["points_injection"].pop(idx)
                                st.session_state["confirm_delete_injection"] = None
                                if st.session_state.get("project_id"):
                                    from services.database import save_project
                                    from services.state_serializer import serialize_state
                                    save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                                st.success("Point supprimé")
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"delete_{idx}", help="Supprimer", use_container_width=True):
                                st.session_state["confirm_delete_injection"] = idx
                                st.rerun()
                if st.session_state["confirm_delete_injection"] == idx:
                    st.warning(f"⚠️ Cliquez sur ✓ pour confirmer la suppression de '{point['nom']}'")
                if idx < len(points) - 1:
                    st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

            # Formulaire de modification si une ligne est sélectionnée
            if st.session_state["edit_injection_idx"] is not None and st.session_state["edit_injection_form"] is not None:
                st.markdown("---")
                st.subheader("Modifier le point d'injection")
                edit_state = st.session_state["edit_injection_form"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    edit_state["nom"] = st.text_input("Nom *", value=edit_state["nom"], key="edit_nom")
                    edit_state["type"] = st.selectbox("Type", ["Solaire", "Éolien"], index=["Solaire", "Éolien"].index(edit_state["type"]) if edit_state["type"] in ["Solaire", "Éolien"] else 0, key="edit_type")
                    segment_options = ["C2", "C3", "C4", "C5"]
                with col2:
                    edit_state["puissance"] = st.number_input("Puissance (kW)", min_value=0, step=1, value=edit_state["puissance"], format="%d", key="edit_puissance")
                    edit_state["segment"] = st.selectbox("Segment", segment_options, index=segment_options.index(edit_state["segment"]) if edit_state["segment"] in segment_options else 2, key="edit_segment")
                    # edit_state["tva"] = st.checkbox("Récupération de TVA", value=edit_state.get("tva", False), key="edit_tva")
                    # edit_state["valorisation"] = st.number_input("Valorisation (cEUR/kWh)", min_value=0.0, step=0.01, value=edit_state["valorisation"], format="%.2f", key="edit_valorisation")
                with col3:
                    edit_state["adresse"] = st.text_input("Adresse", value=edit_state["adresse"], key="edit_adresse")
                    
                    # Auto-géolocalisation si adresse remplie et changée
                    if edit_state["adresse"] and edit_state["adresse"] != edit_state.get("last_geocoded_address", ""):
                        with st.spinner("Géolocalisation..."):
                            coords = get_coordinates_from_address(edit_state["adresse"])
                            if coords and coords.get("lat") and coords.get("lng"):
                                edit_state["coords"] = coords
                                edit_state["manual_lat"] = coords["lat"]
                                edit_state["manual_lng"] = coords["lng"]
                                # Mettre à jour les widgets directement
                                st.session_state["edit_inj_lat"] = coords["lat"]
                                st.session_state["edit_inj_lng"] = coords["lng"]
                                edit_state["last_geocoded_address"] = edit_state["adresse"]
                    
                    # Initialiser les coordonnées manuelles si nécessaire
                    if "manual_lat" not in edit_state:
                        edit_state["manual_lat"] = (edit_state.get("coords") or {}).get("lat", 0.0)
                    if "manual_lng" not in edit_state:
                        edit_state["manual_lng"] = (edit_state.get("coords") or {}).get("lng", 0.0)
                    
                    # Initialiser les widgets dans session_state pour éviter le warning
                    if "edit_inj_lat" not in st.session_state:
                        st.session_state["edit_inj_lat"] = float(edit_state["manual_lat"])
                    if "edit_inj_lng" not in st.session_state:
                        st.session_state["edit_inj_lng"] = float(edit_state["manual_lng"])
                    
                    # Afficher lat/lon éditables
                    col_lat_edit, col_lng_edit = st.columns(2)
                    with col_lat_edit:
                        edit_state["manual_lat"] = st.number_input(
                            "Latitude", 
                            format="%.6f",
                            step=0.001,
                            key="edit_inj_lat"
                        )
                    with col_lng_edit:
                        edit_state["manual_lng"] = st.number_input(
                            "Longitude", 
                            format="%.6f",
                            step=0.001,
                            key="edit_inj_lng"
                        )
                    
                    # Mettre à jour coords avec les valeurs manuelles
                    if edit_state["manual_lat"] != 0.0 or edit_state["manual_lng"] != 0.0:
                        edit_state["coords"] = {"lat": edit_state["manual_lat"], "lng": edit_state["manual_lng"]}
                
                # --- Gestion de la courbe de production dans l'édition ---
                st.markdown("---")
                st.markdown("**Courbe de production**")
                
                # Extract the actual dataframe or data dictionary from the 'courbe_production' wrapper structure if it exists
                current_curve_source = edit_state.get("courbe_production")
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
                    
                    if st.button("🗑️ Supprimer et remplacer cette courbe", key="delete_curve_injection"):
                        # Remove the curve to expose the uploader
                        edit_state["courbe_production"] = None
                        edit_state["curve_data"] = None 
                        st.session_state["points_injection"][st.session_state["edit_injection_idx"]] = edit_state
                        st.rerun()
                else:
                    # Provide the uploader logic exactly as in the add section if no curve is present
                    sources = ["Aucune", "Téléverser XLS", "Modéliser via PVGIS"]
                    # If editing, we might need a distinct state for the edit form's upload selections
                    edit_source = st.radio("Source de la nouvelle courbe", sources, index=0, key="edit_source_radio")
                    
                    if edit_source == "Téléverser XLS":
                        uploaded_file = st.file_uploader("Charger CSV/XLS/XLSX", type=["csv", "xls", "xlsx"], key="edit_upload_xls")
                        if uploaded_file:
                            try:
                                name = uploaded_file.name.lower()
                                if name.endswith(".csv"):
                                    curve_df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8-sig")
                                    curve_df.columns = [str(col).strip().lstrip("\ufeff") for col in curve_df.columns]
                                else:
                                    curve_df = pd.read_excel(uploaded_file)
                                edit_state["curve_data"] = curve_df

                                print(curve_df.head())
                                st.success("✅ Fichier chargé, prêt à être enregistré.")
                            except Exception as e:
                                st.error(f"⚠️ Erreur lecture fichier: {e}")
                                edit_state["curve_data"] = None
                                
                    elif edit_source == "Modéliser via PVGIS":
                        col_pv1, col_pv2, col_pv3 = st.columns(3)
                        with col_pv1:
                            tilt = st.number_input("Inclinaison (°)", min_value=0.0, max_value=90.0, step=1.0, value=30.0, format="%.0f", key="edit_pv_tilt")
                        with col_pv2:
                            azimuth = st.number_input("Azimut (°)", min_value=0.0, max_value=360.0, step=1.0, value=0.0, format="%.0f", key="edit_pv_az")
                        with col_pv3:
                            losses = st.number_input("Pertes système (%)", min_value=0.0, max_value=50.0, step=0.5, value=14.0, format="%.1f", key="edit_pv_loss")
                            
                        # Need dates
                        start_date = st.session_state.get("start_date")
                        end_date = st.session_state.get("end_date")
                        
                        if st.button("� Générer courbe PVGIS", key="edit_gen_pv", use_container_width=True):
                            if not edit_state["nom"] or not edit_state["adresse"] or edit_state["puissance"] <= 0:
                                st.error("⚠️ Remplissez Nom, Adresse et Puissance d'abord")
                            elif not start_date or not end_date:
                                st.error("⚠️ Configurez les dates dans 'Infos générales' d'abord")
                            else:
                                with st.spinner("Génération..."):
                                    coords = get_coordinates_from_address(edit_state["adresse"])
                                    if coords:
                                        curve = compute_pv_curve(
                                            lat=coords["lat"], lon=coords["lng"], peakpower_kw=float(edit_state["puissance"]),
                                            tilt_deg=float(tilt), azimuth_deg=float(azimuth), losses_pct=float(losses),
                                            start_date=start_date, end_date=end_date
                                        )
                                        if curve is not None:
                                            # Multiplier par 1000 pour convertir kW en W
                                            curve['P_ac_kW'] = curve['P_ac_kW'] * 1000
                                            curve.reset_index(inplace=True)
                                            curve.rename(columns={"index": "datetime"}, inplace=True)
                                            curve.rename(columns={"P_ac_kW": "value"}, inplace=True)
                                            edit_state["curve_data"] = curve
                                            st.success("✅ Courbe PVGIS générée, prête à être enregistrée.")
                                        else:
                                            st.error("⚠️ Erreur PVGIS")
                                    else:
                                        st.error("⚠️ Impossible de géolocaliser")

                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Boutons Enregistrer et Annuler ---
                if st.button("�💾 Enregistrer les modifications", key="save_edit_injection", type="primary"):
                    # If we added a new curve_data in the edit form, process it and replace the formal wrapper
                    if not has_curve and edit_state.get("curve_data") is not None:
                        processed = None
                        try:
                            curve_df = edit_state["curve_data"].copy()
                            processed = process_curve(curve_df)
                        except Exception as e:
                            st.error(f"Erreur traitement: {e}")
                        
                        edit_state["courbe_production"] = (
                            {"df": processed.get("df"), "metadata": processed.get("metadata"), "impute_report": processed.get("impute_report")}
                            if processed and processed.get("success") else edit_state["curve_data"]
                        )
                        
                        # Trigger db auto-save for the raw dataset if attached to a project
                        project_id = st.session_state.get("project_id")
                        if project_id:
                            try:
                                save_dataset(
                                    project_id=project_id,
                                    name=f"{edit_state['nom']}_curve.json",
                                    type="production_curve",
                                    data=edit_state["curve_data"],
                                    metadata={"source_type": edit_source, "original_name": edit_state["nom"], "address": edit_state["adresse"]},
                                )
                            except Exception as e:
                                st.error(f"Erreur DB dataset: {e}")
                    
                    # Ensure we drop the raw curve_data key from st.session_state representation
                    if "curve_data" in edit_state:
                         del edit_state["curve_data"]
                         
                    st.session_state["points_injection"][st.session_state["edit_injection_idx"]] = edit_state.copy()
                    if st.session_state.get("project_id"):
                        from services.database import save_project
                        from services.state_serializer import serialize_state
                        save_project(st.session_state["project_name"], "precalibrage", serialize_state(dict(st.session_state)), st.session_state["project_id"])
                    st.success(f"✅ Point '{edit_state['nom']}' modifié avec succès!")
                    st.session_state["edit_injection_idx"] = None
                    st.session_state["edit_injection_form"] = None
                    st.rerun()
                if st.button("❌ Annuler", key="cancel_edit_injection"):
                    st.session_state["edit_injection_idx"] = None
                    st.session_state["edit_injection_form"] = None
                    st.rerun()
        else:
            st.info("Aucun point d'injection configuré. Ajoutez-en un ci-dessous.")

        st.divider()

        # Section 2: Add form (simple form with direct curve display)
                
                # Section 2: Add form (simple form with direct curve display)
        # Masquer le formulaire d'ajout pendant l'édition
        if st.session_state["edit_injection_idx"] is None:
            st.subheader("Ajouter un point d'injection")

            # Initialize form state if needed
            if "inj_form_state" not in st.session_state:
                st.session_state["inj_form_state"] = {
                    "nom": "",
                    "type": "Solaire",
                    "segment": "C4",
                    "puissance": 0,
                    "apply_tva": False,
                    "valorisation": 0.0,
                    "adresse": "",
                    "source": "Aucune",
                    "curve_data": None,
                    "coords": None,
                    "last_pvgis_params": "",
                }

            state = st.session_state["inj_form_state"]

            col1, col2, col3 = st.columns(3)
            with col1:
                state["nom"] = st.text_input("Nom *", value=state["nom"], placeholder="Centrale PV Nord")
                state["type"] = st.selectbox(
                    "Type",
                    ["Solaire", "Éolien"],
                    index=["Solaire", "Éolien"].index(state["type"]) if state["type"] in ["Solaire", "Éolien"] else 0,
                )
                segment_options = ["C2", "C3", "C4", "C5"]
                # state["segment"] = st.selectbox(
                #     "Segment",
                #     segment_options,
                #     index=segment_options.index(state["segment"]) if state["segment"] in segment_options else 2,
                # )

            with col2:
                state["puissance"] = st.number_input(
                    "Puissance (kW)", min_value=0, step=1, value=int(state["puissance"]), format="%d"
                )
                state["segment"] = st.selectbox(
                    "Segment",
                    segment_options,
                    index=segment_options.index(state["segment"]) if state["segment"] in segment_options else 2,
                )
                # state["apply_tva"] = st.checkbox("Récupération de TVA", value=bool(state["apply_tva"]))
                # state["valorisation"] = st.number_input(
                #     "Valorisation (cEUR/kWh)", min_value=0.0, step=0.01, value=float(state["valorisation"]), format="%.2f"
                # )

            with col3:
                state["adresse"] = st.text_input(
                    "Adresse", value=state["adresse"], placeholder="123 Rue de la Production, 75001 Paris"
                )
                
                # Auto-géolocalisation si adresse remplie
                if state["adresse"] and state["adresse"] != state.get("last_geocoded_address", ""):
                    with st.spinner("Géolocalisation..."):
                        coords = get_coordinates_from_address(state["adresse"])
                        if coords and coords.get("lat") and coords.get("lng"):
                            state["coords"] = coords
                            state["manual_lat"] = coords["lat"]
                            state["manual_lng"] = coords["lng"]
                            # Mettre à jour les widgets directement
                            st.session_state["inj_lat"] = coords["lat"]
                            st.session_state["inj_lng"] = coords["lng"]
                            state["last_geocoded_address"] = state["adresse"]
                        else:
                            st.warning("⚠️ Géolocalisation impossible pour cette adresse")
                
                # Initialiser les coordonnées manuelles si nécessaire
                if "manual_lat" not in state:
                    state["manual_lat"] = (state.get("coords") or {}).get("lat", 0.0)
                if "manual_lng" not in state:
                    state["manual_lng"] = (state.get("coords") or {}).get("lng", 0.0)
                
                # Initialiser les widgets dans session_state pour éviter le warning
                if "inj_lat" not in st.session_state:
                    st.session_state["inj_lat"] = float(state["manual_lat"])
                if "inj_lng" not in st.session_state:
                    st.session_state["inj_lng"] = float(state["manual_lng"])
                
                # Afficher lat/lon éditables
                col_lat, col_lng = st.columns(2)
                with col_lat:
                    state["manual_lat"] = st.number_input(
                        "Latitude", 
                        format="%.6f",
                        step=0.001,
                        key="inj_lat"
                    )
                with col_lng:
                    state["manual_lng"] = st.number_input(
                        "Longitude", 
                        format="%.6f",
                        step=0.001,
                        key="inj_lng"
                    )
                
                # Mettre à jour coords avec les valeurs manuelles
                if state["manual_lat"] != 0.0 or state["manual_lng"] != 0.0:
                    state["coords"] = {"lat": state["manual_lat"], "lng": state["manual_lng"]}
                
                sources = ["Aucune", "Téléverser XLS", "Modéliser via PVGIS"]
                state["source"] = st.radio(
                    "Source de la courbe de production",
                    sources,
                    index=sources.index(state["source"]) if state["source"] in sources else 0,
                )

            st.markdown("**Courbe de production**")
            col_curve1, col_curve2 = st.columns([1, 1])

            # -------------------------
            # Colonne gauche : acquisition de la courbe
            # -------------------------
            with col_curve1:
                if state["source"] == "Téléverser XLS":
                    uploaded_file = st.file_uploader(
                        "Charger CSV/XLS/XLSX",
                        type=["csv", "xls", "xlsx"],
                        key="upload_xls_inj",
                    )
                    if uploaded_file:
                        try:
                            name = uploaded_file.name.lower()
                            if name.endswith(".csv"):
                                curve_df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8-sig")
                                curve_df.columns = [str(col).strip().lstrip("\ufeff") for col in curve_df.columns]
                            else:
                                curve_df = pd.read_excel(uploaded_file)

                            state["curve_data"] = curve_df
                            st.success("✅ Fichier chargé")
                        except Exception as e:
                            st.error(f"⚠️ Erreur lecture fichier: {e}")
                            state["curve_data"] = None

                elif state["source"] == "Modéliser via PVGIS":
                    tilt = st.number_input("Inclinaison (°)", min_value=0.0, max_value=90.0, step=1.0, value=30.0, format="%.0f")
                    azimuth = st.number_input("Azimut (°)", min_value=0.0, max_value=360.0, step=1.0, value=0.0, format="%.0f")
                    losses = st.number_input("Pertes système (%)", min_value=0.0, max_value=50.0, step=0.5, value=14.0, format="%.1f")

                    # Utiliser l'année de référence si aucune période n'est configurée

                    # Forcer systématiquement la période PVGIS à l'année de référence
                    reference_year = st.session_state.get("reference_year")
                    import datetime
                    if reference_year is not None:
                        start_date = datetime.date(int(reference_year), 1, 1)
                        end_date = datetime.date(int(reference_year), 12, 31)
                    else:
                        start_date = datetime.date(datetime.datetime.now().year, 1, 1)
                        end_date = datetime.date(datetime.datetime.now().year, 12, 31)


                    import datetime
                    def to_date(val):
                        if isinstance(val, str):
                            try:
                                return datetime.datetime.strptime(val, "%Y-%m-%d").date()
                            except Exception:
                                return datetime.datetime.strptime(val, "%Y-%m-%d %H:%M:%S").date()
                        elif isinstance(val, datetime.datetime):
                            return val.date()
                        return val

                    if start_date and end_date:
                        # Ensure dates are valid
                        if hasattr(start_date, 'strftime'):
                            duration_days = (end_date - start_date).days
                            st.info(f"📅 Période configurée : {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')} ({duration_days} jours)")
                        else:
                            st.warning(f"⚠️ Dates invalides : start={start_date}, end={end_date}")
                    else:
                        st.warning("⚠️ Configurez les dates dans 'Infos générales' d'abord (start_date et end_date)")

                    current_params = f"{state['adresse']}_{state['puissance']}_{tilt}_{azimuth}_{losses}_{start_date}_{end_date}"
                    last_params = state.get("last_pvgis_params", "")

                    if state["curve_data"] is not None and current_params != last_params:
                        st.warning("⚠️ Les paramètres ont changé. Cliquez sur 'Générer' pour recalculer la courbe.")

                    if st.button("🔄 Générer courbe PVGIS", use_container_width=True):
                        if not state["nom"] or state["puissance"] <= 0:
                            st.error("⚠️ Remplissez Nom et Puissance d'abord")
                        elif not state.get("coords") or not state["coords"].get("lat") or not state["coords"].get("lng"):
                            st.error("⚠️ Coordonnées GPS manquantes. Remplissez l'adresse ou saisissez la latitude/longitude")
                        elif not start_date or not end_date:
                            st.error("⚠️ Configurez les dates dans 'Infos générales' d'abord")
                        elif start_date >= end_date:
                            st.error(f"⚠️ Date de début ({start_date}) doit être antérieure à date de fin ({end_date})")
                        elif start_date >= end_date:
                            st.error(f"⚠️ Date de début ({start_date}) doit être antérieure à date de fin ({end_date})")
                        else:
                            with st.spinner("Génération de la courbe PVGIS en cours..."):
                                coords = state["coords"]
                                curve = compute_pv_curve(
                                    lat=coords["lat"],
                                    lon=coords["lng"],
                                    peakpower_kw=float(state["puissance"]),
                                    tilt_deg=float(tilt),
                                    azimuth_deg=float(azimuth),
                                    losses_pct=float(losses),
                                    start_date=start_date,
                                    end_date=end_date,
                                )
                                if curve is not None:
                                    # Multiplier par 1000 pour convertir kW en W
                                    curve['P_ac_kW'] = curve['P_ac_kW'] * 1000
                                    curve.reset_index(inplace=True)
                                    curve.rename(columns={'index': 'datemine'}, inplace=True)
                                    curve.rename(columns={'P_ac_kW': 'value'}, inplace=True)
                                    # curve = curve.iloc[1:]
                                    state["curve_data"] = curve
                                    state["last_pvgis_params"] = current_params
                                    duration_days = (end_date - start_date).days
                                    st.success(f"✅ Courbe PVGIS générée : {len(curve)} heures ({duration_days} jours)")
                                    st.rerun()
                                else:
                                    st.error("⚠️ Erreur génération courbe PVGIS")
                                    state["curve_data"] = None



            # -------------------------
            # Colonne droite : aperçu & sauvegarde
            # -------------------------
            with col_curve2:
                if state.get("curve_data") is not None:
                    st.markdown("**📊 Aperçu**")
                    try:
                        curve_df = state["curve_data"].copy()
                        result = process_curve(curve_df) 

                        print("Result from process_curve:", result)  # Debug log
                        if result.get("success") and result.get("df") is not None and len(result["df"]) > 0:
                            norm_df = result["df"]

                            if "value" in norm_df.columns:
                                st.line_chart(norm_df["value"], use_container_width=True, height=300)
                            else:
                                st.line_chart(norm_df, use_container_width=True, height=300)

                            st.caption(f"Colonnes: {', '.join(norm_df.columns.astype(str))} — Lignes: {len(norm_df)}")

                            if "value" in norm_df.columns:
                                volume_total = float(norm_df["value"].sum())
                                volume_mwh = volume_total / 1000.0
                                st.metric("Volume produit estimé", f"{volume_mwh:.2f} MWh", help=f"{volume_total:.0f} kWh sur la période")


                        else:
                            st.warning("⚠️ Courbe non exploitable pour l'affichage.")
                            if result.get("errors"):
                                st.error(f"Erreurs: {result['errors']}")
                            validation = result.get("validation") or {}
                            if validation.get("errors"):
                                st.error(f"Validation: {validation['errors']}")
                    except Exception as e:
                        st.warning(f"⚠️ Erreur lors de la normalisation: {e}")
                else:
                    if state.get("source") != "Aucune":
                        st.info("↖️ Configurez et générez/téléversez la courbe pour voir l'aperçu")
        else:
            st.info("✏️ Mode édition actif : le formulaire d'ajout est masqué.")

        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        
        with col_btn1:
            if st.button("✅ Valider et ajouter le point", use_container_width=True, type="primary"):
                # Validate all required fields
                if not state["nom"]:
                    st.error("⚠️ Le champ Nom est obligatoire")
                elif state["source"] != "Aucune" and state["curve_data"] is None:
                    st.error("⚠️ Une courbe est requise pour ce point")
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
                            if state.get("curve_data") is not None:
                                curve_df = state["curve_data"].copy()
                                processed = process_curve(curve_df)
                            else:
                                processed = None
                        except Exception as e:
                            st.error(f"Erreur traitement courbe: {e}")

                        # Create and add point (store processed result for aggregation)
                        new_point = {
                            "nom": state["nom"],
                            "type": state["type"],
                            "segment": state["segment"],
                            "puissance": state["puissance"],
                            "tva": state["apply_tva"],
                            "valorisation": state["valorisation"],
                            "adresse": state["adresse"],
                            "hypothetical": False,
                            "active": True,
                            "courbe_production": (
                                {"df": processed.get("df"), "metadata": processed.get("metadata"), "impute_report": processed.get("impute_report")} 
                                if processed and processed.get("success") else state.get("curve_data")
                            ),
                            "lat": state["coords"]["lat"],
                            "lng": state["coords"]["lng"]
                        }
                        st.session_state["points_injection"].append(new_point)
                        
                        # Auto-save Dataset
                        project_id = st.session_state.get("project_id")
                        if project_id and state.get("curve_data") is not None:
                            try:
                                save_dataset(
                                    project_id=project_id,
                                    name=f"{state['nom']}_curve.json",
                                    type="production_curve",
                                    data=state["curve_data"],
                                    metadata={"source_type": state["source"], "original_name": state["nom"], "address": state["adresse"]},
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
                        st.session_state["inj_form_state"] = {
                            "nom": "", "type": "Solaire", "segment": "C4",
                            "puissance": 0, "apply_tva": False, "valorisation": 0.0,
                            "adresse": "", "source": "Aucune",
                            "curve_data": None, "coords": None
                        }
                        st.rerun()
        
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state["inj_form_state"] = {
                    "nom": "", "type": "Solaire", "segment": "C4",
                    "puissance": 0, "apply_tva": False, "valorisation": 0.0,
                    "adresse": "", "source": "Aucune",
                    "curve_data": None, "coords": None
                }
                st.rerun()

    with tab2:
        st.subheader("Vérification des contraintes de distance")

        points = st.session_state["points_injection"]

        def _has_valid_curve(p):
            """Retourne True si le point a une courbe avec au moins 8736h consécutives."""
            courbe = p.get("courbe_production")
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
            full_range = pd.date_range(start=df_sorted.index.min(), end=df_sorted.index.max(), freq='H')
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

        if len(points) == 0:
            st.info("Aucun point d'injection à afficher. Ajoutez des points dans l'onglet 'Gestion des points'.")
        else:
            col_legend1, col_legend2, col_legend3 = st.columns(3)
            with col_legend1:
                active_valid_count = sum(
                    1 for p in points if p.get("active", True) and _has_valid_curve(p)
                )
                st.metric("Points d'injection", active_valid_count)
            with col_legend2:
                distance_constraint_str = st.session_state.get("distance_constraint", "2 km")
                st.metric("Contrainte de distance", distance_constraint_str)
            with col_legend3:
                postal_code = st.session_state.get("postal_code", "N/A")
                st.metric("Code postal centre", postal_code)

            st.divider()

            # Determine radius in km (EPCI deferred: show notice and fallback)
            distance_constraint_str = st.session_state.get("distance_constraint", "2 km")
            if isinstance(distance_constraint_str, str) and distance_constraint_str.strip().upper() == "EPCI":
                st.warning("Mode EPCI non pris en charge pour l'instant — utilisation d'un rayon par défaut.")
            distance_km = extract_distance_km(distance_constraint_str)

            # Prepare points for centroid map (include extra metadata for richer popups/tooltips)
            points_for_map = [
                {
                    "name": p.get("nom", ""),
                    "lat": p.get("lat"),
                    "lon": p.get("lng"),
                    "type": p.get("type"),
                    "segment": p.get("segment"),
                    "puissance": int(p.get("puissance", 0)) if p.get("puissance") is not None else None,
                }
                for p in points
            ]

            # Build centroid circle map with inside/outside classification (guard invalid coords)
            valid_points = [pp for pp in points_for_map if pp["lat"] is not None and pp["lon"] is not None]
            
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

            # --- Création du DataFrame croisé producteurs (datetime en index, noms en colonnes, valeurs = production) ---

            try:
                dfs = []
                reference_year = st.session_state.get("reference_year")
                plages_valides = []
                noms_valides = []
                courbes_valides = []
                for p in points:
                    if p.get("active", True):
                        courbe = p.get("courbe_production")
                        nom = p.get("nom", "Producteur")
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
                        # pour que les heures supprimées à l'import (ex: 01/01 00:00) soient
                        # présentes dans l'index avec NaN, et non absentes.
                        src_year = df_sorted.index[0].year
                        src_is_leap = (src_year % 4 == 0 and (src_year % 100 != 0 or src_year % 400 == 0))
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
                # --- NOUVELLE LOGIQUE ---
                if courbes_valides:
                    if len(courbes_valides) == 1:
                        # Un seul producteur : pas d'intersection, juste alignement
                        nom = noms_valides[0]
                        df_full = courbes_valides[0]
                        # Forcer l'index en DatetimeIndex si besoin
                        if not isinstance(df_full.index, pd.DatetimeIndex):
                            try:
                                df_full.index = pd.to_datetime(df_full.index)
                            except Exception as e:
                                st.error(f"Impossible de convertir l'index en DatetimeIndex : {e}")
                                return
                        if reference_year is None:
                            reference_year = df_full.index[0].year
                            st.session_state["reference_year"] = reference_year

                        # Générer l'index cible pour l'année de référence, sans 29 février si bissextile
                        is_leap_ref = (reference_year % 4 == 0 and (reference_year % 100 != 0 or reference_year % 400 == 0))
                        target_index = pd.date_range(start=f"{reference_year}-01-01 00:00:00", end=f"{reference_year}-12-31 23:00:00", freq="H")
                        if is_leap_ref:
                            target_index = target_index[~((target_index.month == 2) & (target_index.day == 29))]

                        start = df_full.index.min()
                        if start.year == reference_year:
                            # Même année : reindex direct, pas d'alignement par semaine
                            df_aligned = df_full.reindex(target_index)
                        else:
                            # Année différente : alignement calendaire
                            try:
                                df_aligned = align_curve_to_reference_year(df_full, reference_year)
                                df_aligned = df_aligned.reindex(target_index)
                            except CalendarAlignmentError as err:
                                st.error(f"Erreur d'alignement calendaire pour {nom} : {err}")
                                df_prod = None
                                st.session_state["df_prod"] = df_prod
                                return
                        # Calculer les heures manquantes sur la courbe alignée
                        # Les valeurs manquantes sont les NaN de la courbe alignée sur l'index cible
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
                            # Si "Laisser manquant (NaN)", ne rien faire, les NaN restent affichés
                        df_named = df_crop[["value"]].rename(columns={"value": nom})
                        if not isinstance(df_named.index, pd.DatetimeIndex):
                            df_named.index = pd.to_datetime(df_named.index)
                        st.session_state["df_prod"] = df_named
                        if df_named is not None and not df_named.empty:
                            st.dataframe(df_named, use_container_width=True)
                            st.info(f"Année de référence pour l'alignement calendaire : {reference_year}")
                        else:
                            st.warning("⚠️ DataFrame vide après traitement.")
                    else:
                        # Plusieurs producteurs : intersection calendaire
                        best_start, best_end, mask_dict = find_max_common_calendar_range(courbes_valides)
                        if best_start is not None and best_end is not None:
                            reference_year = st.session_state.get("reference_year")
                            if reference_year is None:
                                reference_year = courbes_valides[0].index[0].year
                                st.session_state["reference_year"] = reference_year
                            for i, df_full in enumerate(courbes_valides):
                                nom = noms_valides[i]
                                mask = mask_dict[i]
                                df_crop = df_full[mask].copy()
                                missing_count = 8760 - len(df_crop)
                                missing_datetimes = []
                                if missing_count > 0:
                                    ref_year = reference_year
                                    target_index = pd.date_range(start=f"{ref_year}-01-01 00:00:00", end=f"{ref_year}-12-31 23:00:00", freq="H")
                                    df_crop = df_crop.copy()
                                    missing_datetimes = [dt for dt in target_index if dt not in df_crop.index]
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
                                    # Si "Laisser manquant (NaN)", ne rien faire
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
                                    df_prod = dfs[0]
                                    if df_prod.columns[0] != noms_valides[0]:
                                        df_prod.columns = [noms_valides[0]]
                                else:
                                    df_prod = pd.concat(dfs, axis=1)
                                st.session_state["df_prod"] = df_prod
                                if df_prod is not None and not df_prod.empty:
                                    st.dataframe(df_prod, use_container_width=True)
                                    st.info(f"Année de référence pour l'alignement calendaire : {reference_year}")
                                else:
                                    st.warning("⚠️ DataFrame vide après traitement.")
                            else:
                                st.warning("⚠️ Aucun point d'injection actif avec des données valides.")
                        else:
                            st.warning("⚠️ Pas de plage calendaire commune entre les courbes retenues.")
                else:
                    df_prod = None
                    st.session_state["df_prod"] = df_prod
                    st.warning("⚠️ Aucun point d'injection actif avec des données valides.")
            except Exception as e:
                # Reset du DataFrame dans le state
                df_prod = None  # vide
                st.session_state["df_prod"] = df_prod
                st.error(f"Erreur création DataFrame croisé producteurs : {e}")

        # Nettoyage : suppression des st.write() de debug
