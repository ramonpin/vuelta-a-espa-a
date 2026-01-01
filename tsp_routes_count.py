import csv
import math

def main():
    filepath = 'network.txt'
    nodes = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    nodes.add(row[0].strip())
                    nodes.add(row[1].strip())
                    
        n = len(nodes)
        print(f"Total de nodos (ciudades) en la red: {n}")
        
        # En el Problema del Viajante (TSP), una "ruta" es un ciclo que pasa
        # por todas las ciudades exactamente una vez y vuelve al origen (Ciclo Hamiltoniano).
        # El número total de ciclos posibles en un grafo completo (donde todas las ciudades 
        # están conectadas con todas) de forma simétrica (A->B es igual a B->A) es (N-1)! / 2.
        
        if n > 2:
            total_rutas_teoricas = math.factorial(n - 1) // 2
            print(f"Número total de posibles rutas teóricas (si el grafo fuera completo y simétrico):")
            print(f"({n} - 1)! / 2 = {total_rutas_teoricas}")
            
            # Formato en notación científica para dar contexto
            print(f"\nEn notación científica esto es aproximadamente: {total_rutas_teoricas:.2e}")
        else:
            print("No hay suficientes nodos para calcular rutas.")
            
        print("\n[!] NOTA IMPORTANTE:")
        print("Este cálculo asume que podemos viajar directamente de cualquier ciudad a cualquier otra.")
        print("En tu archivo 'network.txt', no todas las ciudades están conectadas directamente.")
        print("Calcular el número EXACTO de rutas válidas que solo usen los caminos existentes en tu archivo")
        print("para 47 ciudades requeriría un algoritmo de búsqueda exhaustiva (fuerza bruta).")
        print("Debido a la magnitud del número (es un problema NP-Hard), el cálculo exacto de rutas válidas")
        print("tomaría demasiado tiempo (milenios) en completarse de manera exhaustiva.")
            
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{filepath}'.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == '__main__':
    main()
