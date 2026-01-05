import streamlit as st
from state.init_state import init_session_state
from navigation.sidebar_precalibrage import render_sidebar_precalibrage

st.set_page_config(page_title="Easy ACC", layout="wide")
init_session_state()

# Initialize phases if not set
if "current_phase" not in st.session_state:
    st.session_state["current_phase"] = "precalibrage"
if "precalibrage_page" not in st.session_state:
    st.session_state["precalibrage_page"] = 0
if "bilan_page" not in st.session_state:
    st.session_state["bilan_page"] = 1

# Render appropriate sidebar based on current phase
current_phase = st.session_state["current_phase"]

if current_phase == "precalibrage":
    render_sidebar_precalibrage()
    
    # Route to the correct precalibrage page
    page_num = st.session_state["precalibrage_page"]
    
    if page_num == 0:
        from pages.precalibrage import projects_list
        projects_list.render()
    elif page_num == 1:
        from pages.precalibrage import general
        general.render()
    elif page_num == 2:
        from pages.precalibrage import production
        production.render()
    elif page_num == 3:
        from pages.precalibrage import consommation
        consommation.render()
    elif page_num == 4:
        from pages.precalibrage import parametres
        parametres.render()
    elif page_num == 5:
        from pages.precalibrage import financier
        financier.render()

elif current_phase == "bilan":
    from navigation.sidebar_bilan import render_sidebar_bilan
    render_sidebar_bilan()
    
    # Route to the correct bilan page
    bilan_page = st.session_state["bilan_page"]
    
    if bilan_page == 1:
        from pages.bilan import energie
        energie.render()
    elif bilan_page == 2:
        from pages.bilan import financier
        financier.render()
