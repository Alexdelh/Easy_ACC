import streamlit as st


BILAN_MENU = {
    1: "Énergie",
}


def render_sidebar_bilan():
    """Sidebar for bilan phase - navigation only."""
    current_page = st.session_state.get("bilan_page", 1)
    
    with st.sidebar:
        st.markdown("### 📊 Bilan")
        
        # Display all page titles with current page highlighted
        for page_num, label in BILAN_MENU.items():
            if page_num == current_page:
                st.markdown(f"**🔴 {label}**")
            else:
                st.markdown(f"○ {label}")
        
        st.divider()
        
        st.divider()
        
        # Back to precalibrage button
        if st.button("← Retour au précalibrage", width='stretch'):
            st.session_state["current_phase"] = "precalibrage"
            st.session_state["scenario_generated"] = False
            st.rerun()
