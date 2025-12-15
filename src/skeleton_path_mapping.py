#!/usr/bin/env python3
"""
Skeleton Path Mapping

Purpose:
- Build a skeleton (thinned) representation of the edge map from the input P&ID image.
- Construct a graph (networkx) from the skeleton where vertices are junctions/endpoints and
  edges are continuous skeleton paths between vertices.
- Snap OCR-detected components (with x,y coordinates) to the nearest skeleton graph vertices.
- Use graph shortest-path search to find deterministic geometric connectivity between components.
- Produce a PNID JSON where pipes are created deterministically from skeleton paths.
- Produce a concise LLM prompt that describes components + deterministic routes for semantic labeling.

Usage (CLI):
    python -m src.skeleton_path_mapping
    # or integrate into the pipeline; defaults use data/input/brewery.jpg and project outputs

Notes:
- This module prefers deterministic geometry over asking an LLM to infer topology.
- The output file (pnid_skeleton_mapped.json) contains components (copied) and pipes generated
  from skeleton paths.
"""

from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import cv2
import networkx as nx
import numpy as np
from skimage.morphology import skeletonize
from skimage.util import invert

# Type aliases
Point = Tuple[int, int]
Component = Dict[str, Any]
OCRItem = Dict[str, Any]


def load_image_gray(image_path: Path) -> np.ndarray:
    """Load image and convert to grayscale uint8 numpy array."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray


def compute_edge_map(gray: np.ndarray, canny_low: int = 50, canny_high: int = 150) -> np.ndarray:
    """Run Canny edge detector and return binary edge map (bool ndarray)."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, canny_low, canny_high)
    # binary boolean array where True = edge pixel
    return edges > 0


def skeletonize_edge_map(edge_bool: np.ndarray) -> np.ndarray:
    """
    Skeletonize edge boolean array.
    skimage.skeletonize expects foreground==True (or 1) as objects; invert if needed.
    """
    # skeletonize works on binary image where foreground is True. Our edges are True => ok.
    # But skeletonize expects 2D boolean, with True as foreground.
    skel = skeletonize(edge_bool.astype(np.uint8) > 0)
    return skel.astype(np.uint8)


def get_neighbor_coords(pt: Point) -> Iterable[Point]:
    """Yield 8-neighbors (x,y) positions for a pixel point."""
    x, y = pt
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            yield (x + dx, y + dy)


def build_skeleton_graph(skel: np.ndarray) -> Tuple[nx.Graph, Dict[Point, int]]:
    """
    Convert skeleton image to graph.

    Nodes are skeleton pixels with degree != 2 (endpoints or junctions). Edges are paths
    connecting nodes via sequences of degree==2 pixels. Each graph node has attribute 'pos' = (x,y).
    Returns (graph, mapping_point_to_node_id).
    """
    h, w = skel.shape
    # Find all skeleton pixel coordinates
    ys, xs = np.nonzero(skel)
    points = set(zip(xs.tolist(), ys.tolist()))

    # Build quick neighbor degree map
    degrees: Dict[Point, int] = {}
    for pt in points:
        cnt = 0
        for nb in get_neighbor_coords(pt):
            if nb in points:
                cnt += 1
        degrees[pt] = cnt

    # Identify nodes: degree != 2 (endpoints/branch/junction) OR isolated small segments
    node_points = {pt for pt, deg in degrees.items() if deg != 2}
    # If the entire skeleton is a single straight line, endpoints will be nodes; OK.

    # Create graph
    G = nx.Graph()
    point_to_node: Dict[Point, int] = {}

    # Add node points to graph with unique ids
    for idx, pt in enumerate(sorted(node_points)):
        G.add_node(idx, pos=pt)
        point_to_node[pt] = idx

    # Now trace edges: for every node point, explore each neighbor that is a skeleton pixel and
    # walk until we hit another node point, recording the path.
    def walk_path(start: Point, neighbor: Point) -> Tuple[int, List[Point]]:
        """
        Walk from start -> neighbor along skeleton until another node is reached.
        Return (node_idx_of_other, path_points_including_other_node) or (-1, []) if none.
        """
        path = [start, neighbor]
        prev = start
        curr = neighbor
        # Safety limit
        max_steps = skel.size
        steps = 0
        while steps < max_steps:
            steps += 1
            if curr in node_points and curr != start:
                return point_to_node[curr], path
            # find next neighbor (excluding prev)
            next_found = None
            for nb in get_neighbor_coords(curr):
                if nb == prev:
                    continue
                if nb in points:
                    next_found = nb
                    break
            if next_found is None:
                # dead end
                return -1, []
            prev, curr = curr, next_found
            path.append(curr)
        return -1, []

    # For each node point, try each neighbor skeleton pixel to form an edge if path ends at other node
    for pt in sorted(node_points):
        for nb in get_neighbor_coords(pt):
            if nb in points:
                # Avoid duplicate edges by only adding if node id < other node id
                other_node_idx, path = walk_path(pt, nb)
                if other_node_idx != -1:
                    u = point_to_node[pt]
                    v = other_node_idx
                    if u == v:
                        continue
                    if G.has_edge(u, v):
                        continue
                    # compute length as number of pixels (or Euclidean length)
                    length = 0.0
                    for i in range(len(path) - 1):
                        x1, y1 = path[i]
                        x2, y2 = path[i + 1]
                        length += math.hypot(x2 - x1, y2 - y1)
                    # store path as list of points
                    G.add_edge(u, v, length=float(length), pixels=path)
    return G, point_to_node


def snap_components_to_nodes(
    components: List[Component], G: nx.Graph, max_snap: float = 80.0
) -> Dict[str, int]:
    """
    For each component (with x,y), snap to nearest skeleton graph node (by Euclidean distance).
    Returns mapping: component_id -> node_id. If no node within max_snap, mapping is omitted.
    """
    mapping: Dict[str, int] = {}
    node_positions = {n: tuple(G.nodes[n]["pos"]) for n in G.nodes}
    node_items = list(node_positions.items())
    for comp in components:
        comp_id = comp.get("id") or comp.get("label")
        if comp_id is None:
            continue
        cx = float(comp.get("x", 0.0))
        cy = float(comp.get("y", 0.0))
        best = None
        best_dist = float("inf")
        for nid, pos in node_items:
            nxp, nyp = pos
            d = math.hypot(nxp - cx, nyp - cy)
            if d < best_dist:
                best_dist = d
                best = nid
        if best is not None and best_dist <= max_snap:
            mapping[comp_id] = best
        # else: leave unmapped; the component may be off-skeleton (text label away from shape)
    return mapping


def find_all_component_paths(
    G: nx.Graph,
    comp_map: Dict[str, int],
    max_path_length: float = 5000.0,
) -> List[Dict[str, Any]]:
    """
    For each unique pair of mapped components, compute shortest path on skeleton graph if exists
    and path length <= max_path_length. Create list of pipe dicts with geometry metadata.
    """
    pipes: List[Dict[str, Any]] = []
    comp_items = list(comp_map.items())
    # Avoid duplicates: only i<j
    for i in range(len(comp_items)):
        id_i, node_i = comp_items[i]
        for j in range(i + 1, len(comp_items)):
            id_j, node_j = comp_items[j]
            try:
                path_nodes = nx.shortest_path(G, source=node_i, target=node_j, weight="length")
                # compute total length
                total_length = 0.0
                path_pixels: List[Point] = []
                for k in range(len(path_nodes) - 1):
                    u = path_nodes[k]
                    v = path_nodes[k + 1]
                    edge_data = G.get_edge_data(u, v)
                    total_length += float(edge_data.get("length", 0.0))
                    # append pixel chain (exclude duplicated node pixels between segments)
                    seg_pixels = edge_data.get("pixels", [])
                    if seg_pixels:
                        if path_pixels and path_pixels[-1] == seg_pixels[0]:
                            path_pixels.extend(seg_pixels[1:])
                        else:
                            path_pixels.extend(seg_pixels)
                if total_length <= max_path_length and total_length > 5.0:
                    # midpoint for label placement
                    mid_idx = len(path_pixels) // 2 if path_pixels else 0
                    mx, my = path_pixels[mid_idx] if path_pixels else (0, 0)
                    pipes.append(
                        {
                            "label": "",  # to be filled from OCR proximity or LLM
                            "source": id_i,
                            "target": id_j,
                            "description": f"Geometric path via skeleton, length {total_length:.1f}px",
                            "x": float(mx),
                            "y": float(my),
                            "path_length": float(total_length),
                            "path_pixels": path_pixels,
                        }
                    )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
    return pipes


def associate_labels_to_pipes(
    pipes: List[Dict[str, Any]], ocr_items: List[OCRItem], proximity: float = 40.0
) -> None:
    """
    For each pipe, look for OCR items near the pipe midpoint and attach probable label/description.
    Mutates pipes in place.
    """
    for pipe in pipes:
        px = pipe.get("x", 0.0)
        py = pipe.get("y", 0.0)
        candidates: List[Tuple[float, OCRItem]] = []
        for item in ocr_items:
            bbox = item.get("bbox")
            if not bbox:
                continue
            cx = sum(p[0] for p in bbox) / 4.0
            cy = sum(p[1] for p in bbox) / 4.0
            d = math.hypot(cx - px, cy - py)
            if d <= proximity:
                candidates.append((d, item))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            top_texts = [c[1]["text"] for c in candidates[:2]]
            pipe["label"] = " / ".join(top_texts)
            pipe["description"] = (
                pipe.get("description", "") + " | OCR labels: " + ", ".join(top_texts)
            )


def generate_pnid_from_skeleton(
    image_path: Path,
    components: List[Component],
    ocr_items: List[OCRItem],
    canny_low: int = 50,
    canny_high: int = 150,
    snap_threshold: float = 80.0,
    max_path_length: float = 6000.0,
) -> Dict[str, Any]:
    """
    High-level function that runs the full skeleton mapping pipeline.
    Returns PNID dict with components and deterministically discovered pipes.
    """
    gray = load_image_gray(image_path)
    edge_bool = compute_edge_map(gray, canny_low=canny_low, canny_high=canny_high)
    skel = skeletonize_edge_map(edge_bool)

    G, point_to_node = build_skeleton_graph(skel)
    comp_map = snap_components_to_nodes(components, G, max_snap=snap_threshold)

    pipes = find_all_component_paths(G, comp_map, max_path_length=max_path_length)
    # associate OCR labels
    associate_labels_to_pipes(pipes, ocr_items, proximity=40.0)

    pnid_out = {
        "components": components,
        "pipes": pipes,
        "metadata": {"method": "skeleton-mapping"},
    }
    return pnid_out


def format_prompt_for_llm(pnid: Dict[str, Any], top_n_routes: int = 10) -> str:
    """
    Create a concise prompt for an LLM that lists components and deterministic routes,
    asks the LLM to label/annotate pipes and validate stream properties.
    """
    comps = pnid.get("components", [])
    pipes = pnid.get("pipes", [])

    lines: List[str] = []
    lines.append("You are given a P&ID diagram analysis with deterministic geometric connectivity.")
    lines.append(
        "Do NOT change topology. Your task is to assign labels and descriptions to the listed pipes."
    )
    lines.append("")
    lines.append("COMPONENTS (id, label, x, y):")
    for c in comps:
        cid = c.get("id") or c.get("label")
        lines.append(f'- {cid}: "{c.get("label", "")}" at ({c.get("x", 0)},{c.get("y", 0)})')
    lines.append("")
    lines.append("DETERMINISTIC PIPES (source → target, length px, suggested label if any):")
    for i, p in enumerate(sorted(pipes, key=lambda x: -x.get("path_length", 0))[:top_n_routes], 1):
        lines.append(
            f"{i}. {p.get('source')} → {p.get('target')}, length={int(p.get('path_length', 0))} px, "
            f'midpoint=({int(p.get("x", 0))},{int(p.get("y", 0))}), label="{p.get("label", "")}"'
        )
    lines.append("")
    lines.append("INSTRUCTIONS:")
    lines.append("1) For each deterministic pipe above, propose a concise label (<= 6 words).")
    lines.append(
        "2) If OCR labels exist near a pipe, prefer them. Otherwise suggest a label from likely stream."
    )
    lines.append(
        "3) Provide a one-line description for each pipe with probable temperature/contents if available."
    )
    lines.append("4) Do NOT invent new pipes or remove the listed ones; only annotate.")
    lines.append("")
    lines.append(
        'Answer with a JSON array of objects: [{"source":"...","target":"...","label":"...","description":"..."}, ...]'
    )
    return "\n".join(lines)


def main() -> None:
    """
    CLI helper to run skeleton mapping end-to-end using project paths.

    Files used (defaults):
      - image: data/input/brewery.jpg
      - components: data/output/pnid_three_step.json (components)
      - ocr items: data/output/three_step_ocr.json
    Outputs:
      - data/output/pnid_skeleton_mapped.json
      - data/output/pnid_skeleton_prompt.txt
    """
    base = Path(__file__).resolve().parent.parent
    image_path = base / "data" / "input" / "brewery.jpg"
    comps_path = base / "data" / "output" / "pnid_three_step.json"
    ocr_path = base / "data" / "output" / "three_step_ocr.json"
    out_path = base / "data" / "output" / "pnid_skeleton_mapped.json"
    prompt_path = base / "data" / "output" / "pnid_skeleton_prompt.txt"

    # Load components and OCR
    if not comps_path.exists():
        raise FileNotFoundError(f"Components JSON not found: {comps_path}")
    with comps_path.open() as f:
        comps_json = json.load(f)
    components = comps_json.get("components", [])

    ocr_items: List[OCRItem] = []
    if ocr_path.exists():
        with ocr_path.open() as f:
            ocr_items = json.load(f)

    print("Running skeleton-based mapping...")
    pnid_out = generate_pnid_from_skeleton(
        image_path=image_path,
        components=components,
        ocr_items=ocr_items,
        canny_low=50,
        canny_high=150,
        snap_threshold=80.0,
        max_path_length=8000.0,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(pnid_out, f, indent=2, ensure_ascii=False)

    prompt_text = format_prompt_for_llm(pnid_out, top_n_routes=20)
    with prompt_path.open("w") as f:
        f.write(prompt_text)

    print(f"Saved skeleton-mapped PNID to: {out_path}")
    print(f"Saved LLM prompt to: {prompt_path}")


if __name__ == "__main__":
    main()
