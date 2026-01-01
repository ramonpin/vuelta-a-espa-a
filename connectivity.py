import csv
import json
import os
from collections import defaultdict

DATA_DIR = 'data'
CONNECTIVITY_FILE = os.path.join(DATA_DIR, 'conectividad.json')

def main():
    filepath = 'network.txt'
    connectivity = defaultdict(int)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)

            for row in reader:
                if len(row) >= 2:
                    origen = row[0].strip()
                    destino = row[1].strip()
                    connectivity[origen] += 1

        sorted_connectivity = sorted(connectivity.items(), key=lambda x: (-x[1], x[0]))

        print(f"{'Nodo':<10} {'Conexiones (Grado)':<20}")
        print("-" * 35)
        for node, degree in sorted_connectivity:
            print(f"{node:<10} {degree:<20}")

        os.makedirs(DATA_DIR, exist_ok=True)
        conectividad_data = {node: degree for node, degree in sorted_connectivity}
        with open(CONNECTIVITY_FILE, 'w', encoding='utf-8') as f:
            json.dump(conectividad_data, f, ensure_ascii=False, indent=2)
        print(f"\nDatos de conectividad guardados en {CONNECTIVITY_FILE}")

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{filepath}'.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == '__main__':
    main()
