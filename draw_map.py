import csv
import json
import os
import folium

DATA_DIR = 'data'
ROUTE_FILE = os.path.join(DATA_DIR, 'ruta_optima.json')
CITIES_FILE = os.path.join(DATA_DIR, 'ciudades.tsv')
COORDS_FILE = os.path.join(DATA_DIR, 'coordenadas_centro.json')


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


def load_coords(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    cities_map = load_cities(CITIES_FILE)
    ruta = load_route(ROUTE_FILE)

    print(f"Cargando coordenadas desde {COORDS_FILE}...")
    if not os.path.exists(COORDS_FILE):
        print(f"Error: No se encontró el archivo de coordenadas {COORDS_FILE}. Ejecuta coordenadas_centros.py primero.")
        return
        
    coords = load_coords(COORDS_FILE)

    m = folium.Map(location=[40.0, -4.0], zoom_start=6, tiles="cartodbpositron")

    for code in set(ruta):
        if code in coords:
            lat, lon = coords[code]
            city_name = cities_map.get(code, code)
            color = "red" if code == "M" else "blue"
            icon = folium.Icon(color=color, icon="info-sign")
            folium.Marker([lat, lon], popup=city_name, tooltip=city_name, icon=icon).add_to(m)
        else:
            print(f"Advertencia: No hay coordenadas para la ciudad con código {code}")

    route_coords = [(coords[code][0], coords[code][1]) for code in ruta if code in coords]
    folium.PolyLine(
        route_coords, weight=4, color="red", opacity=0.8, tooltip="Ruta Óptima"
    ).add_to(m)

    out_path = 'mapa_ruta.html'
    m.save(out_path)
    print(f"\n¡Mapa interactivo generado y guardado en {out_path}!")


if __name__ == "__main__":
    main()
