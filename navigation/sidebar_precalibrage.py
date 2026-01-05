import streamlit as st


PRECALIBRAGE_MENU = {
    1: "Infos générales",
    2: "Points d'injection",
    3: "Points de soutirage",
    4: "Paramètres",
    5: "Financier",
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
            if current_page > 1:
                if st.button("← Précédent", use_container_width=True, key=f"prev_{current_page}"):
                    st.session_state["precalibrage_page"] = current_page - 1
                    st.rerun()
            else:
                st.button("← Précédent", disabled=True, use_container_width=True)
        with col_next:
            if current_page < max(PRECALIBRAGE_MENU.keys()):
                if st.button("Suivant →", use_container_width=True, key=f"next_{current_page}"):
                    st.session_state["precalibrage_page"] = current_page + 1
                    st.rerun()
            else:
                st.button("Suivant →", disabled=True, use_container_width=True)

        # Generate button only on last page
        if current_page == max(PRECALIBRAGE_MENU.keys()):
            st.divider()
            if st.button("Générer le scénario", type="primary", use_container_width=True):
                st.session_state["scenario_generated"] = True
                st.session_state["current_phase"] = "bilan"
                st.session_state["bilan_page"] = 1
                st.rerun()
