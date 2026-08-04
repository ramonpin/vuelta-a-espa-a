import json
import os
from staticmap import StaticMap, Line, CircleMarker

DATA_DIR = 'data'
ROUTE_FILE = os.path.join(DATA_DIR, 'ruta_optima.json')
COORDS_FILE = os.path.join(DATA_DIR, 'coordenadas_centro.json')


def load_coords(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_route(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['ruta']


def main():
    coords = load_coords(COORDS_FILE)
    ruta = load_route(ROUTE_FILE)

    m = StaticMap(1200, 800)

    for code, (lat, lon) in coords.items():
        color = '#FF0000' if code == 'M' else '#3366CC'
        size = 8 if code == 'M' else 6
        marker = CircleMarker((lon, lat), color, size)
        m.add_marker(marker)

    route_lonlat = [(coords[code][1], coords[code][0]) for code in ruta]
    line = Line(route_lonlat, 'red', 4)
    m.add_line(line)

    print("Renderizando mapa estático...")
    image = m.render(zoom=6)
    out_path = 'mapa_ruta_estatico.png'
    image.save(out_path)
    print(f"Mapa estático guardado en {out_path}")


if __name__ == '__main__':
    main()
