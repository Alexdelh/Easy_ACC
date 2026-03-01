import streamlit as st
import calendar


def safe_rerun():
    """Try to trigger a Streamlit rerun in a version-compatible way."""
    try:
        # Preferred API when available
        st.experimental_rerun()
    except Exception:
        try:
            # Internal exception used by Streamlit to signal a rerun
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Fallback: toggle a dummy session key to cause widgets to detect change
            st.session_state["__rerun_flag"] = not st.session_state.get("__rerun_flag", False)

def render():
   
    st.title("Paramètres du projet")
    st.markdown("**Clé de répartition**")
    consumers = st.session_state.get("consumers", [])
    repartition_mode = st.radio(
        "Choisissez la méthode de répartition :",
        ("Clé par défaut", "Clé statique (pourcentages par consommateur)", "Clé dynamique simple"),
        index=0
    )

    if repartition_mode == "Clé par défaut":
        st.caption("La clé par défaut applique des règles internes sans configuration manuelle.")

    elif repartition_mode == "Clé statique (pourcentages par consommateur)":
        st.markdown("**Clé statique (pourcentages par consommateur)**")
        st.caption("Attribuez un pourcentage à chaque consommateur (la somme doit être 100%).")
        cp = st.session_state.get("consumer_percentages", {})
        total = 0.0
        if not consumers:
            st.info("Aucun consommateur disponible — importez des points de soutirage.")
        else:
            for i, c in enumerate(consumers):
                key = f"perc_{i}"
                default = cp.get(c, round(100.0 / len(consumers), 2))
                v = st.number_input(c, min_value=0.0, max_value=100.0, value=float(default), key=key, format="%.2f")
                cp[c] = v
                total += v
            st.markdown(f"Total: **{total:.2f}%**")
            if abs(total - 100.0) > 0.001:
                st.warning("La somme des pourcentages devrait être égale à 100%.")
        st.session_state["consumer_percentages"] = cp

    elif repartition_mode == "Clé dynamique simple":
        st.markdown("**Clé dynamique simple**")
        st.caption("Attribuez une priorité entière à chaque consommateur. Ensuite, définissez la clé au sein de chaque groupe de priorité (par défaut ou statique).")

        # Priorités par consommateur
        cp = st.session_state.get("consumer_priorities", {})
        if not consumers:
            st.info("Aucun consommateur disponible — importez des points de soutirage dans la page correspondante.")
        else:
            for i, c in enumerate(consumers):
                key = f"prio_{i}"
                default = int(cp.get(c, 1))
                v = st.number_input(f"Priorité — {c}", min_value=1, max_value=20, value=default, step=1, key=key)
                cp[c] = int(v)
            st.session_state["consumer_priorities"] = cp

            if st.button("Suivant : définir clé par groupe", key="dyn_next"):
                st.session_state["dynamic_step"] = "groups"
                safe_rerun()

        # Si on est en étape de définition par groupe
        if st.session_state.get("dynamic_step") == "groups":
            st.divider()
            st.markdown("## Définition des clés par groupe de priorité")
            groups = {}
            for name, pr in cp.items():
                groups.setdefault(pr, []).append(name)

            gstate = st.session_state.get("consumer_group_keys", {})

            for pr in sorted(groups.keys()):
                members = groups[pr]
                st.markdown(f"### Priorité {pr} — {len(members)} acteur(s)")
                st.write(", ".join(members))

                mode_key = f"group_mode_{pr}"
                mode = st.radio(f"Clé pour groupe priorité {pr}", ("Par défaut", "Statique (pourcentages)"), key=mode_key)

                if mode == "Statique (pourcentages)":
                    group_perc = gstate.get(pr, {}).get("percentages", {})
                    total = 0.0
                    for mi, name in enumerate(members):
                        perc_key = f"group_perc_{pr}_{mi}"
                        default = group_perc.get(name, round(100.0 / len(members), 2))
                        val = st.number_input(name, min_value=0.0, max_value=100.0, value=float(default), key=perc_key, format="%.2f")
                        group_perc[name] = val
                        total += val

                    st.markdown(f"Total groupe: **{total:.2f}%**")
                    if abs(total - 100.0) > 0.001:
                        st.warning("La somme des pourcentages dans ce groupe devrait être 100%.")

                    gstate[pr] = {"mode": "static", "percentages": group_perc}
                else:
                    gstate[pr] = {"mode": "default", "percentages": {}}

                st.divider()

            # Back / Apply buttons
            col_back, col_apply = st.columns([1, 1])
            if col_back.button("← Retour", key="dyn_back"):
                st.session_state["dynamic_step"] = None
                safe_rerun()

            if col_apply.button("Appliquer la clé dynamique", key="dyn_apply"):
                st.session_state["consumer_group_keys"] = gstate
                st.success("Clés de répartition multi-dynamiques enregistrées.")
                safe_rerun()

    # Save repartition mode
    st.session_state["repartition_mode"] = repartition_mode

    st.divider()

        # Save repartition mode
    st.session_state["repartition_mode"] = repartition_mode

    # Bibliothèque de données supprimée conformément à la demande
