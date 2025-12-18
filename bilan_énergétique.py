import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import datetime

st.set_page_config(layout="wide", page_title="Easy ACC – Taux de couverture")

# ------------------------------------------------------------
# STYLE CSS
# ------------------------------------------------------------
st.markdown("""
<style>
    .big-title {
        font-size: 36px;
        font-weight: 700;
    }
    .sub-title {
        font-size: 22px;
        font-weight: 600;
    }
    .card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


# --------- HEADER ---------

header_left, header_right = st.columns([6, 1])

with header_left:
    st.markdown("""
        <h1 style='margin:0; padding:0;'>
            Easy ACC ⚡
        </h1>
    """, unsafe_allow_html=True)

with header_right:
    st.markdown("""
        <div style='text-align:right; font-size:20px; margin-top:10px;'>
            Aide
        </div>
    """, unsafe_allow_html=True)

# ➕ Ajout d'espace vertical entre les deux blocs
st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# DONUT TAUX DE COUVERTURE
# ------------------------------------------------------------

# Exemple : remplace par tes données
production_totale = 1591
consommation_totale = 1220

taux_couverture = round((consommation_totale / production_totale) * 100, 1)

# -------------------- HEADER DONUT --------------------

col_logo, col_title, col_right = st.columns([1,4,2])

with col_right:
    st.markdown("""
    <style>
        div.stButton > button:first-child {
            background-color: #1F8A4C;
            color: white;
            border-radius: 8px;
            padding: 0.45rem 1rem;
            font-weight: 600;
        }
        div.stButton > button:first-child:hover {
            background-color: #166b3a;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

    # Export PDF
    st.button("📄 Exporter PDF")
    
    # Affichage période

    min_date = datetime.date(2024, 1, 1)
    max_date = datetime.date(2024, 12, 31)

    start_date = st.date_input("Date de début", value=datetime.date(2024,1,1), min_value=min_date, max_value=max_date)
    end_date = st.date_input("Date de fin", value=datetime.date(2024,12,31), min_value=min_date, max_value=max_date)

    # Correction automatique
    if start_date < min_date or start_date > max_date:
        st.error("Date de début hors limites, réinitialisation automatique.")
        start_date = min_date

    if end_date < min_date or end_date > max_date:
        st.error("Date de fin hors limites, réinitialisation automatique.")
        end_date = max_date

    if start_date > end_date:
        st.error("La période de début doit être avant la période de fin.")
        start_date = min_date
        end_date = max_date

    st.write(f"Période : {start_date.strftime('%b %Y')} – {end_date.strftime('%b %Y')}")

with col_title:
    st.markdown("<div class='big-title'>Taux de couverture</div>", unsafe_allow_html=True)



# -------------------- LÉGENDE + DONUT --------------------

left_legend, donut_col, empty = st.columns([1.2, 2, 1])

with left_legend:
    st.markdown("""
        <div style='font-size:16px; margin-top:30px;'>
            <div style='display:flex; align-items:center; margin-bottom:8px;'>
                <div style='width:14px; height:14px; background-color:#1F8A4C; margin-right:8px;'></div>
                Production totale
            </div>
            <div style='display:flex; align-items:center; margin-bottom:8px;'>
                <div style='width:14px; height:14px; background-color:#3CB371; margin-right:8px;'></div>
                Consommation totale
            </div>
        </div>
    """, unsafe_allow_html=True)


# Donut 100% custom
with donut_col:

    fig = go.Figure(data=[go.Pie(
        values=[taux_couverture, 100 - taux_couverture],
        hole=0.7,
        marker=dict(colors=["#1F8A4C", "#D6EDE0"]),  # vert foncé + vert pâle
        textinfo='none',  # pas de labels ni pourcentages autour
        hoverinfo='skip'
    )])

    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f"{taux_couverture}%",
            x=0.5, y=0.5,
            font=dict(size=32, color="#1F8A4C", family="Arial"),
            showarrow=False
        )],
        margin=dict(l=0, r=0, t=20, b=0),
        height=280
    )

    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# CHOIX DES ACTEURS
# ------------------------------------------------------------

st.markdown("---")
st.markdown("### Choix des acteurs")  # titre inchangé

# Colonnes : plus d'espace à gauche pour décaler le bloc à droite
col_left_space, col_content, col_right_space = st.columns([2, 3, 1])

with col_content:
    # Deux colonnes pour consommateurs et producteurs à l'intérieur
    col_conso, col_prod = st.columns([2, 2])  # espace entre colonnes

    # -------------------------
    # CONSOMMATEURS
    # -------------------------
    with col_conso:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("#### Consommateurs", unsafe_allow_html=True)

        select_all_consumers = st.checkbox("Tous les consommateurs", value=True)

        if select_all_consumers:
            selected_consumers = [f"Consommateur {i}" for i in range(1, 10)]
        else:
            selected_consumers = st.multiselect(
                "Sélectionnez les consommateurs",
                [f"Consommateur {i}" for i in range(1, 10)],
                default=[]
            )

        st.markdown("**Sélection consommateurs :**")
        for c in selected_consumers:
            st.markdown(f"- {c}")
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------
    # PRODUCTEURS
    # -------------------------
    with col_prod:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("#### Producteurs", unsafe_allow_html=True)

        select_all_producers = st.checkbox("Tous les producteurs", value=True)

        if select_all_producers:
            selected_producers = [f"Producteur {i}" for i in range(1, 10)]
        else:
            selected_producers = st.multiselect(
                "Sélectionnez les producteurs",
                [f"Producteur {i}" for i in range(1, 10)],
                default=[]
            )

        st.markdown("**Sélection producteurs :**")
        for p in selected_producers:
            st.markdown(f"- {p}")
        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# 4 DONUTS : Production, Surplus, Conso ACC, Production ACC
# ------------------------------------------------------------

# Palette colorblind
def colorblind_palette(n):
    base_colors = sns.color_palette("colorblind")
    colors = [
        f'rgba({int(r*255)},{int(g*255)},{int(b*255)},1)'
        for r, g, b in base_colors
    ]
    return [colors[i % len(colors)] for i in range(n)]

# Couleur par défaut
ACC_BAR_COLOR = colorblind_palette(4)[0]

# Donut avec total au centre
def donut_total_kwh(values):
    total = sum(values)
    colors = colorblind_palette(len(values))

    fig = go.Figure(go.Pie(
        values=values,
        labels=[""] * len(values),
        hole=0.7,
        marker=dict(colors=colors),
        textinfo='none',
        hoverinfo='value'
    ))

    fig.update_layout(
        annotations=[dict(
            text=f"{total} kWh",
            font_size=22,
            showarrow=False,
            x=0.5, y=0.5
        )],
        margin=dict(t=20, b=20, l=20, r=20),
        width=320,
        height=320,
        showlegend=False
    )

    return fig, colors



# Légende séparée
def display_legend(labels, values, colors):
    for l, v, c in zip(labels, values, colors):
        st.markdown(
            f"<span style='color:{c}; font-weight:bold;'>●</span> {l}: {v} kWh",
            unsafe_allow_html=True
        )



# Barre de taux Plotly
def taux_bar_plotly(taux, color):
    fig = go.Figure(go.Bar(
        x=[taux],
        y=[""],
        orientation="h",
        width=0.25,  # épaisseur de la barre
        text=[f"{taux:.1f} %"],
        textposition="outside",  # texte à l'extérieur de la barre
        textfont=dict(size=50),  # texte plus gros
        marker=dict(color=color)
    ))

    fig.update_layout(
        xaxis=dict(range=[0, 100], visible=False),
        yaxis=dict(visible=False),
        height=70,  # hauteur totale du graphe
        margin=dict(l=10, r=50, t=0, b=0),
        showlegend=False
    )

    return fig



# DONNÉES
prod_labels = ["Producteur 1", "Producteur 2", "Producteur 3"]
prod_values = [20, 35, 15]

surplus_labels = prod_labels
surplus_values = [5, 10, 15]

conso_labels = ["Fourniture de complément", "Autoproduction partagée"]
conso_values = [25, 13]

acc_labels = ["Surplus de production", "Autoconsommation totale"]
acc_values = [35, 23]



# CALCUL DES TAUX
taux_autoproduction = conso_values[1] / sum(conso_values) * 100
taux_autoconsommation = acc_values[1] / sum(acc_values) * 100



# AFFICHAGE
st.markdown("<br><br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

# ----- Production
with col1:
    st.markdown("<h3 style='text-align:center;'>Production</h3>", unsafe_allow_html=True)
    fig, colors = donut_total_kwh(prod_values)
    st.plotly_chart(fig, use_container_width=False)
    display_legend(prod_labels, prod_values, colors)

# ----- Surplus de production
with col2:
    st.markdown("<h3 style='text-align:center;'>Surplus de production</h3>", unsafe_allow_html=True)
    fig, colors = donut_total_kwh(surplus_values)
    st.plotly_chart(fig, use_container_width=False)
    display_legend(surplus_labels, surplus_values, colors)

# ----- Consommation ACC
with col3:
    st.markdown("<h3 style='text-align:center;'>Consommation ACC</h3>", unsafe_allow_html=True)
    fig, colors = donut_total_kwh(conso_values)
    st.plotly_chart(fig, use_container_width=False)
    display_legend(conso_labels, conso_values, colors)

    st.markdown(
        "<div style='margin-bottom:2px; font-weight:600;'>Taux d’autoproduction</div>",
        unsafe_allow_html=True
    )
    st.plotly_chart(
        taux_bar_plotly(taux_autoproduction, ACC_BAR_COLOR),
        use_container_width=True
    )

# ----- Production ACC
with col4:
    st.markdown("<h3 style='text-align:center;'>Production ACC</h3>", unsafe_allow_html=True)
    fig, colors = donut_total_kwh(acc_values)
    st.plotly_chart(fig, use_container_width=False)
    display_legend(acc_labels, acc_values, colors)

    st.markdown(
        "<div style='margin-bottom:2px; font-weight:600;'>Taux d’autoconsommation</div>",
        unsafe_allow_html=True
    )
    st.plotly_chart(
        taux_bar_plotly(taux_autoconsommation, ACC_BAR_COLOR),
        use_container_width=True
    )


# ------------------------------------------------------------
# INDICATEURS ÉNERGÉTIQUES + ÉCONOMIQUES
# ------------------------------------------------------------
st.markdown("---")

# Colonnes : vide plus large | bloc énergétique | bloc économique | vide plus large
col_left_space, col_energy, col_econ, col_right_space = st.columns([2.3, 3, 3, 1.7])

with col_energy:
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.markdown("### Indicateurs Énergétiques", unsafe_allow_html=True)
    st.markdown("""
    - Taux de couverture : Value 1  
    - Taux de surplus collectif : Value 2  
    - Taux d’autoproduction collective : Value 3  
    - Taux d’autoconsommation collective : Value 4  
    - Volume total produit : Value 5  
    - Volume total autoconsommé : Value 6  
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_econ:
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.markdown("### Indicateurs Économiques", unsafe_allow_html=True)
    st.markdown("""
    - Économies de fournitures : Value 1  
    - Économies de TURPE : Value 2  
    - Économies de taxes : Value 3  
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# GRAPHIQUES TEMPORELS
# ------------------------------------------------------------

months = ["Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan"]
data = {
    "Month": months,
    "Consommation Totale": [1000,1100,1250,1350,1591,1450,1500,1550,1600,1700,1800,1900],
    "Consommation Autoconsommée": [700,750,800,850,900,910,930,950,975,1000,1020,1050],
    "Production Totale": [1200,1250,1300,1400,1591,1500,1600,1650,1700,1800,1900,2000],
    "Production Autoconsommée": [800,820,850,880,900,950,980,1000,1025,1050,1100,1150]
}

df = pd.DataFrame(data)

# Graph consommation
fig_conso = px.line(df, x="Month", y=["Consommation Totale", "Consommation Autoconsommée"])
fig_conso.update_layout(title="Rapport de Consommation", legend_title="")

# Graph production
fig_prod = px.line(df, x="Month", y=["Production Totale", "Production Autoconsommée"])
fig_prod.update_layout(title="Rapport de Production", legend_title="")

st.markdown("---")
st.plotly_chart(fig_conso, use_container_width=True)

st.plotly_chart(fig_prod, use_container_width=True)
