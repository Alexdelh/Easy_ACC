import streamlit as st
import datetime

DEFAULTS = {
    "project_name": "",
    "postal_code": "",
    "distance_constraint": "2 km",
    "operation_type": "Ouverte",
    "start_date": datetime.date(2024, 1, 1),
    "end_date": datetime.date(2024, 12, 31),
    "injections_df": None,
    "points_injection": [],
    "points_soutirage": [],
    "consumers_df": None,
    "producers_df": None,
    "current_phase": "precalibrage",
    "precalibrage_page": 0,
    "bilan_page": 1,
    "scenario_generated": False,
    # Paramètres de répartition
    "repartition_mode": "Clé par défaut (pourcentages)",
    "surplus_mode": "Clé par défaut (prorata puissance)",
    "consumer_percentages": {},
    "consumer_priorities": {},
    "seasonal_participation": {},
}


def init_session_state():
    """Initialize Streamlit session_state with standard keys and defaults."""
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
