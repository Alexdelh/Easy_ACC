import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns


def render():
    """Render the Bilan Énergétique page."""
    st.markdown("""
    <style>
        .big-title { font-size: 36px; font-weight: 700; }
        .sub-title { font-size: 22px; font-weight: 600; }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)


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

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    # Donut taux de couverture (exemple statique)
    production_totale = 1591
    consommation_totale = 1220
    taux_couverture = round((consommation_totale / production_totale) * 100, 1)

    col_logo, col_title, col_right = st.columns([1, 4, 2])
    with col_right:
        st.markdown("""
        <style>
            div.stButton > button:first-child {
                background-color: #1F8A4C; color: white; border-radius: 8px; padding: 0.45rem 1rem; font-weight: 600;
            }
            div.stButton > button:first-child:hover { background-color: #166b3a; color: white; }
        </style>
        """, unsafe_allow_html=True)
        st.button("📄 Exporter PDF")
        # st.write("Période : 31 jan 2024 – 31 jan 2025")
    with col_title:
        st.markdown("<div class='big-title'>Taux de couverture</div>", unsafe_allow_html=True)

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

    with donut_col:
        fig = go.Figure(data=[go.Pie(
            values=[taux_couverture, 100 - taux_couverture],
            hole=0.7,
            marker=dict(colors=["#1F8A4C", "#D6EDE0"]),
            textinfo='none', hoverinfo='skip'
        )])
        fig.update_layout(
            showlegend=False,
            annotations=[dict(text=f"{taux_couverture}%", x=0.5, y=0.5, font=dict(size=32, color="#1F8A4C"), showarrow=False)],
            margin=dict(l=0, r=0, t=20, b=0), height=280
        )
        st.plotly_chart(fig, use_container_width=True)

    # Choix des acteurs (exemple)
    st.markdown("---")
    st.markdown("### Choix des acteurs")
    col_left_space, col_content, col_right_space = st.columns([2, 3, 1])
    with col_content:
        col_conso, col_prod = st.columns([2, 2])
        with col_conso:
            st.markdown("#### Consommateurs")
            select_all_consumers = st.checkbox("Tous les consommateurs", value=True)
            selected_consumers = [f"Consommateur {i}" for i in range(1, 10)] if select_all_consumers else st.multiselect(
                "Sélectionnez les consommateurs", [f"Consommateur {i}" for i in range(1, 10)], default=[]
            )
            st.markdown("**Sélection consommateurs :**")
            for c in selected_consumers: st.markdown(f"- {c}")
        with col_prod:
            st.markdown("#### Producteurs")
            select_all_producers = st.checkbox("Tous les producteurs", value=True)
            selected_producers = [f"Producteur {i}" for i in range(1, 10)] if select_all_producers else st.multiselect(
                "Sélectionnez les producteurs", [f"Producteur {i}" for i in range(1, 10)], default=[]
            )
            st.markdown("**Sélection producteurs :**")
            for p in selected_producers: st.markdown(f"- {p}")

    # Donuts (exemples)
    def colorblind_palette(n):
        base_colors = sns.color_palette("colorblind")
        colors = [f'rgba({int(r*255)},{int(g*255)},{int(b*255)},1)' for r,g,b in base_colors]
        return [colors[i % len(colors)] for i in range(n)]

    def donut_total_kwh(values, labels):
        total = sum(values)
        colors = colorblind_palette(len(values))
        fig = go.Figure(data=[go.Pie(values=values, labels=[""]*len(values), hole=0.7, marker=dict(colors=colors), textinfo='none', hoverinfo='label+value')])
        fig.update_layout(annotations=[dict(text=f"{total} kWh", font_size=22, showarrow=False, x=0.5, y=0.5)], margin=dict(t=20, b=20, l=20, r=20), width=350, height=350, showlegend=False)
        return fig, colors

    def display_legend(labels, values, colors):
        for l, v, c in zip(labels, values, colors):
            st.markdown(f"<span style='color:{c}; font-weight:bold;'>●</span> {l}: {v} kWh", unsafe_allow_html=True)

    prod_labels = ["Producteur 1", "Producteur 2", "Producteur 3"]
    prod_values = [20, 35, 15]
    surplus_values = [5, 10, 15]
    conso_labels = ["Fourniture de complément", "Autoproduction partagée"]
    conso_values = [25, 13]
    acc_labels = ["Surplus de production", "Autoconsommation totale"]
    acc_values = [35, 23]

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("<h3 style='text-align:center;'>Production</h3>", unsafe_allow_html=True)
        fig, colors = donut_total_kwh(prod_values, prod_labels); st.plotly_chart(fig, use_container_width=False); display_legend(prod_labels, prod_values, colors)
    with col2:
        st.markdown("<h3 style='text-align:center;'>Surplus de production</h3>", unsafe_allow_html=True)
        fig, colors = donut_total_kwh(surplus_values, prod_labels); st.plotly_chart(fig, use_container_width=False); display_legend(prod_labels, surplus_values, colors)
    with col3:
        st.markdown("<h3 style='text-align:center;'>Consommation ACC</h3>", unsafe_allow_html=True)
        fig, colors = donut_total_kwh(conso_values, conso_labels); st.plotly_chart(fig, use_container_width=False); display_legend(conso_labels, conso_values, colors)
    with col4:
        st.markdown("<h3 style='text-align:center;'>Production ACC</h3>", unsafe_allow_html=True)
        fig, colors = donut_total_kwh(acc_values, acc_labels); st.plotly_chart(fig, use_container_width=False); display_legend(acc_labels, acc_values, colors)

    st.markdown("---")
    months = ["Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan"]
    data = {
        "Month": months,
        "Consommation Totale": [1000,1100,1250,1350,1591,1450,1500,1550,1600,1700,1800,1900],
        "Consommation Autoconsommée": [700,750,800,850,900,910,930,950,975,1000,1020,1050],
        "Production Totale": [1200,1250,1300,1400,1591,1500,1600,1650,1700,1800,1900,2000],
        "Production Autoconsommée": [800,820,850,880,900,950,980,1000,1025,1050,1100,1150],
    }
    df = pd.DataFrame(data)
    fig_conso = px.line(df, x="Month", y=["Consommation Totale", "Consommation Autoconsommée"]); fig_conso.update_layout(title="Rapport de Consommation", legend_title="")
    fig_prod = px.line(df, x="Month", y=["Production Totale", "Production Autoconsommée"]); fig_prod.update_layout(title="Rapport de Production", legend_title="")
    st.markdown("---"); st.plotly_chart(fig_conso, use_container_width=True); st.plotly_chart(fig_prod, use_container_width=True)

    st.markdown('---')
    st.markdown('### Données brutes (debug)')
    # st.write('Points de production:', st.session_state.get('points_production', []))
    # st.write('Points de soutirage (consommateurs):', st.session_state.get('points_soutirage', []))
    # st.write('Résumé:', st.session_state.get('summary'))