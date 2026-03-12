import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import plotly.express as px
import plotly.colors as pc
import plotly.graph_objects as go

def render():
    """Render the Bilan Énergétique page."""
    
    # ===============================
    # STYLES CSS GLOBAUX
    # ===============================
    st.markdown("""
    <style>
        .big-title { font-size: 36px; font-weight: 700; }
        .sub-title { font-size: 22px; font-weight: 600; }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

    # ===============================
    # HEADER : Titre + Bouton Aide/PDF
    # ===============================
    header_left, header_right = st.columns([5, 2])

    with header_left:
        # Titre principal
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

        # CSS personnalisé pour les boutons
        st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end;
            }

            div.stButton > button, div.stDownloadButton > button {
                background-color: #1F8A4C;
                color: white;
                border-radius: 8px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
                border: none;
                width: 180px;   /* largeur fixe pour alignement parfait */
            }

            div.stButton > button:hover, div.stDownloadButton > button:hover {
                background-color: #166b3a;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)

        # Placeholder pour le bouton Export PDF
        export_placeholder = st.empty()
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    
    # ===============================
    # RÉCUPÉRATION DES DONNÉES
    # ===============================
    df_prod = st.session_state.get("df_prod")
    df_conso = st.session_state.get("df_conso")

    if df_prod is None or df_conso is None:
        st.warning("Données de production ou de consommation manquantes.")
        return

    # ===============================
    # CALCULS GLOBAUX : Totaux et taux de couverture
    # ===============================
    production_totale = df_prod.sum().sum()
    consommation_totale = df_conso.sum().sum()

    taux_couverture = 0
    if consommation_totale > 0:  # éviter division par zéro
        taux_couverture = round((production_totale / consommation_totale) * 100, 1)
    
    # Affichage titre Taux de couverture
    col_title, col_right = st.columns([4, 2])
    with col_title:
        st.markdown("<h2 style='text-align:left; margin-top:20px; font-weight:bold;'>Taux de couverture</h2>", unsafe_allow_html=True)

    # Colonnes pour légende et donut
    left_legend, donut_col, empty = st.columns([1.2, 2, 1])
    with left_legend:
        # Légende avec couleur pour production vs consommation
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
    
    # Donut principal pour taux de couverture
    with donut_col:
        fig_donut_main = go.Figure(data=[go.Pie(
            values=[production_totale, consommation_totale],
            hole=0.7,
            marker=dict(colors=["#1F8A4C", "#A8D5BA"]),
            labels=["Production totale", "Consommation totale"],
            textinfo='none',
            hoverinfo='value+label'
        )])
        fig_donut_main.update_layout(
            showlegend=False,
            annotations=[dict(text=f"{taux_couverture}%", x=0.5, y=0.5, font=dict(size=32, color="#1F8A4C"), showarrow=False)],
            margin=dict(l=0, r=0, t=20, b=0), height=280
        )
        st.plotly_chart(fig_donut_main, width="stretch")
        
    # ===============================
    # FONCTIONS UTILITAIRES DONUTS
    # ===============================

    def colorblind_palette(n):
        """Retourne une palette de couleurs adaptée aux daltoniens de longueur n"""
        base_colors = sns.color_palette("colorblind")
        colors = [f'rgba({int(r*255)},{int(g*255)},{int(b*255)},1)' for r,g,b in base_colors]
        return [colors[i % len(colors)] for i in range(n)]
    
    def display_legend(labels, values, colors):
        """Affiche une légende sous forme de texte coloré pour un donut"""
        for l, v, c in zip(labels, values, colors):
            st.markdown(f"<span style='color:{c}; font-weight:bold;'>●</span> {l}: {v} kWh", unsafe_allow_html=True)

    def donut_total_kwh(values, labels):
        """Crée un graphique donut avec le total au centre"""
        total = sum(values)
        colors = colorblind_palette(len(values))
        fig = go.Figure(data=[go.Pie(values=values, labels=labels, hole=0.7, marker=dict(colors=colors), textinfo='none', hoverinfo='label+value')])
        fig.update_layout(
            annotations=[dict(text=f"{total} kWh", font_size=22, showarrow=False, x=0.5, y=0.5)],
            margin=dict(t=20, b=20, l=20, r=20), width=350, height=350, showlegend=False
        )
        return fig, colors
    
    # ===============================
    # CALCUL DES MÉTRIQUES DE RÉPARTITION
    # ===============================
    def compute_metrics(df_prod, df_conso, mode):
        """
        Calcule pour chaque pas de temps :
        - surplus par producteur
        - autoproduction partagée et fourniture de complément pour consommateurs
        - autoproduction consommée par producteur
        Retourne les DataFrames et dictionnaires de totaux
        """
        # Totaux cumulés
        surplus_prod = {p: 0 for p in df_prod.columns}
        auto_partage_total = {c: 0 for c in df_conso.columns}
        fourn_compl_total = {c: 0 for c in df_conso.columns}

        # DataFrames pour courbes temps réel
        auto_partage_df = pd.DataFrame(0, index=df_conso.index, columns=df_conso.columns)
        auto_prod_df = pd.DataFrame(0, index=df_prod.index, columns=df_prod.columns)

        consumer_ACI = st.session_state.get("consumer_ACI", {})

        n_rows = min(len(df_prod), len(df_conso))

        def _deduct_from_producers(cur_prod: dict, amount: float) -> float:
            """Deduct `amount` from producers in-place (largest-first). Returns total actually deducted."""
            if amount <= 0:
                return 0.0
            remaining = amount
            # sort producers by available desc
            for p, avail in sorted(cur_prod.items(), key=lambda x: x[1], reverse=True):
                if remaining <= 0:
                    break
                take = min(cur_prod[p], remaining)
                cur_prod[p] -= take
                remaining -= take
            return amount - remaining

        for t in range(n_rows):

            # Original per-producer production at this timestep
            orig_prod = {p: float(df_prod.iloc[t][p]) for p in df_prod.columns}
            orig_prod_total = sum(orig_prod.values())

            # Current available production (will be decremented when allocated)
            cur_prod = {p: float(v) for p, v in orig_prod.items()}

            # Current consumer demand (will be decremented when satisfied)
            cur_conso = {c: float(df_conso.iloc[t][c]) for c in df_conso.columns}

            if orig_prod_total == 0:
                # Si aucune production → toute consommation devient complément
                for c in df_conso.columns:
                    conso_real = cur_conso[c]
                    auto_partage_df.loc[df_conso.index[t], c] = 0
                    fourn_compl_total[c] += conso_real
                continue

            # ---------- Phase ACI prioritaire ----------
            
            for c in df_conso.columns:
                mapped = consumer_ACI.get(c)
                if isinstance(mapped, str) and mapped in cur_prod:
                    conso_need = cur_conso[c]
                    if conso_need <= 0:
                        continue
                    allocated = min(conso_need, cur_prod[mapped])
                    if allocated > 0:
                        auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + allocated
                        auto_partage_total[c] += allocated
                        cur_conso[c] -= allocated
                        cur_prod[mapped] -= allocated


            surplus_total = 0

            # Recompute remaining production total for subsequent distribution
            prod_total = sum(cur_prod.values())

            # ------------------ MODE STATIQUE / DYNAMIQUE ------------------
            if mode == "statique":
                consumer_percentages = st.session_state.get("consumer_percentages", {})
                for c in df_conso.columns:
                    # remaining demand
                    conso_real = cur_conso[c]
                    allocated = prod_total * (consumer_percentages.get(c, 0) / 100)
                    # allocate from producers
                    if allocated > 0:
                        deducted = _deduct_from_producers(cur_prod, allocated)
                        prod_total -= deducted
                    else:
                        deducted = 0

                    if conso_real <= deducted:
                        auto_partage_total[c] += conso_real
                        auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + conso_real
                        # any surplus from this allocated share becomes surplus_total
                        surplus_total += deducted - conso_real
                        cur_conso[c] = 0
                    else:
                        auto_partage_total[c] += deducted
                        auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + deducted
                        cur_conso[c] -= deducted
                        fourn_compl_total[c] += cur_conso[c]

            elif mode == "dynamique_defaut":
                conso_total = sum(cur_conso.values())
                if conso_total == 0:
                    # Pas de consommation → tout produit restant devient surplus
                    surplus_total += prod_total
                    for c in df_conso.columns:
                        # no additional autoproduction allocated in this phase
                        pass
                    # mark remaining production as surplus after loop
                else:
                    for c in df_conso.columns:
                        conso_real = cur_conso[c]
                        coef = (conso_real / conso_total) if conso_total > 0 else 0
                        allocated = prod_total * coef
                        deducted = _deduct_from_producers(cur_prod, allocated)
                        prod_total -= deducted

                        if conso_real <= deducted:
                            auto_partage_total[c] += conso_real
                            auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + conso_real
                            surplus_total += deducted - conso_real
                            cur_conso[c] = 0
                        else:
                            auto_partage_total[c] += deducted
                            auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + deducted
                            cur_conso[c] -= deducted
                            fourn_compl_total[c] += cur_conso[c]

            elif mode == "dynamique_simple":
                # Gestion par priorités de consommateurs et groupes
                consumer_priorities = st.session_state.get("consumer_priorities", {})
                consumer_group_keys = st.session_state.get("consumer_group_keys", {})

                groups = {}
                for c, pr in consumer_priorities.items():
                    groups.setdefault(pr, []).append(c)

                production_restante = prod_total
                sorted_prios = sorted(groups.keys())

                for i, pr in enumerate(sorted_prios):
                    members = groups[pr]
                    
                    if production_restante <= 0:
                        # Plus de production disponible → tout devient complément
                        for c in members:
                            conso_real = cur_conso[c]
                            auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + 0
                            fourn_compl_total[c] += conso_real
                            cur_conso[c] = 0
                        continue
                    
                    group_conso = df_conso.iloc[t][members].sum()
                    
                    # Si dernier groupe → on alloue tout ce qu'il reste
                    is_last_group = (i == len(sorted_prios) - 1)
                    if is_last_group:
                        prod_for_group = production_restante
                    else:
                        prod_for_group = min(production_restante, group_conso)
                        
                    group_mode = consumer_group_keys.get(pr, {}).get("mode", "default")

                    if group_mode == "static":
                        group_percentages = consumer_group_keys.get(pr, {}).get("percentages", {})
                        for c in members:
                            conso_real = cur_conso[c]
                            allocated = prod_for_group * (group_percentages.get(c, 0) / 100)
                            # deduct from producers
                            deducted = _deduct_from_producers(cur_prod, allocated)
                            production_restante -= deducted

                            if conso_real <= deducted:
                                auto_partage_total[c] += conso_real
                                auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + conso_real
                                surplus_total += deducted - conso_real
                                cur_conso[c] = 0
                            else:
                                auto_partage_total[c] += deducted
                                auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + deducted
                                cur_conso[c] -= deducted
                                fourn_compl_total[c] += cur_conso[c]
                    else:
                        # Distribution proportionnelle par consommation
                        if group_conso > 0:
                            for c in members:
                                conso_real = cur_conso[c]
                                coef = (conso_real / group_conso) if group_conso > 0 else 0
                                allocated = prod_for_group * coef
                                deducted = _deduct_from_producers(cur_prod, allocated)
                                production_restante -= deducted

                                if conso_real <= deducted:
                                    auto_partage_total[c] += conso_real
                                    auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + conso_real
                                    surplus_total += deducted - conso_real
                                    cur_conso[c] = 0
                                else:
                                    auto_partage_total[c] += deducted
                                    auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + deducted
                                    cur_conso[c] -= deducted
                                    fourn_compl_total[c] += cur_conso[c]
                        else:
                            # no group consumption -> all prod_for_group becomes surplus
                            surplus_total += prod_for_group
                            for c in members:
                                auto_partage_df.loc[df_conso.index[t], c] = auto_partage_df.loc[df_conso.index[t], c] + 0


                    production_restante -= prod_for_group

                if production_restante > 0:
                    surplus_total += production_restante

            # ==================== Répartition du surplus par producteur ====================
          
            for p in df_prod.columns:
                if orig_prod_total > 0:
                    surplus_p = surplus_total * (orig_prod[p] / orig_prod_total)
                else:
                    surplus_p = 0.0
                
                surplus_prod[p] += surplus_p

                # Autoproduction réellement consommée = original production - surplus
                auto_prod_df.loc[df_prod.index[t], p] = orig_prod[p] - surplus_p
        return surplus_prod, auto_partage_total, fourn_compl_total, auto_partage_df, auto_prod_df
    
    # ===============================
    # RÉCUPÉRATION PROD DYNAMIQUE ET AFFICHAGE DONUTS
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
    
    st.markdown(f"<br><h5 style='text-align:left;'>Clé de répartition utilisée : {mode_ui}</h3><br>", unsafe_allow_html=True)
    
    surplus_dict, auto_dict, compl_dict, conso_df, prod_df = compute_metrics(df_prod, df_conso, mode)
    
    # Donuts de valeurs totales
    import math
    def safe_round(v):
        if v is None or math.isnan(v):
            return 0
        return round(v)

    surplus_labels = list(surplus_dict.keys())
    surplus_values = [safe_round(v) for v in surplus_dict.values()]
    auto_total = sum(safe_round(v) for v in auto_dict.values())
    compl_total = sum(safe_round(v) for v in compl_dict.values())
    
    conso_labels = ["Autoproduction partagée", "Fourniture de complément"]
    conso_values = [auto_total, compl_total]

    surplus_total = sum(safe_round(v) for v in surplus_dict.values())
    acc_labels = ["Surplus de production", "Autoconsommation totale"]
    acc_values = [surplus_total, auto_total]

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ===============================
    # AFFICHAGE DES DONUTS SUR UNE SEULE LIGNE
    # ===============================
    col1_title, col2_title, col3_title, col4_title = st.columns(4)
    col1_title.markdown("<h4 style='text-align:center;'>Production</h4>", unsafe_allow_html=True)
    col2_title.markdown("<h4 style='text-align:center;'>Surplus de production</h4>", unsafe_allow_html=True)
    col3_title.markdown("<h4 style='text-align:center;'>Consommation ACC</h4>", unsafe_allow_html=True)
    col4_title.markdown("<h4 style='text-align:center;'>Production ACC</h4>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        fig_prod_donut, colors = donut_total_kwh(prod_values, prod_labels)
        st.plotly_chart(fig_prod_donut, width="content")
        display_legend(prod_labels, prod_values, colors)

    with col2:
        fig_surplus_donut, colors = donut_total_kwh(surplus_values, surplus_labels)
        st.plotly_chart(fig_surplus_donut, width="content")
        display_legend(surplus_labels, surplus_values, colors)

    with col3:
        fig_conso_donut, colors = donut_total_kwh(conso_values, conso_labels)
        st.plotly_chart(fig_conso_donut, width="content")
        display_legend(conso_labels, conso_values, colors)

    with col4:
        fig_acc_donut, colors = donut_total_kwh(acc_values, acc_labels)
        st.plotly_chart(fig_acc_donut, width="content")
        display_legend(acc_labels, acc_values, colors)
    
    # ===============================
    # Choix des acteurs pour affichage des courbes
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

    # ===============================
    # FILTRAGE DES DATAFRAMES SÉLECTIONNÉS
    # ===============================
    df_conso_selected = df_conso[selected_consumers] if selected_consumers else pd.DataFrame()
    df_prod_selected = df_prod[selected_producers] if selected_producers else pd.DataFrame()

    fig_conso = px.line(title="Courbes de Consommation") # Default empty fig
    
    # =========================================================
    # ================= CONSOMMATION ==========================
    # =========================================================
    if not df_conso_selected.empty:
        df_conso_plot = df_conso_selected.copy()

        n_conso = len(df_conso_plot.columns)

        # Palette dynamique
        bleu_palette = pc.sample_colorscale(
            "Blues",
            np.linspace(0.35, 1, max(n_conso, 1))
        )

        fig_conso = px.line(
            df_conso_plot,
            y=df_conso_plot.columns,
            color_discrete_sequence=bleu_palette,
            title="Courbes de Consommation"
        )

        fig_conso.update_layout(
            legend_title="",
            xaxis_title="Pas de temps",
            yaxis_title="kWh"
        )

        fig_conso.update_yaxes(fixedrange=True)

        st.plotly_chart(fig_conso, width="stretch")

    else:
        st.info("Aucune consommation sélectionnée.")

    fig_prod = px.line(title="Courbes de Production") # Default empty fig
    
    # =========================================================
    # ================= PRODUCTION ============================
    # =========================================================
    if not df_prod_selected.empty:
        df_prod_plot = df_prod_selected.copy()

        n_prod = len(df_prod_plot.columns)

        bleu_palette = pc.sample_colorscale(
            "Blues",
            np.linspace(0.35, 1, max(n_prod, 1))
        )

        fig_prod = px.line(
            df_prod_plot,
            y=df_prod_plot.columns,
            color_discrete_sequence=bleu_palette,
            title="Courbes de Production"
        )

        fig_prod.update_layout(
            legend_title="",
            xaxis_title="Pas de temps",
            yaxis_title="kWh"
        )

        fig_prod.update_yaxes(fixedrange=True)

        st.plotly_chart(fig_prod, width="stretch")

    else:
        st.info("Aucune production sélectionnée.")

    # ===============================
    # GÉNÉRATION DU PDF DANS LE PLACEHOLDER
    # ===============================
    with export_placeholder:
        # Since generating the PDF takes time and uses kaleido/tempfiles,
        # we put it behind a standard button first, then render the download button
        
        # We store the PDF bytes in session state to prevent the download button from disappearing
        # when the user tries to click it (a classic Streamlit nested-button issue).
        if st.button("📄 Préparer PDF", width="stretch"):
            with st.spinner("Génération du PDF en cours... (Téléchargement des graphiques)"):
                from services.pdf_generator import generate_bilan_pdf, ensure_kaleido_is_patched
                import concurrent.futures
                
                try:
                    # 1. Ensure Mac paths with spaces are patched automatically
                    ensure_kaleido_is_patched()
                    
                    # Store state to normal dict to avoid missing ScriptRunContext in thread
                    state_dict = dict(st.session_state)
                    
                    # 2. Wrap generation in an isolated thread to allow timeouts
                    def _generate():
                        return generate_bilan_pdf(
                            state=state_dict,
                            fig_donut_main=fig_donut_main,
                            fig_prod_donut=fig_prod_donut,
                            fig_surplus_donut=fig_surplus_donut,
                            fig_conso_donut=fig_conso_donut,
                            fig_acc_donut=fig_acc_donut,
                            fig_conso_line=fig_conso,
                            fig_prod_line=fig_prod
                        )

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(_generate)
                        # Kaleido is fast. A stall natively means it crashed silently due to architectures.
                        pdf_bytes = future.result(timeout=45)
                    
                    st.session_state["bilan_pdf_bytes"] = pdf_bytes
                except concurrent.futures.TimeoutError:
                    st.error("⚠️ La génération PDF a pris trop de temps (Timeout). Si vous êtes sur un Mac M1/M2/M3, l'export de graphiques nécessite *Rosetta 2*. \\n\\n👉 Ouvrez le terminal et tapez : `softwareupdate --install-rosetta` puis redémarrez l'application.")
                except OSError as e:
                    if "Bad CPU type in executable" in str(e):
                        st.error("⚠️ Incompatibilité système détectée (Mac sans Rosetta 2). \\n\\n👉 Ouvrez le terminal et tapez : `softwareupdate --install-rosetta` puis redémarrez l'application.")
                    else:
                        st.error(f"⚠️ Erreur système lors de la génération : {e}")
                except Exception as e:
                    st.error(f"⚠️ Erreur lors de la génération : {e}")

        if "bilan_pdf_bytes" in st.session_state:
            st.download_button(
                label="⬇️ Télécharger le PDF",
                data=st.session_state["bilan_pdf_bytes"],
                file_name=f"Bilan_{st.session_state.get('project_name', 'projet')}.pdf",
                mime="application/pdf",
                width="stretch",
                type="primary"
            )