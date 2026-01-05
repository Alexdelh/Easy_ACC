import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from utils.helpers import get_coordinates_from_postal_code
from services.geolocation import get_coordinates_from_address
from services.pvgis import compute_pv_curve
from services.curve_standardizer import CurveStandardizer
from functions import cercle, show_map_with_radius
import html
import re


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

    # Create two tabs
    tab1, tab2 = st.tabs(["📊 Gestion des points", "🗺️ Vérification des contraintes"])

    with tab1:
        # Full-width layout: Table + Form (no map)
        st.subheader("Points d'injection")
        
        points = st.session_state["points_injection"]
        
        # Initialize confirmation state if not exists
        if "confirm_delete_injection" not in st.session_state:
            st.session_state["confirm_delete_injection"] = None
        
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
                        <th style="width: 16%;">Nom</th>
                        <th style="width: 11%;">Type</th>
                        <th style="width: 9%;">Segment</th>
                        <th style="width: 12%;">Activité</th>
                        <th style="width: 12%;">Puissance (kW)</th>
                        <th style="width: 9%;">TVA</th>
                        <th style="width: 16%;">Valorisation (cEUR/kWh)</th>
                        <th style="width: 15%;">Actions</th>
                    </tr>
                </thead>
            </table>
            """
            st.markdown(table_html, unsafe_allow_html=True)
            
            # Display each point with action buttons
            for idx, point in enumerate(points):
                # Create columns for data display and action buttons
                cols = st.columns([0.16, 0.11, 0.09, 0.12, 0.12, 0.09, 0.16, 0.15])
                
                with cols[0]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['nom']}</div>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['type']}</div>", unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['segment']}</div>", unsafe_allow_html=True)
                with cols[3]:
                    activite_display = point.get('activite', 'N/A')
                    st.markdown(f"<div style='padding: 4px 0;'>{activite_display}</div>", unsafe_allow_html=True)
                with cols[4]:
                    st.markdown(f"<div style='padding: 4px 0;'>{int(point['puissance'])}</div>", unsafe_allow_html=True)
                with cols[5]:
                    tva_status = "✅" if point.get('tva', False) else "❌"
                    st.markdown(f"<div style='padding: 4px 0;'>{tva_status}</div>", unsafe_allow_html=True)
                with cols[6]:
                    st.markdown(f"<div style='padding: 4px 0;'>{point['valorisation']}</div>", unsafe_allow_html=True)
                with cols[7]:
                    # Action buttons with emojis
                    action_cols = st.columns([1, 1, 1], gap="small")
                    
                    with action_cols[0]:
                        if st.button("✏️", key=f"edit_{idx}", help="Modifier", use_container_width=True):
                            st.info("Fonction de modification à venir")
                    
                    with action_cols[1]:
                        if st.button("📋", key=f"dup_{idx}", help="Dupliquer", use_container_width=True):
                            # Duplicate the point
                            duplicated_point = point.copy()
                            duplicated_point["nom"] = f"{point['nom']} (copie)"
                            st.session_state["points_injection"].append(duplicated_point)
                            st.success(f"✅ Point '{point['nom']}' dupliqué!")
                            st.rerun()
                    
                    with action_cols[2]:
                        # Two-step deletion with confirmation
                        if st.session_state["confirm_delete_injection"] == idx:
                            if st.button("✓", key=f"confirm_{idx}", help="Confirmer la suppression", use_container_width=True):
                                st.session_state["points_injection"].pop(idx)
                                st.session_state["confirm_delete_injection"] = None
                                st.success("Point supprimé")
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"delete_{idx}", help="Supprimer", use_container_width=True):
                                st.session_state["confirm_delete_injection"] = idx
                                st.rerun()
                
                # Show confirmation message
                if st.session_state["confirm_delete_injection"] == idx:
                    st.warning(f"⚠️ Cliquez sur ✓ pour confirmer la suppression de '{point['nom']}'")
                
                # Add separator between rows
                if idx < len(points) - 1:
                    st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
        else:
            st.info("Aucun point d'injection configuré. Ajoutez-en un ci-dessous.")

        st.divider()

        # Section 2: Add form (simple form with direct curve display)
        st.subheader("Ajouter un point d'injection")
        
        # Initialize form state if needed
        if "inj_form_state" not in st.session_state:
            st.session_state["inj_form_state"] = {
                "nom": "", "type": "Solaire", "segment": "C4", 
                "puissance": 0, "apply_tva": False, "valorisation": 0.0,
                "adresse": "", "source": "Aucune",
                "curve_data": None, "coords": None, "last_pvgis_params": "",
                "activite": "Publique"
            }
        
        state = st.session_state["inj_form_state"]
        
        # Input form
        col1, col2, col3 = st.columns(3)
        
        with col1:
            state["nom"] = st.text_input("Nom *", value=state["nom"], placeholder="Centrale PV Nord")
            state["type"] = st.selectbox("Type", ["Solaire", "Éolien"], index=["Solaire", "Éolien"].index(state["type"]) if state["type"] in ["Solaire", "Éolien"] else 0)
            segment_options = ["C2", "C3", "C4", "C5"]
            state["segment"] = st.selectbox("Segment", segment_options, index=segment_options.index(state["segment"]) if state["segment"] in segment_options else 2)
            
            # Activity type with EPCI constraint
            distance_constraint = st.session_state.get("distance_constraint", "2 km")
            is_epci = distance_constraint.strip().upper() == "EPCI"
            activite_options = ["Publique", "Semi-publique", "Privée"]
            if is_epci:
                activite_options = ["Publique", "Semi-publique"]
                # If current value is Privée in EPCI mode, reset to Publique
                if state.get("activite") == "Privée":
                    state["activite"] = "Publique"
            state["activite"] = st.selectbox(
                "Type d'activité", 
                activite_options, 
                index=activite_options.index(state.get("activite", "Publique")) if state.get("activite", "Publique") in activite_options else 0,
                help="En mode EPCI, seules les activités publiques et semi-publiques sont autorisées."
            )
        
        with col2:
            state["puissance"] = st.number_input("Puissance (kW)", min_value=0, step=1, value=state["puissance"], format="%d")
            state["apply_tva"] = st.checkbox("Récupération de TVA", value=state["apply_tva"])
            state["valorisation"] = st.number_input("Valorisation (cEUR/kWh)", min_value=0.0, step=0.01, value=state["valorisation"], format="%.2f")
        
        with col3:
            state["adresse"] = st.text_input("Adresse *", value=state["adresse"], placeholder="123 Rue de la Production, 75001 Paris")
            state["source"] = st.radio("Source de la courbe de production", ["Aucune", "Téléverser XLS", "Modéliser via PVGIS"], 
                                       index=["Aucune", "Téléverser XLS", "Modéliser via PVGIS"].index(state["source"]))
        
        # Handle curve upload/generation based on source
        st.markdown("**Courbe de production**")
        
        # Two-column layout: configuration on left, preview on right
        col_curve1, col_curve2 = st.columns([1, 1])
        
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
                            curve_df = pd.read_csv(uploaded_file)
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
                
                # Afficher les dates sélectionnées dans Infos Générales
                start_date = st.session_state.get("start_date")
                end_date = st.session_state.get("end_date")
                
                if start_date and end_date:
                    duration_days = (end_date - start_date).days
                    st.info(f"📅 Période configurée : {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')} ({duration_days} jours)")
                else:
                    st.warning("⚠️ Configurez les dates dans 'Infos générales' d'abord")
                
                # Détecter les changements de paramètres
                current_params = f"{state['adresse']}_{state['puissance']}_{tilt}_{azimuth}_{losses}_{start_date}_{end_date}"
                last_params = state.get("last_pvgis_params", "")
                
                if state["curve_data"] is not None and current_params != last_params:
                    st.warning("⚠️ Les paramètres ont changé. Cliquez sur 'Générer' pour recalculer la courbe.")
                
                if st.button("🔄 Générer courbe PVGIS", use_container_width=True):
                    if not state["nom"] or not state["adresse"] or state["puissance"] <= 0:
                        st.error("⚠️ Remplissez Nom, Adresse et Puissance d'abord")
                    elif not start_date or not end_date:
                        st.error("⚠️ Configurez les dates dans 'Infos générales' d'abord")
                    elif start_date >= end_date:
                        st.error("⚠️ La date de début doit être antérieure à la date de fin")
                    else:
                        with st.spinner("Géolocalisation et génération en cours..."):
                            coords = get_coordinates_from_address(state["adresse"])
                            if coords and coords.get("lat") and coords.get("lng"):
                                state["coords"] = coords
                                curve = compute_pv_curve(
                                    lat=coords["lat"],
                                    lon=coords["lng"],
                                    peakpower_kw=float(state["puissance"]),
                                    tilt_deg=float(tilt),
                                    azimuth_deg=float(azimuth),
                                    losses_pct=float(losses),
                                    start_date=start_date,
                                    end_date=end_date
                                )
                                if curve is not None:
                                    state["curve_data"] = curve
                                    state["last_pvgis_params"] = f"{state['adresse']}_{state['puissance']}_{tilt}_{azimuth}_{losses}_{start_date}_{end_date}"
                                    duration_days = (end_date - start_date).days
                                    st.success(f"✅ Courbe PVGIS générée : {len(curve)} heures ({duration_days} jours)")
                                else:
                                    st.error("⚠️ Erreur génération courbe PVGIS")
                                    state["curve_data"] = None
                            else:
                                st.error("⚠️ Impossible de géolocaliser l'adresse")
                                state["curve_data"] = None
            
            elif state["source"] == "Aucune":
                st.info("Pas de courbe de production pour ce point")
        
        with col_curve2:
            # Display curve preview if available
            if state["curve_data"] is not None:
                st.markdown("**📊 Aperçu**")
                # Use CurveStandardizer for normalization
                try:
                    standardizer = CurveStandardizer(prm_id=state.get("nom", "temp"))
                    result = standardizer.process(state["curve_data"])
                    
                    if result['success'] and standardizer.parsed_df is not None and len(standardizer.parsed_df) > 0:
                        norm_df = standardizer.parsed_df
                        st.line_chart(norm_df, use_container_width=True, height=300)
                        st.caption(f"Colonnes: {', '.join(norm_df.columns.astype(str))} — Lignes: {len(norm_df)}")
                        
                        # Calculer le volume produit
                        if 'value' in norm_df.columns:
                            volume_total = norm_df['value'].sum()
                            volume_mwh = volume_total / 1000.0  # Conversion kWh -> MWh
                            st.metric("Volume produit estimé", f"{volume_mwh:.2f} MWh", help=f"{volume_total:.0f} kWh sur la période")
                    else:
                        st.warning("⚠️ Courbe non exploitable pour l'affichage.")
                        if result.get('errors'):
                            st.error(f"Erreurs: {result['errors']}")
                        validation = result.get('validation') or {}
                        if validation.get('errors'):
                            st.error(f"Validation: {validation['errors']}")
                except Exception as e:
                    st.warning(f"⚠️ Erreur lors de la normalisation: {e}")
            elif state["source"] != "Aucune":
                st.info("↖️ Configurez et générez/téléversez la courbe pour voir l'aperçu")
            elif state["source"] != "Aucune":
                st.info("↖️ Configurez et générez/téléversez la courbe")
        
        st.divider()
        
        # Validation button (always visible)
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        
        with col_btn1:
            if st.button("✅ Valider et ajouter le point", use_container_width=True, type="primary"):
                # Validate all required fields
                if not state["nom"] or not state["adresse"]:
                    st.error("⚠️ Les champs Nom et Adresse sont obligatoires")
                elif state["source"] != "Aucune" and state["curve_data"] is None:
                    st.error("⚠️ Une courbe est requise pour ce point")
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
                            "type": state["type"],
                            "segment": state["segment"],
                            "activite": state["activite"],
                            "puissance": state["puissance"],
                            "tva": state["apply_tva"],
                            "valorisation": state["valorisation"],
                            "adresse": state["adresse"],
                            "hypothetical": False,
                            "courbe_production": state["curve_data"],
                            "lat": state["coords"]["lat"],
                            "lng": state["coords"]["lng"]
                        }
                        st.session_state["points_injection"].append(new_point)
                        st.success(f"✅ Point '{state['nom']}' ajouté avec succès!")
                        
                        # Reset form state
                        st.session_state["inj_form_state"] = {
                            "nom": "", "type": "Solaire", "segment": "C4",
                            "puissance": 0, "apply_tva": False, "valorisation": 0.0,
                            "adresse": "", "source": "Aucune",
                            "curve_data": None, "coords": None, "activite": "Publique"
                        }
                        st.rerun()
        
        with col_btn2:
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state["inj_form_state"] = {
                    "nom": "", "type": "Solaire", "segment": "C4",
                    "puissance": 0, "apply_tva": False, "valorisation": 0.0,
                    "adresse": "", "source": "Aucune",
                    "curve_data": None, "coords": None, "activite": "Publique"
                }
                st.rerun()

    with tab2:
        st.subheader("Vérification des contraintes de distance")

        points = st.session_state["points_injection"]

        if len(points) == 0:
            st.info("Aucun point d'injection à afficher. Ajoutez des points dans l'onglet 'Gestion des points'.")
        else:
            col_legend1, col_legend2, col_legend3 = st.columns(3)
            with col_legend1:
                st.metric("Points d'injection", len(points))
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
