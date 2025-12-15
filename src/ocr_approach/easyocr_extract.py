#!/usr/bin/env python3
"""
EasyOCR extraction script for P&ID diagrams.

Purpose:
- Run EasyOCR on the project's test image (brewery.jpg).
- Save recognized text fragments with confidence and bounding boxes (pixel coordinates)
  to a JSON file for downstream processing (e.g., LLM-based graph extraction).

Output:
- data/output/easyocr_boxes.json

Format:
[
  {
    "text": "MAK",
    "confidence": 0.987,
    "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
  },
  ...
]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import easyocr  # Assumes EasyOCR is installed and available


def run_easyocr(image_path: Path, languages: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Run EasyOCR on the given image and return flattened OCR items.

    Args:
        image_path: Path to the input image.
        languages: List of language codes for EasyOCR reader (e.g., ["en"]).

    Returns:
        List of dictionaries with keys:
        - text: recognized text (str)
        - confidence: recognition confidence (float)
        - bbox: list of 4 [x,y] points (quadrilateral in pixel coordinates)
    """
    langs = languages or ["en"]
    reader = easyocr.Reader(langs)

    # EasyOCR returns a list of entries: [bbox, text, confidence]
    result = reader.readtext(str(image_path))

    items: list[dict[str, Any]] = []
    for entry in result:
        # Robust parsing across EasyOCR versions
        bbox: list[list[float]] | None = None
        text: str = ""
        conf: float = 0.0

        if isinstance(entry, (list, tuple)):
            # Typical format: [bbox, text, confidence]
            if len(entry) >= 3:
                bbox_candidate = entry[0]
                text_candidate = entry[1]
                conf_candidate = entry[2]
                # Validate bbox as 4 points
                if (
                    isinstance(bbox_candidate, (list, tuple))
                    and len(bbox_candidate) == 4
                    and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in bbox_candidate)
                ):
                    bbox = [[float(p[0]), float(p[1])] for p in bbox_candidate]
                text = str(text_candidate)
                try:
                    conf = float(conf_candidate)
                except (TypeError, ValueError):
                    conf = 0.0
            elif len(entry) == 2:
                # Some variants: [bbox, (text, confidence)] or [bbox, text]
                bbox_candidate = entry[0]
                rec_candidate = entry[1]
                if (
                    isinstance(bbox_candidate, (list, tuple))
                    and len(bbox_candidate) == 4
                    and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in bbox_candidate)
                ):
                    bbox = [[float(p[0]), float(p[1])] for p in bbox_candidate]
                if isinstance(rec_candidate, (list, tuple)) and len(rec_candidate) >= 2:
                    text = str(rec_candidate[0])
                    try:
                        conf = float(rec_candidate[1])
                    except (TypeError, ValueError):
                        conf = 0.0
                else:
                    text = str(rec_candidate)
        elif isinstance(entry, dict):
            # Rare dict format (not typical for EasyOCR)
            bbox_candidate = entry.get("bbox") or entry.get("points")
            if (
                isinstance(bbox_candidate, (list, tuple))
                and len(bbox_candidate) == 4
                and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in bbox_candidate)
            ):
                bbox = [[float(p[0]), float(p[1])] for p in bbox_candidate]
            text = str(entry.get("text", ""))
            try:
                conf = float(entry.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0

        # Skip entries without valid bbox or empty text
        if bbox is None or not text.strip():
            continue

        items.append(
            {
                "text": text.strip(),
                "confidence": conf,
                "bbox": bbox,
            }
        )

    return items


def main() -> None:
    """
    CLI entry point:
    - Reads:  data/input/brewery.jpg
    - Writes: data/output/easyocr_boxes.json
    """
    base_dir = Path(__file__).resolve().parent.parent
    image_path = base_dir / "data" / "input" / "brewery.jpg"
    output_path = base_dir / "data" / "output" / "easyocr_boxes.json"

    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    print(f"📸 Running EasyOCR on: {image_path}")
    items = run_easyocr(image_path=image_path, languages=["en"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    print(f"✅ Saved {len(items)} OCR items to: {output_path}")


if __name__ == "__main__":
    main()
