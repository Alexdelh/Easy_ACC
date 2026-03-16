import streamlit as st


PRECALIBRAGE_MENU = {
    0: "Projets",
    1: "Infos générales",
    2: "Points d'injection",
    3: "Points de soutirage",
    4: "Paramètres",
}


def render_sidebar_precalibrage():
    """Sidebar for precalibrage phase - navigation only."""
    current_page = st.session_state.get("precalibrage_page", 1)
    
    with st.sidebar:
        st.markdown("### 📋 Précalibrage")
        
        # Display all page titles with current page highlighted
        for page_num, label in PRECALIBRAGE_MENU.items():
            if page_num == current_page:
                st.markdown(f"**🔴 {label}**")
            else:
                st.markdown(f"○ {label}")
        
        st.divider()

        # Prev/Next controls
        col_prev, col_next = st.columns(2, gap="small")
        with col_prev:
            if current_page > 0: # Allow going back to Projets (0)
                if st.button("← Précédent", width='stretch', key=f"prev_{current_page}"):
                    st.session_state["precalibrage_page"] = current_page - 1
                    st.rerun()
            else:
                st.button("← Précédent", disabled=True, width='stretch')
        with col_next:
            if current_page < max(PRECALIBRAGE_MENU.keys()):
                if st.button("Suivant →", width='stretch', key=f"next_{current_page}"):
                    st.session_state["precalibrage_page"] = current_page + 1
                    st.rerun()
            else:
                st.button("Suivant →", disabled=True, width='stretch')

        # Generate button only on last page
        if current_page == max(PRECALIBRAGE_MENU.keys()):
            st.divider()
            if st.button("Générer le scénario", type="primary", width='stretch'):
                # Call aggregation to build consolidated DataFrames
                with st.spinner("Agrégation des courbes et sauvegarde du projet..."):
                    try:
                        from services.data_aggregation import build_dataframes
                        from services.database import save_project
                        from services.state_serializer import serialize_state
                        
                        points_consumers = st.session_state.get("points_soutirage", [])
                        points_producers = st.session_state.get("points_injection", [])
                        
                        consumers_df, producers_df, aggregation_summary = build_dataframes(
                            points_consumers, points_producers
                        )
                        
                        # Store results in session_state
                        st.session_state["consumers_df"] = consumers_df
                        st.session_state["producers_df"] = producers_df
                        st.session_state["aggregation_summary"] = aggregation_summary
                        
                        # Log any errors/warnings
                        if aggregation_summary.get("errors"):
                            for error in aggregation_summary["errors"]:
                                st.warning(f"⚠️ {error}")
                        
                        st.success(
                            f"✅ Agrégation complète: "
                            f"{aggregation_summary.get('consumers_with_data', 0)} consommateurs, "
                            f"{aggregation_summary.get('producers_with_data', 0)} producteurs"
                        )
                        
                        # Auto-save after successful generation
                        if st.session_state.get("project_id"):
                            state_to_save = serialize_state(dict(st.session_state))
                            save_project(
                                name=st.session_state.get("project_name", "Sans titre"),
                                current_phase="precalibrage",
                                state_dict=state_to_save,
                                project_id=st.session_state.get("project_id")
                            )
                            st.toast("✅ Projet sauvegardé automatiquement")

                    except Exception as e:
                        st.error(f"❌ Erreur agrégation ou sauvegarde: {e}")
                        import traceback
                        st.error(traceback.format_exc())
                
                st.session_state["scenario_generated"] = True
                st.session_state["current_phase"] = "bilan"
                st.session_state["bilan_page"] = 1
                st.rerun()

        st.divider()
        
        st.divider()
