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


def auto_save_params_field(state_key=None, widget_key=None):
    if state_key and widget_key and widget_key in st.session_state:
        st.session_state[state_key] = st.session_state[widget_key]
    if st.session_state.get("project_id"):
        from services.database import save_project
        from services.state_serializer import serialize_state
        save_project(
            st.session_state.get("project_name", "Sans titre"), 
            "precalibrage", 
            serialize_state(dict(st.session_state)), 
            st.session_state["project_id"]
        )

def update_dict_val(dict_name, key_name, widget_key):
    if dict_name not in st.session_state:
        st.session_state[dict_name] = {}
    if widget_key in st.session_state:
        st.session_state[dict_name][key_name] = st.session_state[widget_key]
    auto_save_params_field()

def update_group_perc(pr, name, widget_key):
    if "consumer_group_keys" not in st.session_state:
        st.session_state["consumer_group_keys"] = {}
    if pr not in st.session_state["consumer_group_keys"]:
        st.session_state["consumer_group_keys"][pr] = {"mode": "static", "percentages": {}}
    if "percentages" not in st.session_state["consumer_group_keys"][pr]:
        st.session_state["consumer_group_keys"][pr]["percentages"] = {}
    if widget_key in st.session_state:
        st.session_state["consumer_group_keys"][pr]["percentages"][name] = st.session_state[widget_key]
    auto_save_params_field()

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
    if "repartition_mode" not in st.session_state:
        st.session_state["repartition_mode"] = "Clé par défaut"

    try:
        rm_index = ("Clé par défaut", "Clé statique (pourcentages par consommateur)", "Clé dynamique simple").index(st.session_state["repartition_mode"])
    except ValueError:
        rm_index = 0

    repartition_mode = st.radio(
        "Choisissez la méthode de répartition :",
        ("Clé par défaut", "Clé statique (pourcentages par consommateur)", "Clé dynamique simple"),
        index=rm_index,
        key="_repartition_mode",
        on_change=auto_save_params_field,
        args=("repartition_mode", "_repartition_mode")
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
                default = float(cp.get(c, round(100.0 / len(consumers), 2)))
                if key not in st.session_state:
                    st.session_state[key] = default
                
                st.number_input(
                    c, min_value=0.0, max_value=100.0,
                    key=key, step=1.0, format="%.1f",
                    on_change=update_dict_val,
                    args=("consumer_percentages", c, key)
                )
                cp[c] = st.session_state[key]
                total += cp[c]

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
                if key not in st.session_state:
                    st.session_state[key] = default

                st.number_input(
                    f"Priorité — {c}", min_value=1, max_value=20, step=1, key=key,
                    on_change=update_dict_val,
                    args=("consumer_priorities", c, key)
                )
                cp[c] = int(st.session_state[key])

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
                        default = float(group_perc.get(name, round(100.0 / len(members), 2)))
                        if perc_key not in st.session_state:
                            st.session_state[perc_key] = default
                            
                        st.number_input(
                            name, min_value=0.0, max_value=100.0,
                            key=perc_key, step=1.0, format="%.1f",
                            on_change=update_group_perc,
                            args=(pr, name, perc_key)
                        )
                        group_perc[name] = st.session_state[perc_key]
                        total += st.session_state[perc_key]

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
                auto_save_params_field()
                st.success("Clés de répartition multi-dynamiques enregistrées.")
                safe_rerun()

    st.divider()