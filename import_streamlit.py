"""
Import page for Easy ACC — compact 2-column layout for consumers + load curves
Left column: Import consumers Excel (minimal UI)
Right column: Import load curves (multiple/ZIP, minimal UI)
Below: Producers + production curves
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re
import unicodedata
import io
import zipfile

st.set_page_config(page_title="Importer - Easy ACC", layout="wide")
st.title("📥 Importer vos données Easy ACC")

DATA_DIR = os.path.join(os.path.dirname(__file__), "ACC_data")
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================================================
# HELPERS
# ============================================================================

def _sanitize_name(name: str) -> str:
    """Return a filesystem-safe name."""
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
    """Find PDL column (case-insensitive) using normalized comparisons.

    This function normalizes column names (removes diacritics and spaces)
    and looks for common tokens such as 'point de livraison', 'pdl' or 'livraison'.
    """
    if df is None:
        return None
    for col in df.columns:
        col_norm = _normalize_text(col)
        if ('pointdelivraison' in col_norm) or ('pdl' in col_norm) or ('livraison' in col_norm):
            return col
    return None

def _extract_pdl_from_filename(fname: str) -> str:
    """Extract 14-digit PDL from filename."""
    match = re.search(r'\b(\d{14})\b', fname)
    return match.group(1) if match else ""

def _save_dataframe(df: pd.DataFrame, target_filename: str) -> str:
    """Save dataframe to DATA_DIR. Return path (may be alternate if overwrite blocked)."""
    target_path = os.path.join(DATA_DIR, target_filename)
    timestamp = _timestamp()
    try:
        df.to_excel(target_path, index=False)
        return target_path
    except PermissionError:
        alt_path = os.path.join(DATA_DIR, f"{target_filename.rstrip('.xlsx')}_saved_{timestamp}.xlsx")
        df.to_excel(alt_path, index=False)
        return alt_path
    except Exception:
        raise

# ============================================================================
# SECTION 1: CONSUMERS (LEFT) + LOAD CURVES (RIGHT) - 2 COLUMN LAYOUT
# ============================================================================

st.subheader("Étape 1: Consommateurs & Courbes de charge")

col1, col2 = st.columns(2)

# ============================================================================
# LEFT COLUMN: CONSUMERS IMPORT (COMPACT)
# ============================================================================
with col1:
    st.markdown("**Importer Consommateurs**")
    consumers_file = st.file_uploader(
        "Fichier Excel",
        type=["xlsx", "xls"],
        key="upload_consumers",
        label_visibility="collapsed"
    )

    # compact import button
    if consumers_file is not None:
        if st.button("Importer consommateurs", key="btn_import_consumers"):
            try:
                xls = pd.read_excel(consumers_file, sheet_name=None)
                sheets = list(xls.keys())
                if len(sheets) > 1:
                    # only prompt sheet selection when necessary
                    sheet = st.selectbox("Feuille", sheets, key='sheet_consumers')
                    df_consumers = pd.read_excel(consumers_file, sheet_name=sheet)
                else:
                    df_consumers = pd.read_excel(consumers_file)

                # Validate columns
                if 'Bâtiment' not in df_consumers.columns:
                    st.error("❌ Colonne 'Bâtiment' manquante")
                elif _find_pdl_column(df_consumers) is None:
                    st.error("❌ Colonne 'Point de livraison' manquante")
                else:
                    if 'Statut' not in df_consumers.columns:
                        df_consumers['Statut'] = None

                    # Save and persist
                    _save_dataframe(df_consumers, 'consumers.xlsx')
                    st.session_state['consumers_df'] = df_consumers
                    st.success(f"✅ {len(df_consumers)} acteurs importés")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)[:120]}")
    else:
        st.write("")

# ============================================================================
# RIGHT COLUMN: LOAD CURVES IMPORT (COMPACT)
# ============================================================================
with col2:
    st.markdown("**Importer Courbes de charge**")
    load_curves_files = st.file_uploader(
        "Fichiers CSV/Excel/ZIP",
        accept_multiple_files=True,
        type=["csv", "xlsx", "xls", "zip"],
        key="upload_load_curves",
        label_visibility="collapsed"
    )

    # compact import button for curves
    if load_curves_files is not None and st.button("Importer courbes", key="btn_import_curves"):
        # prepare consumers DF
        if 'consumers_df' not in st.session_state:
            try:
                cpath = os.path.join(DATA_DIR, 'consumers.xlsx')
                if os.path.exists(cpath):
                    st.session_state['consumers_df'] = pd.read_excel(cpath)
            except Exception as e:
                st.warning(f"⚠️ Impossible de charger consumers.xlsx: {e}")

        if 'consumers_df' not in st.session_state:
            st.warning("⚠️ Importer d'abord les consommateurs")
            bulk_results = []
        else:
            df_consumers = st.session_state['consumers_df']
            pdl_col = _find_pdl_column(df_consumers)
            bulk_results = []
            matched = []
            unmatched = []
            errors = []

            # build pdl map
            pdl_to_bat = {}
            if pdl_col:
                for idx, row in df_consumers.iterrows():
                    pdl = str(row.get(pdl_col, '')).strip()
                    bat = str(row.get('Bâtiment', ''))
                    if pdl and pdl != 'nan':
                        pdl_to_bat[pdl] = bat

            # collect files (including zip extraction)
            files_to_process = []
            for uf in load_curves_files:
                fname = getattr(uf, 'name', 'unknown')
                fbytes = uf.read()
                if fname.lower().endswith('.zip'):
                    try:
                        z = zipfile.ZipFile(io.BytesIO(fbytes))
                        for zi in z.infolist():
                            if zi.is_dir():
                                continue
                            if zi.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
                                files_to_process.append((os.path.basename(zi.filename), z.read(zi)))
                    except Exception as e:
                        errors.append({'msg': f'Erreur ZIP: {e}'})
                else:
                    files_to_process.append((fname, fbytes))

            curves_dir = os.path.join(DATA_DIR, 'consumers_curves')
            os.makedirs(curves_dir, exist_ok=True)

            for fname, fbytes in files_to_process:
                pdl = _extract_pdl_from_filename(fname)
                if pdl and pdl in pdl_to_bat:
                    bat = pdl_to_bat[pdl]
                    try:
                        _, ext = os.path.splitext(fname)
                        if not ext:
                            ext = '.csv'
                        out_name = f"{pdl}_{_sanitize_name(bat)}_load_curve_{_timestamp()}{ext}"
                        out_path = os.path.join(curves_dir, out_name)
                        with open(out_path, 'wb') as f:
                            f.write(fbytes)
                        matched.append({'pdl': pdl, 'bat': bat})
                        # mark consumer as having curve
                        # find consumer index and update Statut
                        try:
                            idx = df_consumers.index[df_consumers[pdl_col].astype(str).str.strip() == pdl][0]
                            df_consumers.at[idx, 'Statut'] = 'has_curve'
                        except Exception:
                            pass
                    except Exception as e:
                        errors.append({'pdl': pdl or '?', 'msg': str(e)[:120]})
                else:
                    unmatched.append({'pdl': pdl or None})

            # persist updated consumers df
            try:
                _save_dataframe(df_consumers, 'consumers.xlsx')
                st.session_state['consumers_df'] = df_consumers
            except Exception as e:
                errors.append({'msg': f"Erreur sauvegarde consommateurs: {e}"})

            bulk_results = {'matched': matched, 'unmatched': unmatched, 'errors': errors}
            # store results in session for full-width details below
            st.session_state['last_bulk_import'] = bulk_results
            st.success(f"✅ {len(matched)}/{len(files_to_process)} fichiers appariés")


st.markdown("---")

# ============================================================================
# SECTION 2: PRODUCERS (LEFT) + PRODUCTION CURVES (RIGHT) - 2 COLUMN LAYOUT
# ============================================================================

st.subheader("Étape 2: Producteurs & Courbes de production")

col3, col4 = st.columns(2)

# ============================================================================
# LEFT COLUMN: PRODUCERS IMPORT (COMPACT)
# ============================================================================
with col3:
    st.markdown("**Importer Producteurs**")
    producers_file = st.file_uploader(
        "Fichier Excel",
        type=["xlsx", "xls"],
        key="upload_producers",
        label_visibility="collapsed"
    )

    if producers_file is not None:
        try:
            xls = pd.read_excel(producers_file, sheet_name=None)
            sheets = list(xls.keys())
            if len(sheets) > 1:
                sheet = st.selectbox("Feuille", sheets, key='sheet_producers')
                df_producers = pd.read_excel(producers_file, sheet_name=sheet)
            else:
                df_producers = pd.read_excel(producers_file)

            # Validate columns
            if 'Bâtiment' not in df_producers.columns:
                st.error("❌ Colonne 'Bâtiment' manquante")
            elif _find_pdl_column(df_producers) is None:
                st.error("❌ Colonne 'Point de livraison' manquante")
            else:
                if 'Statut' not in df_producers.columns:
                    df_producers['Statut'] = None

                # Save
                _save_dataframe(df_producers, 'producers.xlsx')
                st.session_state['producers_df'] = df_producers
                st.success(f"✅ {len(df_producers)} lignes importées")
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)[:100]}")

# ============================================================================
# RIGHT COLUMN: PRODUCTION CURVES IMPORT (COMPACT)
# ============================================================================
with col4:
    st.markdown("**Importer Courbes de production**")
    prod_curves_files = st.file_uploader(
        "Fichiers CSV/Excel/ZIP",
        accept_multiple_files=True,
        type=["csv", "xlsx", "xls", "zip"],
        key="upload_prod_curves",
        label_visibility="collapsed"
    )

    if prod_curves_files:
        # Load producers database if not in session
        if 'producers_df' not in st.session_state:
            try:
                ppath = os.path.join(DATA_DIR, 'producers.xlsx')
                if os.path.exists(ppath):
                    st.session_state['producers_df'] = pd.read_excel(ppath)
            except Exception as e:
                st.warning(f"⚠️ Impossible de charger producers.xlsx: {e}")

        if 'producers_df' not in st.session_state:
            st.warning("⚠️ Importer d'abord les producteurs")
        else:
            df_producers = st.session_state['producers_df']
            pdl_col = _find_pdl_column(df_producers)

            if pdl_col is None:
                st.error("❌ Colonne 'Point de livraison' introuvable")
            else:
                # Build PDL->Bâtiment map
                pdl_to_bat = {}
                for idx, row in df_producers.iterrows():
                    pdl = str(row.get(pdl_col, '')).strip()
                    bat = str(row.get('Bâtiment', ''))
                    if pdl and pdl != 'nan':
                        pdl_to_bat[pdl] = bat

                # Process uploaded files
                files_to_process = []
                for uf in prod_curves_files:
                    fname = getattr(uf, 'name', 'unknown')
                    fbytes = uf.read()
                    if fname.lower().endswith('.zip'):
                        try:
                            z = zipfile.ZipFile(io.BytesIO(fbytes))
                            for zi in z.infolist():
                                if not zi.is_dir() and zi.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
                                    files_to_process.append((os.path.basename(zi.filename), z.read(zi)))
                        except Exception as e:
                            st.error(f"❌ Erreur ZIP: {e}")
                    else:
                        files_to_process.append((fname, fbytes))

                # Match & save
                results = []
                curves_dir = os.path.join(DATA_DIR, 'producers_curves')
                os.makedirs(curves_dir, exist_ok=True)

                for fname, fbytes in files_to_process:
                    pdl = _extract_pdl_from_filename(fname)
                    if pdl in pdl_to_bat:
                        bat = pdl_to_bat[pdl]
                        _, ext = os.path.splitext(fname)
                        if not ext:
                            ext = '.csv'
                        out_name = f"{pdl}_{_sanitize_name(bat)}_prod_curve_{_timestamp()}{ext}"
                        out_path = os.path.join(curves_dir, out_name)
                        try:
                            with open(out_path, 'wb') as f:
                                f.write(fbytes)
                            results.append({'PDL': pdl, 'Bâtiment': bat, 'Fichier': fname, 'État': '✅'})
                        except Exception as e:
                            results.append({'PDL': pdl, 'Bâtiment': bat, 'Fichier': fname, 'État': f'❌ {e}'})
                    else:
                        results.append({'PDL': pdl if pdl else '?', 'Bâtiment': '?', 'Fichier': fname, 'État': '❌ PDL non trouvé'})

                # Display summary (compact)
                success = sum(1 for r in results if '✅' in r['État'])
                st.success(f"✅ {success}/{len(results)} fichiers")

                # Detailed table in expander
                if results:
                    with st.expander("Voir les détails"):
                        df_results = pd.DataFrame(results)
                        st.dataframe(df_results, use_container_width=True)

st.markdown("---")
st.caption("Tous les fichiers sont sauvegardés dans `ACC_data/` pour utilisation par les autres pages.")

# ============================================================================
# Consumer management: cards, attach/duplicate/delete helpers
# ============================================================================

def generate_unique_name(base_name: str, df: pd.DataFrame) -> str:
    """Return a unique building name by appending _2, _3, ... when needed."""
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


def _has_curve_in_dir(pdl: str, curves_dir: str) -> bool:
    if not pdl:
        return False
    if not os.path.exists(curves_dir):
        return False
    for fn in os.listdir(curves_dir):
        if fn.startswith(pdl + '_'):
            return True
    return False


def attach_curve(actor_type: str, index: int, file_obj) -> tuple:
    """Attach a single uploaded file to actor at index. actor_type in ('consumer','producer')."""
    try:
        key = 'consumers_df' if actor_type == 'consumer' else 'producers_df'
        df_key = st.session_state.get(key)
        if df_key is None:
            return False, "Base non chargée"
        df = df_key
        pdl_col = _find_pdl_column(df)
        if pdl_col is None:
            return False, "Colonne PDL introuvable"
        row = df.iloc[index]
        pdl = str(row.get(pdl_col, '')).strip()
        bat = str(row.get('Bâtiment', ''))
        if not pdl:
            return False, "PDL manquant"

        fbytes = file_obj.read()
        fname = getattr(file_obj, 'name', f"{pdl}.csv")
        _, ext = os.path.splitext(fname)
        if not ext:
            ext = '.csv'

        curves_dir = os.path.join(DATA_DIR, 'consumers_curves' if actor_type == 'consumer' else 'producers_curves')
        os.makedirs(curves_dir, exist_ok=True)
        out_name = f"{pdl}_{_sanitize_name(bat)}_{'load' if actor_type=='consumer' else 'prod'}_curve_{_timestamp()}{ext}"
        out_path = os.path.join(curves_dir, out_name)
        with open(out_path, 'wb') as f:
            f.write(fbytes)

        # update df status
        try:
            st.session_state[key].at[index, 'Statut'] = 'has_curve'
            _save_dataframe(st.session_state[key], f"{ 'consumers' if actor_type=='consumer' else 'producers' }.xlsx")
        except Exception:
            pass
        return True, "Courbe attachée"
    except Exception as e:
        return False, str(e)


def delete_actor(actor_type: str, index: int) -> tuple:
    try:
        key = 'consumers_df' if actor_type == 'consumer' else 'producers_df'
        if key not in st.session_state:
            return False, "Aucune base chargée"
        df = st.session_state[key]
        if index not in df.index:
            return False, "Index introuvable"
        df2 = df.drop(index).reset_index(drop=True)
        st.session_state[key] = df2
        _save_dataframe(df2, f"{ 'consumers' if actor_type=='consumer' else 'producers' }.xlsx")
        return True, "Supprimé"
    except Exception as e:
        return False, str(e)


def duplicate_actor(actor_type: str, index: int) -> tuple:
    try:
        key = 'consumers_df' if actor_type == 'consumer' else 'producers_df'
        if key not in st.session_state:
            return False, "Aucune base chargée"
        df = st.session_state[key]
        if index not in df.index:
            return False, "Index introuvable"
        row = df.iloc[index].copy()
        base_name = str(row.get('Bâtiment', 'copy'))
        new_name = generate_unique_name(base_name, df)
        row['Bâtiment'] = new_name
        df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        st.session_state[key] = df2
        _save_dataframe(df2, f"{ 'consumers' if actor_type=='consumer' else 'producers' }.xlsx")
        return True, f"Dupliqué: {new_name}"
    except Exception as e:
        return False, str(e)


def render_actor_row(actor_type: str, index: int, row: pd.Series, curves_dir: str, pdl_col: str):
    bat = str(row.get('Bâtiment', ''))
    pdl = str(row.get(pdl_col, '')).strip() if pdl_col else ''
    statut = str(row.get('Statut', ''))

    a1, a2, a3, a4 = st.columns([3, 2, 1, 3])
    with a1:
        st.write(bat)
    with a2:
        st.code(pdl, language='')
    with a3:
        has = (statut == 'has_curve') or _has_curve_in_dir(pdl, curves_dir)
        st.write("✔" if has else "✖")
    with a4:
        # inline actions
        if st.button("Importer courbe", key=f"attach_{actor_type}_{index}"):
            st.session_state[f"show_attach_{actor_type}_{index}"] = True
        if st.button("Dupliquer", key=f"dup_{actor_type}_{index}"):
            ok, msg = duplicate_actor(actor_type, index)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
        if st.button("Supprimer", key=f"del_{actor_type}_{index}"):
            ok, msg = delete_actor(actor_type, index)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

        if st.session_state.get(f"show_attach_{actor_type}_{index}"):
            fup = st.file_uploader("Fichier (1)", type=['csv', 'xlsx', 'xls'], key=f"file_attach_{actor_type}_{index}")
            if fup is not None:
                ok, msg = attach_curve(actor_type, index, fup)
                if ok:
                    st.success(msg)
                    st.session_state[f"show_attach_{actor_type}_{index}"] = False
                else:
                    st.error(msg)


def render_actor_list(df: pd.DataFrame, actor_type: str, curves_directory: str):
    """Render a collapsible, paginated, row-based actor list for consumers or producers."""
    total = 0 if df is None else len(df)
    title = f"{ 'Consommateurs' if actor_type=='consumer' else 'Producteurs' } ({total})"
    expanded_key = f"exp_{actor_type}_expanded"
    show_all_key = f"show_all_{actor_type}"

    if expanded_key not in st.session_state:
        st.session_state[expanded_key] = False
    if show_all_key not in st.session_state:
        st.session_state[show_all_key] = False

    with st.expander(title, expanded=False):
        if df is None or df.empty:
            st.info("Aucun acteur.")
            return
        pdl_col = _find_pdl_column(df)
        # pagination: first 10 unless show_all
        if not st.session_state.get(show_all_key):
            display_df = df.head(10)
        else:
            display_df = df

        for idx, row in display_df.reset_index().iterrows():
            real_index = int(row['index'])
            render_actor_row(actor_type, real_index, df.loc[real_index], curves_directory, pdl_col)

        if not st.session_state.get(show_all_key) and len(df) > 10:
            if st.button(f"Afficher plus", key=f"more_{actor_type}"):
                st.session_state[show_all_key] = True


# ============================================================================
# Full-width details and actor lists (below the top columns)
# ============================================================================

st.markdown("---")

# Consumers list (collapsible, paginated)
cons_df = st.session_state.get('consumers_df')
render_actor_list(cons_df, 'consumer', os.path.join(DATA_DIR, 'consumers_curves'))

# Producers list (collapsible, paginated)
prod_df = st.session_state.get('producers_df')
render_actor_list(prod_df, 'producer', os.path.join(DATA_DIR, 'producers_curves'))

# Bulk import details expander (full-width)
if 'last_bulk_import' in st.session_state:
    bulk = st.session_state['last_bulk_import'] or {}
    with st.expander("Détails de l'import des courbes (voir)", expanded=False):
        matched = bulk.get('matched', [])
        unmatched = bulk.get('unmatched', [])
        errors = bulk.get('errors', [])

        st.markdown(f"**Fichiers appariés**: {len(matched)}")
        if matched:
            for m in matched:
                st.write(f"PDL: `{m.get('pdl')}` — {m.get('bat')}")

        st.markdown(f"**PDL non trouvés**: {len(unmatched)}")
        if unmatched:
            for u in unmatched:
                st.write(f"PDL détecté: `{u.get('pdl') or 'aucun'}`")

        st.markdown(f"**Erreurs**: {len(errors)}")
        if errors:
            for e in errors:
                st.write(e.get('msg') or str(e))

