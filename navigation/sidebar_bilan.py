import streamlit as st


BILAN_MENU = {
    1: "Énergie",
    2: "Financier",
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
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Énergie", use_container_width=True, disabled=(current_page == 1)):
                st.session_state["bilan_page"] = 1
                st.rerun()
        with col2:
            if st.button("Financier", use_container_width=True, disabled=(current_page == 2)):
                st.session_state["bilan_page"] = 2
                st.rerun()
        
        st.divider()
        
        # Back to precalibrage button
        if st.button("← Retour au précalibrage", use_container_width=True):
            st.session_state["current_phase"] = "precalibrage"
            st.rerun()
