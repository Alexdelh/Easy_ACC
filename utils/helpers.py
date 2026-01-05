import streamlit as st
import pandas as pd
import os
import io
import zipfile
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# Basic constants
H_UPLOADER_CONTAINER = 300
DATA_DIR = os.path.join(os.getcwd(), "ACC_data")
PAGES = {
    1: "pages/1_infos_generales.py",
    2: "pages/2_points_injection.py",
    3: "pages/3_points_soutirage.py",
    4: "pages/4_points_stockage.py",
    5: "pages/5_cles_repartition.py",
    6: "pages/6_parametres_financiers.py"
}

# Mock geographic database of communes and addresses
GEO_DATABASE = {
    "Paris": {"lat": 48.8566, "lng": 2.3522, "epci": "Métropole du Grand Paris"},
    "Lyon": {"lat": 45.7640, "lng": 4.8357, "epci": "Métropole de Lyon"},
    "Marseille": {"lat": 43.2965, "lng": 5.3698, "epci": "Provence Alpes Côte d'Azur"},
    "Toulouse": {"lat": 43.6047, "lng": 1.4442, "epci": "Toulouse Métropole"},
    "Nice": {"lat": 43.7102, "lng": 7.2620, "epci": "Métropole Nice Côte d'Azur"},
}

DISTANCE_OPTIONS = ["2 km", "10 km", "20 km", "EPCI"]

def get_coordinates_from_address(commune: str) -> dict:
    """Retrieve coordinates from mock geographic database."""
    if commune in GEO_DATABASE:
        return GEO_DATABASE[commune]
    return {"lat": 48.8566, "lng": 2.3522, "epci": "Non trouvé"}


@st.cache_data(ttl=3600)
def get_coordinates_from_postal_code(postal_code: str) -> dict:
    """
    Retrieve coordinates from postal code using Nominatim API (OpenStreetMap).
    Results are cached for 1 hour to minimize API calls.
    
    Args:
        postal_code: French postal code (5 digits)
    
    Returns:
        dict with keys: lat, lng, city, epci
    """
    try:
        # Initialize Nominatim geocoder with a descriptive user_agent
        geolocator = Nominatim(user_agent="acc_app_v1")
        
        # Search for postal code in France
        query = f"{postal_code}, France"
        location = geolocator.geocode(query, timeout=10)
        
        if location:
            # Extract city name from address if possible
            address_parts = location.address.split(',')
            city = address_parts[0].strip() if address_parts else "N/A"
            
            return {
                "lat": location.latitude,
                "lng": location.longitude,
                "city": city,
                "epci": "N/A"  # EPCI would require a separate database lookup
            }
        else:
            st.warning(f"Code postal {postal_code} non trouvé. Vérifiez le format.")
            return {
                "lat": None,
                "lng": None,
                "city": f"Code postal {postal_code} non trouvé",
                "epci": "N/A"
            }
    except Exception as e:
        st.error(f"Erreur API géolocalisation: {str(e)}")
        return {
            "lat": None,
            "lng": None,
            "city": "Erreur de géolocalisation",
            "epci": "N/A"
        }


def render_banner_with_navigation(current_page: int, banner_content=None):
    """Render left banner (1/4) with navigation structure, buttons, and project info."""
    st.markdown(
        """
        <style>
        .sidebar-nav {
            background: #f7f7f9;
            padding: 0.75rem 0.85rem 1rem;
            border-radius: 8px;
            border: 1px solid #e0e0e5;
        }
        .sidebar-nav p {
            margin: 0 0 6px;
            font-size: 16px;
            font-weight: 650;
            color: #1f1f2e;
        }
        .sidebar-nav .stButton>button {
            width: 100%;
            font-size: 16px;
            font-weight: 700;
            padding: 0.55rem 0.6rem;
        }
        .sidebar-title {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.2px;
            color: #5b5b6b;
            margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    banner_col, content_col = st.columns([0.25, 0.75], gap="large")

    with banner_col:
        with st.container(border=True):
            st.markdown("<div class='sidebar-nav'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-title'>📋 Navigation</div>", unsafe_allow_html=True)
            st.markdown("<p>App</p>", unsafe_allow_html=True)
            st.markdown("<p>Infos générales</p>", unsafe_allow_html=True)
            st.markdown("<p>Points injection</p>", unsafe_allow_html=True)
            st.markdown("<p>Points soutirage</p>", unsafe_allow_html=True)
            st.markdown("<p>Points stockage</p>", unsafe_allow_html=True)
            st.markdown("<p>Clés répartition</p>", unsafe_allow_html=True)
            st.markdown("<p>Paramètres financiers</p>", unsafe_allow_html=True)

            st.divider()

            col_prev, col_next = st.columns(2, gap="small")

            with col_prev:
                if current_page > 1:
                    if st.button("← Précédent", use_container_width=True, key=f"prev_{current_page}"):
                        st.switch_page(PAGES[current_page - 1])
                else:
                    st.button("← Précédent", disabled=True, use_container_width=True)

            with col_next:
                if current_page < 6:
                    if st.button("Suivant →", use_container_width=True, key=f"next_{current_page}"):
                        st.switch_page(PAGES[current_page + 1])
                else:
                    st.button("Suivant →", disabled=True, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("📊 Infos du projet", expanded=True):
            if banner_content:
                banner_content()

    return content_col


def render_page_header_with_banner(title: str, banner_content=None):
    """Render page with expandable banner (1/4) and title + content area (3/4)."""
    st.markdown("""
    <style>
    .main > div:first-child { padding-top: 1rem; }
    h1, h2, h3 { font-size: 28px !important; font-weight: 700 !important; margin-bottom: 20px; }
    label { font-size: 16px !important; font-weight: 600 !important; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div {
        font-size: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Banner (1/4) + Content (3/4) layout
    banner_col, content_col = st.columns([0.25, 0.75], gap="large")
    
    with banner_col:
        with st.expander("📋 Infos du projet", expanded=True):
            if banner_content:
                banner_content()
    
    return content_col


def init_session_state():
    st.session_state.setdefault("project_name", "")
    st.session_state.setdefault("commune", "")
    st.session_state.setdefault("distance_constraint", 0.0)
    st.session_state.setdefault("operation_type", "Ouverte")
    st.session_state.setdefault("injections_df", None)
    st.session_state.setdefault("consumers_df", None)
    st.session_state.setdefault("producers_df", None)


def render_navigation_footer(current_page: int):
    """Render Previous/Next navigation buttons at page bottom."""
    st.divider()
    col1, col_spacer, col2 = st.columns([0.15, 0.7, 0.15])
    
    with col1:
        if current_page > 1:
            if st.button("← Précédent", use_container_width=True):
                st.switch_page(PAGES[current_page - 1])
        else:
            st.button("← Précédent", disabled=True, use_container_width=True)
    
    with col2:
        if current_page < 6:
            if st.button("Suivant →", use_container_width=True):
                st.switch_page(PAGES[current_page + 1])
        else:
            st.button("Suivant →", disabled=True, use_container_width=True)


def process_actors_file(uploaded_file, actor_type: str):
    try:
        df = pd.read_excel(uploaded_file)
    except Exception:
        # fallback: try reading as csv
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)

    st.session_state[f"{actor_type}s_df"] = df
    st.session_state[f"msg_{actor_type}"] = f"Chargé {len(df)} acteurs"


def _save_bytes_to_path(b: bytes, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b)


def process_curves_files(uploaded_files, actor_type: str, subdir: str):
    out_dir = os.path.join(DATA_DIR, subdir)
    os.makedirs(out_dir, exist_ok=True)
    saved = 0
    for uf in uploaded_files:
        name = getattr(uf, "name", None) or f"uploaded_{saved}.dat"
        uf.seek(0)
        content = uf.read()
        if name.lower().endswith(".zip"):
            try:
                z = zipfile.ZipFile(io.BytesIO(content))
                for info in z.infolist():
                    if info.filename.lower().endswith(
                        (".csv",)
                    ):
                        data = z.read(info.filename)
                        _save_bytes_to_path(data, os.path.join(out_dir, os.path.basename(info.filename)))
                        saved += 1
            except Exception:
                continue
        else:
            _save_bytes_to_path(content, os.path.join(out_dir, name))
            saved += 1

    st.session_state[f"msg_{actor_type}"] = f"Courbes: {saved} fichiers enregistrés dans {out_dir}"


def render_actor_list(df, actor_type, curves_dir):
    if df is None:
        st.caption("Aucun acteur chargé")
    else:
        st.dataframe(df)

    if os.path.isdir(curves_dir):
        files = os.listdir(curves_dir)
        if files:
            st.markdown("**Fichiers de courbes:**")
            for f in files[:50]:
                st.write(f)


def render_actor_block(block_title: str, actor_type: str, curves_subdir: str):
    """Reusable actor block: upload actors and curves, show list."""
    st.subheader(block_title, anchor=False)

    left_col, right_col = st.columns([0.25, 0.75], gap="medium")

    with left_col:
        st.markdown("**📤 Importer**")
        with st.container():
            actors_file = st.file_uploader(
                "Excel acteurs",
                type=["xlsx", "xls"],
                key=f"upload_{actor_type}"
            )
            if actors_file is not None:
                process_actors_file(actors_file, actor_type)

            st.write("")

            curves_files = st.file_uploader(
                "Courbes (CSV/ZIP)",
                accept_multiple_files=True,
                type=["csv", "xlsx", "xls", "zip"],
                key=f"upload_curves_{actor_type}"
            )
            if curves_files:
                process_curves_files(curves_files, actor_type, curves_subdir)

    with right_col:
        st.markdown("**📋 Acteurs**")
        msg = st.session_state.get(f"msg_{actor_type}", "")
        if msg:
            st.caption(msg)

        df_actors = st.session_state.get(f"{actor_type}s_df")
        curves_dir = os.path.join(DATA_DIR, curves_subdir)
        render_actor_list(df_actors, actor_type, curves_dir)
