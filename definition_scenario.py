import streamlit as st
import pandas as pd

# --------- CONFIG ---------
st.set_page_config(page_title="Easy ACC", layout="wide")

# --------- SIDEBAR / LEFT PANEL ---------

st.title("Easy ACC ⚡")

# ========= PARAMÈTRES =========
st.sidebar.header("Paramètres")

distance = st.sidebar.selectbox("Distance", ["5 km", "10 km", "20 km", "50 km"])

# ========= PRODUCTEURS =========
st.sidebar.subheader("Producteurs")

producteurs = {
    "Acteur I": ["Privée", False],
    "Acteur II": ["Public", True],
    "Acteur III": ["Para Public", False],
    "Acteur IV": ["Privée", False],
    "Acteur V": ["Privée", False],
    "Acteur VI": ["Public", True],
    "Acteur VII": ["Public", False],
    "Acteur VIII": ["Para Public", False],
}

prod_df = pd.DataFrame.from_dict(producteurs, orient="index",
                                 columns=["Type", "ACI"])
prod_df["Choix"] = False

prod_df["Choix"] = st.sidebar.checkbox("Sélectionner tous les producteurs ?", value=False)

# On affiche un tableau éditable
prod_edit = st.sidebar.data_editor(prod_df)

# ========= CONSOMMATEURS =========
st.sidebar.subheader("Consommateurs")

consos = pd.DataFrame({
    "Acteur": ["Acteur I","Acteur II","Acteur III","Acteur IV","Acteur V","Acteur VI","Acteur VII","Acteur VIII"],
    "Choix": [False, True, False, False, False, True, False, True],
    "Type": ["Public","Para Public","Privée","Privée","Public","Public","Privée","Para Public"]
})

consos_edit = st.sidebar.data_editor(consos)

# ========= BOUTON =========
if st.sidebar.button("Générer"):
    st.success("Simulation générée 🎉")


# --------- MAIN UI ---------

col1, col2 = st.columns([2,3])

with col1:
    st.subheader("Carte / Visualisation")
    st.info("👉 Ici tu mettras ta carte, ton dashboard ou ton plot\n(example: plotly mapbox, folium…)")

with col2:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Bretagne_administrative_map.svg",
             caption="Exemple de carte (placeholder)",
             use_column_width=True)

# --------- RÉPARTITION ---------
st.subheader("Clé de répartition 🔑")

tabs = st.tabs(["Statique", "Dynamique par défaut", "Dynamique simple"])

# Valeurs par défaut
actors = [f"Acteur {i}" for i in range(1, 9)]
values = [22,8,30,5,10,4,1,0]

df_split = pd.DataFrame({"Acteur": actors, "Répartition (%)": values})

with tabs[0]:
    st.write("🔹 Mode statique")
    edit = st.data_editor(df_split)
    restant = 100 - edit["Répartition (%)"].sum()

    st.metric("Restant (%)", restant)

with tabs[1]:
    st.info("Mode dynamique par défaut — à implémenter selon ton algorithme ⚙")

with tabs[2]:
    st.warning("Mode dynamique simple — ex: pondération par consommation ou distance")

# Footer
st.caption("Prototype UI — Easy ACC ©")