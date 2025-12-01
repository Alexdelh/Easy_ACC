from geopy.distance import geodesic
import folium

def show_map_with_radius(points, radius_km=20, zoom=12):
        if not points:
            raise ValueError("La liste de points est vide")

        # 1. Centroïde
        center_lat = sum(p["lat"] for p in points) / len(points)
        center_lon = sum(p["lon"] for p in points) / len(points)

        # 2. Carte Folium
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

        # 5. Vérification des distances (fait avant pour avoir les listes)
        inside = []
        outside = []

        for p in points:
            d = geodesic((center_lat, center_lon), (p["lat"], p["lon"])).km
            if d <= radius_km:
                inside.append((p["name"], round(d, 2)))
            else:
                outside.append((p["name"], round(d, 2)))

        # 3. Points avec couleurs (vert=inside, rouge=outside)
        for p in points:
            # Déterminer la couleur basée sur si le point est inside ou outside
            is_inside = any(name == p["name"] for name, _ in inside)
            color = "green" if is_inside else "red"
            
            folium.Marker(
                location=[p["lat"], p["lon"]],
                popup=p["name"],
                icon=folium.Icon(color=color)
            ).add_to(m)

        # 4. Cercle autour du centroïde (gris)
        folium.Circle(
            location=[center_lat, center_lon],
            radius=radius_km * 1000,  # meters
            color="gray",
            fill=True,
            fill_opacity=0.15
        ).add_to(m)

        return m, (center_lat, center_lon), inside, outside