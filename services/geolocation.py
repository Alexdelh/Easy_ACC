from typing import Dict
import re
import streamlit as st
from geopy.geocoders import Nominatim
import ssl
import certifi
import geopy.geocoders

# Fix for macOS SSL certificate errors: explicitly use certifi's CA bundle & create a context
ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx

# Placeholder service for geolocation; will replace utils.helpers later
GEO_DATABASE = {
    "Paris": {"lat": 48.8566, "lng": 2.3522, "epci": "Métropole du Grand Paris"},
    "Lyon": {"lat": 45.7640, "lng": 4.8357, "epci": "Métropole de Lyon"},
    "Marseille": {"lat": 43.2965, "lng": 5.3698, "epci": "Provence Alpes Côte d'Azur"},
    "Toulouse": {"lat": 43.6047, "lng": 1.4442, "epci": "Toulouse Métropole"},
    "Nice": {"lat": 43.7102, "lng": 7.2620, "epci": "Métropole Nice Côte d'Azur"},
}


def extract_postal_code(address: str) -> str:
    """
    Extract French postal code from address string.
    French postal codes are 5 digits.
    
    Args:
        address: Address string that may contain a postal code
    
    Returns:
        Postal code string (5 digits) or empty string if not found
    """
    # Find 5-digit sequence in the address
    match = re.search(r'\b(\d{5})\b', address)
    return match.group(1) if match else ""


@st.cache_data(ttl=3600)
def get_coordinates_from_address(address: str) -> Dict[str, float]:
    """
    Retrieve coordinates from address using Nominatim API (OpenStreetMap).
    First tries the mock database for known cities, then falls back to live API.
    Results cached for 1 hour to minimize API calls.
    """
    # Try mock database first
    if address in GEO_DATABASE:
        return GEO_DATABASE[address]
    
    # Fall back to live API using Nominatim
    try:
        geopy.geocoders.options.default_ssl_context = ctx
        geopy.geocoders.options.default_timeout = 10
        
        geolocator = Nominatim(user_agent="acc_app_v1", ssl_context=ctx)
        location = geolocator.geocode(
            address, 
            country_codes="FR",  # Forcer France
            timeout=10,          # Timeout prolongé
            language="fr"       # Résultats en français
        )
        
        if location:
            return {
                "lat": location.latitude,
                "lng": location.longitude,
                "epci": "N/A"
            }
        else:
            # Log failure for debugging
            st.error(f"Adresse non trouvée: {address}")
            # Return None values to indicate failure instead of Paris fallback
            return {
                "lat": None,
                "lng": None,
                "epci": "Non trouvé"
            }
    except Exception as e:
        st.error(f"Erreur API géolocalisation: {str(e)}")
        return {
            "lat": None,
            "lng": None,
            "epci": "Erreur API"
        }
