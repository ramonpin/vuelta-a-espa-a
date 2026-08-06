import json
import csv
import requests
from pathlib import Path


def generar_fichero_distancias_filtradas():
    directorio_data = Path(__file__).parent / "data"
    ruta_coordenadas = directorio_data / "coordenadas_centro.json"
    ruta_ciudades = directorio_data / "ciudades.tsv"
    ruta_salida = directorio_data / "distancias_menos_250km.tsv"

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
    try:
        with open(ruta_coordenadas, mode="r", encoding="utf-8") as f:
            coordenadas = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encuentra '{ruta_coordenadas}'.")
        return

    # 3. Preparar la llamada a la API OSRM (Table service)
    codigos = list(coordenadas.keys())
    # OSRM recibe las coordenadas como lon,lat
    coordenadas_str = ";".join([f"{coordenadas[c][1]},{coordenadas[c][0]}" for c in codigos])
    
    url = f"http://router.project-osrm.org/table/v1/driving/{coordenadas_str}?annotations=distance"
    
    print(f"Consultando matriz de distancias a OSRM para {len(codigos)} ciudades...")
    try:
        respuesta = requests.get(url, timeout=20)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if datos.get("code") == "Ok":
                distancias_matrix = datos.get("distances")
            else:
                print(f"Error en OSRM: {datos.get('code')}")
                return
        else:
            print(f"Error HTTP {respuesta.status_code}: {respuesta.text}")
            return
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")
        return

    # 4. Procesar red y generar salida
    conexiones_guardadas = 0
    with open(ruta_salida, mode="w", encoding="utf-8", newline="") as f_out:
        escritor = csv.writer(f_out, delimiter="\t")
        escritor.writerow(["Origen", "Destino", "Distancia_km"])
        
        for i in range(len(codigos)):
            for j in range(i + 1, len(codigos)):
                distancia_metros = distancias_matrix[i][j]
                if distancia_metros is not None:
                    distancia_km = distancia_metros / 1000
                    if distancia_km < 250:
                        origen = codigos[i]
                        destino = codigos[j]
                        nombre_origen = ciudades.get(origen, origen)
                        nombre_destino = ciudades.get(destino, destino)
                        
                        escritor.writerow([origen, destino, f"{distancia_km:.2f}"])
                        print(f"✓ {nombre_origen} -> {nombre_destino}: {distancia_km:.2f} km")
                        conexiones_guardadas += 1

    print(f"\nProceso finalizado. Se encontraron {conexiones_guardadas} conexiones de menos de 250km.")
    print(f"Guardadas en: {ruta_salida}")


if __name__ == "__main__":
    generar_fichero_distancias_filtradas()
