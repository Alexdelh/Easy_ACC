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
        
        if "_project_name" not in st.session_state:
            st.session_state["_project_name"] = st.session_state.get("project_name", "")
        st.text_input(
            "Nom de l'opération",
            key="_project_name",
            on_change=auto_save_general_field,
            args=("project_name", "_project_name")
        )

        if "_postal_code" not in st.session_state:
            st.session_state["_postal_code"] = st.session_state.get("postal_code", "")
        st.text_input(
            "Code postal",
            placeholder="Ex: 75001",
            max_chars=5,
            key="_postal_code",
            on_change=auto_save_general_field,
            args=("postal_code", "_postal_code")
        )

        # Dynamic index for Distance Constraint
        if "_distance_constraint" not in st.session_state:
            val = st.session_state.get("distance_constraint", "2 km")
            if val not in DISTANCE_OPTIONS:
                val = "2 km"
            st.session_state["_distance_constraint"] = val
            
        st.selectbox(
            "Distance contrainte",
            DISTANCE_OPTIONS,
            key="_distance_constraint",
            on_change=auto_save_general_field,
            args=("distance_constraint", "_distance_constraint")
        )

        # Dynamic index for Operation Type
        OPERATION_TYPES = ["Ouverte", "Patrimoniale"]
        if "_operation_type" not in st.session_state:
            val = st.session_state.get("operation_type", "Ouverte")
            if val not in OPERATION_TYPES:
                val = "Ouverte"
            st.session_state["_operation_type"] = val

        st.selectbox(
            "Type d'opération",
            OPERATION_TYPES,
            key="_operation_type",
            on_change=auto_save_general_field,
            args=("operation_type", "_operation_type")
        )
        
        st.divider()       
        
            
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
