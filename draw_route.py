import csv
import json
import os
import networkx as nx
import matplotlib.pyplot as plt

DATA_DIR = 'data'
ROUTE_FILE = os.path.join(DATA_DIR, 'ruta_optima.json')

def load_route(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['ruta']


def main():
    filepath = "network.txt"
    G = nx.Graph()

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 3:
                u, v, w = row[0].strip(), row[1].strip(), float(row[2].strip())
                G.add_edge(u, v, weight=w)

    ruta = load_route(ROUTE_FILE)
    path_edges = list(zip(ruta[:-1], ruta[1:]))

    pos = nx.kamada_kawai_layout(G, weight="weight")

    plt.figure(figsize=(14, 10))

    nx.draw_networkx_nodes(
        G, pos, node_color="#87CEFA", node_size=600, edgecolors="black"
    )
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold")

    nx.draw_networkx_edges(G, pos, edge_color="#cccccc", style="dashed", alpha=0.5)

    nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color="#e74c3c", width=3.5)

    nx.draw_networkx_nodes(
        G, pos, nodelist=["M"], node_color="#f1c40f", node_size=800, edgecolors="black"
    )

    plt.title("Ruta Óptima del Viajante (Ciclo Hamiltoniano)", fontsize=16)
    plt.axis("off")
    plt.tight_layout()

    out_path = 'ruta_optima.png'
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Imagen guardada en: {out_path}")


if __name__ == "__main__":
    main()
