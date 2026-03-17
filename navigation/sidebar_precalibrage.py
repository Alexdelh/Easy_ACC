import streamlit as st


PRECALIBRAGE_MENU = {
    0: "Projets",
    1: "Infos générales",
    2: "Points d'injection",
    3: "Points de soutirage",
    4: "Paramètres",
}

def repartition_is_valid():
    """Vérifie que les clés de répartition sont correctes."""

    mode = st.session_state.get("repartition_mode", "Clé par défaut")

    # Mode par défaut -> toujours valide
    if mode == "Clé par défaut":
        return True

    # Mode statique
    if mode == "Clé statique (pourcentages par consommateur)":
        cp = st.session_state.get("consumer_percentages", {})
        if not cp:
            return False
        total = sum(cp.values())
        return abs(total - 100.0) < 0.001

    # Mode dynamique
    if mode == "Clé dynamique simple":
        gstate = st.session_state.get("consumer_group_keys", {})

        for pr, group in gstate.items():
            if group.get("mode") == "static":
                perc = group.get("percentages", {})
                total = sum(perc.values())
                if abs(total - 100.0) > 0.001:
                    return False

        return True

    return True


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

        def _nav_save():
            """Sauvegarde silencieuse à chaque navigation entre pages."""
            project_id = st.session_state.get("project_id")
            if project_id:
                try:
                    from services.database import save_project
                    from services.state_serializer import serialize_state
                    save_project(
                        name=st.session_state.get("project_name", "Sans titre"),
                        current_phase="precalibrage",
                        state_dict=serialize_state(dict(st.session_state)),
                        project_id=project_id,
                    )
                except Exception:
                    pass  # Navigation must never be blocked by a save error

        with col_prev:
            if current_page > 0: # Allow going back to Projets (0)
                if st.button("← Précédent", width='stretch', key=f"prev_{current_page}"):
                    _nav_save()
                    st.session_state["precalibrage_page"] = current_page - 1
                    st.rerun()
            else:
                st.button("← Précédent", disabled=True, width='stretch')
        with col_next:
            if current_page < max(PRECALIBRAGE_MENU.keys()):
                if st.button("Suivant →", width='stretch', key=f"next_{current_page}"):
                    _nav_save()
                    st.session_state["precalibrage_page"] = current_page + 1
                    st.rerun()
            else:
                st.button("Suivant →", disabled=True, width='stretch')


        # Generate button only on last page
        if current_page == max(PRECALIBRAGE_MENU.keys()):
            st.divider()
            valid_repartition = repartition_is_valid()
            if not valid_repartition:
                st.warning("⚠️ Les clés de répartition doivent totaliser 100 %.")
            if st.button("Générer le scénario", type="primary", width='stretch', disabled=not valid_repartition):
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
