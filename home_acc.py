"""
Easy ACC Home Page — Projet ACC
PIXEL-STABLE LAYOUT (no global scroll on 1920×1080)

Core principles:
✅ Fixed heights everywhere — all containers reserved at init
✅ Upload = immediate processing (no validation buttons)
✅ No dynamic elements appearing (no st.success/info/warning)
✅ Scroll only inside fixed-height containers
✅ Compact rows, minimal spacing with gap="small"
✅ No automatic file loading on startup
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re
import io
import zipfile
import unicodedata

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(page_title="Projet ACC", layout="wide", initial_sidebar_state="collapsed")

# ============================================================================
# CRITICAL CONFIGURATION
# ============================================================================

DATA_DIR = os.path.join(os.path.dirname(__file__), "ACC_data")
os.makedirs(DATA_DIR, exist_ok=True)

# FIXED HEIGHTS (pixels) — DO NOT CHANGE
H_UPLOADER_CONTAINER = 180  # Left column: both uploaders
H_ACTOR_LIST_CONTAINER = 250  # Right column: scrollable list

# Minimal CSS for compactness
st.markdown("""
<style>
    .stButton button { padding: 0.4rem 0.8rem; font-size: 0.85rem; height: auto; }
    .stCaption { margin: 0 !important; padding: 0 !important; line-height: 1.2; }
    .stText { margin: 0 !important; padding: 0 !important; }
    div[data-testid="stVerticalBlock"] { gap: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION (EXPLICIT)
# ============================================================================

# Initialize all session state keys (never auto-load from disk)
if "project_name" not in st.session_state:
    st.session_state["project_name"] = "Mon Projet ACC"

if "consumers_df" not in st.session_state:
    st.session_state["consumers_df"] = None

if "producers_df" not in st.session_state:
    st.session_state["producers_df"] = None

# Message placeholders
if "msg_consumer" not in st.session_state:
    st.session_state["msg_consumer"] = ""

if "msg_producer" not in st.session_state:
    st.session_state["msg_producer"] = ""

if "final_msg" not in st.session_state:
    st.session_state["final_msg"] = ""


# ============================================================================
# HELPERS
# ============================================================================

def _sanitize_name(name: str) -> str:
    name = str(name).strip()
    name = re.sub(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ]+", "_", name)
    return name


def _timestamp() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def _normalize_text(s: str) -> str:
    if not s:
        return ''
    s = str(s).lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = re.sub(r'\s+', '', s)
    return s


def _find_pdl_column(df: pd.DataFrame) -> str:
    if df is None:
        return None
    for col in df.columns:
        col_norm = _normalize_text(col)
        if ('pointdelivraison' in col_norm) or ('pdl' in col_norm) or ('livraison' in col_norm):
            return col
    return None


def _extract_pdl_from_filename(fname: str) -> str:
    match = re.search(r'\b(\d{14})\b', fname)
    return match.group(1) if match else ""


def _save_dataframe(df: pd.DataFrame, target_filename: str) -> str:
    target_path = os.path.join(DATA_DIR, target_filename)
    timestamp = _timestamp()
    try:
        df.to_excel(target_path, index=False)
        return target_path
    except PermissionError:
        alt_path = os.path.join(DATA_DIR, f"{target_filename.rstrip('.xlsx')}_saved_{timestamp}.xlsx")
        df.to_excel(alt_path, index=False)
        return alt_path


def _has_curve_in_dir(pdl: str, curves_dir: str) -> bool:
    if not pdl or not os.path.exists(curves_dir):
        return False
    try:
        for fn in os.listdir(curves_dir):
            if fn.startswith(pdl + '_'):
                return True
    except Exception:
        pass
    return False


def generate_unique_name(base_name: str, df: pd.DataFrame) -> str:
    base = str(base_name).strip()
    if 'Bâtiment' not in df.columns:
        return base
    existing = set(df['Bâtiment'].astype(str).tolist())
    if base not in existing:
        return base
    i = 2
    while True:
        candidate = f"{base}_{i}"
        if candidate not in existing:
            return candidate
        i += 1


def duplicate_actor(actor_type: str, index: int) -> tuple:
    """Duplicate actor in dataframe and save to Excel."""
    try:
        key = f'{actor_type}s_df'
        if st.session_state[key] is None:
            return False, "Base non chargée"
        df = st.session_state[key]
        if index not in df.index:
            return False, "Index introuvable"
        
        row = df.iloc[index].copy()
        base_name = str(row.get('Bâtiment', 'copy'))
        new_name = generate_unique_name(base_name, df)
        row['Bâtiment'] = new_name
        
        df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        st.session_state[key] = df2
        _save_dataframe(df2, f'{actor_type}s.xlsx')
        return True, f"Dupliqué: {new_name}"
    except Exception as e:
        return False, str(e)[:50]


def delete_actor(actor_type: str, index: int) -> tuple:
    """Delete actor from dataframe and save to Excel."""
    try:
        key = f'{actor_type}s_df'
        if st.session_state[key] is None:
            return False, "Base non chargée"
        df = st.session_state[key]
        if index not in df.index:
            return False, "Index introuvable"
        
        df2 = df.drop(index).reset_index(drop=True)
        st.session_state[key] = df2
        _save_dataframe(df2, f'{actor_type}s.xlsx')
        return True, "Supprimé"
    except Exception as e:
        return False, str(e)[:50]


# ============================================================================
# UPLOAD PROCESSING (IMMEDIATE)
# ============================================================================

def process_actors_file(uploaded_file, actor_type: str):
    """Process actor Excel file immediately on upload."""
    if uploaded_file is None:
        return
    
    try:
        xls = pd.read_excel(uploaded_file, sheet_name=None)
        sheets = list(xls.keys())
        sheet = sheets[0]
        df_actors = pd.read_excel(uploaded_file, sheet_name=sheet)

        # Validate required columns
        if 'Bâtiment' not in df_actors.columns:
            st.session_state[f"msg_{actor_type}"] = "❌ Colonne 'Bâtiment' manquante"
            return
        
        if _find_pdl_column(df_actors) is None:
            st.session_state[f"msg_{actor_type}"] = "❌ Colonne 'PDL' manquante"
            return

        # Initialize Statut column if missing
        if 'Statut' not in df_actors.columns:
            df_actors['Statut'] = pd.Series(dtype='object')

        # Save and store in session
        _save_dataframe(df_actors, f'{actor_type}s.xlsx')
        st.session_state[f'{actor_type}s_df'] = df_actors
        st.session_state[f"msg_{actor_type}"] = f"✅ {len(df_actors)} acteurs importés"
    except Exception as e:
        st.session_state[f"msg_{actor_type}"] = f"❌ Erreur: {str(e)[:40]}"


def process_curves_files(uploaded_files, actor_type: str, curves_subdir: str):
    """Process curve files immediately on upload."""
    if not uploaded_files:
        return

    # Ensure actors are loaded
    if st.session_state[f'{actor_type}s_df'] is None:
        # Try loading from disk
        try:
            path = os.path.join(DATA_DIR, f'{actor_type}s.xlsx')
            if os.path.exists(path):
                st.session_state[f'{actor_type}s_df'] = pd.read_excel(path)
            else:
                st.session_state[f"msg_{actor_type}"] = "⚠️ Charger d'abord les acteurs"
                return
        except Exception:
            st.session_state[f"msg_{actor_type}"] = "❌ Erreur chargement acteurs"
            return

    df_actors = st.session_state[f'{actor_type}s_df']
    pdl_col = _find_pdl_column(df_actors)
    if not pdl_col:
        st.session_state[f"msg_{actor_type}"] = "❌ Colonne PDL introuvable"
        return

    # Build PDL map
    pdl_to_bat = {}
    for idx, row in df_actors.iterrows():
        pdl = str(row.get(pdl_col, '')).strip()
        bat = str(row.get('Bâtiment', ''))
        if pdl and pdl != 'nan':
            pdl_to_bat[pdl] = bat

    # Collect files from uploads
    files_to_process = []
    for uf in uploaded_files:
        fname = getattr(uf, 'name', 'unknown')
        fbytes = uf.read()
        if fname.lower().endswith('.zip'):
            try:
                z = zipfile.ZipFile(io.BytesIO(fbytes))
                for zi in z.infolist():
                    if not zi.is_dir() and zi.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
                        files_to_process.append((os.path.basename(zi.filename), z.read(zi)))
            except Exception:
                pass
        else:
            files_to_process.append((fname, fbytes))

    if not files_to_process:
        st.session_state[f"msg_{actor_type}"] = "⚠️ Aucun fichier valide"
        return

    # Process and save curves
    curves_dir = os.path.join(DATA_DIR, curves_subdir)
    os.makedirs(curves_dir, exist_ok=True)

    matched = 0
    for fname, fbytes in files_to_process:
        pdl = _extract_pdl_from_filename(fname)
        if pdl and pdl in pdl_to_bat:
            bat = pdl_to_bat[pdl]
            _, ext = os.path.splitext(fname)
            if not ext:
                ext = '.csv'
            out_name = f"{pdl}_{_sanitize_name(bat)}_curve_{_timestamp()}{ext}"
            out_path = os.path.join(curves_dir, out_name)
            try:
                with open(out_path, 'wb') as f:
                    f.write(fbytes)
                matched += 1
                # Update actor status
                try:
                    idx = df_actors.index[df_actors[pdl_col].astype(str).str.strip() == pdl][0]
                    df_actors.at[idx, 'Statut'] = 'has_curve'
                except Exception:
                    pass
            except Exception:
                pass

    # Save updated actor dataframe
    try:
        _save_dataframe(df_actors, f'{actor_type}s.xlsx')
        st.session_state[f'{actor_type}s_df'] = df_actors
    except Exception:
        pass

    st.session_state[f"msg_{actor_type}"] = f"✅ {matched}/{len(files_to_process)} courbes appariées"


# ============================================================================
# RENDERING: ACTOR ROWS (COMPACT)
# ============================================================================

def render_actor_row(actor_row: pd.Series, actor_index: int, actor_type: str, 
                     curves_directory: str, pdl_col: str):
    """Render ultra-compact actor row: name | PDL | status | actions."""
    bat = str(actor_row.get('Bâtiment', ''))
    pdl = str(actor_row.get(pdl_col, '')).strip() if pdl_col else ''
    statut = str(actor_row.get('Statut', ''))
    has_curve = (statut == 'has_curve') or _has_curve_in_dir(pdl, curves_directory)

    # Row with minimal spacing
    cols = st.columns([2.5, 1.5, 0.4, 2], gap="small")

    with cols[0]:
        st.caption(f"**{bat}**")
    with cols[1]:
        st.caption(pdl if pdl else "—")
    with cols[2]:
        st.caption("✅" if has_curve else "❌")
    with cols[3]:
        # Action buttons (horizontal, gap="small")
        action_cols = st.columns([1, 1], gap="small")
        with action_cols[0]:
            if st.button("Dupliquer", key=f"dup_{actor_type}_{actor_index}", 
                        use_container_width=True):
                ok, msg = duplicate_actor(actor_type, actor_index)
                st.session_state[f"msg_{actor_type}"] = f"✅ {msg}" if ok else f"❌ {msg}"
                st.rerun()
        with action_cols[1]:
            if st.button("Supprimer", key=f"del_{actor_type}_{actor_index}", 
                        use_container_width=True):
                ok, msg = delete_actor(actor_type, actor_index)
                st.session_state[f"msg_{actor_type}"] = f"✅ {msg}" if ok else f"❌ {msg}"
                st.rerun()


# ============================================================================
# RENDERING: ACTOR LIST (SCROLLABLE)
# ============================================================================

def render_actor_list(df: pd.DataFrame, actor_type: str, curves_directory: str):
    """Render actor list in fixed-height scrollable container."""
    # Container is ALWAYS rendered (fixed height reserved)
    with st.container(height=H_ACTOR_LIST_CONTAINER, border=True):
        if df is None or df.empty:
            st.caption("_Aucun acteur importé_")
            return

        pdl_col = _find_pdl_column(df)
        if pdl_col is None:
            st.caption("⚠️ Colonne PDL introuvable")
            return

        # Header
        h_cols = st.columns([2.5, 1.5, 0.4, 2], gap="small")
        with h_cols[0]:
            st.caption("**Bâtiment**")
        with h_cols[1]:
            st.caption("**PDL**")
        with h_cols[2]:
            st.caption("**État**")
        with h_cols[3]:
            st.caption("**Actions**")
        
        st.divider()

        # Rows
        for idx, row in df.iterrows():
            render_actor_row(row, idx, actor_type, curves_directory, pdl_col)


# ============================================================================
# RENDERING: ACTOR BLOCK (REUSABLE)
# ============================================================================

def render_actor_block(block_title: str, actor_type: str, curves_subdir: str):
    """Render complete actor block with fixed heights."""
    st.subheader(block_title, anchor=False)

    # Two-column layout: 25% uploads | 75% list
    left_col, right_col = st.columns([0.25, 0.75], gap="medium")

    # ===== LEFT: UPLOADS (FIXED HEIGHT RESERVED) =====
    with left_col:
        st.markdown("**📤 Importer**")
        
        # Container to reserve height even if empty
        with st.container(height=H_UPLOADER_CONTAINER, border=False):
            # Actor file uploader
            actors_file = st.file_uploader(
                "Excel acteurs",
                type=["xlsx", "xls"],
                key=f"upload_{actor_type}"
            )
            if actors_file is not None:
                process_actors_file(actors_file, actor_type)

            st.write("")  # Small spacer

            # Curves file uploader
            curves_files = st.file_uploader(
                "Courbes (CSV/ZIP)",
                accept_multiple_files=True,
                type=["csv", "xlsx", "xls", "zip"],
                key=f"upload_curves_{actor_type}"
            )
            if curves_files:
                process_curves_files(curves_files, actor_type, curves_subdir)

    # ===== RIGHT: ACTOR LIST (FIXED HEIGHT) =====
    with right_col:
        st.markdown("**📋 Acteurs**")
        
        # Display message if any
        msg = st.session_state.get(f"msg_{actor_type}", "")
        if msg:
            st.caption(msg)
        
        # Render list in fixed-height container
        df_actors = st.session_state.get(f'{actor_type}s_df')
        curves_dir = os.path.join(DATA_DIR, curves_subdir)
        render_actor_list(df_actors, actor_type, curves_dir)


# ============================================================================
# MAIN PAGE
# ============================================================================

# Header
st.markdown("## 🏗️ Projet ACC")
project_name = st.text_input(
    "Nom du projet",
    value=st.session_state["project_name"],
    key="project_name_input",
    label_visibility="collapsed"
)
st.session_state["project_name"] = project_name

st.divider()

# Consumers block
render_actor_block("👥 Consommateurs", "consumer", "consumers_curves")
st.divider()

# Producers block
render_actor_block("⚡ Producteurs", "producer", "producers_curves")

st.divider()

# Footer - Final button
col_spacer, col_button = st.columns([0.7, 0.3])
with col_button:
    if st.button("🚀 Importer les acteurs", key="btn_final", use_container_width=True):
        consumers_df = st.session_state["consumers_df"]
        producers_df = st.session_state["producers_df"]

        if consumers_df is None and producers_df is None:
            st.session_state["final_msg"] = "⚠️ Chargez au moins un fichier"
        else:
            c_count = len(consumers_df) if consumers_df is not None else 0
            p_count = len(producers_df) if producers_df is not None else 0
            st.session_state["final_msg"] = f"✅ Projet '{project_name}' prêt | Consommateurs: {c_count} | Producteurs: {p_count}"

# Display final message
if st.session_state.get("final_msg"):
    st.caption(st.session_state["final_msg"])
