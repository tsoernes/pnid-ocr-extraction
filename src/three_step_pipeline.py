#!/usr/bin/env python3
"""
Three-step P&ID extraction pipeline: OCR + Edge Detection + LLM.

Purpose:
- Step 1: Extract text and positions using EasyOCR
- Step 2: Extract structural features (lines, contours) using OpenCV
- Step 3: Combine OCR + edge data and send to LLM for graph extraction

This provides the LLM with both textual labels AND geometric structure,
enabling more accurate identification of pipes, vessels, and connections.

Output:
- data/output/pnid_three_step.json (final graph structure)
- data/output/three_step_ocr.json (OCR results)
- data/output/three_step_edges.json (edge detection results)
- data/output/three_step_combined_viz.jpg (visualization)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai.messages import BinaryContent

from easyocr_extract import run_easyocr
from opencv_edge_extraction import PNIDEdgeExtractor, format_features_for_llm
from pnid_agent import PNID, Component, Pipe, Provider, create_agent


class ThreeStepPipeline:
    """Integrated pipeline combining OCR, edge detection, and LLM."""

    def __init__(
        self,
        provider: str = "azure-anthropic",
        model: str = "claude-opus-4-5",
    ):
        """
        Initialize pipeline.

        Args:
            provider: LLM provider ("google", "azure-anthropic", "azure-openai")
            model: Model name
        """
        self.provider = provider
        self.model = model

    def step1_ocr(self, image_path: Path) -> list[dict[str, Any]]:
        """
        Step 1: Extract text and bounding boxes using EasyOCR.

        Args:
            image_path: Path to input image.

        Returns:
            List of OCR items with text, confidence, and bbox.
        """
        print("\n📝 Step 1: Running EasyOCR...")
        items = run_easyocr(image_path, languages=["en"])
        print(f"   Found {len(items)} text items")
        return items

    def step2_edges(self, image_path: Path) -> dict[str, Any]:
        """
        Step 2: Extract edges, lines, and contours using OpenCV.

        Args:
            image_path: Path to input image.

        Returns:
            Dictionary with lines, contours, and statistics.
        """
        print("\n🔍 Step 2: Running OpenCV edge detection...")
        extractor = PNIDEdgeExtractor(
            canny_low=50,
            canny_high=150,
            hough_threshold=60,
            hough_min_line_length=20,
            hough_max_line_gap=15,
        )
        features = extractor.extract_features(image_path)
        print(f"   Found {features['statistics']['total_lines']} lines")
        print(f"   Found {features['statistics']['total_contours']} contours")
        return features

    def format_combined_prompt(
        self,
        ocr_items: list[dict[str, Any]],
        edge_features: dict[str, Any],
    ) -> str:
        """
        Format combined OCR + edge data as prompt for LLM.

        Args:
            ocr_items: OCR results from EasyOCR.
            edge_features: Edge detection results from OpenCV.

        Returns:
            Formatted text prompt.
        """
        lines = []
        lines.append("# P&ID DIAGRAM ANALYSIS")
        lines.append("")
        lines.append("You are analyzing a Process & Instrumentation Diagram (P&ID).")
        lines.append("I have extracted both TEXT LABELS and STRUCTURAL FEATURES from the diagram.")
        lines.append("")
        lines.append("## EXTRACTED TEXT (from OCR):")
        lines.append("")
        lines.append(f"Total text items: {len(ocr_items)}")
        lines.append("")

        # Group OCR items by confidence
        high_conf = [item for item in ocr_items if item["confidence"] > 0.8]
        med_conf = [item for item in ocr_items if 0.5 < item["confidence"] <= 0.8]
        low_conf = [item for item in ocr_items if item["confidence"] <= 0.5]

        if high_conf:
            lines.append("High Confidence (>80%):")
            for item in high_conf:
                bbox = item["bbox"]
                center_x = int(sum(p[0] for p in bbox) / 4)
                center_y = int(sum(p[1] for p in bbox) / 4)
                lines.append(
                    f"  • '{item['text']}' at position ({center_x}, {center_y}) "
                    f"[confidence: {item['confidence']:.2f}]"
                )
            lines.append("")

        if med_conf:
            lines.append("Medium Confidence (50-80%):")
            for item in med_conf:
                bbox = item["bbox"]
                center_x = int(sum(p[0] for p in bbox) / 4)
                center_y = int(sum(p[1] for p in bbox) / 4)
                lines.append(
                    f"  • '{item['text']}' at position ({center_x}, {center_y}) "
                    f"[confidence: {item['confidence']:.2f}]"
                )
            lines.append("")

        # Add structural analysis
        lines.append("")
        edge_text = format_features_for_llm(edge_features)
        lines.append(edge_text)
        lines.append("")

        # Instructions for LLM
        lines.append("")
        lines.append("## YOUR TASK:")
        lines.append("")
        lines.append("Using the OCR text labels AND structural line/contour information:")
        lines.append("")
        lines.append("1. Identify COMPONENTS (vessels, heat exchangers, pumps, valves, etc.):")
        lines.append("   - Use text labels to name components (e.g., 'MAK', 'MAT', 'WOK')")
        lines.append("   - Use contour positions and sizes to locate components")
        lines.append("   - Set x,y coordinates based on OCR bbox or contour center")
        lines.append("")
        lines.append("2. Identify PIPES (process streams connecting components):")
        lines.append("   - Use detected lines to trace pipe routes")
        lines.append("   - Use text labels near lines for stream names/properties")
        lines.append("   - Set x,y coordinates at pipe midpoint or label position")
        lines.append("   - Connect pipes between components using source/target IDs")
        lines.append("")
        lines.append("3. CORRELATE text with geometry:")
        lines.append("   - Text near a contour likely labels that component")
        lines.append("   - Text near a line likely describes that pipe/stream")
        lines.append("   - Use spatial proximity to associate labels with features")
        lines.append("")
        lines.append("Extract a complete PNID graph with all components and pipes.")
        lines.append("Include accurate x,y coordinates for visualization alignment.")

        return "\n".join(lines)

    def step3_llm(
        self,
        image_path: Path,
        ocr_items: list[dict[str, Any]],
        edge_features: dict[str, Any],
    ) -> PNID:
        """
        Step 3: Send combined data to LLM for graph extraction.

        Args:
            image_path: Path to original image.
            ocr_items: OCR results.
            edge_features: Edge detection results.

        Returns:
            Extracted PNID graph.
        """
        print(f"\n🤖 Step 3: Running LLM extraction ({self.provider})...")

        # Create combined prompt
        prompt_text = self.format_combined_prompt(ocr_items, edge_features)

        # Create agent
        # Convert string provider to enum
        if isinstance(self.provider, str):
            provider_enum = Provider(self.provider)
        else:
            provider_enum = self.provider
        agent = create_agent(provider=provider_enum, model_name=self.model)

        # Read image and create BinaryContent
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Determine media type from file extension
        ext = image_path.suffix.lower()
        media_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_type_map.get(ext, "image/jpeg")
        binary_content = BinaryContent(data=image_data, media_type=media_type)

        # Run agent with prompt text and image
        result = agent.run_sync([prompt_text, binary_content])

        pnid = result.output
        print(f"   Extracted {len(pnid.components)} components")
        print(f"   Extracted {len(pnid.pipes)} pipes")

        return pnid

    def create_combined_visualization(
        self,
        image_path: Path,
        ocr_items: list[dict[str, Any]],
        edge_features: dict[str, Any],
        output_path: Path,
    ) -> None:
        """
        Create visualization showing OCR + edges together.

        Args:
            image_path: Path to original image.
            ocr_items: OCR results.
            edge_features: Edge detection results.
            output_path: Path to save visualization.
        """
        print("\n🎨 Creating combined visualization...")

        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        annotated = image.copy()

        # Draw edges (lines in green, contours in blue)
        for line in edge_features["lines"]:
            x1, y1 = line["start"]
            x2, y2 = line["end"]
            cv2.line(annotated, (x1, y1), (x2, y2), (0, 255, 0), 1)

        for contour in edge_features["contours"]:
            x, y, w, h = contour["bbox"]
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 1)

        # Draw OCR bounding boxes and text (in red)
        for item in ocr_items:
            bbox = item["bbox"]
            pts = np.array(bbox, dtype=np.int32)
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 0, 255), thickness=2)

            # Draw text label
            center_x = int(sum(p[0] for p in bbox) / 4)
            center_y = int(sum(p[1] for p in bbox) / 4)
            cv2.putText(
                annotated,
                item["text"],
                (center_x, center_y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1,
            )

        # Add legend
        legend_y = 30
        cv2.putText(
            annotated,
            "Red: OCR Text | Green: Lines | Blue: Contours",
            (10, legend_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )

        cv2.imwrite(str(output_path), annotated)
        print(f"✅ Saved combined visualization to: {output_path}")

    def run(self, image_path: Path, output_dir: Path) -> dict[str, Any]:
        """
        Run complete three-step pipeline.

        Args:
            image_path: Path to input P&ID image.
            output_dir: Directory for output files.

        Returns:
            Dictionary with all results and output paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: OCR
        ocr_items = self.step1_ocr(image_path)
        ocr_output = output_dir / "three_step_ocr.json"
        ocr_output.write_text(json.dumps(ocr_items, indent=2, ensure_ascii=False))
        print(f"✅ Saved OCR results to: {ocr_output}")

        # Step 2: Edge Detection
        edge_features = self.step2_edges(image_path)
        edge_output = output_dir / "three_step_edges.json"
        edge_output.write_text(json.dumps(edge_features, indent=2, ensure_ascii=False))
        print(f"✅ Saved edge features to: {edge_output}")

        # Create combined visualization
        viz_output = output_dir / "three_step_combined_viz.jpg"
        self.create_combined_visualization(image_path, ocr_items, edge_features, viz_output)

        # Step 3: LLM Extraction
        pnid = self.step3_llm(image_path, ocr_items, edge_features)

        # Save final PNID
        pnid_output = output_dir / "pnid_three_step.json"
        pnid_dict = pnid.model_dump()
        pnid_output.write_text(json.dumps(pnid_dict, indent=2, ensure_ascii=False))
        print(f"✅ Saved PNID graph to: {pnid_output}")

        return {
            "ocr_items": len(ocr_items),
            "lines": edge_features["statistics"]["total_lines"],
            "contours": edge_features["statistics"]["total_contours"],
            "components": len(pnid.components),
            "pipes": len(pnid.pipes),
            "outputs": {
                "ocr": str(ocr_output),
                "edges": str(edge_output),
                "visualization": str(viz_output),
                "pnid": str(pnid_output),
            },
        }


def main() -> None:
    """
    CLI entry point:
    - Reads: data/input/brewery.jpg
    - Writes: data/output/three_step_*.{json,jpg}
    """
    # Load environment variables
    load_dotenv()

    base_dir = Path(__file__).resolve().parent.parent
    image_path = base_dir / "data" / "input" / "brewery.jpg"
    output_dir = base_dir / "data" / "output"

    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    print("=" * 80)
    print("THREE-STEP P&ID EXTRACTION PIPELINE")
    print("=" * 80)
    print(f"Input: {image_path}")
    print(f"Output: {output_dir}")
    print("")

    # Create pipeline (default: Azure Anthropic)
    provider = os.getenv("PNID_PROVIDER", "azure-anthropic")
    model = os.getenv("PNID_MODEL", "claude-opus-4-5")

    pipeline = ThreeStepPipeline(provider=provider, model=model)

    # Run pipeline
    results = pipeline.run(image_path, output_dir)

    # Print summary
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"OCR Items:    {results['ocr_items']}")
    print(f"Lines:        {results['lines']}")
    print(f"Contours:     {results['contours']}")
    print(f"Components:   {results['components']}")
    print(f"Pipes:        {results['pipes']}")
    print("")
    print("Output Files:")
    for name, path in results["outputs"].items():
        print(f"  {name:12s}: {path}")
    print("")
    print("Next: Visualize with `uv run src/plot_pnid_graph.py`")
    print("=" * 80)


if __name__ == "__main__":
    main()
