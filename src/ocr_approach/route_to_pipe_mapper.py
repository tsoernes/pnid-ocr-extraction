#!/usr/bin/env python3
"""
Route-to-Pipe Mapper: Convert detected pipe routes directly into PNID pipes.

Purpose:
- Ensure all detected OpenCV pipe routes are represented in the final graph
- Use OCR text to label routes with stream names and properties
- Use route endpoints to determine component connections
- Minimize information loss between edge detection and final graph

Approach:
1. For each detected pipe route, create a corresponding pipe in the PNID
2. Use spatial proximity to associate OCR text labels with routes
3. Use endpoint proximity to determine source/target component connections
4. Let LLM enhance/refine labels and descriptions, not rebuild from scratch
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


class RouteMapper:
    """Map detected pipe routes to PNID pipes with OCR-based labeling."""

    def __init__(self, proximity_threshold: float = 50.0):
        """
        Initialize route mapper.

        Args:
            proximity_threshold: Maximum distance (pixels) to associate text with route.
        """
        self.proximity_threshold = proximity_threshold

    def distance_point_to_route(self, point: tuple[float, float], route: dict[str, Any]) -> float:
        """
        Calculate minimum distance from a point to any segment in a route.

        Args:
            point: (x, y) coordinates.
            route: Route dictionary with segments.

        Returns:
            Minimum distance to route in pixels.
        """
        min_dist = float("inf")
        px, py = point

        for segment in route["segments"]:
            x1, y1 = segment["start"]
            x2, y2 = segment["end"]

            # Distance to line segment
            # Vector from start to end
            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx * dx + dy * dy

            if length_sq == 0:
                # Degenerate segment (point)
                dist = np.sqrt((px - x1) ** 2 + (py - y1) ** 2)
            else:
                # Projection of point onto line
                t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                dist = np.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

            min_dist = min(min_dist, dist)

        return min_dist

    def find_nearest_ocr_labels(
        self, route: dict[str, Any], ocr_items: list[dict[str, Any]], max_labels: int = 3
    ) -> list[dict[str, Any]]:
        """
        Find OCR labels near a pipe route.

        Args:
            route: Route dictionary.
            ocr_items: List of OCR items with text and bbox.
            max_labels: Maximum number of labels to return.

        Returns:
            List of nearest OCR items sorted by distance.
        """
        labels_with_distance = []

        for item in ocr_items:
            # Calculate OCR text center
            bbox = item["bbox"]
            center_x = sum(p[0] for p in bbox) / 4
            center_y = sum(p[1] for p in bbox) / 4

            # Distance to route
            dist = self.distance_point_to_route((center_x, center_y), route)

            if dist <= self.proximity_threshold:
                labels_with_distance.append(
                    {"item": item, "distance": dist, "center": (center_x, center_y)}
                )

        # Sort by distance and return top N
        labels_with_distance.sort(key=lambda x: x["distance"])
        return labels_with_distance[:max_labels]

    def find_nearest_component(
        self, point: tuple[float, float], components: list[dict[str, Any]]
    ) -> tuple[str | None, float]:
        """
        Find the nearest component to a point.

        Args:
            point: (x, y) coordinates.
            components: List of component dictionaries with x, y coordinates.

        Returns:
            Tuple of (component_id, distance) or (None, inf) if none found.
        """
        min_dist = float("inf")
        nearest_id = None

        px, py = point

        for comp in components:
            cx = comp.get("x", 0)
            cy = comp.get("y", 0)
            dist = np.sqrt((px - cx) ** 2 + (py - cy) ** 2)

            if dist < min_dist:
                min_dist = dist
                nearest_id = comp.get("id", comp.get("label", "unknown"))

        return nearest_id, min_dist

    def create_pipe_from_route(
        self,
        route_idx: int,
        route: dict[str, Any],
        ocr_items: list[dict[str, Any]],
        components: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create a PNID pipe from a detected route.

        Args:
            route_idx: Index of the route.
            route: Route dictionary.
            ocr_items: OCR text items for labeling.
            components: List of components for endpoint connections.

        Returns:
            Pipe dictionary with label, source, target, description, x, y.
        """
        # Find nearest OCR labels
        nearby_labels = self.find_nearest_ocr_labels(route, ocr_items)

        # Build label and description from nearby text
        label_parts = []
        description_parts = []

        for label_info in nearby_labels:
            text = label_info["item"]["text"]
            conf = label_info["item"]["confidence"]

            if conf > 0.7:
                label_parts.append(text)
            description_parts.append(f"{text} (dist: {label_info['distance']:.0f}px)")

        # Construct label
        if label_parts:
            label = " ".join(label_parts[:2])  # Max 2 words for label
        else:
            label = f"Route-{route_idx + 1}"

        # Construct description
        if description_parts:
            description = f"{route['dominant_orientation']} pipe route with labels: " + ", ".join(
                description_parts
            )
        else:
            description = (
                f"{route['dominant_orientation']} pipe route, "
                f"{route['segment_count']} segments, "
                f"{route['total_length']:.0f}px length"
            )

        # Find source/target from endpoints
        endpoints = route.get("endpoints", [])
        source = "inlet"
        target = "outlet"

        if len(endpoints) >= 2:
            start_point = tuple(endpoints[0])
            end_point = tuple(endpoints[1])

            # Find nearest components to endpoints
            source_id, source_dist = self.find_nearest_component(start_point, components)
            target_id, target_dist = self.find_nearest_component(end_point, components)

            # Use component if within reasonable distance (100px)
            if source_dist < 100 and source_id:
                source = source_id
            if target_dist < 100 and target_id:
                target = target_id

        # Calculate midpoint for x,y position
        if route["segments"]:
            # Use midpoint of route (center of bounding box of all points)
            all_x = []
            all_y = []
            for seg in route["segments"]:
                all_x.extend([seg["start"][0], seg["end"][0]])
                all_y.extend([seg["start"][1], seg["end"][1]])

            x = sum(all_x) / len(all_x)
            y = sum(all_y) / len(all_y)
        else:
            x, y = 0.0, 0.0

        return {
            "label": label,
            "source": source,
            "target": target,
            "description": description,
            "x": float(x),
            "y": float(y),
            "route_index": route_idx,
            "route_length": route["total_length"],
            "route_segments": route["segment_count"],
        }

    def map_routes_to_pipes(
        self,
        routes: list[dict[str, Any]],
        ocr_items: list[dict[str, Any]],
        components: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Map all detected routes to PNID pipes.

        Args:
            routes: List of detected pipe routes.
            ocr_items: OCR text items for labeling.
            components: List of components for connections.

        Returns:
            List of pipe dictionaries.
        """
        pipes = []

        for idx, route in enumerate(routes):
            pipe = self.create_pipe_from_route(idx, route, ocr_items, components)
            pipes.append(pipe)

        return pipes


def main() -> None:
    """
    CLI entry point: Generate pipes from routes.

    Reads:
    - data/output/opencv_edges.json (routes)
    - data/output/three_step_ocr.json (OCR labels)
    - data/output/pnid_three_step.json (components)

    Writes:
    - data/output/pnid_route_based.json (PNID with route-based pipes)
    """
    base_dir = Path(__file__).resolve().parent.parent

    # Load data
    edges_path = base_dir / "data" / "output" / "opencv_edges.json"
    ocr_path = base_dir / "data" / "output" / "three_step_ocr.json"
    pnid_path = base_dir / "data" / "output" / "pnid_three_step.json"
    output_path = base_dir / "data" / "output" / "pnid_route_based.json"

    print("📂 Loading data...")
    with open(edges_path) as f:
        edges_data = json.load(f)
    with open(ocr_path) as f:
        ocr_items = json.load(f)
    with open(pnid_path) as f:
        pnid_data = json.load(f)

    routes = edges_data.get("pipe_routes", [])
    components = pnid_data.get("components", [])

    print(f"   Detected routes: {len(routes)}")
    print(f"   OCR items: {len(ocr_items)}")
    print(f"   Components: {len(components)}")

    # Map routes to pipes
    print("\n🔗 Mapping routes to pipes...")
    mapper = RouteMapper(proximity_threshold=50.0)
    pipes = mapper.map_routes_to_pipes(routes, ocr_items, components)

    print(f"   Created {len(pipes)} pipes from {len(routes)} routes")

    # Create output PNID
    output_pnid = {
        "components": components,
        "pipes": pipes,
        "metadata": {
            "source": "route_to_pipe_mapper",
            "routes_detected": len(routes),
            "pipes_created": len(pipes),
            "ocr_items_used": len(ocr_items),
        },
    }

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_pnid, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved route-based PNID to: {output_path}")
    print("\nPipe Summary:")
    print(f"  Total pipes: {len(pipes)}")

    # Show sample pipes
    print("\nSample Pipes:")
    for i, pipe in enumerate(pipes[:5], 1):
        print(f"  {i}. {pipe['label']}: {pipe['source']} → {pipe['target']}")
        print(f"     Length: {pipe['route_length']:.0f}px, Segments: {pipe['route_segments']}")

    if len(pipes) > 5:
        print(f"  ... and {len(pipes) - 5} more pipes")

    print(f"\n🎨 Next: Visualize with:")
    print(f"   uv run src/plot_pnid_graph.py --json {output_path}")


if __name__ == "__main__":
    main()
