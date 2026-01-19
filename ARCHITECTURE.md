# 📐 Architecture détaillée de l'application Easy ACC

## 🎯 Vue d'ensemble

**Easy ACC** est une application web développée avec **Streamlit** pour la gestion et l'analyse d'**Auto-Consommation Collective (ACC)** de production énergétique (principalement photovoltaïque). L'application permet de modéliser des projets ACC, d'importer/générer des courbes de production et consommation, et de générer des bilans énergétiques et financiers.

---

## 🏗️ Architecture générale

### Pattern architectural : **MVC-inspired avec navigation par phases**

```
┌─────────────────────────────────────────────────────────┐
│                     app.py (Entry Point)                │
│  • Configuration Streamlit                              │
│  • Initialisation de l'état                             │
│  • Routage phase/page                                   │
└─────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
    ┌───────────────┐              ┌────────────────┐
    │  PRÉCALIBRAGE │              │     BILAN      │
    │    (Phase 1)  │              │   (Phase 2)    │
    └───────────────┘              └────────────────┘
            │                               │
    ┌───────┴────────┐             ┌───────┴────────┐
    │ 6 pages        │             │ 2 pages        │
    │ navigation/    │             │ navigation/    │
    └────────────────┘             └────────────────┘
```

---

## 📂 Structure détaillée du code

### **1. Point d'entrée : `app.py`**

Le fichier `app.py` est le **cœur de l'application**. Il gère :

#### **Responsabilités principales :**
- **Configuration globale** : `st.set_page_config()` définit le titre et le layout "wide"
- **Initialisation de l'état** : Appel à `init_session_state()` pour créer les variables de session
- **Gestion des phases** : 
  - Phase `"precalibrage"` : Configuration du projet (6 pages)
  - Phase `"bilan"` : Visualisation des résultats (2 pages)
- **Routage dynamique** : Basé sur `st.session_state["current_phase"]` et `st.session_state["precalibrage_page"]`/`st.session_state["bilan_page"]`

#### **Flux de navigation :**
```python
# Pseudo-code simplifié
if current_phase == "precalibrage":
    render_sidebar_precalibrage()
    
    if page_num == 0: projects_list.render()
    elif page_num == 1: general.render()
    elif page_num == 2: production.render()
    elif page_num == 3: consommation.render()
    elif page_num == 4: parametres.render()
    elif page_num == 5: financier.render()

elif current_phase == "bilan":
    render_sidebar_bilan()
    
    if bilan_page == 1: energie.render()
    elif bilan_page == 2: financier.render()
```

---

### **2. Gestion de l'état : `state/`**

#### **2.1 `state/init_state.py`**
Définit l'état initial de l'application via un dictionnaire `DEFAULTS` :

```python
DEFAULTS = {
    "project_name": "",           # Nom du projet
    "postal_code": "",            # Code postal
    "distance_constraint": "2 km", # Contrainte de distance
    "operation_type": "Ouverte",  # Type d'opération ACC
    "start_date": datetime.date(2024, 1, 1),
    "end_date": datetime.date(2024, 12, 31),
    "points_injection": [],       # Liste des producteurs
    "points_soutirage": [],       # Liste des consommateurs
    "consumers_df": None,         # DataFrame des consommateurs
    "producers_df": None,         # DataFrame des producteurs
    "current_phase": "precalibrage",
    "precalibrage_page": 0,
    "bilan_page": 1,
    "scenario_generated": False,
}
```

**Fonction** : `init_session_state()` initialise ces valeurs dans `st.session_state` au démarrage.

---

### **3. Navigation : `navigation/`**

#### **3.1 `navigation/sidebar_precalibrage.py`**
Affiche la **barre latérale de navigation** pour la phase précalibrage :

**Menu des pages :**
```python
PRECALIBRAGE_MENU = {
    0: "Projets",
    1: "Infos générales",
    2: "Points d'injection",      # Producteurs PV
    3: "Points de soutirage",      # Consommateurs
    4: "Paramètres",
    5: "Financier",
}
```

**Fonctionnalités :**
- Indicateur visuel de la page actuelle (🔴)
- Boutons **Précédent/Suivant** pour naviguer
- Bouton **"Générer le scénario"** (dernière page) → Bascule vers phase "bilan"
- Bouton **"💾 Sauver l'état"** pour persister le projet en base

#### **3.2 `navigation/sidebar_bilan.py`**
Barre latérale simplifiée pour la phase bilan :
- Navigation entre "Énergie" et "Financier"
- Bouton retour vers le précalibrage

---

### **4. Pages de l'application : `pages/`**

#### **Phase Précalibrage**

##### **4.1 `pages/precalibrage/projects_list.py`**
**Écran de gestion des projets** :
- Liste tous les projets sauvegardés (depuis SQLite)
- Créer un nouveau projet
- Charger un projet existant
- Supprimer un projet

**Interactions avec la base de données :**
- `list_projects()` : Récupère la liste
- `load_project(id)` : Restaure l'état complet
- `delete_project(id)` : Suppression

##### **4.2 `pages/precalibrage/general.py`**
**Configuration générale du projet** :

**Formulaire de saisie :**
- Nom du projet
- Code postal → Géolocalisation automatique via Nominatim API
- Distance contrainte (2 km, 10 km, 20 km, EPCI)
- Type d'opération (Ouverte/Patrimoniale)
- **Période d'étude** : Date début/fin (important pour PVGIS)

**Visualisation :**
- Carte interactive Folium affichant la localisation
- Affichage des coordonnées GPS et ville

##### **4.3 `pages/precalibrage/production.py`**
**Gestion des points d'injection (producteurs PV)** :

**Structure à deux onglets :**

**Onglet 1 : Gestion des points**
- Table HTML personnalisée affichant tous les producteurs
- Colonnes : Nom, Type, Segment, Puissance, TVA, Localisation, Courbe, Actions
- Actions par ligne : ✏️ Éditer, 📋 Dupliquer, 🗑️ Supprimer

**Formulaire d'ajout de point :**
```python
{
    "nom": str,
    "type": "Photovoltaïque" | "Éolien" | "Autre",
    "segment": "Résidentiel" | "Professionnel" | "Agricole",
    "puissance_kw": float,
    "tva": bool,
    "adresse": str,  # Géocodée automatiquement
    "lat": float,
    "lon": float,
    "courbe_df": DataFrame,  # Courbe de production
    "courbe_source": "PVGIS" | "Import fichier"
}
```

**Fonctionnalités avancées :**

**a) Modélisation PVGIS :**
- Formulaire avec Puissance, Inclinaison, Azimut, Pertes
- Appel API PVGIS via `services/pvgis.py`
- Génération automatique de courbe horaire (8760 points/an)

**b) Import de courbe :**
- Upload CSV/Excel
- **Standardisation automatique** via `CurveStandardizer`
- Parsing, validation, resampling (PT15M, PT30M, PT60M)
- Export multi-formats (SGE Tiers, Archelios, PVGIS)

**Onglet 2 : Vérification contraintes**
- Carte Folium avec tous les points d'injection
- Cercle de contrainte autour du code postal
- Validation que tous les points sont dans le périmètre

##### **4.4 `pages/precalibrage/consommation.py`**
**Gestion des points de soutirage (consommateurs)** :

Structure identique à `production.py`, mais avec des champs spécifiques :
```python
{
    "nom": str,
    "segment": "Résidentiel" | "Professionnel" | "Collectivité",
    "tarif_reference": float,  # c€/kWh
    "aci": bool,  # Acteur Commun d'Intermédiation
    "aci_partenaire": str,
    "tva": bool,
    "structure_tarifaire": "Base" | "HP/HC" | "Tempo",
    "tarif_complement": "Tarif régulé" | "Offre marché",
    "courbe_df": DataFrame
}
```

**Particularité :**
- Import de courbe de consommation uniquement (pas de PVGIS)
- Validation de structure tarifaire

##### **4.5 `pages/precalibrage/parametres.py`**
Placeholder pour clés de répartition (à développer).

##### **4.6 `pages/precalibrage/financier.py`**
Placeholder pour paramètres financiers (à développer).

---

#### **Phase Bilan**

##### **4.7 `pages/bilan/energie.py`**
**Bilan énergétique complet** :

**Visualisations :**
1. **Donut "Taux de couverture"** :
   - Ratio Production/Consommation
   - Affichage central du pourcentage

2. **Sélection des acteurs** :
   - Checkboxes consommateurs/producteurs
   - Filtrage dynamique

3. **4 donuts principaux** :
   - Production totale (par producteur)
   - Surplus de production
   - Consommation ACC
   - Production ACC (autoconso/surplus)

4. **Graphiques mensuels** :
   - Évolution production/consommation
   - Surplus/Autoconsommation

**Technologies :** Plotly (graphiques interactifs), Seaborn (palettes colorblind)

##### **4.8 `pages/bilan/financier.py`**
À développer (bilan financier, économies, ROI)

---

### **5. Services métier : `services/`**

#### **5.1 `services/database.py` - Persistance SQLite**

**Schéma de la table `projects` :**
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_phase TEXT,
    state_data JSON
)
```

**Fonctions exposées :**
- `init_db()` : Création de la base si nécessaire
- `save_project(name, phase, state_dict)` : Sauvegarde/Mise à jour
- `load_project(id)` : Chargement d'un projet
- `list_projects()` : Liste de tous les projets
- `delete_project(id)` : Suppression

**Note** : Le `state_data` est sérialisé en JSON avec `state_serializer.py`.

---

#### **5.2 `services/state_serializer.py` - Sérialisation d'état**

**Problème résolu :** Streamlit `session_state` contient des objets non-sérialisables (DataFrames, numpy, widgets).

**Fonctions :**

**`serialize_state(state)`** :
- Convertit `pd.DataFrame` → `{"__type__": "pd.DataFrame", "data": {...}}`
- Convertit numpy types → Python natives
- Exclut les widgets temporaires (`prev_`, `next_`, `confirm_`, etc.)

**`deserialize_state(state)`** :
- Reconstruit les DataFrames depuis le JSON
- Restaure l'arbre d'état complet

---

#### **5.3 `services/pvgis.py` - Modélisation photovoltaïque**

**Bibliothèques utilisées :** `pvlib` (simulation PV)

**Fonction principale : `compute_pv_curve()`**

**Pipeline de calcul :**
```python
1. Fetch TMY data (Typical Meteorological Year)
   └─> get_pvgis_tmy(lat, lon) → weather DataFrame
   
2. Calculate solar position
   └─> location.get_solarposition(weather.index)
   
3. Transpose irradiance to panel plane (POA)
   └─> get_total_irradiance(tilt, azimuth, dni, ghi, dhi)
   
4. Estimate cell temperature
   └─> T_cell = T_air + 0.0045 * POA
   
5. Compute DC power (PVWatts model)
   └─> pvwatts_dc(poa, T_cell, pdc0, gamma_pdc)
   
6. Apply inverter efficiency + system losses
   └─> P_ac = P_dc * 0.96 * (1 - losses%)
   
7. Adjust to date range (tile if multi-year)
```

**Paramètres d'entrée :**
- `lat`, `lon` : Coordonnées GPS
- `peakpower_kw` : Puissance crête (kW)
- `tilt_deg` : Inclinaison (0-90°)
- `azimuth_deg` : Azimut (0-360°, 180=Sud)
- `losses_pct` : Pertes système (défaut 14%)
- `start_date`, `end_date` : Période de simulation

**Sortie :** DataFrame avec `P_ac_kW` indexé par datetime horaire.

---

#### **5.4 `services/geolocation.py` - Géocodage**

**API utilisée :** Nominatim (OpenStreetMap)

**Fonction :** `get_coordinates_from_address(address)`

**Stratégie :**
1. Vérifier dans un dictionnaire de villes connues (cache statique)
2. Sinon, requête Nominatim avec `country_codes="FR"`
3. Cache Streamlit (`@st.cache_data`) avec TTL 1h

**Retour :**
```python
{
    "lat": float,
    "lng": float,
    "epci": str  # EPCI = territoire intercommunal
}
```

---

#### **5.5 `services/curve_standardizer/` - Normalisation de courbes**

**Architecture modulaire :** Pipeline en 4 étapes

##### **Pipeline complet :**

```
Input (CSV/Excel/DataFrame)
    │
    ▼
┌────────────────────┐
│ 1. parser.py       │  Détecte format, colonnes datetime/valeurs
│    parse_curve()   │  Retourne DataFrame + metadata
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 2. validator.py    │  Vérifie continuité temporelle, valeurs aberrantes
│ validate_curve()   │  Génère rapport de validation
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 3. resampler.py    │  Resampling vers PT15M, PT30M, PT60M
│ resample_curve()   │  Interpolation linéaire si nécessaire
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ 4. formatters.py   │  Export vers 3 formats :
│  - to_sge_tiers()  │  • SGE Tiers (format Enedis)
│  - to_archelios()  │  • Archelios (logiciel BE)
│  - to_pvgis()      │  • PVGIS (recherche)
└────────────────────┘
    │
    ▼
9 fichiers de sortie (3 formats × 3 pas de temps)
```

##### **Classe principale : `CurveStandardizer`**

```python
standardizer = CurveStandardizer(prm_id="ACCKB_12345")
result = standardizer.process(uploaded_file)

# result contient :
{
    'success': bool,
    'parsed': {'rows': int, 'metadata': dict},
    'validation': {'is_valid': bool, 'warnings': []},
    'exports': {
        ('sge_tiers', 'PT15M'): str,  # Contenu CSV
        ('archelios', 'PT30M'): str,
        ('pvgis', 'PT60M'): DataFrame,
        # ... 9 combinaisons au total
    }
}
```

**Utilisation dans l'app :**
- Dans `production.py`, lors de l'upload de courbe
- Validation temps réel de la cohérence des données
- Export multi-formats pour interopérabilité

---

### **6. Utilitaires : `utils/`**

#### **6.1 `utils/helpers.py`**

**Constantes :**
```python
DISTANCE_OPTIONS = ["2 km", "10 km", "20 km", "EPCI"]
DATA_DIR = "ACC_data/"
```

**Fonction clé :** `get_coordinates_from_postal_code(postal_code)`
- Wrapper autour de Nominatim
- Cache Streamlit avec TTL 1h
- Gestion d'erreurs robuste

---

#### **6.2 `functions.py`**

**Fonctions de manipulation de données :**

- `import_consumers(path)` : Import CSV/Excel consommateurs
- `import_producers(path)` : Import CSV/Excel producteurs
- `create_map_from_points(points_data)` : Génération carte Folium
- `cercle(lat, lon, radius_km)` : Dessin de cercle de contrainte
- `show_map_with_radius()` : Carte avec rayon de contrainte

**Constantes :**
```python
STATUT_CHOICES = ['Public', 'Privé', 'Para-public']
STATUT_COLORS = {'Public': 'blue', 'Privé': 'orange', 'Para-public': 'green'}
```

---

## 🔄 Flux de données complet

### **Scénario type : Création d'un projet ACC**

```
1. Démarrage
   └─> app.py → init_session_state()
   └─> Phase = "precalibrage", Page = 0 (Projects List)

2. Création nouveau projet
   └─> projects_list.py : Formulaire "Créer projet"
   └─> Reset session_state + project_name
   └─> Navigation → Page 1 (Infos générales)

3. Configuration générale
   └─> general.py : Saisie code postal
   └─> geolocation.py : Géocodage Nominatim
   └─> Affichage carte Folium
   └─> Sauvegarde : postal_code, start_date, end_date → session_state

4. Ajout point d'injection (producteur PV)
   └─> production.py : Formulaire avec adresse
   └─> Choix : Modélisation PVGIS ou Import courbe
   
   4a. Si PVGIS :
       └─> pvgis.py : compute_pv_curve()
       └─> API PVGIS TMY → weather data
       └─> PVLib simulation → DataFrame P_ac_kW
   
   4b. Si Import :
       └─> Upload fichier CSV/Excel
       └─> CurveStandardizer.process()
       └─> Parsing → Validation → Resampling → Formatage
   
   └─> Stockage : points_injection.append({...})

5. Ajout point de soutirage (consommateur)
   └─> consommation.py : Formulaire + upload courbe
   └─> CurveStandardizer pour normalisation
   └─> Stockage : points_soutirage.append({...})

6. Génération du scénario
   └─> Bouton "Générer le scénario" (sidebar)
   └─> Transition : current_phase = "bilan"
   └─> Navigation → energie.py

7. Visualisation bilan énergétique
   └─> energie.py : Agrégation des courbes
   └─> Calculs : taux_couverture, surplus, autoconso
   └─> Plotly : Graphiques interactifs

8. Sauvegarde du projet
   └─> Bouton "💾 Sauver" (sidebar)
   └─> state_serializer.py : serialize_state()
   └─> database.py : save_project() → SQLite
```

---

## 🗄️ Gestion des données

### **Session State (Streamlit)**

**Variables clés :**
```python
st.session_state = {
    # Projet
    "project_name": str,
    "postal_code": str,
    "start_date": date,
    "end_date": date,
    
    # Navigation
    "current_phase": "precalibrage" | "bilan",
    "precalibrage_page": 0..5,
    "bilan_page": 1..2,
    
    # Données métier
    "points_injection": [
        {
            "nom": str,
            "lat": float,
            "lon": float,
            "courbe_df": pd.DataFrame,
            "puissance_kw": float,
            ...
        }
    ],
    "points_soutirage": [...],
    
    # Flags
    "scenario_generated": bool,
}
```

### **Persistance (SQLite)**

**Fichier :** `projects.db` (créé automatiquement)

**Format JSON du state_data :**
```json
{
    "project_name": "Mon Projet Solaire",
    "postal_code": "75001",
    "points_injection": [
        {
            "nom": "Toiture Mairie",
            "courbe_df": {
                "__type__": "pd.DataFrame",
                "data": {
                    "index": [...],
                    "columns": ["P_ac_kW"],
                    "data": [[0.5], [1.2], ...]
                }
            }
        }
    ]
}
```

---

## 📊 Technologies et dépendances

### **Framework principal**
- **Streamlit 1.25+** : Interface web interactive
- **Python 3.11+** : Langage de base

### **Data Science**
- **Pandas 2.3+** : Manipulation de données tabulaires
- **NumPy <2** : Calculs numériques
- **Matplotlib 3.10+** : Visualisation statique
- **Seaborn 0.13+** : Palettes de couleurs (colorblind-friendly)
- **Plotly 5.15+** : Graphiques interactifs (donuts, barres)

### **Géospatial**
- **Folium 0.20+** : Cartes interactives (OpenStreetMap)
- **streamlit-folium** : Intégration Folium/Streamlit
- **Geopy 2.4+** : Géocodage (Nominatim API)

### **Photovoltaïque**
- **pvlib 0.10+** : Simulation PV (PVGIS, PVWatts)

### **Formats de données**
- **PyArrow 12+** : Parquet (performances)
- **OpenPyXL 3.1+** : Lecture/écriture Excel

---

## 🔐 Patterns de conception

### **1. Page Pattern**
Chaque page est un module Python avec une fonction `render()` :
```python
# pages/precalibrage/general.py
def render():
    st.title("Infos générales")
    # ... logique de la page
```

### **2. Service Pattern**
Les services encapsulent la logique métier :
- `services/pvgis.py` : Calculs PV
- `services/database.py` : Persistance
- `services/geolocation.py` : Géocodage

### **3. State Management Pattern**
État centralisé dans `st.session_state` :
- Initialisation : `state/init_state.py`
- Sérialisation : `services/state_serializer.py`
- Persistance : `services/database.py`

### **4. Pipeline Pattern**
`CurveStandardizer` implémente un pipeline de transformation :
```
Input → Parse → Validate → Resample → Format → Output
```

---

## 🚀 Points d'extension

### **Fonctionnalités à développer :**

1. **Paramètres de répartition** (`parametres.py`) :
   - Clés de répartition statiques/dynamiques
   - Règles de ventilation

2. **Bilan financier** (`pages/bilan/financier.py`) :
   - Calcul économies (€/an)
   - ROI (Return On Investment)
   - Simulations tarifaires

3. **Calcul moteur ACC** :
   - Algorithme de répartition horaire
   - Gestion surplus/complément
   - Optimisation autoconsommation

4. **Export PDF** (bouton dans `energie.py`) :
   - Génération rapport avec graphiques
   - Synthèse du projet

5. **Import courbes multiples** :
   - Upload ZIP avec plusieurs fichiers
   - Association automatique PRM ↔ Points

---

## 🧪 Tests et validation

### **Tests manuels**
- `services/curve_standardizer/test_curve_import.py`
- `services/curve_standardizer/test_debug_parser.py`

### **Validation en temps réel**
- `validator.py` vérifie la continuité temporelle
- Warnings affichés dans Streamlit

---

## 📈 Performance

### **Optimisations**
1. **Cache Streamlit** :
   - `@st.cache_data(ttl=3600)` pour PVGIS, géocodage
   - Évite requêtes API redondantes

2. **Resampling intelligent** :
   - Détection automatique du pas de temps source
   - Interpolation linéaire uniquement si nécessaire

3. **Lazy loading** :
   - Pages chargées dynamiquement (`import` dans `if`)
   - Réduction du temps de démarrage

---

## 🎨 Design UI/UX

### **Principes**
- **Layout wide** : Exploitation de l'espace horizontal
- **Navigation claire** : Sidebar avec indicateur de progression
- **Validation temps réel** : Erreurs affichées immédiatement
- **Confirmation actions critiques** : Suppression en 2 étapes

### **Composants personnalisés**
- Tables HTML avec CSS inline (performance)
- Cartes Folium avec marqueurs colorés par statut
- Donuts Plotly avec texte central (taux de couverture)

---

Cette architecture modulaire et extensible permet une évolution progressive tout en maintenant une base de code claire et maintenable. 🚀
