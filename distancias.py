import json
import csv
import time
import requests
from pathlib import Path


def obtener_distancia_carretera(coord1, coord2):
    lon1, lat1 = coord1[1], coord1[0]
    lon2, lat2 = coord2[1], coord2[0]

    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"

    try:
        respuesta = requests.get(url, timeout=10)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if datos.get("code") == "Ok":
                return datos["routes"][0]["distance"] / 1000
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")

    return None


def generar_fichero_distancias():
    directorio_data = Path(__file__).parent / "data"
    ruta_coordenadas = directorio_data / "coordenadas_centro.json"
    ruta_network = "network.txt"
    ruta_ciudades = directorio_data / "ciudades.tsv"
    ruta_salida = directorio_data / "distancias_nombres.tsv"

    # 1. Leer el diccionario de códigos a nombres
    ciudades = {}
    try:
        with open(ruta_ciudades, mode="r", encoding="utf-8") as f:
            lector = csv.reader(f, delimiter="\t")
            next(lector)  # Saltar la cabecera (Codigo, Nombre)
            for fila in lector:
                if len(fila) >= 2:
                    ciudades[fila[0].strip()] = fila[1].strip()
    except FileNotFoundError:
        print("Error: No se encuentra 'ciudades.tsv' en la carpeta data/")
        return

    # 2. Leer las coordenadas
    with open(ruta_coordenadas, mode="r", encoding="utf-8") as f:
        coordenadas = json.load(f)

    # 3. Procesar red y generar salida
    with (
        open(ruta_network, mode="r", encoding="utf-8") as f_in,
        open(ruta_salida, mode="w", encoding="utf-8", newline="") as f_out,
    ):
        # Omitimos la cabecera en el fichero de salida según tu formato
        escritor = csv.writer(f_out, delimiter="\t")

        # Saltar la cabecera de network.txt (Origen Destino Distancia)
        lineas = f_in.readlines()[1:]

        for linea in lineas:
            if not linea.strip():
                continue

            partes = linea.split()
            if len(partes) >= 2:
                origen = partes[0]
                destino = partes[1]

                if origen in coordenadas and destino in coordenadas:
                    coord_origen = coordenadas[origen]
                    coord_destino = coordenadas[destino]

                    distancia = obtener_distancia_carretera(coord_origen, coord_destino)

                    # Traducir a nombres completos (usa el código si no encuentra el nombre)
                    nombre_origen = ciudades.get(origen, origen)
                    nombre_destino = ciudades.get(destino, destino)

                    if distancia is not None:
                        # Formato a 2 decimales
                        valor_formateado = f"{distancia:.2f}"
                    else:
                        valor_formateado = "Error"

                    escritor.writerow([origen, destino, valor_formateado])
                    print(
                        f"Procesado: {nombre_origen} -> {nombre_destino}: {valor_formateado} km"
                    )

                    time.sleep(1)
                else:
                    print(f"Coordenadas no encontradas para: {origen} o {destino}")


if __name__ == "__main__":
    generar_fichero_distancias()
