from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "analysis_outputs"
ASSET_DIR.mkdir(parents=True, exist_ok=True)


def save_figure(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close()


def main() -> None:
    graph = nx.karate_club_graph()
    nodes = sorted(graph.nodes())
    degrees = dict(graph.degree())
    clustering = nx.clustering(graph)
    degree_centrality = nx.degree_centrality(graph)
    betweenness = nx.betweenness_centrality(graph, normalized=True)
    closeness = nx.closeness_centrality(graph)
    eigenvector = nx.eigenvector_centrality(graph, max_iter=2000)

    true_labels = [0 if graph.nodes[node]["club"] == "Mr. Hi" else 1 for node in nodes]
    first_split = next(nx.community.girvan_newman(graph))
    detected_sets = [set(group) for group in first_split]
    predicted = [0 if node in detected_sets[0] else 1 for node in nodes]
    direct_accuracy = np.mean(np.array(predicted) == np.array(true_labels))
    flipped_accuracy = np.mean((1 - np.array(predicted)) == np.array(true_labels))
    split_accuracy = float(max(direct_accuracy, flipped_accuracy))
    if flipped_accuracy > direct_accuracy:
        predicted = [1 - label for label in predicted]

    degree_values = np.array([degrees[node] for node in nodes], dtype=float)
    hi_degrees = [
        degrees[node] for node in nodes if graph.nodes[node]["club"] == "Mr. Hi"
    ]
    officer_degrees = [
        degrees[node] for node in nodes if graph.nodes[node]["club"] == "Officer"
    ]
    mann_whitney = mannwhitneyu(
        hi_degrees, officer_degrees, alternative="two-sided", method="auto"
    )
    spearman = spearmanr(
        [degrees[node] for node in nodes],
        [betweenness[node] for node in nodes],
    )

    component_sizes = sorted(
        (len(component) for component in nx.connected_components(graph)), reverse=True
    )
    results = {
        "network_type": "Yönsüz, ağırlıksız, basit ağ",
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "density": nx.density(graph),
        "mean_degree": float(degree_values.mean()),
        "median_degree": float(np.median(degree_values)),
        "min_degree": int(degree_values.min()),
        "max_degree": int(degree_values.max()),
        "average_clustering": nx.average_clustering(graph),
        "transitivity": nx.transitivity(graph),
        "components": len(component_sizes),
        "component_sizes": component_sizes,
        "average_shortest_path": nx.average_shortest_path_length(graph),
        "diameter": nx.diameter(graph),
        "degree_assortativity": nx.degree_assortativity_coefficient(graph),
        "girvan_newman_community_sizes": [len(group) for group in detected_sets],
        "girvan_newman_modularity": nx.community.modularity(graph, detected_sets),
        "girvan_newman_accuracy": split_accuracy,
        "girvan_newman_ari": adjusted_rand_score(true_labels, predicted),
        "girvan_newman_nmi": normalized_mutual_info_score(true_labels, predicted),
        "mann_whitney_u": float(mann_whitney.statistic),
        "mann_whitney_p": float(mann_whitney.pvalue),
        "spearman_degree_betweenness_rho": float(spearman.statistic),
        "spearman_degree_betweenness_p": float(spearman.pvalue),
    }

    table = pd.DataFrame(
        {
            "Düğüm": [node + 1 for node in nodes],
            "Gerçek grup": [graph.nodes[node]["club"] for node in nodes],
            "Derece": [degrees[node] for node in nodes],
            "Kümelenme": [clustering[node] for node in nodes],
            "Derece merkeziliği": [degree_centrality[node] for node in nodes],
            "Aradalık merkeziliği": [betweenness[node] for node in nodes],
            "Yakınlık merkeziliği": [closeness[node] for node in nodes],
            "Özvektör merkeziliği": [eigenvector[node] for node in nodes],
            "GN topluluğu": [label + 1 for label in predicted],
        }
    )
    table.to_csv(ASSET_DIR / "node_metrics.csv", index=False, encoding="utf-8-sig")

    top_nodes = (
        table.sort_values("Aradalık merkeziliği", ascending=False)
        .head(8)
        .reset_index(drop=True)
    )
    top_nodes.to_csv(
        ASSET_DIR / "top_nodes.csv", index=False, encoding="utf-8-sig"
    )
    (ASSET_DIR / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    nx.write_graphml(graph, ASSET_DIR / "karate_club.graphml")

    colors = [
        "#2563EB" if graph.nodes[node]["club"] == "Mr. Hi" else "#F97316"
        for node in nodes
    ]
    sizes = [230 + 55 * degrees[node] for node in nodes]
    positions = nx.spring_layout(graph, seed=42, k=0.62)
    plt.figure(figsize=(8.6, 5.7))
    nx.draw_networkx_edges(
        graph, positions, edge_color="#94A3B8", alpha=0.55, width=1.0
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        node_color=colors,
        node_size=sizes,
        edgecolors="white",
        linewidths=1.0,
    )
    nx.draw_networkx_labels(
        graph,
        positions,
        labels={node: str(node + 1) for node in nodes},
        font_size=7.4,
        font_color="white",
        font_weight="bold",
    )
    plt.title("Zachary Karate Kulübü ağı: gerçek ayrışma", fontsize=14, weight="bold")
    plt.text(
        0.01,
        0.01,
        "Mavi: Mr. Hi | Turuncu: Officer | Düğüm boyutu: derece",
        transform=plt.gca().transAxes,
        fontsize=9,
        color="#334155",
    )
    plt.axis("off")
    save_figure(ASSET_DIR / "network.png")

    degree_counts = Counter(degrees.values())
    degree_x = sorted(degree_counts)
    degree_y = [degree_counts[value] for value in degree_x]
    plt.figure(figsize=(7.8, 4.4))
    plt.bar(degree_x, degree_y, color="#2563EB", width=0.72)
    plt.xlabel("Derece (k)")
    plt.ylabel("Düğüm sayısı")
    plt.title("Derece dağılımı", fontsize=14, weight="bold")
    plt.grid(axis="y", alpha=0.22)
    save_figure(ASSET_DIR / "degree_distribution.png")

    plt.figure(figsize=(7.8, 4.4))
    for label, color, name in [
        ("Mr. Hi", "#2563EB", "Mr. Hi"),
        ("Officer", "#F97316", "Officer"),
    ]:
        group_nodes = [
            node for node in nodes if graph.nodes[node]["club"] == label
        ]
        plt.scatter(
            [degrees[node] for node in group_nodes],
            [clustering[node] for node in group_nodes],
            s=64,
            alpha=0.82,
            color=color,
            edgecolor="white",
            linewidth=0.7,
            label=name,
        )
    plt.xlabel("Derece")
    plt.ylabel("Yerel kümelenme katsayısı")
    plt.title("Derece ve yerel kümelenme ilişkisi", fontsize=14, weight="bold")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)
    save_figure(ASSET_DIR / "clustering_degree.png")

    top_betweenness = sorted(
        betweenness.items(), key=lambda item: item[1], reverse=True
    )[:8]
    labels = [str(node + 1) for node, _ in reversed(top_betweenness)]
    values = [value for _, value in reversed(top_betweenness)]
    plt.figure(figsize=(7.8, 4.5))
    plt.barh(labels, values, color="#0F766E")
    plt.xlabel("Normalize aradalık merkeziliği")
    plt.ylabel("Düğüm")
    plt.title("Köprü rolü en güçlü düğümler", fontsize=14, weight="bold")
    plt.grid(axis="x", alpha=0.22)
    save_figure(ASSET_DIR / "betweenness_top.png")

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
