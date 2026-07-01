# apps/core/utils/tree.py
"""
Generic flat-to-tree builder.

Converts any flat list of dicts that have 'id' and 'parent_id' fields
into a nested tree structure.

Works for any self-referencing model:
    - Category  (parent FK to self)
    - Location  (country > state > city)
    - Department (company > division > team)
    - MenuItems (menu > section > item)

Requirements for input dicts:
    - Must have an 'id' field
    - Must have a 'parent_id' field (None for root nodes)
    - All other fields are passed through untouched

Usage:
    flat_data = [
        {"id": 1, "name": "Engine",   "parent_id": None},
        {"id": 2, "name": "Pistons",  "parent_id": 1},
        {"id": 3, "name": "Rings",    "parent_id": 2},
        {"id": 4, "name": "Brakes",   "parent_id": None},
    ]
    tree = build_tree(flat_data)
    # [
    #   {"id": 1, "name": "Engine", "parent_id": None, "children": [
    #       {"id": 2, "name": "Pistons", "parent_id": 1, "children": [
    #           {"id": 3, "name": "Rings", "parent_id": 2, "children": []}
    #       ]}
    #   ]},
    #   {"id": 4, "name": "Brakes", "parent_id": None, "children": []}
    # ]
"""
from __future__ import annotations

from typing import Any


def build_tree(
    flat_items: list[dict[str, Any]],
    *,
    id_field: str = "id",
    parent_field: str = "parent",
) -> list[dict[str, Any]]:
    """
    Converts a flat list of dicts into a nested tree in O(n) time.

    Args:
        flat_items   : list of dicts — typically from serializer.data
        id_field     : name of the primary key field (default: "id")
        parent_field : name of the parent FK field (default: "parent")
                       This matches DRF's default output for FK fields
                       which serializes ForeignKey as the raw ID value.

    Returns:
        List of root node dicts, each with a "children" key containing
        their nested descendants.

    Why O(n):
        Pass 1 — build a lookup dict: id → node copy.        O(n)
        Pass 2 — attach each node to its parent's children.  O(n)
        No nested loops, no recursion, no repeated searching.

    Why copy each item:
        We add a "children" key to each dict.
        Mutating the original serializer output would affect cached data
        (same object in memory).
        dict() makes a shallow copy — safe because we only ADD a key,
        we do not modify existing values.

    Why id_field and parent_field are configurable:
        Different models or serializers may use different field names.
        Default values match Django/DRF conventions so most callers
        need zero configuration.
    """
    if not flat_items:
        return []

    # ── Pass 1: build lookup and attach empty children list ───────────────
    # Why separate pass: every node needs a children list before
    # we start attaching — otherwise a child might arrive before its parent.
    lookup: dict[Any, dict[str, Any]] = {}
    for item in flat_items:
        node = dict(item)        # shallow copy — do not mutate cached data
        node["children"] = []
        lookup[node[id_field]] = node

    # ── Pass 2: wire parents to children, collect roots ───────────────────
    roots: list[dict[str, Any]] = []
    for node in lookup.values():
        parent_id = node.get(parent_field)
        if parent_id is None:
            # No parent → this is a root node
            roots.append(node)
        elif parent_id in lookup:
            # Attach to parent's children list
            lookup[parent_id]["children"].append(node)
        else:
            # Parent ID exists but not in our dataset
            # Why treat as root: parent may be inactive/deleted.
            # Better to show orphan at root than to silently drop it.
            roots.append(node)

    return roots