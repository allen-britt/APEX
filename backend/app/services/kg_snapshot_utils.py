from __future__ import annotations

import json
from typing import Any, Dict


def summarize_kg_snapshot(snapshot: Dict[str, Any] | None, *, max_examples: int = 5) -> str:
    """Return a human-readable summary of the KG snapshot for prompt conditioning."""

    if not isinstance(snapshot, dict) or not snapshot:
        return "No KG snapshot available."

    summary_parts: list[str] = []

    nodes = snapshot.get("nodes")
    if isinstance(nodes, list):
        summary_parts.append(f"Nodes: {len(nodes)} total")
        labels = [
            str(node.get("label") or node.get("name"))
            for node in nodes
            if isinstance(node, dict) and (node.get("label") or node.get("name"))
        ]
        if labels:
            summary_parts.append(
                "Key nodes: " + ", ".join(labels[:max_examples])
            )
    elif isinstance(snapshot.get("node_count"), int):
        summary_parts.append(f"Nodes: {snapshot['node_count']}")

    edges = snapshot.get("edges") or snapshot.get("relationships")
    if isinstance(edges, list):
        summary_parts.append(f"Edges: {len(edges)} total")
        edge_labels = [
            str(edge.get("type"))
            for edge in edges
            if isinstance(edge, dict) and edge.get("type")
        ]
        if edge_labels:
            summary_parts.append(
                "Relationship types: " + ", ".join(sorted(set(edge_labels[:max_examples])))
            )
    elif isinstance(snapshot.get("edge_count"), int):
        summary_parts.append(f"Edges: {snapshot['edge_count']}")

    updated = snapshot.get("updated_at") or snapshot.get("refreshed_at")
    if updated:
        summary_parts.append(f"Snapshot updated at {updated}")

    if summary_parts:
        return " | ".join(summary_parts)

    # Fallback to compact JSON if structure is unknown
    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))


def summarize_kg_metrics(metrics: Dict[str, Any] | None) -> str:
    """Return a compact string describing KG node/edge counts for prompts."""

    if not isinstance(metrics, dict) or not metrics:
        return "Knowledge graph has not been initialized yet."

    nodes = metrics.get("node_count")
    if nodes is None:
        nodes = metrics.get("nodes")
    edges = metrics.get("edge_count")
    if edges is None:
        edges = metrics.get("edges")

    parts: list[str] = []
    if isinstance(nodes, int):
        parts.append(f"Nodes: {nodes}")
    if isinstance(edges, int):
        parts.append(f"Edges: {edges}")

    top_labels = metrics.get("top_labels")
    if isinstance(top_labels, list) and top_labels:
        labels = [str(item.get("label")) for item in top_labels if isinstance(item, dict) and item.get("label")]
        if labels:
            parts.append("Top labels: " + ", ".join(labels[:4]))

    if not parts:
        return "Knowledge graph metrics are currently unavailable."

    return " | ".join(parts)
