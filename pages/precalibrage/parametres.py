import streamlit as st
from services.database import list_datasets, delete_dataset
import json

def render():
    """Render the Paramètres page with tabs."""
    st.title("Paramètres du projet")
    
    tab1, tab2 = st.tabs(["Clés de répartition", "📚 Bibliothèque de données"])
    
    with tab1:
        st.info("Page placeholder pour les clés de répartition — à compléter.")

    with tab2:
        st.subheader("Données sauvegardées")
        datasets = list_datasets()
        
        if not datasets:
            st.info("La bibliothèque est vide.")
        else:
            for d in datasets:
                with st.expander(f"{d['type']} : {d['name']}"):
                    st.caption(f"Créé le : {d['created_at']}")
                    if st.button("🗑️ Supprimer", key=f"del_ds_{d['id']}"):
                        delete_dataset(d['id'])
                        st.success("Donnée supprimée.")
                        st.rerun()
