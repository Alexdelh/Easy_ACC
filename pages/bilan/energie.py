import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import plotly.express as px
import plotly.colors as pc
import plotly.graph_objects as go


def render():
    """Render the Bilan Énergétique page."""
    st.markdown("""
    <style>
        .big-title { font-size: 36px; font-weight: 700; }
        .sub-title { font-size: 22px; font-weight: 600; }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)


    header_left, header_right = st.columns([5, 2])

    with header_left:
        st.markdown("""
            <h1 style='margin:0; padding:0;'>
                Easy ACC ⚡
            </h1>
        """, unsafe_allow_html=True)

    with header_right:
        # Titre Aide
        st.markdown("""
            <div style='text-align:right; font-size:20px; margin-top:10px;'>
                Aide
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # CSS boutons
        st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end;
            }

            div.stButton > button {
                background-color: #1F8A4C;
                color: white;
                border-radius: 8px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
                border: none;
                width: 180px;   /* largeur fixe pour alignement parfait */
            }

            div.stButton > button:hover {
                background-color: #166b3a;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)

        st.button("📄 Exporter PDF")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

#     ## Donut taux de couverture (exemple statique) 
#     ## production_totale = 1591
#     ## consommation_totale = 1220
#     ## taux_couverture = round((consommation_totale / production_totale) * 100, 1)
    
    # ===============================
    # 🔋 RÉCUPÉRATION DES DONNÉES
    # ===============================

    df_prod = st.session_state.get("df_prod")
    df_conso = st.session_state.get("df_conso")

    if df_prod is None or df_conso is None:
        st.warning("Données de production ou de consommation manquantes.")
        return

    # ===============================
    # 📊 CALCULS GLOBAUX
    # ===============================

    production_totale = df_prod.sum().sum()
    consommation_totale = df_conso.sum().sum()

    taux_couverture = 0
    if consommation_totale > 0:  # éviter division par zéro
        taux_couverture = round((production_totale / consommation_totale) * 100, 1)
    
    
    
#     # ===============================
#     # 🔁 INITIALISATION DES SÉLECTIONS
#     # ===============================

#     consumers_list = list(df_conso.columns)
#     producers_list = list(df_prod.columns)

#     if "selected_consumers" not in st.session_state:
#         st.session_state.selected_consumers = consumers_list

#     if "selected_producers" not in st.session_state:
#         st.session_state.selected_producers = producers_list

#     selected_consumers = st.session_state.selected_consumers
#     selected_producers = st.session_state.selected_producers

#     # ===============================
#     # 📊 CALCUL SELON SÉLECTION
#     # ===============================

#     if selected_producers:
#         production_totale = df_prod[selected_producers].sum().sum()
#     else:
#         production_totale = 0

#     if selected_consumers:
#         consommation_totale = df_conso[selected_consumers].sum().sum()
#     else:
#         consommation_totale = 0

#     if consommation_totale > 0:
#         taux_couverture = round((production_totale / consommation_totale) * 100, 1)
#     else:
#         taux_couverture = 0
    
    col_title, col_right = st.columns([4, 2])
    # with col_right:
    #     st.markdown("""
    #     <style>
    #         div.stButton > button:first-child {
    #             background-color: #1F8A4C; color: white; border-radius: 8px; padding: 0.45rem 1rem; font-weight: 600;
    #         }
    #         div.stButton > button:first-child:hover { background-color: #166b3a; color: white; }
    #     </style>
    #     """, unsafe_allow_html=True)
    #     st.button("📄 Exporter PDF")
        # st.write("Période : 31 jan 2024 – 31 jan 2025")
    with col_title:
        st.markdown("<h2 style='text-align:left; margin-top:20px; font-weight:bold;'>Taux de couverture</h2>", unsafe_allow_html=True)

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

    #with donut_col:
        #fig = go.Figure(data=[go.Pie(
            #values=[taux_couverture, 100 - taux_couverture],
            #hole=0.7,
            #marker=dict(colors=["#1F8A4C", "#A8D5BA"]),
            #textinfo='none', hoverinfo='skip'
        #)])
        #fig.update_layout(
            #showlegend=False,
            #annotations=[dict(text=f"{taux_couverture}%", x=0.5, y=0.5, font=dict(size=32, color="#1F8A4C"), showarrow=False)],
            #margin=dict(l=0, r=0, t=20, b=0), height=280
        #)
        #st.plotly_chart(fig, use_container_width=True)
    
    with donut_col:
        fig = go.Figure(data=[go.Pie(
            values=[production_totale, consommation_totale],
            hole=0.7,
            marker=dict(colors=["#1F8A4C", "#A8D5BA"]),
            labels=["Production totale", "Consommation totale"],
            textinfo='none',
            hoverinfo='value+label'
        )])
        fig.update_layout(
            showlegend=False,
            annotations=[dict(text=f"{taux_couverture}%", x=0.5, y=0.5, font=dict(size=32, color="#1F8A4C"), showarrow=False)],
            margin=dict(l=0, r=0, t=20, b=0), height=280
        )
        st.plotly_chart(fig, use_container_width=True)

    
    
    
    
    
#     # Choix des acteurs (exemple)
    
#     #st.markdown("---")
#     #st.markdown("### Choix des acteurs")
#     #col_left_space, col_content, col_right_space = st.columns([2, 3, 1])
#     #with col_content:
#         #col_conso, col_prod = st.columns([2, 2])
#         #with col_conso:
#             #st.markdown("#### Consommateurs")
#             #select_all_consumers = st.checkbox("Tous les consommateurs", value=True)
#             #selected_consumers = [f"Consommateur {i}" for i in range(1, 10)] if select_all_consumers else st.multiselect(
#                 #"Sélectionnez les consommateurs", [f"Consommateur {i}" for i in range(1, 10)], default=[]
#             #)
#             #st.markdown("**Sélection consommateurs :**")
#             #for c in selected_consumers: st.markdown(f"- {c}")
#         #with col_prod:
#             #st.markdown("#### Producteurs")
#             #select_all_producers = st.checkbox("Tous les producteurs", value=True)
#             #selected_producers = [f"Producteur {i}" for i in range(1, 10)] if select_all_producers else st.multiselect(
#                 #"Sélectionnez les producteurs", [f"Producteur {i}" for i in range(1, 10)], default=[]
#             #)
#             #st.markdown("**Sélection producteurs :**")
#             #for p in selected_producers: st.markdown(f"- {p}")
    
#     # ===============================
#     # Choix des acteurs
#     # ===============================
#     st.markdown("---")
#     st.markdown("### Choix des acteurs")
#     col_left_space, col_content, col_right_space = st.columns([2, 3, 1])

#     with col_content:
#         col_conso, col_prod = st.columns([2, 2])

#         # Consommateurs
#         with col_conso:
#             st.markdown("#### Consommateurs")
#             df_conso = st.session_state.get("df_conso")
#             if df_conso is not None:
#                 consumers_list = list(df_conso.columns)
#             else:
#                 st.warning("Aucune donnée de consommation disponible.")
#                 consumers_list = []

#             select_all_consumers = st.checkbox("Tous les consommateurs", value=True, key="select_all_conso")
#             if select_all_consumers:
#                 selected_consumers = consumers_list
#             else:
#                 if consumers_list:
#                     selected_consumers = st.multiselect(
#                         "Sélectionnez les consommateurs", consumers_list, default=consumers_list
#                     )
#                 else:
#                     selected_consumers = []

#             st.markdown("**Sélection consommateurs :**")
#             for c in selected_consumers:
#                 st.markdown(f"- {c}")

#         # Producteurs
#         with col_prod:
#             st.markdown("#### Producteurs")
#             df_prod = st.session_state.get("df_prod")
#             if df_prod is not None:
#                 producers_list = list(df_prod.columns)
#             else:
#                 st.warning("Aucune donnée de production disponible.")
#                 producers_list = []

#             select_all_producers = st.checkbox("Tous les producteurs", value=True, key="select_all_prod")
#             if select_all_producers:
#                 selected_producers = producers_list
#             else:
#                 if producers_list:
#                     selected_producers = st.multiselect(
#                         "Sélectionnez les producteurs", producers_list, default=producers_list
#                     )
#                 else:
#                     selected_producers = []

#             st.markdown("**Sélection producteurs :**")
#             for p in selected_producers:
#                 st.markdown(f"- {p}")
















# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import seaborn as sns

# def render():
#     """Render the Bilan Énergétique page."""
#     st.markdown("""
#     <style>
#         .big-title { font-size: 36px; font-weight: 700; }
#         .sub-title { font-size: 22px; font-weight: 600; }
#         .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
#         div.stButton > button:first-child {
#             background-color: #1F8A4C; color: white; border-radius: 8px;
#             padding: 0.45rem 1rem; font-weight: 600;
#         }
#         div.stButton > button:first-child:hover { background-color: #166b3a; color: white; }
#     </style>
#     """, unsafe_allow_html=True)

#     # ===============================
#     # 🔝 HEADER
#     # ===============================
#     header_left, header_right = st.columns([6, 1])
#     with header_left:
#         st.markdown("<h1 style='margin:0; padding:0;'>Easy ACC ⚡</h1>", unsafe_allow_html=True)
#     with header_right:
#         st.markdown("<div style='text-align:right; font-size:20px; margin-bottom:5px;'>Aide</div>", unsafe_allow_html=True)
        
#         # Bouton juste en dessous de "Aide", aligné à droite
#         st.markdown("""
#         <style>
#             div.stButton > button:first-child {
#                 background-color: #1F8A4C; 
#                 color: white; 
#                 border-radius: 8px; 
#                 padding: 0.45rem 1rem; 
#                 font-weight: 600;
#                 min-width: 150px; /* largeur minimale du bouton */
#             }
#             div.stButton > button:first-child:hover { 
#                 background-color: #166b3a; 
#                 color: white; 
#             }
#         </style>
#         """, unsafe_allow_html=True)
#         st.button("📄 Exporter PDF")

#     st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

#     # ===============================
#     # 🔋 RÉCUPÉRATION DES DONNÉES
#     # ===============================
#     df_prod = st.session_state.get("df_prod")
#     df_conso = st.session_state.get("df_conso")

#     if df_prod is None or df_conso is None:
#         st.warning("Données de production ou de consommation manquantes.")
#         return

#     consumers_list = list(df_conso.columns)
#     producers_list = list(df_prod.columns)

#     # ===============================
#     # 👥 CHOIX DES ACTEURS (avant le donut !)
#     # ===============================
#     st.markdown("---")
#     st.markdown("### Choix des acteurs")

#     # Initialisation par défaut pour éviter NameError
#     selected_consumers = consumers_list
#     selected_producers = producers_list

#     col_left_space, col_actors, col_right_space = st.columns([2, 3, 1])
#     with col_actors:
#         col_conso, col_prod = st.columns(2)

#         with col_conso:
#             st.markdown("#### Consommateurs")
#             select_all_consumers = st.checkbox("Tous les consommateurs", value=True, key="select_all_conso")
#             if not select_all_consumers:
#                 selected_consumers = st.multiselect(
#                     "Sélectionnez les consommateurs", consumers_list, default=consumers_list
#                 )
#             st.markdown("**Sélection consommateurs :**")
#             for c in selected_consumers:
#                 st.markdown(f"- {c}")

#         with col_prod:
#             st.markdown("#### Producteurs")
#             select_all_producers = st.checkbox("Tous les producteurs", value=True, key="select_all_prod")
#             if not select_all_producers:
#                 selected_producers = st.multiselect(
#                     "Sélectionnez les producteurs", producers_list, default=producers_list
#                 )
#             st.markdown("**Sélection producteurs :**")
#             for p in selected_producers:
#                 st.markdown(f"- {p}")

#     # ===============================
#     # 📊 CALCULS GLOBAUX (après la sélection)
#     # ===============================
#     production_totale = df_prod[selected_producers].sum().sum() if selected_producers else 0
#     consommation_totale = df_conso[selected_consumers].sum().sum() if selected_consumers else 0
#     taux_couverture = round((production_totale / consommation_totale) * 100, 1) if consommation_totale > 0 else 0

#     # ===============================
#     # 🍩 DONUT (après les calculs basés sur la sélection)
#     # ===============================
#     st.markdown("---")
#     st.markdown("<h3 style='margin-top:0;'>Taux de couverture</h3>", unsafe_allow_html=True)
#     #_, col_title, _ = st.columns([1, 4, 2])
#     #with col_title:
#         #st.markdown("<div class='big-title'>Taux de couverture</div>", unsafe_allow_html=True)

#     left_legend, donut_col, _ = st.columns([1.2, 2, 1])
#     with left_legend:
#         st.markdown("""
#             <div style='font-size:16px; margin-top:30px;'>
#                 <div style='display:flex; align-items:center; margin-bottom:8px;'>
#                     <div style='width:14px; height:14px; background-color:#1F8A4C; margin-right:8px;'></div>
#                     Production totale
#                 </div>
#                 <div style='display:flex; align-items:center; margin-bottom:8px;'>
#                     <div style='width:14px; height:14px; background-color:#A8D5BA; margin-right:8px;'></div>
#                     Consommation totale
#                 </div>
#             </div>
#         """, unsafe_allow_html=True)

#     with donut_col:
#         fig = go.Figure(data=[go.Pie(
#             values=[production_totale, consommation_totale],
#             hole=0.7,
#             marker=dict(colors=["#1F8A4C", "#A8D5BA"]),
#             labels=["Production totale", "Consommation totale"],
#             textinfo='none',
#             hoverinfo='value+label'
#         )])
#         fig.update_layout(
#             showlegend=False,
#             annotations=[dict(
#                 text=f"{taux_couverture}%",
#                 x=0.5, y=0.5,
#                 font=dict(size=32, color="#1F8A4C"),
#                 showarrow=False
#             )],
#             margin=dict(l=0, r=0, t=20, b=0),
#             height=280
#         )
#         st.plotly_chart(fig, use_container_width=True)

    
    
    
    
    
    
    
    # Donuts (exemples)
    def colorblind_palette(n):
        base_colors = sns.color_palette("colorblind")
        colors = [f'rgba({int(r*255)},{int(g*255)},{int(b*255)},1)' for r,g,b in base_colors]
        return [colors[i % len(colors)] for i in range(n)]
    
    def display_legend(labels, values, colors):
        for l, v, c in zip(labels, values, colors):
            st.markdown(f"<span style='color:{c}; font-weight:bold;'>●</span> {l}: {v} kWh", unsafe_allow_html=True)

    def donut_total_kwh(values, labels):
        total = sum(values)
        colors = colorblind_palette(len(values))
        fig = go.Figure(data=[go.Pie(values=values, labels=labels, hole=0.7, marker=dict(colors=colors), textinfo='none', hoverinfo='label+value')])
        fig.update_layout(annotations=[dict(text=f"{total} kWh", font_size=22, showarrow=False, x=0.5, y=0.5)], margin=dict(t=20, b=20, l=20, r=20), width=350, height=350, showlegend=False)
        return fig, colors
    
    def compute_metrics(df_prod, df_conso, mode):
        """
        Calcule pour chaque pas de temps :
        - le surplus par producteur (total)
        - pour la consommation ACC : autoproduction partagée et fourniture de complément (totaux pour les donuts)
        - autoproduction partagée à chaque pas de temps (DataFrame pour les courbes côté consommateurs)
        - autoproduction réellement consommée à chaque pas de temps par producteur (DataFrame côté producteurs)
        """
        # Totaux cumulés pour les donuts
        surplus_prod = {p: 0 for p in df_prod.columns}
        auto_partage_total = {c: 0 for c in df_conso.columns}
        fourn_compl_total = {c: 0 for c in df_conso.columns}

        # Valeurs à chaque pas de temps pour les courbes
        auto_partage_df = pd.DataFrame(0, index=df_conso.index, columns=df_conso.columns)
        auto_prod_df = pd.DataFrame(0, index=df_prod.index, columns=df_prod.columns)

        n_rows = min(len(df_prod), len(df_conso))

        for t in range(n_rows):
            prod_total = df_prod.iloc[t].sum()
            if prod_total == 0:
                continue

            surplus_total = 0

            # ==================== Calcul autopartage consommateurs ====================
            if mode == "statique":
                consumer_percentages = st.session_state.get("consumer_percentages", {})
                for c in df_conso.columns:
                    allocated = prod_total * (consumer_percentages.get(c, 0) / 100)
                    conso_real = df_conso.iloc[t][c]

                    if conso_real <= allocated:
                        auto_partage_total[c] += conso_real
                        auto_partage_df.loc[df_conso.index[t], c] = conso_real
                        surplus_total += allocated - conso_real
                    else:
                        auto_partage_total[c] += allocated
                        auto_partage_df.loc[df_conso.index[t], c] = allocated
                        fourn_compl_total[c] += conso_real - allocated

            elif mode == "dynamique_defaut":
                conso_total = df_conso.iloc[t].sum()
                if conso_total == 0:
                    continue
                for c in df_conso.columns:
                    coef = df_conso.iloc[t][c] / conso_total
                    allocated = prod_total * coef
                    conso_real = df_conso.iloc[t][c]

                    if conso_real <= allocated:
                        auto_partage_total[c] += conso_real
                        auto_partage_df.loc[df_conso.index[t], c] = conso_real
                        surplus_total += allocated - conso_real
                    else:
                        auto_partage_total[c] += allocated
                        auto_partage_df.loc[df_conso.index[t], c] = allocated
                        fourn_compl_total[c] += conso_real - allocated

            elif mode == "dynamique_simple":
                consumer_priorities = st.session_state.get("consumer_priorities", {})
                consumer_group_keys = st.session_state.get("consumer_group_keys", {})

                groups = {}
                for c, pr in consumer_priorities.items():
                    groups.setdefault(pr, []).append(c)

                production_restante = prod_total

                for pr in sorted(groups.keys()):
                    members = groups[pr]
                    group_conso = df_conso.iloc[t][members].sum()
                    if production_restante <= 0:
                        break

                    prod_for_group = min(production_restante, group_conso)
                    group_mode = consumer_group_keys.get(pr, {}).get("mode", "default")

                    if group_mode == "static":
                        group_percentages = consumer_group_keys.get(pr, {}).get("percentages", {})
                        for c in members:
                            allocated = prod_for_group * (group_percentages.get(c, 0) / 100)
                            conso_real = df_conso.iloc[t][c]
                            if conso_real <= allocated:
                                auto_partage_total[c] += conso_real
                                auto_partage_df.loc[df_conso.index[t], c] = conso_real
                                surplus_total += allocated - conso_real
                            else:
                                auto_partage_total[c] += allocated
                                auto_partage_df.loc[df_conso.index[t], c] = allocated
                                fourn_compl_total[c] += conso_real - allocated
                    else:
                        if group_conso > 0:
                            for c in members:
                                coef = df_conso.iloc[t][c] / group_conso
                                allocated = prod_for_group * coef
                                auto_partage_df.loc[df_conso.index[t], c] = min(allocated, df_conso.iloc[t][c])
                                auto_partage_total[c] += min(allocated, df_conso.iloc[t][c])
                                # pas de surplus interne pour dynamique par défaut

                    production_restante -= prod_for_group

                if production_restante > 0:
                    surplus_total += production_restante

            # ==================== Répartition du surplus par producteur ====================
            for p in df_prod.columns:
                prod_p = df_prod.iloc[t][p]
                surplus_p = surplus_total * (prod_p / prod_total)
                surplus_prod[p] += surplus_p

                # ==================== Calcul autoproduction consommée par producteur ====================
                auto_prod_df.loc[df_prod.index[t], p] = prod_p - surplus_p

        return surplus_prod, auto_partage_total, fourn_compl_total, auto_partage_df, auto_prod_df

    #prod_labels = ["Producteur 1", "Producteur 2", "Producteur 3"]
    #prod_values = [20, 35, 15]
    
    # ===============================
    # 🔋 RÉCUPÉRATION PROD DYNAMIQUE
    # ===============================

    prod_series = df_prod.select_dtypes(include='number').sum().round().astype(int)

    prod_values = prod_series.tolist()
    prod_labels = prod_series.index.tolist()
    
    mode_map = {
    "Clé par défaut": "dynamique_defaut",
    "Clé statique (pourcentages par consommateur)": "statique",
    "Clé dynamique simple": "dynamique_simple"
    } 
    mode_ui = st.session_state.get("repartition_mode", "Clé par défaut")
    mode = mode_map.get(mode_ui, "dynamique_defaut")
    
    # Affichage de la clé de répartition utilisée, plus gros et espacée
    st.markdown(f"<br><h5 style='text-align:left;'>Clé de répartition utilisée : {mode_ui}</h3><br>", unsafe_allow_html=True)
    
    surplus_dict, auto_dict, compl_dict, conso_df, prod_df = compute_metrics(df_prod, df_conso, mode)
    
    surplus_labels = list(surplus_dict.keys())
    surplus_values = [round(v) for v in surplus_dict.values()]
    
    # Somme sur la période pour le donut
    auto_total = sum(auto_dict.values())
    compl_total = sum(compl_dict.values())

    conso_labels = ["Autoproduction partagée", "Fourniture de complément"]
    conso_values = [round(auto_total), round(compl_total)]
    
    # Calcul dynamique pour le Donut 4
    surplus_total = sum(surplus_dict.values())

    acc_labels = ["Surplus de production", "Autoconsommation totale"]
    acc_values = [round(surplus_total), round(auto_total)]

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Titres sur une seule ligne
    col1_title, col2_title, col3_title, col4_title = st.columns(4)
    col1_title.markdown("<h4 style='text-align:center;'>Production</h4>", unsafe_allow_html=True)
    col2_title.markdown("<h4 style='text-align:center;'>Surplus de production</h4>", unsafe_allow_html=True)
    col3_title.markdown("<h4 style='text-align:center;'>Consommation ACC</h4>", unsafe_allow_html=True)
    col4_title.markdown("<h4 style='text-align:center;'>Production ACC</h4>", unsafe_allow_html=True)

    # Donuts sur une seule ligne
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        fig, colors = donut_total_kwh(prod_values, prod_labels)
        st.plotly_chart(fig, use_container_width=False)
        display_legend(prod_labels, prod_values, colors)

    with col2:
        fig, colors = donut_total_kwh(surplus_values, surplus_labels)
        st.plotly_chart(fig, use_container_width=False)
        display_legend(surplus_labels, surplus_values, colors)

    with col3:
        fig, colors = donut_total_kwh(conso_values, conso_labels)
        st.plotly_chart(fig, use_container_width=False)
        display_legend(conso_labels, conso_values, colors)

    with col4:
        fig, colors = donut_total_kwh(acc_values, acc_labels)
        st.plotly_chart(fig, use_container_width=False)
        display_legend(acc_labels, acc_values, colors)
    
    
    
    
    
    
    
    # ===============================
    # 🔹 Choix des acteurs pour les courbes
    # ===============================
    st.markdown("---")
    st.markdown("### Choix des courbes à afficher")
    col_left_space, col_content, col_right_space = st.columns([1, 4, 1])

    with col_content:
        col_conso, col_prod = st.columns([2, 2])

        # --- Consommateurs ---
        with col_conso:
            st.markdown("#### Consommateurs")
            df_conso = st.session_state.get("df_conso")
            consumers_list = list(df_conso.columns) if df_conso is not None else []

            select_all_conso = st.checkbox("Tous les consommateurs", value=True, key="select_all_conso")
            if select_all_conso:
                selected_consumers = consumers_list
            else:
                selected_consumers = st.multiselect(
                    "Sélectionnez les consommateurs", consumers_list, default=consumers_list
                )

            st.markdown("**Sélection consommateurs :**")
            for c in selected_consumers:
                st.markdown(f"- {c}")

        # --- Producteurs ---
        with col_prod:
            st.markdown("#### Producteurs")
            df_prod = st.session_state.get("df_prod")
            producers_list = list(df_prod.columns) if df_prod is not None else []

            select_all_prod = st.checkbox("Tous les producteurs", value=True, key="select_all_prod")
            if select_all_prod:
                selected_producers = producers_list
            else:
                selected_producers = st.multiselect(
                    "Sélectionnez les producteurs", producers_list, default=producers_list
                )

            st.markdown("**Sélection producteurs :**")
            for p in selected_producers:
                st.markdown(f"- {p}")


    # ==============================
    # FILTRAGE DATAFRAMES
    # ==============================

    df_conso_selected = df_conso[selected_consumers] if selected_consumers else pd.DataFrame()
    df_prod_selected = df_prod[selected_producers] if selected_producers else pd.DataFrame()


    # =========================================================
    # ================= CONSOMMATION ==========================
    # =========================================================

    if not df_conso_selected.empty:

        df_conso_plot = df_conso_selected.copy()
        df_auto_conso_plot = conso_df[selected_consumers].copy()

        n_conso = len(df_conso_plot.columns)
        n_auto = len(df_auto_conso_plot.columns)

        # Palettes dynamiques infinies
        bleu_palette = pc.sample_colorscale(
            "Blues",
            np.linspace(0.35, 1, max(n_conso, 1))
        )

        rouge_palette = pc.sample_colorscale(
            "Oranges",
            np.linspace(0.35, 1, max(n_auto, 1))
        )

        fig_conso = px.line(
            df_conso_plot,
            y=df_conso_plot.columns,
            color_discrete_sequence=bleu_palette,
            title="Courbes de Consommation"
        )

        # Ajout autoconsommation (ligne continue rouge/orange)
        for i, c in enumerate(df_auto_conso_plot.columns):
            fig_conso.add_scatter(
                x=df_auto_conso_plot.index,
                y=df_auto_conso_plot[c],
                mode="lines",
                name=f"{c} (Autoproduite)",
                line=dict(
                    color=rouge_palette[i],
                    width=2
                )
            )

        fig_conso.update_layout(
            legend_title="",
            xaxis_title="Pas de temps",
            yaxis_title="kWh"
        )

        # On garde ta config zoom
        fig_conso.update_yaxes(fixedrange=True)

        st.plotly_chart(fig_conso, use_container_width=True)

    else:
        st.info("Aucune consommation sélectionnée.")


    # =========================================================
    # ================= PRODUCTION ============================
    # =========================================================

    if not df_prod_selected.empty:

        # Production brute
        df_prod_plot = df_prod_selected.copy()

        # Autoproduction réellement consommée par producteur
        df_auto_prod_plot = prod_df[df_prod_plot.columns]  # on prend juste les producteurs sélectionnés

        n_prod = len(df_prod_plot.columns)

        # Palette de couleurs
        bleu_palette = pc.sample_colorscale(
            "Blues",
            np.linspace(0.35, 1, max(n_prod, 1))
        )

        rouge_palette = pc.sample_colorscale(
            "Oranges",
            np.linspace(0.35, 1, max(n_prod, 1))
        )

        # Graphique production brute
        fig_prod = px.line(
            df_prod_plot,
            y=df_prod_plot.columns,
            color_discrete_sequence=bleu_palette,
            title="Courbes de Production"
        )

        # Graphique autoproduite (orange)
        for i, p in enumerate(df_auto_prod_plot.columns):
            fig_prod.add_scatter(
                x=df_auto_prod_plot.index,
                y=df_auto_prod_plot[p],
                mode="lines",
                name=f"{p} (Autoconsommée)",
                line=dict(
                    color=rouge_palette[i],
                    width=2
                )
            )

        # Mise en forme
        fig_prod.update_layout(
            legend_title="",
            xaxis_title="Pas de temps",
            yaxis_title="kWh"
        )

        fig_prod.update_yaxes(fixedrange=True)

        st.plotly_chart(fig_prod, use_container_width=True)

    else:
        st.info("Aucune production sélectionnée.")
    
    
    
    
    
    
    
    
    
    
    # #Graphes
    # st.markdown("---")
    # months = ["Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan"]
    # data = {
    #     "Month": months,
    #     "Consommation Totale": [1000,1100,1250,1350,1591,1450,1500,1550,1600,1700,1800,1900],
    #     "Consommation Autoconsommée": [700,750,800,850,900,910,930,950,975,1000,1020,1050],
    #     "Production Totale": [1200,1250,1300,1400,1591,1500,1600,1650,1700,1800,1900,2000],
    #     "Production Autoconsommée": [800,820,850,880,900,950,980,1000,1025,1050,1100,1150],
    # }
    # df = pd.DataFrame(data)
    # fig_conso = px.line(df, x="Month", y=["Consommation Totale", "Consommation Autoconsommée"]); fig_conso.update_layout(title="Rapport de Consommation", legend_title="")
    # fig_prod = px.line(df, x="Month", y=["Production Totale", "Production Autoconsommée"]); fig_prod.update_layout(title="Rapport de Production", legend_title="")
    # st.plotly_chart(fig_conso, use_container_width=True); st.plotly_chart(fig_prod, use_container_width=True)