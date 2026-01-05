from geopy.distance import geodesic
import folium
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATUT_CHOICES = ['Public', 'Privé', 'Para-public']
STATUT_COLORS = {
    'Public': 'blue',
    'Privé': 'orange',
    'Para-public': 'green',
}


def import_consumers(path: str) -> pd.DataFrame:
    """Importe et normalise le fichier des consommateurs (CSV ou Excel)."""
    try:
        if path.endswith('.xlsx'):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)
        
        # Ajouter colonne Statut si absente
        if 'Statut' not in df.columns:
            df['Statut'] = None
        
        # Convertir Lat/Long en float
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Long'] = pd.to_numeric(df['Long'], errors='coerce')
        
        logger.info(f"Consommateurs importés: {len(df)} lignes")
        return df
    except Exception as e:
        logger.error(f"Erreur import consommateurs: {e}")
        raise


def import_producers(path: str) -> pd.DataFrame:
    """Importe et normalise le fichier des producteurs (CSV ou Excel)."""
    try:
        if path.endswith('.xlsx'):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)
        
        # Ajouter colonne Statut si absente
        if 'Statut' not in df.columns:
            df['Statut'] = None
        
        # Convertir Lat/Long en float
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Long'] = pd.to_numeric(df['Long'], errors='coerce')
        
        logger.info(f"Producteurs importés: {len(df)} lignes")
        return df
    except Exception as e:
        logger.error(f"Erreur import producteurs: {e}")
        raise


def get_marker_color(statut: str) -> str:
    """Retourne la couleur folium selon le Statut."""
    return STATUT_COLORS.get(statut, 'gray')


def create_map_from_points(points_data: list, zoom: int = 12) -> folium.Map:
    """
    Crée une carte folium à partir d'une liste de points.
    
    Args:
        points_data: list of dicts {'lat', 'lon', 'nom', 'statut', 'type', 'commune', 'priorite'}
        zoom: niveau de zoom
    
    Returns:
        folium.Map
    """
    if not points_data:
        # Centre par défaut (Paris)
        center_lat, center_lon = 48.8566, 2.3522
    else:
        center_lat = sum(p['lat'] for p in points_data) / len(points_data)
        center_lon = sum(p['lon'] for p in points_data) / len(points_data)
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
    
    for p in points_data:
        color = get_marker_color(p.get('statut'))
        popup_html = f"""
        <b>{p['nom']}</b><br>
        Type: {p.get('type', 'N/A')}<br>
        Statut: {p.get('statut', 'N/A')}<br>
        Commune: {p.get('commune', 'N/A')}<br>
        Priorité: {p.get('priorite', 'N/A')}
        """
        folium.Marker(
            location=[p['lat'], p['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=p.get('nom', ''),
            icon=folium.Icon(color=color, icon='info-sign'),
        ).add_to(m)
    
    return m


def show_map_with_radius(points: list, radius_km: float = 10, zoom: int = 12):
    """
    Crée une carte avec cercle de rayon et centroïde optimisé.
    
    Cherche le centroïde qui maximise le nombre de points à l'intérieur du rayon.
    Si plusieurs centroïdes donnent le même nombre de points inside,
    choisit celui minimisant la somme totale des distances.
    
    Args:
        points: list of dicts {'name', 'lat', 'lon'}
        radius_km: rayon du cercle en km
        zoom: niveau de zoom folium
    
    Retourne : (folium.Map, (center_lat, center_lon), inside_list, outside_list)
        - inside_list / outside_list: list of tuples (name, distance_km)
    """
    if not points:
        raise ValueError("La liste de points est vide")

    # Centroïde initial (moyenne simple)
    def _lon(p):
        return p.get("lon", p.get("lng"))

    # Filter out points missing coordinates
    valid_points = [p for p in points if p.get("lat") is not None and _lon(p) is not None]
    if not valid_points:
        raise ValueError("La liste de points est vide ou invalide")

    orig_lat = sum(p["lat"] for p in valid_points) / len(valid_points)
    orig_lon = sum(_lon(p) for p in valid_points) / len(valid_points)

    def compute_lists(center_lat, center_lon):
        inside = []
        outside = []
        for p in valid_points:
            d = geodesic((center_lat, center_lon), (p["lat"], _lon(p))).km
            if d <= radius_km:
                inside.append((p.get("name", p.get("nom", "")), round(d, 2)))
            else:
                outside.append((p.get("name", p.get("nom", "")), round(d, 2)))
        return inside, outside

    # Calcul initial
    inside, outside = compute_lists(orig_lat, orig_lon)

    # Si des points sont en dehors, rechercher un centre candidat
    center_lat, center_lon = orig_lat, orig_lon
    if outside:
        candidates = [(p["lat"], _lon(p)) for p in valid_points]
        candidates.append((orig_lat, orig_lon))

        def total_distance(center_lat, center_lon):
            return sum(
                geodesic((center_lat, center_lon), (p["lat"], _lon(p))).km
                for p in valid_points
            )

        best_center = (orig_lat, orig_lon)
        best_inside, best_outside = inside, outside
        best_count = len(inside)
        best_total_dist = total_distance(orig_lat, orig_lon)

        for cand_lat, cand_lon in candidates:
            in_c, out_c = compute_lists(cand_lat, cand_lon)
            count = len(in_c)
            if count > best_count:
                best_count = count
                best_center = (cand_lat, cand_lon)
                best_inside, best_outside = in_c, out_c
                best_total_dist = total_distance(cand_lat, cand_lon)
            elif count == best_count:
                td = total_distance(cand_lat, cand_lon)
                if td < best_total_dist:
                    best_center = (cand_lat, cand_lon)
                    best_inside, best_outside = in_c, out_c
                    best_total_dist = td

        center_lat, center_lon = best_center
        inside, outside = best_inside, best_outside

    # Construire la carte centrée sur le centre choisi
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    names_inside = {name for name, _ in inside}
    for p in valid_points:
        actor_name = p.get("name", p.get("nom", ""))
        color = "green" if actor_name in names_inside else "red"
        # Build richer popup if optional fields are present
        popup_html = f"""
        <b>{actor_name}</b><br>
        Type: {p.get('type', 'N/A')}<br>
        Segment: {p.get('segment', 'N/A')}<br>
        Puissance: {p.get('puissance', 'N/A')}<br>
        """
        folium.Marker(
            location=[p["lat"], _lon(p)],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=actor_name,
            icon=folium.Icon(color=color)
        ).add_to(m)

    # Cercle gris
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_km * 1000,
        color="gray",
        fill=True,
        fill_opacity=0.15,
    ).add_to(m)

    return m, (center_lat, center_lon), inside, outside


def cercle(coords: dict, map_object: folium.Map, radius_km: float = 2.0, 
           color: str = "blue", fill_opacity: float = 0.15, **kwargs) -> None:
    """
    Ajoute un cercle sur une carte Folium.
    
    Args:
        coords: dict avec keys 'lat' et 'lng'
        map_object: objet folium.Map
        radius_km: rayon du cercle en kilomètres
        color: couleur du cercle
        fill_opacity: opacité du remplissage
        **kwargs: arguments supplémentaires pour folium.Circle
    """
    if not coords or not coords.get('lat') or not coords.get('lng'):
        logger.warning("Coordonnées invalides pour le cercle")
        return
    
    folium.Circle(
        location=[coords['lat'], coords['lng']],
        radius=radius_km * 1000,  # Convert km to meters
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=fill_opacity,
        opacity=0.5,
        **kwargs
    ).add_to(map_object)