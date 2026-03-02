import streamlit as st

# ===============================
# FONCTION UTILE : safe_rerun
# ===============================
def safe_rerun():
    """
    Tente de déclencher un rerun dans Streamlit, de manière compatible avec différentes versions.
    
    - Priorité 1 : API officielle `st.experimental_rerun()`.
    - Priorité 2 : Lever l'exception interne `RerunException` (pour versions plus récentes).
    - Priorité 3 : Toggle d'une clé de session dummy pour forcer la détection de changement.
    """
    try:
        st.experimental_rerun()
    except Exception:
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            st.session_state["__rerun_flag"] = not st.session_state.get("__rerun_flag", False)


# ===============================
# PAGE PARAMÈTRES
# ===============================
def render():
    """Render de la page Paramètres du projet."""
    
    st.title("Paramètres du projet")

    # -------------------------------
    # Section : Clés de répartition
    # -------------------------------
    st.subheader("Clés de répartition")

    # Récupération des points de soutirage depuis la session
    points_soutirage = st.session_state.get("points_soutirage", [])
    
    # Construction de la liste des consommateurs valides
    consumers = [p.get("nom", f"Consommateur {i+1}") for i, p in enumerate(points_soutirage)]
    valid_consumers = set(consumers)

    # Nettoyage des anciens consommateurs dans les données statiques
    if "consumer_percentages" in st.session_state:
        st.session_state["consumer_percentages"] = {
            c: v for c, v in st.session_state["consumer_percentages"].items()
            if c in valid_consumers
        }

    if "consumer_priorities" in st.session_state:
        st.session_state["consumer_priorities"] = {
            c: v for c, v in st.session_state["consumer_priorities"].items()
            if c in valid_consumers
        }

    st.divider()

    # -------------------------------
    # Choix de la méthode de répartition
    # -------------------------------
    repartition_mode = st.radio(
        "Choisissez la méthode de répartition :",
        ("Clé par défaut", "Clé statique (pourcentages par consommateur)", "Clé dynamique simple"),
        index=0
    )

    # ===============================
    # MODE : Clé par défaut
    # ===============================
    if repartition_mode == "Clé par défaut":
        st.caption("La clé par défaut applique des règles internes sans configuration manuelle.")

    # ===============================
    # MODE : Clé statique
    # ===============================
    elif repartition_mode == "Clé statique (pourcentages par consommateur)":
        st.markdown("**Clé statique (pourcentages par consommateur)**")
        st.caption("Attribuez un pourcentage à chaque consommateur (la somme doit être 100%).")

        cp = st.session_state.get("consumer_percentages", {})
        total = 0.0

        # Vérification qu'il y a des consommateurs
        if not consumers:
            st.info("Aucun consommateur disponible — importez des points de soutirage.")
        else:
            # Boucle pour chaque consommateur
            for i, c in enumerate(consumers):
                key = f"perc_{i}"  # clé unique pour le widget Streamlit
                default = cp.get(c, round(100.0 / len(consumers), 2))
                v = st.number_input(
                    c, min_value=0.0, max_value=100.0,
                    value=float(default), key=key, step=1.0, format="%.1f"
                )
                cp[c] = v
                total += v

            # Affichage de la somme des pourcentages
            st.markdown(f"Total: **{total:.2f}%**")
            if abs(total - 100.0) > 0.001:
                st.warning("La somme des pourcentages devrait être égale à 100%.")

        # Enregistrement dans la session
        st.session_state["consumer_percentages"] = cp

    # ===============================
    # MODE : Clé dynamique simple
    # ===============================
    elif repartition_mode == "Clé dynamique simple":
        st.markdown("**Clé dynamique simple**")
        st.caption(
            "Attribuez une priorité entière à chaque consommateur. "
            "Ensuite, définissez la clé au sein de chaque groupe de priorité (par défaut ou statique)."
        )

        # Priorités par consommateur
        cp = st.session_state.get("consumer_priorities", {})

        if not consumers:
            st.info("Aucun consommateur disponible — importez des points de soutirage dans la page correspondante.")
        else:
            # Boucle pour définir la priorité de chaque consommateur
            for i, c in enumerate(consumers):
                key = f"prio_{i}"  # clé unique pour le widget
                default = int(cp.get(c, 1))
                v = st.number_input(
                    f"Priorité — {c}", min_value=1, max_value=20, value=default, step=1, key=key
                )
                cp[c] = int(v)

            # Sauvegarde dans la session
            st.session_state["consumer_priorities"] = cp

            # Bouton pour passer à la définition des clés par groupe
            if st.button("Suivant : définir clé par groupe", key="dyn_next"):
                st.session_state["dynamic_step"] = "groups"
                safe_rerun()

        # ===============================
        # Étape : définition des clés par groupe
        # ===============================
        if st.session_state.get("dynamic_step") == "groups":
            st.divider()
            st.markdown("## Définition des clés par groupe de priorité")

            # Regroupement des consommateurs par priorité
            groups = {}
            for name, pr in cp.items():
                groups.setdefault(pr, []).append(name)

            gstate = st.session_state.get("consumer_group_keys", {})

            # Boucle sur chaque groupe de priorité
            for pr in sorted(groups.keys()):
                members = groups[pr]
                st.markdown(f"### Priorité {pr} — {len(members)} acteur(s)")
                st.write(", ".join(members))

                # Choix du mode de clé pour le groupe
                mode_key = f"group_mode_{pr}"
                mode = st.radio(
                    f"Clé pour groupe priorité {pr}",
                    ("Par défaut", "Statique (pourcentages)"),
                    key=mode_key
                )

                if mode == "Statique (pourcentages)":
                    group_perc = gstate.get(pr, {}).get("percentages", {})
                    total = 0.0

                    # Boucle sur chaque membre du groupe
                    for mi, name in enumerate(members):
                        perc_key = f"group_perc_{pr}_{mi}"
                        default = group_perc.get(name, round(100.0 / len(members), 2))
                        val = st.number_input(
                            name, min_value=0.0, max_value=100.0,
                            value=float(default), key=perc_key, step=1.0, format="%.1f"
                        )
                        group_perc[name] = val
                        total += val

                    st.markdown(f"Total groupe: **{total:.2f}%**")
                    if abs(total - 100.0) > 0.001:
                        st.warning("La somme des pourcentages dans ce groupe devrait être 100%.")

                    # Enregistrement du groupe dans la session
                    gstate[pr] = {"mode": "static", "percentages": group_perc}
                else:
                    gstate[pr] = {"mode": "default", "percentages": {}}

                st.divider()

            # Boutons de navigation : Retour / Appliquer
            col_back, col_apply = st.columns([1, 1])
            if col_back.button("← Retour", key="dyn_back"):
                st.session_state["dynamic_step"] = None
                safe_rerun()

            if col_apply.button("Appliquer la clé dynamique", key="dyn_apply"):
                st.session_state["consumer_group_keys"] = gstate
                st.success("Clés de répartition multi-dynamiques enregistrées.")
                safe_rerun()

    # ===============================
    # Sauvegarde du mode de répartition
    # ===============================
    st.session_state["repartition_mode"] = repartition_mode

    st.divider()