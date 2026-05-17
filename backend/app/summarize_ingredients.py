"""
Import and call sum_leaf_ingredients(tree) with the raw dict from build_tree().

Returns a dict keyed by item_id, sorted by qty descending:
    {
        "iron_ore": { "name": "Iron Ore", "qty": 12.0 },
        "coal":     { "name": "Coal",     "qty": 4.0  },
        ...
    }
"""

from __future__ import annotations
from typing import Any


def sum_leaf_ingredients(node: dict[str, Any]) -> dict[str, dict]:
    """
    Recursively walk a raw build_tree() node and accumulate quantities
    for every leaf (nodes with no inputs). Duplicate ingredients across
    branches are summed together.

    Returns a dict keyed by item_id, sorted by qty descending.
    """
    totals: dict[str, dict] = {}
    _walk(node, totals)

    sorted_totals = dict(
        sorted(totals.items(), key=lambda kv: kv[1]["qty"], reverse=True)
    )
    return sorted_totals


def _walk(node: dict[str, Any], totals: dict[str, dict]) -> None:
    inputs = node.get("inputs") or []

    if not inputs:
        item_id = node.get("item", "unknown")

        name = node.get("name", item_id)
        for output in node.get("outputs", []):
            if output.get("id") == item_id and output.get("name"):
                name = output["name"]
                break

        qty = node.get("qty", 1)
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            qty = 1.0

        if item_id in totals:
            totals[item_id]["qty"] += qty
        else:
            totals[item_id] = {"name": name, "qty": qty}
    else:
        for child in inputs:
            _walk(child, totals)