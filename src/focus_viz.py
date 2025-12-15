#!/usr/bin/env python3
"""
focus_viz.py

Utility to generate a focused PNID (components + pipes) JSON containing the
neighborhood around specified components (e.g., HWT-1, MAK-1, MAT-1, V-1, WT-1)
and optionally render an interactive visualization.

Usage (from repo root):
    uv run src/focus_viz.py                          # runs with defaults
    uv run src/focus_viz.py --pnid data/output/pnid_merged_fixed.json \
                            --seeds HWT-1 MAK-1 MAT-1 V-1 WT-1 \
                            --hops 2 \
                            --out-json data/output/pnid_focus.json \
                            --out-html data/output/pnid_focus_graph.html

Behavior:
- Loads a PNID JSON (LLM or merged output).
- Builds an adjacency graph from pipes (source/target).
- Performs BFS from seed node ids up to `hops` distance to collect neighborhood.
- Writes focused PNID JSON containing only the selected components and pipes.
- Optionally calls the project visualization function to render the focused HTML.

Notes:
- Component identity uses the `id` field. If missing, `label` is used as fallback.
- Pipes that reference non-component inlets/outlets are preserved if either
  endpoint is within the focused set (they will be included with the same ids).
- This script tries to be conservative: it does not alter the original data,
  only filters and writes a focused view.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

# Try to import the existing visualization function. If unavailable,
# we still produce the focused JSON (rendering is optional).
try:
    # import function from local script
    from plot_pnid_graph import create_interactive_graph  # type: ignore
except Exception:  # pragma: no cover - import may fail in some contexts
    create_interactive_graph = None  # type: ignore


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def component_key(comp: Dict[str, Any]) -> str:
    """Return unique key used to identify a component (prefer 'id', fallback to 'label')."""
    return str(comp.get("id") or comp.get("label"))


def build_adjacency(pipes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    Build adjacency map from pipes (undirected).
    Each pipe is expected to have 'source' and 'target' fields (original ids).
    """
    adj: Dict[str, Set[str]] = {}
    for p in pipes:
        s = p.get("source")
        t = p.get("target")
        if not s or not t:
            continue
        s = str(s)
        t = str(t)
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)
    return adj


def bfs_neighborhood(seeds: Iterable[str], adj: Dict[str, Set[str]], hops: int) -> Set[str]:
    """
    BFS from seeds over adjacency map for up to 'hops' steps.
    Returns set of reachable node ids including seeds.
    """
    visited: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque()

    for s in seeds:
        queue.append((s, 0))
        visited.add(s)

    while queue:
        node, depth = queue.popleft()
        if depth >= hops:
            continue
        for nb in adj.get(node, ()):
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, depth + 1))
    return visited


def filter_pnid_by_components(pnid: Dict[str, Any], component_ids: Set[str]) -> Dict[str, Any]:
    """
    Return a filtered PNID dict that includes only components whose id (or label)
    is in component_ids and only pipes that have both endpoints in the
    resulting component set OR where at least one endpoint is in the set (keeps inlets).
    """
    comps = pnid.get("components", [])
    pipes = pnid.get("pipes", [])

    # Build mapping from component key to full component
    comp_map: Dict[str, Dict[str, Any]] = {}
    for c in comps:
        key = str(c.get("id") or c.get("label"))
        if key in component_ids:
            comp_map[key] = c

    # Determine pipes to include:
    # - If both endpoints are known components and in comp_map -> include
    # - Else if at least one endpoint is in comp_map -> include (keeps inlets/outlets connected)
    included_pipes: List[Dict[str, Any]] = []
    for p in pipes:
        s = str(p.get("source")) if p.get("source") is not None else None
        t = str(p.get("target")) if p.get("target") is not None else None
        include = False
        if s and t:
            if s in comp_map and t in comp_map:
                include = True
            elif s in comp_map or t in comp_map:
                # include as partial connection (keeps inlets/outlets)
                include = True
        if include:
            included_pipes.append(p)

    return {"components": list(comp_map.values()), "pipes": included_pipes}


def compute_focus(
    pnid_path: Path,
    seeds: List[str],
    hops: int,
) -> Dict[str, Any]:
    """
    Compute focused PNID around seed component ids (hops graph distance).
    Returns focused PNID dict.
    """
    pnid = load_json(pnid_path)

    # extract components and pipes depending on format
    if "output" in pnid:
        # earlier agents stored under output
        components = pnid["output"].get("components", [])
        pipes = pnid["output"].get("pipes", [])
    else:
        components = pnid.get("components", [])
        pipes = pnid.get("pipes", [])

    # map component ids (id or label)
    comp_ids = [component_key(c) for c in components]
    # adjacency from pipes (by original 'source' and 'target')
    adj = build_adjacency(pipes)

    # ensure seeds are valid keys; if user provided labels, accept them as-is
    normalized_seeds = [str(s) for s in seeds]

    # BFS to get focused component ids
    neighborhood = bfs_neighborhood(normalized_seeds, adj, hops)

    # Also include any seed that might not be in adjacency but is in components
    neighborhood |= set([s for s in normalized_seeds if s in comp_ids])

    # Build focused PNID
    focused = filter_pnid_by_components({"components": components, "pipes": pipes}, neighborhood)
    return focused


def make_highlighted_visual(
    focused_pnid: Dict[str, Any],
    focus_ids: List[str],
    image_path: Path,
    out_html: Path,
) -> None:
    """
    Write focused PNID JSON and render an HTML visualization with focused nodes highlighted.
    This function uses the existing create_interactive_graph if available; otherwise,
    it writes the focused PNID and prints instructions.
    """
    out_json = out_html.with_suffix(".json")
    save_json(focused_pnid, out_json)
    print(f"Saved focused PNID JSON to: {out_json}")

    if create_interactive_graph is None:
        print(
            "Visualization function not available in this environment. "
            "You can visualize the focused PNID using the project's plotting script:\n"
            f"  uv run src/plot_pnid_graph.py --json {out_json} --image {image_path} --output {out_html}\n"
        )
        return

    # Render interactive graph from the focused PNID
    create_interactive_graph(str(out_json), str(image_path), str(out_html))
    print(f"Rendered focused HTML to: {out_html}")
    print(
        "NOTE: After loading, use the Controls to 'Stabilize' and 'Toggle Physics' to reveal layout."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create focused PNID neighborhood and visualize it"
    )
    parser.add_argument(
        "--pnid",
        type=str,
        default="data/output/pnid_merged_fixed.json",
        help="Path to source PNID JSON (merged/LLM graph).",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        nargs="+",
        default=["HWT-1", "MAK-1", "MAT-1", "V-1", "WT-1"],
        help="Seed component ids (space separated) to focus neighborhood around.",
    )
    parser.add_argument(
        "--hops",
        type=int,
        default=2,
        help="Number of graph hops to include around seeds.",
    )
    parser.add_argument(
        "--image",
        type=str,
        default="data/input/brewery.jpg",
        help="Background image for visualization.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/output/pnid_focus_graph.html",
        help="Output HTML file for focused visualization (also writes JSON alongside).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pnid_path = Path(args.pnid)
    image_path = Path(args.image)
    out_html = Path(args.out)

    print("Loading PNID:", pnid_path)
    print("Seeds:", args.seeds)
    print("Hops:", args.hops)

    focused = compute_focus(pnid_path, args.seeds, args.hops)
    print("Focused components:", len(focused.get("components", [])))
    print("Focused pipes:", len(focused.get("pipes", [])))

    make_highlighted_visual(focused, args.seeds, image_path, out_html)


if __name__ == "__main__":
    main()
