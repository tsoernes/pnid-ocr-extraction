#!/usr/bin/env python3
"""
Two-step pipeline:
1) Use PaddleOCR output for text+positions.
2) Call Azure Anthropic (Claude Opus 4.5) via the project's pnid_agent using OCR as structured context
   alongside the original image, to produce a PNID (components + pipes with coordinates).

Outputs:
- data/output/pnid_from_paddle_anthropic.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic_ai import BinaryContent

from pnid_agent import Provider, create_agent


def build_ocr_context(ocr_items: list[dict[str, Any]]) -> str:
    """
    Convert PaddleOCR items into a textual context for the LLM.

    Each OCR item is expected to have:
      - "text": str
      - "confidence": float
      - "bbox": list[list[float]] of length 4 (quadrilateral points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]])

    We compute the approximate center (cx, cy) of the quadrilateral and emit one line per detection.
    """
    lines: list[str] = []
    for item in ocr_items:
        bbox = item.get("bbox", [])
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(isinstance(p, list) and len(p) == 2 for p in bbox)
        ):
            # Skip malformed bbox entries
            continue

        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        text = str(item.get("text", "")).strip()

        # Confidence may be missing or non-float; coerce defensively
        conf_val = item.get("confidence", 0.0)
        try:
            conf = float(conf_val)
        except (TypeError, ValueError):
            conf = 0.0

        # Emit a simple, machine-readable line per detection
        lines.append(f'Text "{text}" at ({cx:.1f}, {cy:.1f}), conf={conf:.2f}')

    header = (
        "The following OCR detections come from EasyOCR and are ground truth text with "
        "pixel coordinates in the original image:\n"
        "Use ONLY this list for text content and positions; do NOT perform your own OCR.\n\n"
    )
    return header + "\n".join(lines)


def main() -> None:
    """
    CLI entry point:
    - Reads:  data/output/paddle_ocr_boxes.json and data/input/brewery.jpg
    - Writes: data/output/pnid_from_paddle_anthropic.json
    """
    base_dir = Path(__file__).parent.parent
    image_path = base_dir / "data" / "input" / "brewery.jpg"
    ocr_path = base_dir / "data" / "output" / "easyocr_boxes.json"
    output_path = base_dir / "data" / "output" / "pnid_from_paddle_anthropic.json"

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not ocr_path.exists():
        raise FileNotFoundError(f"OCR JSON not found: {ocr_path}")

    # 1) Load OCR items and build context
    ocr_items: list[dict[str, Any]] = json.loads(ocr_path.read_text(encoding="utf-8"))
    ocr_context = build_ocr_context(ocr_items)

    # 2) Read image as binary and determine media type
    image_bytes = image_path.read_bytes()
    ext = image_path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")
    binary_image = BinaryContent(data=image_bytes, media_type=media_type)

    # 3) Create Azure Anthropic agent (Claude Opus 4.5)
    agent = create_agent(Provider.AZURE_ANTHROPIC, model_name="claude-opus-4-5")

    # 4) Run agent with [OCR context, image]
    #    The OCR context provides text and positions; the image provides shapes/geometry.
    result = agent.run_sync([ocr_context, binary_image])

    # 5) Save PNID output (nested format consistent with other outputs)
    data = {
        "output": result.output.model_dump(),
        "provider": "azure-anthropic",
        "model": result.response.model_name or "claude-opus-4-5",
        "image_path": str(image_path),
        "ocr_source": "paddleocr",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # 6) Print summary
    components = data["output"].get("components", [])
    pipes = data["output"].get("pipes", [])
    print(f"✅ Saved PNID from PaddleOCR + Anthropic to: {output_path}")
    print(f"Components: {len(components)}")
    print(f"Pipes: {len(pipes)}")


if __name__ == "__main__":
    main()
