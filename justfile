_default:
    @just --list

resolver:
    uv run python solve_tsp.py

grafo: resolver
    uv run python draw_route.py

mapa: resolver
    uv run python draw_map.py

estatico: mapa
    uv run python draw_static_map.py

conectar:
    uv run python connectivity.py

rutas:
    uv run python tsp_routes_count.py

all: conectar resolver grafo mapa estatico

clean:
    rm -f data/ruta_optima.json data/coordenadas_centro.json data/conectividad.json
    rm -f ruta_optima.png mapa_ruta.html mapa_ruta_estatico.png
