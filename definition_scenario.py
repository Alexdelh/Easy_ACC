import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from functions import show_map_with_radius

st.set_page_config(page_title="Easy ACC", layout="wide")

# --------- HEADER ---------
st.title("Easy ACC ⚡")

# ========== LAYOUT PRINCIPAL ==========
# Colonne gauche : paramètres / producteurs / consommateurs
# Colonne droite : carte puis clés de répartition
left_col, right_col = st.columns([1.2, 3])   # Ajuste le ratio si nécessaire

# =====================================
# -------- COLONNE GAUCHE -------------
# =====================================
with left_col:

    # ========= PARAMÈTRES =========
    st.header("Paramètres")

    distance = st.selectbox("Distance", ["5 km", "10 km", "20 km"])
    

    # ========= PRODUCTEURS =========
    st.subheader("Producteurs")

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

    # Checkbox sélection globale
    select_all = st.checkbox("Sélectionner tous les producteurs ?", value=False)
    prod_df["Choix"] = select_all

    # Tableau éditable
    prod_edit = st.data_editor(prod_df)

    # ========= CONSOMMATEURS =========
    st.subheader("Consommateurs")

    consos = pd.DataFrame({
        "Acteur": ["Acteur I","Acteur II","Acteur III","Acteur IV",
                   "Acteur V","Acteur VI","Acteur VII","Acteur VIII"],
        "Choix": [False, True, False, False, False, True, False, True],
        "Type": ["Public","Para Public","Privée","Privée",
                 "Public","Public","Privée","Para Public"]
    })

    consos_edit = st.data_editor(consos)

    # ========= BOUTON =========
    if st.button("Générer la simulation"):
        st.success("Simulation générée 🎉")


# =====================================
# -------- COLONNE DROITE -------------
# =====================================
with right_col:

    st.title("Carte Folium — Centroïde + Rayon 📍")

    # Exemple de points
    points = [
        {"name": "Producteur A", "lat": 48.8566, "lon": 2.3522},
        {"name": "Consommateur B", "lat": 48.8666, "lon": 2.3222},
        {"name": "Consommateur C", "lat": 48.8466, "lon": 2.3622}
        
    ]

    radius_km = int(distance.split()[0])

    # Génération de la carte
    m, centroid, inside, outside = show_map_with_radius(points, radius_km=radius_km)

    st.subheader("🗺️ Carte")
    st_folium(m, width=700, height=500)


    st.subheader("✔️ Points dans le rayon")
    st.write(inside)

    st.subheader("❌ Points hors rayon")
    st.write(outside)
    
    if outside:
        st.error("⚠️ Attention : Des points se trouvent en dehors du rayon défini !")
    # --------- CLÉ DE RÉPARTITION -----------
    st.subheader("Clé de répartition 🔑")

    tabs = st.tabs(["Statique", "Dynamique par défaut", "Dynamique simple"])

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


# --------- FOOTER ----------
st.caption("Prototype UI — Easy ACC ©")
