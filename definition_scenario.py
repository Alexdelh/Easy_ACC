"""
Easy ACC - Interface pour visualiser et sélectionner consommateurs/producteurs.

Layout 3 colonnes :
- Gauche : Sélection consommateurs/producteurs avec Statut
- Centre : Carte interactive (Folium) avec distance & cercles
- Droite : Haut=Taux de couverture, Bas=Clé de répartition (3 onglets)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_folium import st_folium
from functions import (
    show_map_with_radius, STATUT_CHOICES
)
import import_consumers, import_producers
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Easy ACC",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("Easy ACC ⚡ - Gestion Consommateurs & Producteurs")

# ============================================================================
# SESSION STATE
# ============================================================================

if 'consumers_df' not in st.session_state:
    st.session_state['consumers_df'] = None
if 'producers_df' not in st.session_state:
    st.session_state['producers_df'] = None
if 'selected_consumers' not in st.session_state:
    st.session_state['selected_consumers'] = set()
if 'selected_producers' not in st.session_state:
    st.session_state['selected_producers'] = set()

# ============================================================================
# DONNÉES D'EXEMPLE
# ============================================================================

if st.session_state['consumers_df'] is None:
    # example_consumers = pd.DataFrame({
    #     'Bâtiment': ['École Jean Jaurès', 'Mairie', 'Bibliothèque', 'Salle des fêtes', 'Centre social'],
    #     'Commune': ['Paris', 'Paris', 'Paris', 'Paris', 'Paris'],
    #     'Priorité': [1, 2, 1, 3, 2],
    #     'Nombre': [100, 200, 150, 50, 120],
    #     'Type de compteur': ['T1', 'T2', 'T1', 'T1', 'T2'],
    #     'Lat': [45.8566, 48.8600, 48.8550, 48.8580, 48.8570],
    #     'Long': [2.3522, 2.3550, 2.3480, 2.3600, 2.3450],
    #     'Puissance de raccordement (kVA)': [6, 9, 6, 3, 6],
    #     'Statut': [None, None, None, None, None],
    #     'Activé': [True, True, True, False, True],
    #     'Boucle': [1, 1, 2, 1, 2],
    #     'Adresse': ['Rue 1', 'Rue 2', 'Rue 3', 'Rue 4', 'Rue 5'],
    #     'Code Postal': [75001, 75001, 75002, 75002, 75003],
    #     'Source': ['A', 'B', 'A', 'B', 'A'],
    #     'Point de livraison': [1, 2, 1, 2, 1],
    #     'Fournisseur de complément': [None, None, None, None, None],
    #     'Type de contrat': ['C1', 'C2', 'C1', 'C1', 'C2'],
    #     'Plages temporelles': ['9-18', '9-18', '9-17', '8-20', '9-18'],
    #     'Utilisation': [None, None, None, None, None],
    #     'Puissance souscrite HPH (kVA)': [6, 9, 6, 3, 6],
    #     'Puissance souscrite HCH (kVA)': [3, 6, 3, 1.5, 3],
    #     'Puissance souscrite HPB (kVA)': [0, 0, 0, 0, 0],
    #     'Puissance souscrite HCB (kVA)': [0, 0, 0, 0, 0],
    # })

    example_consumers = pd.read_excel("ACC_data/consumers.xlsx")
    example_consumers['Statut'] = None
    st.session_state['consumers_df'] = example_consumers

if st.session_state['producers_df'] is None:

    example_producers = pd.read_excel("ACC_data/producers.xlsx")
    example_producers['Statut'] = None
    st.session_state['producers_df'] = example_producers
    st.session_state['producers_df'] = example_producers

st.info("📌 Utilisation de données d'exemple")

# ============================================================================
# LAYOUT - 3 COLONNES
# ============================================================================

left_col, center_col, right_col = st.columns([1.2, 2, 1.2], gap="medium")

# ============================================================================
# COLONNE GAUCHE - SÉLECTION
# ============================================================================

with left_col:
    st.header("🏢 Sélection")
    
    # Consommateurs
    with st.expander("👥 Consommateurs", expanded=True):
        if st.session_state['consumers_df'] is not None and len(st.session_state['consumers_df']) > 0:
            consumers_df = st.session_state['consumers_df'].copy()
            edit_df = consumers_df[['Bâtiment', 'Commune', 'Priorité', 'Nombre']].copy()
            edit_df.insert(0, 'Sélectionner', False)
            edit_df['Statut'] = consumers_df['Statut']
            
            edited = st.data_editor(
                edit_df,
                column_config={
                    'Sélectionner': st.column_config.CheckboxColumn('✓', width='small'),
                    'Bâtiment': st.column_config.TextColumn('Bâtiment', width='large', disabled=True),
                    'Commune': st.column_config.TextColumn('Commune', width='small', disabled=True),
                    'Priorité': st.column_config.NumberColumn('Priorité', width='small', disabled=True),
                    'Nombre': st.column_config.NumberColumn('Nombre', width='small', disabled=True),
                    'Statut': st.column_config.SelectboxColumn('Statut', width='medium', options=STATUT_CHOICES),
                },
                hide_index=True,
                use_container_width=True,
                key='consumers_editor'
            )
            
            st.session_state['selected_consumers'] = set(edited[edited['Sélectionner']].index)
            for idx, row in edited.iterrows():
                st.session_state['consumers_df'].at[idx, 'Statut'] = row['Statut']
            
            st.caption(f"✓ {len(st.session_state['selected_consumers'])} / {len(consumers_df)}")
    
    # Producteurs
    with st.expander("⚡ Producteurs", expanded=True):
        if st.session_state['producers_df'] is not None and len(st.session_state['producers_df']) > 0:
            producers_df = st.session_state['producers_df'].copy()
            edit_df = producers_df[['Bâtiment', 'Commune']].copy()
            edit_df.insert(0, 'Sélectionner', False)
            edit_df['Statut'] = producers_df['Statut']
            
            edited = st.data_editor(
                edit_df,
                column_config={
                    'Sélectionner': st.column_config.CheckboxColumn('✓', width='small'),
                    'Bâtiment': st.column_config.TextColumn('Bâtiment', width='large', disabled=True),
                    'Commune': st.column_config.TextColumn('Commune', width='small', disabled=True),
                    'Statut': st.column_config.SelectboxColumn('Statut', width='medium', options=STATUT_CHOICES),
                },
                hide_index=True,
                use_container_width=True,
                key='producers_editor'
            )
            
            st.session_state['selected_producers'] = set(edited[edited['Sélectionner']].index)
            for idx, row in edited.iterrows():
                st.session_state['producers_df'].at[idx, 'Statut'] = row['Statut']
            
            st.caption(f"⚡ {len(st.session_state['selected_producers'])} / {len(producers_df)}")

# ============================================================================
# COLONNE CENTRALE - CARTE AVEC DISTANCE & CERCLES
# ============================================================================

with center_col:
    st.header("🗺️ Carte Interactive")
    
    # Sélection distance
    distance = st.selectbox("Distance (km)", [2, 5, 10, 20], index=2)
    
    if st.session_state['consumers_df'] is not None and st.session_state['producers_df'] is not None:
        # Collecter points
        points = []
        
        for idx in st.session_state['selected_consumers']:
            if idx < len(st.session_state['consumers_df']):
                row = st.session_state['consumers_df'].iloc[idx]
                if pd.notna(row['Lat']) and pd.notna(row['Long']):
                    points.append({
                        "name": row['Bâtiment'],
                        "lat": float(row['Lat']),
                        "lon": float(row['Long'])
                    })
        
        for idx in st.session_state['selected_producers']:
            if idx < len(st.session_state['producers_df']):
                row = st.session_state['producers_df'].iloc[idx]
                if pd.notna(row['Lat']) and pd.notna(row['Long']):
                    points.append({
                        "name": row['Bâtiment'],
                        "lat": float(row['Lat']),
                        "lon": float(row['Long'])
                    })
        
        if points:
            try:
                # Afficher carte avec cercles et centroïde optimal
                m, centroid, inside, outside = show_map_with_radius(points, radius_km=distance, zoom=12)
                st_folium(m, width=700, height=600)
                
                st.subheader("📊 Analyse")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Points inside", len(inside))
                with col2:
                    st.metric("Points outside", len(outside))
                
                if outside:
                    st.warning(f"⚠️ {len(outside)} points hors rayon")
            
            except Exception as e:
                st.error(f"Erreur carte: {e}")
        else:
            st.info("👈 Sélectionnez des acteurs pour voir la carte")

# ============================================================================
# COLONNE DROITE - TAUX COUVERTURE + CLÉ RÉPARTITION
# ============================================================================

with right_col:
    # ---- TAUX DE COUVERTURE (haut) ----
    st.header("📊 Taux de Couverture")
    
    if st.session_state['consumers_df'] is not None and st.session_state['producers_df'] is not None:
        # Calculer sommes
        consommation_total = 0
        production_total = 0
        
        for idx in st.session_state['selected_consumers']:
            if idx < len(st.session_state['consumers_df']):
                row = st.session_state['consumers_df'].iloc[idx]
                consommation_total += float(row.get('Puissance de raccordement (kVA)', 0))
        
        for idx in st.session_state['selected_producers']:
            if idx < len(st.session_state['producers_df']):
                row = st.session_state['producers_df'].iloc[idx]
                production_total += float(row.get('Puissance de raccordement (kVA)', 0))
        
        if consommation_total > 0 or production_total > 0:
            # Pie chart
            labels = ['Production', 'Consommation']
            values = [production_total, consommation_total]
            colors = ['#4CAF50', '#FF6B6B']
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4, marker=dict(colors=colors))])
            fig.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            
            # Métriques
            st.metric("Production (kVA)", f"{production_total:.1f}")
            st.metric("Consommation (kVA)", f"{consommation_total:.1f}")
            if consommation_total > 0:
                coverage = (production_total / consommation_total) * 100
                st.metric("Taux couverture", f"{coverage:.1f}%")
        else:
            st.info("Sélectionnez des acteurs")
    
    st.divider()
    
    # ---- CLÉ DE RÉPARTITION (bas) ----
    st.header("🔑 Clé de Répartition")
    
    if st.session_state['consumers_df'] is not None and len(st.session_state['selected_consumers']) > 0:
        consumers_df = st.session_state['consumers_df']
        selected_idx = sorted(list(st.session_state['selected_consumers']))
        
        # Créer DataFrame
        cle_data = []
        for idx in selected_idx:
            row = consumers_df.iloc[idx]
            cle_data.append({
                'Bâtiment': row['Bâtiment'],
                'Commune': row['Commune'],
                'Priorité': row['Priorité'],
                'Nombre': row['Nombre'],
                'Type de compteur': row['Type de compteur'],
                'Statut': row['Statut'],
                '% Répartition': 100.0 / len(selected_idx),
            })
        
        cle_df = pd.DataFrame(cle_data)
        
        # Onglets
        tabs = st.tabs(["Statique", "Dynamique simple", "Dynamique par défaut"])
        
        with tabs[0]:
            st.subheader("Mode Statique")
            cle_edited = st.data_editor(
                cle_df,
                column_config={
                    'Bâtiment': st.column_config.TextColumn('Bâtiment', disabled=True),
                    'Commune': st.column_config.TextColumn('Commune', disabled=True),
                    'Priorité': st.column_config.NumberColumn('Priorité', disabled=True),
                    'Nombre': st.column_config.NumberColumn('Nombre', disabled=True),
                    'Type de compteur': st.column_config.TextColumn('Type', disabled=True),
                    'Statut': st.column_config.TextColumn('Statut', disabled=True),
                    '% Répartition': st.column_config.NumberColumn('% Rép.', format='%.2f'),
                },
                hide_index=True,
                use_container_width=True,
                key='cle_statique'
            )
            
            total = cle_edited['% Répartition'].sum()
            st.metric("Total", f"{total:.2f}%")
            
            if st.button("🔧 Normaliser"):
                if total > 0:
                    cle_edited['% Répartition'] = cle_edited['% Répartition'] * 100.0 / total
                    st.success("✓ Normalisé")
                    st.rerun()
        
        with tabs[1]:
            st.info("Mode dynamique simple - À implémenter selon priorité/consommation")
        
        with tabs[2]:
            st.info("Mode dynamique par défaut - À implémenter selon algorithme")
    
    else:
        st.info("Sélectionnez des consommateurs")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("© Easy ACC 2025")
with col2:
    if st.session_state['consumers_df'] is not None:
        st.caption(f"👥 {len(st.session_state['consumers_df'])} consommateurs")
with col3:
    if st.session_state['producers_df'] is not None:
        st.caption(f"⚡ {len(st.session_state['producers_df'])} producteurs")
