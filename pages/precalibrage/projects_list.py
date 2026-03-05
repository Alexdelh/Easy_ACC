import streamlit as st
import time
from services.database import init_db, list_projects, load_project, delete_project, save_project
from services.state_serializer import deserialize_state

def render():
    """Render the Projects List within the Precalibrage phase."""
    
    st.title("🗂️ Gestion des Projets")
    
    # Initialize DB (idempotent)
    init_db()
    
    # Import serialize_state for auto-save
    from services.state_serializer import serialize_state

    # --- Actions bar ---
    col_new, col_spacer = st.columns([0.4, 0.6])
    with col_new:
        with st.expander("➕ Créer un nouveau projet", expanded=False):
            new_name = st.text_input("Nom du nouveau projet", placeholder="Mon Projet Solaire")
            if st.button("Créer", type="primary", use_container_width=True):
                if new_name.strip():
                     # 1. Reset Session State
                    st.session_state.clear()
                    from state.init_state import init_session_state
                    init_session_state()
                    
                    # 2. Save Initial Project to DB to get ID (Atomic Requirement)
                    try:
                        project_id = save_project(
                            name=new_name.strip(),
                            current_phase="precalibrage",
                            state_dict=serialize_state(dict(st.session_state))
                        )
                        st.session_state["project_id"] = project_id
                        st.session_state["project_name"] = new_name.strip()
                        st.session_state["current_phase"] = "precalibrage"
                        st.session_state["precalibrage_page"] = 1 # Start at General
                        
                        st.success(f"Nouveau projet '{new_name}' créé et sauvegardé (ID: {project_id})")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la création: {e}")
                else:
                    st.warning("Veuillez entrer un nom.")

    st.divider()

    # --- Projects List ---
    projects = list_projects()
    
    if not projects:
        st.info("Aucun projet enregistré.")
    else:
        # Table Header
        header_cols = st.columns([0.3, 0.25, 0.15, 0.3])
        header_cols[0].markdown("**Nom du projet**")
        header_cols[1].markdown("**Dernière modification**")
        header_cols[2].markdown("**Phase**")
        header_cols[3].markdown("**Actions**")
        
        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
        
        for p in projects:
            cols = st.columns([0.3, 0.25, 0.15, 0.3])
            
            # Name
            cols[0].write(p["name"])
            
            # Date
            cols[1].caption(p["updated_at"])
            
            # Phase
            cols[2].caption(p["current_phase"])
            
            # Actions
            with cols[3]:
                col_act1, col_act2 = st.columns(2)
                
                # Load
                if col_act1.button("📂 Charger", key=f"load_{p['id']}", use_container_width=True):
                    try:
                        project_data = load_project(p['id'])
                        if project_data:
                            # deserialize
                            saved_state = deserialize_state(project_data["state_data"])
                            # restore
                            st.session_state.clear()
                            
                            # Keys to exclude during restore (double safety)
                            exclude_prefixes = ("prev_", "next_", "load_", "del_", "delete_", "confirm_")
                            
                            for k, v in saved_state.items():
                                if isinstance(k, str) and k.startswith(exclude_prefixes):
                                    continue
                                st.session_state[k] = v
                            
                            st.session_state["project_name"] = project_data["name"]
                            st.session_state["current_phase"] = project_data["current_phase"]
                            st.session_state["project_id"] = project_data["id"]
                            
                            st.toast(f"Projet '{project_data['name']}' chargé !", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
                
                # Delete
                if "confirm_delete_project" not in st.session_state:
                    st.session_state["confirm_delete_project"] = None
                    
                if st.session_state["confirm_delete_project"] == p['id']:
                    col_act2.button("Suppression...", disabled=True, key=f"del_dis_{p['id']}", use_container_width=True)
                else:
                    if col_act2.button("🗑️ Supprimer", key=f"del_{p['id']}", help="Supprimer", use_container_width=True):
                        st.session_state["confirm_delete_project"] = p['id']
                        st.rerun()
            
            if st.session_state.get("confirm_delete_project") == p['id']:
                st.error("⚠️ Êtes-vous sûr de vouloir supprimer ce projet et toutes ses données (incluant les courbes) de façon permanente ?")
                col_yes, col_no = st.columns([1, 1])
                if col_yes.button("🚨 Oui, supprimer", key=f"confirm_yes_{p['id']}", use_container_width=True, type="primary"):
                    delete_project(p['id'])
                    # If the currently active project was deleted, reset the tracking keys
                    if st.session_state.get("project_id") == p['id']:
                        st.session_state["project_id"] = None
                        st.session_state["project_name"] = None
                    st.session_state["confirm_delete_project"] = None
                    st.success("Projet supprimé avec succès.")
                    time.sleep(1)
                    st.rerun()
                if col_no.button("❌ Annuler", key=f"confirm_no_{p['id']}", use_container_width=True):
                    st.session_state["confirm_delete_project"] = None
                    st.rerun()
            
            st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
