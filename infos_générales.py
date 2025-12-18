"""
Easy ACC — Definition Scenario Wizard
Multi-step wizard for defining ACC scenarios

Layout:
- Left column (narrow): Step indicator (non-clickable)
- Right column (wide): Step content
- Navigation via "Suivant" button (becomes "Générer le scénario" at last step)
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(page_title="Définir Scénario ACC", layout="wide", initial_sidebar_state="collapsed")

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = os.path.join(os.path.dirname(__file__), "ACC_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Define all steps
STEPS = [
    {"id": 0, "title": "Informations générales", "key": "general_info"},
    {"id": 1, "title": "Points d'injection", "key": "injection_points"},
    {"id": 2, "title": "Points de soutirage", "key": "consumption_points"},
    {"id": 3, "title": "Points de stockage", "key": "storage_points"},
    {"id": 4, "title": "Clés de répartition", "key": "distribution_keys"},
    {"id": 5, "title": "Paramètres financiers", "key": "financial_params"},
]

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "current_step" not in st.session_state:
    st.session_state["current_step"] = 0

if "scenario_data" not in st.session_state:
    st.session_state["scenario_data"] = {
        "general_info": {},
        "injection_points": [],
        "consumption_points": [],
        "storage_points": [],
        "distribution_keys": {},
        "financial_params": {},
    }


# ============================================================================
# HELPERS
# ============================================================================

def save_scenario_draft(scenario_name: str = "draft"):
    """Save current scenario draft to JSON."""
    try:
        file_path = os.path.join(DATA_DIR, f"scenario_{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(st.session_state["scenario_data"], f, ensure_ascii=False, indent=2)
        return True, f"Scénario sauvegardé: {file_path}"
    except Exception as e:
        return False, f"Erreur sauvegarde: {str(e)[:50]}"


def go_to_next_step():
    """Advance to next step."""
    if st.session_state["current_step"] < len(STEPS) - 1:
        st.session_state["current_step"] += 1


def is_last_step():
    """Check if current step is last."""
    return st.session_state["current_step"] == len(STEPS) - 1


# ============================================================================
# STEP RENDER FUNCTIONS
# ============================================================================

def render_general_info():
    """Step 1: General information about the ACC scenario."""
    st.write("### Informations générales du scénario ACC")
    st.write("")
    
    # Scenario name
    scenario_name = st.text_input(
        "Nom du scénario",
        value=st.session_state["scenario_data"]["general_info"].get("name", ""),
        key="general_scenario_name"
    )
    st.session_state["scenario_data"]["general_info"]["name"] = scenario_name
    
    # Description
    description = st.text_area(
        "Description",
        value=st.session_state["scenario_data"]["general_info"].get("description", ""),
        height=100,
        key="general_description"
    )
    st.session_state["scenario_data"]["general_info"]["description"] = description
    
    # Start date
    start_date = st.date_input(
        "Date de début",
        key="general_start_date"
    )
    st.session_state["scenario_data"]["general_info"]["start_date"] = str(start_date)
    
    # End date
    end_date = st.date_input(
        "Date de fin",
        key="general_end_date"
    )
    st.session_state["scenario_data"]["general_info"]["end_date"] = str(end_date)
    
    st.write("")


def render_injection_points():
    """Step 2: Define injection points (producers)."""
    st.write("### Points d'injection (producteurs)")
    st.write("")
    
    st.info("Définir les points d'injection d'énergie (producteurs, sources)")
    
    # Load consumers to display available producers
    try:
        producers_path = os.path.join(DATA_DIR, "producers.xlsx")
        if os.path.exists(producers_path):
            df_producers = pd.read_excel(producers_path)
            st.write(f"**{len(df_producers)} producteurs disponibles**")
            st.dataframe(df_producers[["Bâtiment", "Point de livraison"]] if "Point de livraison" in df_producers.columns else df_producers, use_container_width=True)
        else:
            st.warning("Aucun fichier producteurs trouvé. Importez d'abord les producteurs sur la page d'accueil.")
    except Exception as e:
        st.error(f"Erreur lecture producteurs: {str(e)[:50]}")
    
    st.write("")
    st.write("_À compléter: sélection et configuration des points d'injection_")
    st.write("")


def render_consumption_points():
    """Step 3: Define consumption points (consumers)."""
    st.write("### Points de soutirage (consommateurs)")
    st.write("")
    
    st.info("Définir les points de soutirage d'énergie (consommateurs, charges)")
    
    # Load consumers to display available consumers
    try:
        consumers_path = os.path.join(DATA_DIR, "consumers.xlsx")
        if os.path.exists(consumers_path):
            df_consumers = pd.read_excel(consumers_path)
            st.write(f"**{len(df_consumers)} consommateurs disponibles**")
            st.dataframe(df_consumers[["Bâtiment", "Point de livraison"]] if "Point de livraison" in df_consumers.columns else df_consumers, use_container_width=True)
        else:
            st.warning("Aucun fichier consommateurs trouvé. Importez d'abord les consommateurs sur la page d'accueil.")
    except Exception as e:
        st.error(f"Erreur lecture consommateurs: {str(e)[:50]}")
    
    st.write("")
    st.write("_À compléter: sélection et configuration des points de soutirage_")
    st.write("")


def render_storage_points():
    """Step 4: Define storage points."""
    st.write("### Points de stockage")
    st.write("")
    
    st.info("Définir les points de stockage d'énergie (batteries, réservoirs, etc.)")
    
    st.write("_À compléter: configuration des points de stockage_")
    st.write("")


def render_distribution_keys():
    """Step 5: Define distribution keys (sharing rules)."""
    st.write("### Clés de répartition")
    st.write("")
    
    st.info("Définir les clés de répartition entre les acteurs (règles d'attribution)")
    
    st.write("_À compléter: configuration des clés de répartition_")
    st.write("")


def render_financial_params():
    """Step 6: Define financial parameters."""
    st.write("### Paramètres financiers")
    st.write("")
    
    st.info("Définir les paramètres financiers du scénario (prix, tarifs, etc.)")
    
    st.write("_À compléter: configuration des paramètres financiers_")
    st.write("")


# Map steps to render functions
STEP_RENDERERS = [
    render_general_info,
    render_injection_points,
    render_consumption_points,
    render_storage_points,
    render_distribution_keys,
    render_financial_params,
]


# ============================================================================
# MAIN PAGE
# ============================================================================

st.markdown("## 🎯 Définir un Scénario ACC")
st.write("")

# Two-column layout: left (narrow) for steps, right (wide) for content
left_col, right_col = st.columns([1, 4], gap="medium")

# ===== LEFT COLUMN: STEP INDICATOR =====
with left_col:
    st.markdown("**📍 Étapes**")
    st.write("")
    
    for idx, step in enumerate(STEPS):
        is_current = idx == st.session_state["current_step"]
        is_completed = idx < st.session_state["current_step"]
        
        if is_current:
            st.markdown(f"**▶ {idx + 1}. {step['title']}**", help="Étape courante")
        elif is_completed:
            st.markdown(f"✅ {idx + 1}. {step['title']}", help="Complétée")
        else:
            st.markdown(f"⭕ {idx + 1}. {step['title']}", help="À venir")
        
        st.write("")

# ===== RIGHT COLUMN: STEP CONTENT =====
with right_col:
    # Render current step
    current_step_renderer = STEP_RENDERERS[st.session_state["current_step"]]
    current_step_renderer()
    
    # Navigation buttons
    st.divider()
    
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
    
    with nav_col1:
        if st.session_state["current_step"] > 0:
            if st.button("⬅️ Précédent", use_container_width=True):
                st.session_state["current_step"] -= 1
                st.rerun()
    
    with nav_col3:
        if is_last_step():
            if st.button("🚀 Générer le scénario", use_container_width=True, type="primary"):
                # Save scenario
                ok, msg = save_scenario_draft(st.session_state["scenario_data"].get("general_info", {}).get("name", "untitled"))
                if ok:
                    st.success(msg)
                    st.write("Scénario généré et sauvegardé!")
                    # Reset to step 0 for next scenario
                    st.session_state["current_step"] = 0
                    st.session_state["scenario_data"] = {
                        "general_info": {},
                        "injection_points": [],
                        "consumption_points": [],
                        "storage_points": [],
                        "distribution_keys": {},
                        "financial_params": {},
                    }
                    st.rerun()
                else:
                    st.error(msg)
        else:
            if st.button("Suivant ➡️", use_container_width=True, type="primary"):
                go_to_next_step()
                st.rerun()




