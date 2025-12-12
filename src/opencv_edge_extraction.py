#!/usr/bin/env python3
"""
OpenCV edge and line extraction for P&ID diagrams.

Purpose:
- Extract edges, lines, and contours from P&ID diagrams using OpenCV.
- Provide structural information (pipes, vessels, connections) to complement OCR text.
- Support multiple edge detection methods: Canny, Hough Lines, Contours.

Output:
- JSON file with detected lines, edges, and geometric features.
- Annotated visualization images showing detected features.

Methods:
1. Canny Edge Detection: Pixel-level edge detection
2. Hough Line Transform: Straight line detection (for pipes)
3. Contour Detection: Closed shapes (for vessels, equipment)
4. Morphological Operations: Clean up and enhance features
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


class PNIDEdgeExtractor:
    """Extract edges, lines, and contours from P&ID diagrams using OpenCV."""

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        hough_threshold: int = 80,
        hough_min_line_length: int = 30,
        hough_max_line_gap: int = 10,
    ):
        """
        Initialize edge extractor with configurable parameters.

        Args:
            canny_low: Lower threshold for Canny edge detection.
            canny_high: Upper threshold for Canny edge detection.
            hough_threshold: Accumulator threshold for Hough line detection.
            hough_min_line_length: Minimum length of detected lines (pixels).
            hough_max_line_gap: Maximum gap between line segments (pixels).
        """
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold
        self.hough_min_line_length = hough_min_line_length
        self.hough_max_line_gap = hough_max_line_gap

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for edge detection.

        Args:
            image: Input image (BGR or grayscale).

        Returns:
            Preprocessed grayscale image.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Optional: Apply adaptive histogram equalization for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)

        return enhanced

    def detect_edges_canny(self, gray: np.ndarray) -> np.ndarray:
        """
        Detect edges using Canny edge detector.

        Args:
            gray: Grayscale image.

        Returns:
            Binary edge map.
        """
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        return edges

    def detect_lines_hough(self, edges: np.ndarray) -> list[dict[str, Any]]:
        """
        Detect straight lines using Hough Line Transform.

        Args:
            edges: Binary edge map from Canny.

        Returns:
            List of line dictionaries with start/end points and properties.
        """
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.hough_min_line_length,
            maxLineGap=self.hough_max_line_gap,
        )

        if lines is None:
            return []

        line_list: list[dict[str, Any]] = []
        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate line properties
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi

            # Classify orientation
            orientation = "horizontal"
            if abs(angle) > 60 and abs(angle) < 120:
                orientation = "vertical"
            elif abs(angle) > 30 and abs(angle) < 60:
                orientation = "diagonal"
            elif abs(angle) > 120 and abs(angle) < 150:
                orientation = "diagonal"

            line_list.append(
                {
                    "start": [int(x1), int(y1)],
                    "end": [int(x2), int(y2)],
                    "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                    "length": float(length),
                    "angle": float(angle),
                    "orientation": orientation,
                }
            )

        return line_list

    def detect_contours(self, edges: np.ndarray) -> list[dict[str, Any]]:
        """
        Detect contours (closed shapes) for vessels and equipment.

        Args:
            edges: Binary edge map.

        Returns:
            List of contour dictionaries with bounding boxes and properties.
        """
        # Apply morphological closing to close gaps in contours
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        contour_list: list[dict[str, Any]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)

            # Filter out very small contours (noise)
            if area < 100:
                continue

            # Get bounding box
            x, y, w, h = cv2.boundingRect(cnt)

            # Calculate shape properties
            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

            # Approximate polygon
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            num_vertices = len(approx)

            # Classify shape
            shape_type = "irregular"
            if num_vertices == 3:
                shape_type = "triangle"
            elif num_vertices == 4:
                # Check if it's a square or rectangle
                aspect_ratio = float(w) / h if h > 0 else 0
                if 0.95 <= aspect_ratio <= 1.05:
                    shape_type = "square"
                else:
                    shape_type = "rectangle"
            elif num_vertices > 8 and circularity > 0.7:
                shape_type = "circle"
            elif num_vertices > 4:
                shape_type = "polygon"

            contour_list.append(
                {
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "center": [int(x + w / 2), int(y + h / 2)],
                    "area": float(area),
                    "perimeter": float(perimeter),
                    "circularity": float(circularity),
                    "vertices": int(num_vertices),
                    "shape_type": shape_type,
                }
            )

        return contour_list

    def trace_pipe_routes(
        self, lines: list[dict[str, Any]], connection_threshold: float = 10.0
    ) -> list[dict[str, Any]]:
        """
        Connect line segments into continuous pipe routes.

        Args:
            lines: List of line segments from detect_lines_hough.
            connection_threshold: Maximum distance to consider segments connected (pixels).

        Returns:
            List of pipe routes, each containing:
            - segments: List of connected line segments
            - total_length: Total length of the route
            - endpoints: [start_point, end_point] of the complete route
            - points: Ordered list of points forming the route
            - orientation: Dominant orientation
        """
        if not lines:
            return []

        # Build adjacency graph
        n = len(lines)
        graph: dict[int, list[int]] = {i: [] for i in range(n)}

        for i in range(n):
            for j in range(i + 1, n):
                # Check if lines are connected at any endpoint
                line_i = lines[i]
                line_j = lines[j]

                # Get endpoints
                i_start = np.array(line_i["start"])
                i_end = np.array(line_i["end"])
                j_start = np.array(line_j["start"])
                j_end = np.array(line_j["end"])

                # Check all endpoint combinations
                connections = [
                    (i_start, j_start),
                    (i_start, j_end),
                    (i_end, j_start),
                    (i_end, j_end),
                ]

                for p1, p2 in connections:
                    dist = np.linalg.norm(p1 - p2)
                    if dist <= connection_threshold:
                        graph[i].append(j)
                        graph[j].append(i)
                        break

        # Trace routes using DFS
        visited = set()
        routes = []

        def dfs_trace(start_idx: int) -> list[int]:
            """Depth-first search to trace connected segments."""
            stack = [start_idx]
            route = []
            local_visited = set()

            while stack:
                idx = stack.pop()
                if idx in local_visited:
                    continue

                local_visited.add(idx)
                route.append(idx)

                # Add unvisited neighbors
                for neighbor in graph[idx]:
                    if neighbor not in local_visited and neighbor not in visited:
                        stack.append(neighbor)

            return route

        for i in range(n):
            if i not in visited:
                route_indices = dfs_trace(i)
                visited.update(route_indices)

                if route_indices:
                    # Build route information
                    route_segments = [lines[idx] for idx in route_indices]
                    total_length = sum(seg["length"] for seg in route_segments)

                    # Collect all unique points
                    points = []
                    for seg in route_segments:
                        points.append(seg["start"])
                        points.append(seg["end"])

                    # Find endpoints (points that appear only once)
                    point_counts: dict[tuple[int, int], int] = {}
                    for pt in points:
                        key = tuple(pt)
                        point_counts[key] = point_counts.get(key, 0) + 1

                    endpoints = [list(pt) for pt, count in point_counts.items() if count == 1]

                    # Determine dominant orientation
                    orientations = [seg["orientation"] for seg in route_segments]
                    dominant = max(set(orientations), key=orientations.count)

                    routes.append(
                        {
                            "segments": route_segments,
                            "segment_count": len(route_segments),
                            "total_length": float(total_length),
                            "endpoints": endpoints[:2] if len(endpoints) >= 2 else endpoints,
                            "num_junctions": len(
                                [pt for pt, count in point_counts.items() if count > 2]
                            ),
                            "dominant_orientation": dominant,
                        }
                    )

        return routes

    def extract_features(self, image_path: Path) -> dict[str, Any]:
        """
        Extract all edge features from a P&ID diagram.

        Args:
            image_path: Path to input image.

        Returns:
            Dictionary containing:
            - lines: List of detected straight lines (pipes)
            - contours: List of detected shapes (vessels, equipment)
            - image_size: Original image dimensions [width, height]
            - statistics: Summary statistics
        """
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        height, width = image.shape[:2]

        # Preprocess
        gray = self.preprocess_image(image)

        # Detect edges
        edges = self.detect_edges_canny(gray)

        # Detect lines (pipes)
        lines = self.detect_lines_hough(edges)

        # Detect contours (vessels, equipment)
        contours = self.detect_contours(edges)

        # Trace pipe routes (connect line segments)
        pipe_routes = self.trace_pipe_routes(lines, connection_threshold=15.0)

        # Calculate statistics
        total_line_length = sum(line["length"] for line in lines)
        horizontal_lines = [l for l in lines if l["orientation"] == "horizontal"]
        vertical_lines = [l for l in lines if l["orientation"] == "vertical"]
        diagonal_lines = [l for l in lines if l["orientation"] == "diagonal"]

        statistics = {
            "total_lines": len(lines),
            "horizontal_lines": len(horizontal_lines),
            "vertical_lines": len(vertical_lines),
            "diagonal_lines": len(diagonal_lines),
            "total_line_length": float(total_line_length),
            "average_line_length": float(total_line_length / len(lines)) if lines else 0.0,
            "total_contours": len(contours),
            "total_contour_area": sum(c["area"] for c in contours),
        }

        return {
            "image_size": [width, height],
            "lines": lines,
            "pipe_routes": pipe_routes,
            "contours": contours,
            "statistics": statistics,
        }

    def create_visualization(
        self,
        image_path: Path,
        features: dict[str, Any],
        output_path: Path,
        show_lines: bool = True,
        show_contours: bool = True,
    ) -> None:
        """
        Create annotated visualization of detected features.

        Args:
            image_path: Path to original image.
            features: Extracted features dictionary.
            output_path: Path to save annotated image.
            show_lines: Whether to draw detected lines.
            show_contours: Whether to draw detected contours.
        """
        # Load original image
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        annotated = image.copy()

        # Draw contours first (background)
        if show_contours:
            for contour in features["contours"]:
                x, y, w, h = contour["bbox"]
                # Draw bounding box in blue
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)
                # Draw center point
                cx, cy = contour["center"]
                cv2.circle(annotated, (cx, cy), 5, (255, 0, 0), -1)
                # Label shape type
                label = contour["shape_type"]
                cv2.putText(
                    annotated,
                    label,
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 0, 0),
                    1,
                )

        # Draw lines on top (foreground)
        if show_lines:
            for line in features["lines"]:
                x1, y1 = line["start"]
                x2, y2 = line["end"]

                # Color code by orientation
                color = (0, 255, 0)  # Green for horizontal
                if line["orientation"] == "vertical":
                    color = (0, 0, 255)  # Red for vertical
                elif line["orientation"] == "diagonal":
                    color = (255, 255, 0)  # Cyan for diagonal

                cv2.line(annotated, (x1, y1), (x2, y2), color, 2)

        # Add statistics overlay
        stats = features["statistics"]
        y_offset = 30
        info_texts = [
            f"Lines: {stats['total_lines']} (H:{stats['horizontal_lines']}, V:{stats['vertical_lines']}, D:{stats['diagonal_lines']})",
            f"Avg Line Length: {stats['average_line_length']:.1f}px",
            f"Contours: {stats['total_contours']}",
        ]

        for i, text in enumerate(info_texts):
            cv2.putText(
                annotated,
                text,
                (10, y_offset + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                3,
            )
            cv2.putText(
                annotated,
                text,
                (10, y_offset + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )

        # Save annotated image
        cv2.imwrite(str(output_path), annotated)
        print(f"✅ Saved annotated visualization to: {output_path}")


def format_features_for_llm(features: dict[str, Any]) -> str:
    """
    Format extracted edge features as text prompt for LLM.

    Args:
        features: Extracted features dictionary.

    Returns:
        Formatted text description of structural features.
    """
    lines = features["lines"]
    contours = features["contours"]
    stats = features["statistics"]

    # Group lines by orientation
    horizontal = [l for l in lines if l["orientation"] == "horizontal"]
    vertical = [l for l in lines if l["orientation"] == "vertical"]

    # Group contours by shape type
    shapes_by_type: dict[str, list[dict[str, Any]]] = {}
    for contour in contours:
        shape_type = contour["shape_type"]
        if shape_type not in shapes_by_type:
            shapes_by_type[shape_type] = []
        shapes_by_type[shape_type].append(contour)

    # Build text description
    text_parts = [
        "=== STRUCTURAL ANALYSIS ===",
        "",
        f"Image Size: {features['image_size'][0]}×{features['image_size'][1]} pixels",
        "",
        "## DETECTED LINES (Pipes/Connections):",
        f"Total: {stats['total_lines']} line segments",
        f"- Horizontal: {len(horizontal)} segments",
        f"- Vertical: {len(vertical)} segments",
        f"- Diagonal: {stats['diagonal_lines']} segments",
        f"Average Segment Length: {stats['average_line_length']:.1f} pixels",
        "",
    ]

    # Add pipe routes information
    pipe_routes = features.get("pipe_routes", [])
    if pipe_routes:
        text_parts.extend(
            [
                "## PIPE ROUTES (Connected Segments):",
                f"Total: {len(pipe_routes)} continuous pipe routes",
                "",
            ]
        )

        # Show major routes (length > 100px)
        major_routes = [r for r in pipe_routes if r["total_length"] > 100]
        if major_routes:
            text_parts.append(f"Major Routes (length > 100px): {len(major_routes)}")
            for i, route in enumerate(major_routes[:5], 1):
                endpoints = route["endpoints"]
                if len(endpoints) >= 2:
                    text_parts.append(
                        f"  Route {i}: {route['segment_count']} segments, "
                        f"{route['total_length']:.0f}px total, "
                        f"{route['dominant_orientation']}, "
                        f"endpoints: {endpoints[0]} → {endpoints[1]}"
                    )
                else:
                    text_parts.append(
                        f"  Route {i}: {route['segment_count']} segments, "
                        f"{route['total_length']:.0f}px total, "
                        f"{route['dominant_orientation']}"
                    )
            if len(major_routes) > 5:
                text_parts.append(f"  ... and {len(major_routes) - 5} more major routes")
            text_parts.append("")

        # Show route statistics
        single_segment = len([r for r in pipe_routes if r["segment_count"] == 1])
        multi_segment = len([r for r in pipe_routes if r["segment_count"] > 1])
        text_parts.extend(
            [
                "Route Statistics:",
                f"  Single-segment routes: {single_segment}",
                f"  Multi-segment routes: {multi_segment}",
                f"  Average segments per route: {sum(r['segment_count'] for r in pipe_routes) / len(pipe_routes):.1f}",
                "",
            ]
        )
    else:
        text_parts.append("")

    # Sample horizontal lines
    if horizontal:
        text_parts.append("Sample Horizontal Lines:")
        for line in horizontal[:5]:
            text_parts.append(
                f"  • [{line['start'][0]},{line['start'][1]}] → [{line['end'][0]},{line['end'][1]}] "
                f"(length: {line['length']:.0f}px)"
            )
        if len(horizontal) > 5:
            text_parts.append(f"  ... and {len(horizontal) - 5} more")
        text_parts.append("")

    # Sample vertical lines
    if vertical:
        text_parts.append("Sample Vertical Lines:")
        for line in vertical[:5]:
            text_parts.append(
                f"  • [{line['start'][0]},{line['start'][1]}] → [{line['end'][0]},{line['end'][1]}] "
                f"(length: {line['length']:.0f}px)"
            )
        if len(vertical) > 5:
            text_parts.append(f"  ... and {len(vertical) - 5} more")
        text_parts.append("")

    # Contour summary
    text_parts.extend(
        [
            "## DETECTED CONTOURS (Vessels/Equipment):",
            f"Total: {stats['total_contours']} shapes",
            "",
        ]
    )

    for shape_type, shape_contours in sorted(shapes_by_type.items()):
        text_parts.append(f"{shape_type.title()}s: {len(shape_contours)}")
        for contour in shape_contours[:3]:
            x, y, w, h = contour["bbox"]
            text_parts.append(
                f"  • Position: ({contour['center'][0]},{contour['center'][1]}), "
                f"Size: {w}×{h}px, Area: {contour['area']:.0f}px²"
            )
        if len(shape_contours) > 3:
            text_parts.append(f"  ... and {len(shape_contours) - 3} more")
        text_parts.append("")

    text_parts.append("=== END STRUCTURAL ANALYSIS ===")

    return "\n".join(text_parts)


def main() -> None:
    """
    CLI entry point:
    - Reads:  data/input/brewery.jpg
    - Writes: data/output/opencv_edges.json
    - Writes: data/output/brewery_edges_annotated.jpg
    """
    base_dir = Path(__file__).resolve().parent.parent
    image_path = base_dir / "data" / "input" / "brewery.jpg"
    output_json = base_dir / "data" / "output" / "opencv_edges.json"
    output_image = base_dir / "data" / "output" / "brewery_edges_annotated.jpg"
    output_text = base_dir / "data" / "output" / "opencv_edges_llm_prompt.txt"

    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    print(f"🔍 Extracting edges from: {image_path}")

    # Create extractor with tuned parameters for P&ID diagrams
    extractor = PNIDEdgeExtractor(
        canny_low=50,
        canny_high=150,
        hough_threshold=60,  # Lower threshold to detect more lines
        hough_min_line_length=20,  # Shorter minimum for small pipe segments
        hough_max_line_gap=15,  # Larger gap to connect dashed lines
    )

    # Extract features
    features = extractor.extract_features(image_path)

    # Save JSON output
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(features, indent=2, ensure_ascii=False))
    print(f"✅ Saved edge data to: {output_json}")
    print(f"   Lines: {features['statistics']['total_lines']}")
    print(f"   Contours: {features['statistics']['total_contours']}")

    # Create visualization
    extractor.create_visualization(image_path, features, output_image)

    # Format for LLM
    llm_text = format_features_for_llm(features)
    output_text.write_text(llm_text, encoding="utf-8")
    print(f"✅ Saved LLM prompt to: {output_text}")
    print(f"\n{llm_text}")


if __name__ == "__main__":
    main()
