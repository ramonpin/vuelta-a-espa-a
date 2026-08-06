#!/usr/bin/env python3
"""
TSP resolver — Algoritmo Genético + búsqueda local (algoritmo memético).

Estrategia:
  1. Inicialización con greedy aleatorio: sigue aristas válidas siempre que es
     posible, creando rutas mayoritariamente válidas (~35/47 aristas correctas).
  2. Reparación agresiva: corrige aristas inválidas mediante swaps locales
     que reducen el número total de aristas rotas.
  3. PMX como cruce. Mutaciones ligeras para diversidad.
  4. Búsqueda local 2-opt como post-optimización de rutas válidas.
"""

import csv
import json
import os
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass

DATA_DIR = "data"
ROUTE_FILE = os.path.join(DATA_DIR, "ruta_optima_genetic.json")

POP_SIZE = 200
MAX_GENERATIONS = 1000
TOURNAMENT_SIZE = 3
CROSSOVER_RATE = 0.75
MUTATION_RATE = 0.40
ELITE_COUNT = 10
PATIENCE = 200

INIT_PENALTY = 3000.0
FINAL_PENALTY = 15000.0


@dataclass
class Individual:
    route: list[str]
    fitness: float = float("inf")
    invalid_edges: int = 0
    valid_distance: float = 0.0


# ── Carga de datos ──────────────────────────────────────────────────────────


def load_network(filepath: str = "network.txt"):
    edges: dict[tuple[str, str], float] = {}
    adj_list: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()

    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 3:
                u, v, w = row[0].strip(), row[1].strip(), float(row[2].strip())
                edges[(u, v)] = w
                adj_list[u].add(v)
                nodes.add(u)
                nodes.add(v)

    return edges, adj_list, sorted(nodes)


# ── Inicialización guiada por el grafo ──────────────────────────────────────


def greedy_random_route(
    start: str, adj_list: dict, nodes_set: set
) -> list[str]:
    """
    Construye una ruta siguiendo aristas válidas siempre que sea posible.
    - En cada paso, elige un vecino no visitado al azar (si existe).
    - Si no quedan vecinos no visitados, salta a cualquier ciudad no visitada
      (genera arista inválida mínima).
    - Cierra volviendo a `start`.
    """
    route = [start]
    unvisited = set(nodes_set) - {start}

    while unvisited:
        current = route[-1]
        candidates = [c for c in unvisited if c in adj_list[current]]
        if candidates:
            route.append(random.choice(candidates))
        else:
            route.append(random.choice(list(unvisited)))
        unvisited.remove(route[-1])

    route.append(start)
    return route


def init_population(
    adj_list: dict, nodes_set: set, pop_size: int
) -> list[list[str]]:
    return [greedy_random_route("M", adj_list, nodes_set) for _ in range(pop_size)]


# ── Evaluación ──────────────────────────────────────────────────────────────


def route_fitness(
    route: list[str], edges: dict, penalty: float
) -> tuple[float, int, float]:
    valid_dist = 0.0
    invalid = 0
    for i in range(len(route) - 1):
        key = (route[i], route[i + 1])
        if key in edges:
            valid_dist += edges[key]
        else:
            invalid += 1
    return valid_dist + penalty * invalid, invalid, valid_dist


def evaluate(
    population: list[list[str]], edges: dict, penalty: float
) -> list[Individual]:
    return sorted(
        (
            Individual(route=r, fitness=f, invalid_edges=i, valid_distance=v)
            for r in population
            for f, i, v in [route_fitness(r, edges, penalty)]
        ),
        key=lambda x: x.fitness,
    )


def current_penalty(gen: int, max_gen: int) -> float:
    if gen < max_gen // 2:
        t = gen / (max_gen // 2)
        return INIT_PENALTY + (FINAL_PENALTY - INIT_PENALTY) * t
    return FINAL_PENALTY


# ── Reparación agresiva ─────────────────────────────────────────────────────


def _count_invalid(route: list[str], adj_list: dict) -> int:
    return sum(
        1
        for i in range(len(route) - 1)
        if route[i + 1] not in adj_list[route[i]]
    )


def repair_route(route: list[str], adj_list: dict, max_iter: int = 200) -> bool:
    """
    Hill-climbing sobre la permutación: para cada arista inválida (a,b),
    busca un swap (b ↔ c) que reduzca el número total de aristas inválidas.
    Retorna True si se realizó al menos una mejora.
    """
    improved = True
    total_improved = False
    iters = 0

    while improved and iters < max_iter:
        improved = False
        iters += 1
        n = len(route)
        old_invalid = _count_invalid(route, adj_list)
        if old_invalid == 0:
            break

        for i in range(n - 1):
            a, b = route[i], route[i + 1]
            if b in adj_list[a]:
                continue  # arista ya válida

            for j in range(i + 2, n):
                c = route[j]
                if c not in adj_list[a]:
                    continue

                route[i + 1], route[j] = route[j], route[i + 1]
                new_invalid = _count_invalid(route, adj_list)

                if new_invalid < old_invalid:
                    improved = True
                    total_improved = True
                    break
                else:
                    route[i + 1], route[j] = route[j], route[i + 1]

            if improved:
                break

    return total_improved


# ── Selección ───────────────────────────────────────────────────────────────


def tournament_select(individuals: list[Individual], k: int) -> Individual:
    candidates = random.sample(individuals, min(k, len(individuals)))
    return min(candidates, key=lambda x: x.fitness)


# ── Cruce PMX ───────────────────────────────────────────────────────────────


def pmx_crossover(p1: list[str], p2: list[str]) -> list[str]:
    n = len(p1)
    a = random.randint(1, n - 3)
    b = random.randint(a, n - 2)

    child = ["M"] + [None] * (n - 2) + ["M"]

    for i in range(a, b + 1):
        child[i] = p1[i]

    mapping: dict[str, str] = {}
    for i in range(a, b + 1):
        mapping[p1[i]] = p2[i]

    for i in range(1, n - 1):
        if child[i] is not None:
            continue
        val = p2[i]
        while val in mapping:
            val = mapping[val]
        child[i] = val

    return child


# ── Mutaciones ──────────────────────────────────────────────────────────────


def mutate_swap(route: list[str]) -> bool:
    n = len(route) - 1
    i = random.randint(1, n - 1)
    j = random.randint(1, n - 1)
    if abs(i - j) <= 1:
        return False
    route[i], route[j] = route[j], route[i]
    return True


def mutate_invert(route: list[str]) -> bool:
    n = len(route)
    i = random.randint(1, n - 3)
    j = random.randint(i + 1, n - 2)
    route[i : j + 1] = list(reversed(route[i : j + 1]))
    return True


def mutate_insert(route: list[str]) -> bool:
    n = len(route) - 1
    i = random.randint(1, n - 1)
    val = route.pop(i)
    j = random.randint(1, n - 1)
    route.insert(j, val)
    return True


# ── Búsqueda local 2-opt ────────────────────────────────────────────────────


def _route_distance(route: list[str], edges: dict) -> float:
    d = 0.0
    for i in range(len(route) - 1):
        key = (route[i], route[i + 1])
        if key not in edges:
            return float("inf")
        d += edges[key]
    return d


def local_search_2opt(
    route: list[str], edges: dict, adj_list: dict
) -> list[str]:
    improved = True
    best_route = route.copy()
    best_dist = _route_distance(best_route, edges)

    while improved:
        improved = False
        n = len(best_route)
        for i in range(1, n - 3):
            for j in range(i + 1, n - 2):
                a_before, b_after = best_route[i - 1], best_route[j + 1]
                if best_route[j] in adj_list[a_before] and best_route[i] in adj_list[
                    b_after
                ]:
                    candidate = best_route.copy()
                    candidate[i : j + 1] = list(reversed(candidate[i : j + 1]))
                    cand_dist = _route_distance(candidate, edges)
                    if cand_dist < best_dist:
                        best_route = candidate
                        best_dist = cand_dist
                        improved = True

    return best_route


# ── Comparación robusta ─────────────────────────────────────────────────────


def is_strictly_better(a: Individual, b: Individual) -> bool:
    if a.invalid_edges < b.invalid_edges:
        return True
    if a.invalid_edges == b.invalid_edges:
        return a.fitness < b.fitness - 0.01
    return False


# ── Stats ───────────────────────────────────────────────────────────────────


def population_stats(
    individuals: list[Individual],
) -> tuple[int, float, float, float]:
    valid = [ind for ind in individuals if ind.invalid_edges == 0]
    n_valid = len(valid)
    best_valid = min((ind.valid_distance for ind in valid), default=float("inf"))
    avg_inv = sum(ind.invalid_edges for ind in individuals) / len(individuals)
    min_inv = min(ind.invalid_edges for ind in individuals)
    return n_valid, best_valid, avg_inv, min_inv


# ── GA principal ────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  ALGORITMO MEMÉTICO — TSP Vuelta a España")
    print("=" * 60)

    edges, adj_list, nodes = load_network()
    nodes_set = set(nodes)
    N = len(nodes)
    print(f"\nCiudades: {N}  |  Conexiones: {len(edges) // 2}")
    print(
        f"Parámetros: pop={POP_SIZE}  max_gen={MAX_GENERATIONS}  elite={ELITE_COUNT}"
    )
    print(
        f"             torneo_k={TOURNAMENT_SIZE}  pc={CROSSOVER_RATE}  pm={MUTATION_RATE}"
    )
    print(f"             penalización: {INIT_PENALTY:.0f} → {FINAL_PENALTY:.0f}")

    random.seed(42)
    t0 = time.time()

    OPTIMUM = 6036.3

    print(f"\nInicializando con greedy aleatorio ({POP_SIZE} rutas)...")
    population = init_population(adj_list, nodes_set, POP_SIZE)
    penalty = current_penalty(0, MAX_GENERATIONS)
    individuals = evaluate(population, edges, penalty)

    best_ever = individuals[0]
    gens_no_improve = 0

    best_valid_ever = float("inf")
    best_valid_route = None

    n_valid, bv, avg_inv, min_inv = population_stats(individuals)
    print(
        f"  Mejor inicial: {best_ever.fitness:.1f} km"
        f"  (inválidas: {best_ever.invalid_edges})"
    )
    print(
        f"  Válidos: {n_valid}/{POP_SIZE}  |  inv_media: {avg_inv:.1f}  |  inv_mín: {min_inv}"
    )
    print(f"  Penalización: {penalty:.0f}\n")

    for gen in range(MAX_GENERATIONS):
        penalty = current_penalty(gen, MAX_GENERATIONS)

        individuals = evaluate(
            [ind.route for ind in individuals], edges, penalty
        )

        new_pop = [ind.route.copy() for ind in individuals[:ELITE_COUNT]]

        while len(new_pop) < POP_SIZE:
            parent1 = tournament_select(individuals, TOURNAMENT_SIZE)
            parent2 = tournament_select(individuals, TOURNAMENT_SIZE)

            if random.random() < CROSSOVER_RATE:
                child = pmx_crossover(parent1.route, parent2.route)
            else:
                child = parent1.route.copy()

            # Reparar SIEMPRE tras el cruce
            repair_route(child, adj_list)

            if random.random() < MUTATION_RATE:
                r = random.random()
                if r < 0.30:
                    mutate_swap(child)
                elif r < 0.55:
                    mutate_invert(child)
                elif r < 0.75:
                    mutate_insert(child)
                else:
                    # Reparación adicional como "mutación"
                    repair_route(child, adj_list)

            new_pop.append(child)

        individuals = evaluate(new_pop, edges, penalty)
        current_best = individuals[0]

        for ind in individuals:
            if ind.invalid_edges == 0 and ind.valid_distance < best_valid_ever:
                best_valid_ever = ind.valid_distance
                best_valid_route = ind.route.copy()

        if is_strictly_better(current_best, best_ever):
            best_ever = current_best
            gens_no_improve = 0
        else:
            gens_no_improve += 1

        if gen % 100 == 0 or gen == MAX_GENERATIONS - 1 or gens_no_improve == 0:
            n_valid, _, avg_inv, min_inv = population_stats(individuals)
            marker = " *" if gens_no_improve == 0 else "  "
            if best_valid_ever < float("inf"):
                gap = (best_valid_ever / OPTIMUM - 1) * 100
                vinfo = f"mejor_vál={best_valid_ever:.1f} ({gap:+.1f}%)"
            else:
                vinfo = "mejor_vál=—"
            print(
                f"{marker} Gen {gen:4d} | best={current_best.fitness:.1f}"
                f" (inv={current_best.invalid_edges}) |"
                f" vál={n_valid}/{POP_SIZE} | {vinfo} |"
                f" inv_avg={avg_inv:.1f}"
            )

        if gens_no_improve >= PATIENCE:
            print(f"\n  Convergencia: {PATIENCE} generaciones sin mejora.")
            break

    if best_valid_route is not None:
        best_valid_route = local_search_2opt(best_valid_route, edges, adj_list)
        best_valid_ever = _route_distance(best_valid_route, edges)
    elif best_ever.invalid_edges == 0:
        best_valid_route = local_search_2opt(best_ever.route, edges, adj_list)
        best_valid_ever = _route_distance(best_valid_route, edges)

    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print(f"  RESULTADO")
    print(f"{'='*60}")
    print(f"  Generaciones:    {gen + 1}")
    print(f"  Tiempo:          {elapsed:.1f}s")

    if best_valid_route is not None:
        gap = (best_valid_ever / OPTIMUM - 1) * 100
        print(f"  Mejor distancia: {best_valid_ever:.1f} km")
        print(f"  Óptimo ILP:      {OPTIMUM:.1f} km")
        print(
            f"  Diferencia:      {best_valid_ever - OPTIMUM:+.1f} km ({gap:+.2f}%)"
        )

        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ROUTE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "distancia_km": round(best_valid_ever, 2),
                    "ruta": best_valid_route,
                    "metodo": "genetico",
                    "generaciones": gen + 1,
                    "tiempo_s": round(elapsed, 1),
                    "gap_pct": round(gap, 2),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n  Resultado guardado en {ROUTE_FILE}")

        print("\n  Ruta encontrada:")
        path = best_valid_route
        for i in range(0, len(path), 10):
            chunk = path[i : i + 10]
            suffix = " →" if i + 10 < len(path) else ""
            print("    " + " → ".join(chunk) + suffix)
    else:
        print("  No se encontró ninguna ruta válida.")


if __name__ == "__main__":
    main()
