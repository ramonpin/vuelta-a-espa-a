import json
import csv
import time
from pathlib import Path
from geopy.geocoders import Nominatim

def generar_coordenadas_centros():
    directorio_data = Path(__file__).parent / 'data'
    ruta_ciudades = directorio_data / 'ciudades.tsv'
    ruta_salida = directorio_data / 'coordenadas_centro.json'
    
    # Inicializar Nominatim con un user_agent descriptivo
    geolocator = Nominatim(user_agent="calculadora_rutas_espana")
    
    nuevas_coordenadas = {}

    print("Obteniendo coordenadas de centros urbanos...")
    print("-" * 50)
    
    try:
        with open(ruta_ciudades, mode='r', encoding='utf-8') as f:
            lector = csv.reader(f, delimiter='\t')
            next(lector)  # Saltar cabecera
            
            for fila in lector:
                if len(fila) >= 2:
                    codigo = fila[0].strip()
                    ciudad = fila[1].strip()
                    
                    # Búsqueda estructurada: fuerza a buscar la ciudad, no la provincia
                    query = {
                        'city': ciudad,
                        'country': 'Spain'
                    }
                    
                    try:
                        ubicacion = geolocator.geocode(query)
                        
                        if ubicacion:
                            # Guardamos en formato [latitud, longitud]
                            nuevas_coordenadas[codigo] = [ubicacion.latitude, ubicacion.longitude]
                            print(f"[OK] {ciudad:<15} -> {ubicacion.latitude:.6f}, {ubicacion.longitude:.6f}")
                        else:
                            # Plan B: Añadir "capital" o "Ayuntamiento" si falla la primera
                            ubicacion_alt = geolocator.geocode(f"Ayuntamiento de {ciudad}, España")
                            if ubicacion_alt:
                                nuevas_coordenadas[codigo] = [ubicacion_alt.latitude, ubicacion_alt.longitude]
                                print(f"[OK] {ciudad:<15} -> {ubicacion_alt.latitude:.6f}, {ubicacion_alt.longitude:.6f} (Plan B)")
                            else:
                                print(f"[FALLO] No se encontró: {ciudad}")
                                
                    except Exception as e:
                        print(f"[ERROR] Excepción con {ciudad}: {e}")
                    
                    # Retraso obligatorio de 1 segundo para Nominatim
                    time.sleep(1)
                    
    except FileNotFoundError:
        print(f"Error: No se encuentra '{ruta_ciudades}'.")
        return

    # Guardar el nuevo JSON
    with open(ruta_salida, mode='w', encoding='utf-8') as f_out:
        json.dump(nuevas_coordenadas, f_out, indent=2, ensure_ascii=False)
        
    print("-" * 50)
    print(f"Proceso finalizado. Archivo guardado en: {ruta_salida}")

if __name__ == "__main__":
    generar_coordenadas_centros()