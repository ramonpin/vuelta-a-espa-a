import csv
import json
import os
import pulp
from collections import defaultdict

DATA_DIR = 'data'
ROUTE_FILE = os.path.join(DATA_DIR, 'ruta_optima.json')

def main():
    filepath = 'network.txt'
    edges = {}
    nodes = set()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader, None)
            for row in reader:
                if len(row) >= 3:
                    u, v, w = row[0].strip(), row[1].strip(), float(row[2].strip())
                    edges[(u, v)] = w
                    edges[(v, u)] = w
                    nodes.add(u)
                    nodes.add(v)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    nodes = list(nodes)
    N = len(nodes)
    print(f"Total de ciudades en la red: {N}")

    degree = defaultdict(int)
    for u, v in edges:
        degree[u] += 1

    impossible = False
    for node in nodes:
        if degree[node] < 2:
            print(f"¡Atención! El nodo {node} tiene solo {degree[node]} conexiones.")
            impossible = True

    if impossible:
        print("Es imposible formar un ciclo que visite todas las ciudades (Ciclo Hamiltoniano).")

    prob = pulp.LpProblem("TSP_M", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", edges.keys(), cat=pulp.LpBinary)
    u_var = pulp.LpVariable.dicts("u", nodes, cat=pulp.LpContinuous)

    prob += pulp.lpSum(edges[e] * x[e] for e in edges), "Total_Distance"

    for i in nodes:
        prob += pulp.lpSum(x[(i, j)] for j in nodes if (i, j) in edges) == 1, f"Out_{i}"
        prob += pulp.lpSum(x[(j, i)] for j in nodes if (j, i) in edges) == 1, f"In_{i}"

    start_node = 'M'
    if start_node not in nodes:
        print(f"Error: la ciudad base {start_node} no existe.")
        return

    for i in nodes:
        if i == start_node:
            prob += u_var[i] == 1, f"MTZ_Init_{i}"
        else:
            prob += u_var[i] >= 2, f"MTZ_Min_{i}"
            prob += u_var[i] <= N, f"MTZ_Max_{i}"

    for i in nodes:
        for j in nodes:
            if i != j and i != start_node and j != start_node and (i, j) in edges:
                prob += u_var[i] - u_var[j] + N * x[(i, j)] <= N - 1, f"MTZ_Subtour_{i}_{j}"

    print("Resolviendo el modelo (esto puede tardar unos segundos dependiendo de la red)...")
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if prob.status == pulp.LpStatusOptimal:
        distancia = pulp.value(prob.objective)
        print(f"\n¡Solución óptima exacta encontrada!")
        print(f"Distancia total: {distancia:.2f}")

        next_node = {}
        for (i, j) in edges:
            if pulp.value(x[(i, j)]) and pulp.value(x[(i, j)]) > 0.5:
                next_node[i] = j

        path = [start_node]
        current = start_node
        while True:
            current = next_node[current]
            path.append(current)
            if current == start_node:
                break

        print("\nRuta óptima:")
        chunk_size = 10
        for i in range(0, len(path), chunk_size):
            chunk = path[i:i+chunk_size]
            print(" -> ".join(chunk) + (" ->" if i + chunk_size < len(path) else ""))

        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ROUTE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"distancia_km": round(distancia, 2), "ruta": path}, f, ensure_ascii=False, indent=2)
        print(f"\nRuta guardada en {ROUTE_FILE}")

    elif prob.status == pulp.LpStatusInfeasible:
        print("\nEl problema es INFACTIBLE.")
        print("Esto significa que NO EXISTE ninguna ruta válida en tu archivo que pueda visitar todas las ciudades sin repetir ninguna y volver a 'M'.")
        print("La red no está lo suficientemente conectada para permitir un Ciclo Hamiltoniano puro.")
    else:
        print(f"\nEl solver terminó con el estado: {pulp.LpStatus[prob.status]}")

if __name__ == '__main__':
    main()
