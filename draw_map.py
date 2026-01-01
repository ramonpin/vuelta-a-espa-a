import csv
import json
import os
import time
import folium
from geopy.geocoders import Nominatim

DATA_DIR = 'data'
ROUTE_FILE = os.path.join(DATA_DIR, 'ruta_optima.json')
CITIES_FILE = os.path.join(DATA_DIR, 'ciudades.tsv')
COORDS_FILE = os.path.join(DATA_DIR, 'coordenadas.json')


def load_cities(filepath):
    cities = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                cities[row[0].strip()] = row[1].strip()
    return cities


def load_route(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['ruta']


def main():
    cities_map = load_cities(CITIES_FILE)
    ruta = load_route(ROUTE_FILE)

    geolocator = Nominatim(user_agent="viajante_spain_agent")

    coords = {}
    print("Obteniendo coordenadas de las ciudades mediante Nominatim...")

    for code in set(ruta):
        city_name = cities_map[code]
        query = f"{city_name}, Spain"
        try:
            location = geolocator.geocode(query)
            if location:
                coords[code] = [location.latitude, location.longitude]
                print(f"✓ {city_name} -> {coords[code]}")
            else:
                print(f"✗ No se encontró: {query}")
                coords[code] = [40.4168, -3.7038]
        except Exception as e:
            print(f"Error con {query}: {e}")
            coords[code] = [40.4168, -3.7038]
        time.sleep(1.2)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(coords, f, ensure_ascii=False, indent=2)
    print(f"Coordenadas guardadas en {COORDS_FILE}")

    m = folium.Map(location=[40.0, -4.0], zoom_start=6, tiles="cartodbpositron")

    for code, (lat, lon) in coords.items():
        city_name = cities_map[code]
        color = "red" if code == "M" else "blue"
        icon = folium.Icon(color=color, icon="info-sign")
        folium.Marker([lat, lon], popup=city_name, tooltip=city_name, icon=icon).add_to(m)

    route_coords = [(coords[code][0], coords[code][1]) for code in ruta]
    folium.PolyLine(
        route_coords, weight=4, color="red", opacity=0.8, tooltip="Ruta Óptima"
    ).add_to(m)

    out_path = 'mapa_ruta.html'
    m.save(out_path)
    print(f"\n¡Mapa interactivo generado y guardado en {out_path}!")


if __name__ == "__main__":
    main()
