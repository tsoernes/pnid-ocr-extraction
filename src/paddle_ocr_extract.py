#!/usr/bin/env python3
"""
Run PaddleOCR on the brewery image and save OCR bounding boxes.

This script is intended as the **first step** in a two-stage pipeline:

1. OCR/layout: Use PaddleOCR to get (text, bbox) for all text regions.
2. Semantics: Feed that structured OCR into an LLM-based P&ID extractor
   (Anthropic, Gemini, Azure GPT-5.x, etc.) to build the PNID graph.

The output format is a JSON file:

[
  {
    "text": "MAK",
    "confidence": 0.987,
    "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
  },
  ...
]

Coordinates are pixel coordinates in the original image's coordinate system.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paddleocr import PaddleOCR  # type: ignore[import]


def run_paddle_ocr(
    image_path: Path,
    lang: str = "en",
    use_angle_cls: bool = True,
) -> list[dict[str, Any]]:
    """
    Run PaddleOCR on the given image and return flattened OCR items.

    Args:
        image_path: Path to the input image.
        lang: Language code for PaddleOCR.
        use_angle_cls: Whether to enable angle classification.

    Returns:
        List of dictionaries with keys:
        - text: recognized text
        - confidence: recognition confidence
        - bbox: list of 4 [x,y] points (quadrilateral in pixel coordinates)
    """
    ocr = PaddleOCR(use_textline_orientation=True, lang=lang)
    result = ocr.predict(str(image_path))

    items: list[dict[str, Any]] = []

    # result is typically: [ [ [bbox, (text, score)], ... ], ... ]
    for page in result:
        for line in page:
            if not line:
                continue
            # Robust parsing across PaddleOCR versions/pipelines
            bbox = None
            text = ""
            conf = 0.0

            # List/tuple format: [bbox, (text, score)] or [bbox, (text, score), ...]
            if isinstance(line, (list, tuple)):
                if len(line) >= 2:
                    candidate_bbox = line[0]
                    candidate_rec = line[1]
                    bbox = candidate_bbox
                    if isinstance(candidate_rec, (list, tuple)) and len(candidate_rec) >= 2:
                        text = str(candidate_rec[0])
                        try:
                            conf = float(candidate_rec[1])
                        except (TypeError, ValueError):
                            conf = 0.0
                    elif isinstance(candidate_rec, dict):
                        text = str(candidate_rec.get("text", ""))
                        try:
                            conf = float(candidate_rec.get("score", 0.0))
                        except (TypeError, ValueError):
                            conf = 0.0
                # Some variants return three entries; ensure bbox from first
                if bbox is None and len(line) > 0:
                    bbox = line[0]
            # Dict format: {'bbox': ..., 'text': ..., 'score': ...} or keys variants
            elif isinstance(line, dict):
                bbox = line.get("bbox") or line.get("points")
                text = str(line.get("text", ""))
                try:
                    conf = float(line.get("score", 0.0))
                except (TypeError, ValueError):
                    conf = 0.0

            # Validate bbox (expect quadrilateral with 4 points)
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                # Skip malformed bbox entries
                continue

            items.append(
                {
                    "text": text,
                    "confidence": conf,
                    "bbox": bbox,
                }
            )

    return items


def save_ocr_items(items: list[dict[str, Any]], output_path: Path) -> None:
    """
    Save OCR items to a JSON file.

    Args:
        items: List of OCR item dictionaries.
        output_path: Path to output JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(items, indent=2, ensure_ascii=False))


def main() -> None:
    """
    CLI entry point.

    - Reads:  data/input/brewery.jpg
    - Writes: data/output/paddle_ocr_boxes.json
    """
    base_dir = Path(__file__).resolve().parent.parent
    image_path = base_dir / "data" / "input" / "brewery.jpg"
    output_path = base_dir / "data" / "output" / "paddle_ocr_boxes.json"

    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    print(f"📸 Running PaddleOCR on: {image_path}")
    items = run_paddle_ocr(image_path=image_path, lang="en", use_angle_cls=True)

    save_ocr_items(items, output_path)
    print(f"✅ Saved {len(items)} OCR items to: {output_path}")


if __name__ == "__main__":
    main()
