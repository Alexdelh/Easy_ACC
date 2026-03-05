import streamlit as st
import folium
from streamlit_folium import st_folium

from utils.helpers import DISTANCE_OPTIONS, get_coordinates_from_postal_code


def auto_save_general_field(state_key, widget_key):
    if widget_key in st.session_state:
        st.session_state[state_key] = st.session_state[widget_key]
    if st.session_state.get("project_id"):
        from services.database import save_project
        from services.state_serializer import serialize_state
        save_project(
            st.session_state.get("project_name", "Sans titre"), 
            "precalibrage", 
            serialize_state(dict(st.session_state)), 
            st.session_state["project_id"]
        )

def render():
    """Render the Infos Générales page."""
    st.title("Infos générales")
    
    # Project inputs
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Configuration du projet")
        
        st.session_state.setdefault("project_name", "") # Ensure initialized
        st.text_input(
            "Nom de l'opération",
            value=st.session_state["project_name"],
            key="_project_name",
            on_change=auto_save_general_field,
            args=("project_name", "_project_name")
        )

        st.session_state.setdefault("postal_code", "") # Ensure initialized
        st.text_input(
            "Code postal",
            value=st.session_state["postal_code"],
            placeholder="Ex: 75001",
            max_chars=5,
            key="_postal_code",
            on_change=auto_save_general_field,
            args=("postal_code", "_postal_code")
        )

        # Dynamic index for Distance Constraint
        if "distance_constraint" not in st.session_state or st.session_state["distance_constraint"] not in DISTANCE_OPTIONS:
            st.session_state["distance_constraint"] = "2 km"

        try:
            dist_index = DISTANCE_OPTIONS.index(st.session_state["distance_constraint"])
        except ValueError:
            dist_index = 0

        st.selectbox(
            "Distance contrainte",
            DISTANCE_OPTIONS,
            index=dist_index,
            key="_distance_constraint",
            on_change=auto_save_general_field,
            args=("distance_constraint", "_distance_constraint")
        )

        # Dynamic index for Operation Type
        OPERATION_TYPES = ["Ouverte", "Patrimoniale"]
        if "operation_type" not in st.session_state or st.session_state["operation_type"] not in OPERATION_TYPES:
            st.session_state["operation_type"] = "Ouverte"

        try:
            op_index = OPERATION_TYPES.index(st.session_state["operation_type"])
        except ValueError:
            op_index = 0

        st.selectbox(
            "Type d'opération",
            OPERATION_TYPES,
            index=op_index,
            key="_operation_type",
            on_change=auto_save_general_field,
            args=("operation_type", "_operation_type")
        )
        
        st.divider()
        st.subheader("Période d'étude")
        
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            st.date_input(
                "Date de début",
                value=st.session_state.get("start_date"),
                key="_start_date",
                help="Date de début pour la modélisation PVGIS et l'import des courbes",
                on_change=auto_save_general_field,
                args=("start_date", "_start_date")
            )
        
        with date_col2:
            st.date_input(
                "Date de fin",
                value=st.session_state.get("end_date"),
                key="_end_date",
                help="Date de fin pour la modélisation PVGIS et l'import des courbes",
                on_change=auto_save_general_field,
                args=("end_date", "_end_date")
            )
        
        # Validation des dates
        start_date = st.session_state.get("start_date")
        end_date = st.session_state.get("end_date")
        if start_date and end_date:
            if start_date >= end_date:
                st.error("⚠️ La date de début doit être antérieure à la date de fin")
            
    with col2:
        st.subheader("Localisation du projet")

        if st.session_state.get("postal_code"):
            coords = get_coordinates_from_postal_code(st.session_state["postal_code"])
            
            if coords["lat"] and coords["lng"]:
                # Create and display map
                m = folium.Map(
                    location=[coords["lat"], coords["lng"]],
                    zoom_start=12,
                    tiles="OpenStreetMap"
                )

                folium.Marker(
                    location=[coords["lat"], coords["lng"]],
                    popup=f"{st.session_state['postal_code']} - {coords['city']}",
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)

                st_folium(m, width=700, height=500)

                st.markdown(f"""
                **Détails géographiques:**
                - **Code postal**: {st.session_state['postal_code']}
                - **Ville**: {coords['city']}
                - **Coordonnées**: {coords['lat']:.4f}°, {coords['lng']:.4f}°
                - **Périmètre d'opération**: {st.session_state.get('distance_constraint', '2 km')}
                """)
            else:
                st.error(f" {coords['city']}")
                st.info("Entrez un code postal valide pour voir la localisation sur la carte.")
        else:
            st.info("Entrez un code postal pour voir sa localisation sur la carte.")
