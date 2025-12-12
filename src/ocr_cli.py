#!/usr/bin/env python3
"""Simple CLI for running DeepSeek OCR via Ollama.

Usage:
    python src/ocr_cli.py <image_path> [--output OUTPUT] [--prompt PROMPT] [--no-overlay]

Examples:
    # Basic OCR with bounding box overlay
    python src/ocr_cli.py data/input/brewery.png

    # OCR without overlay (text only)
    python src/ocr_cli.py data/input/brewery.png --no-overlay

    # Custom output path
    python src/ocr_cli.py data/input/brewery.png --output results/my_output.jpg

    # Custom prompt
    python src/ocr_cli.py data/input/brewery.png --prompt "Extract all text"
"""

import argparse
import json
import sys
from pathlib import Path

from ocr_bbox_overlay import OCRBoundingBoxOverlay
from ollama_deepseel_ocr_fixed import run_deepseek_ocr_via_ollama


def main():
    parser = argparse.ArgumentParser(
        description="Run DeepSeek OCR via Ollama with optional bounding box overlay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic OCR with overlay
  %(prog)s data/input/brewery.png

  # Text-only output
  %(prog)s data/input/brewery.png --no-overlay

  # Custom output path
  %(prog)s data/input/brewery.png --output results/annotated.jpg

  # Custom prompt
  %(prog)s data/input/brewery.png --prompt "Extract all text and tables"
        """,
    )

    parser.add_argument("image_path", type=str, help="Path to input image")

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output path for annotated image (default: data/output/<image>_annotated.jpg)",
    )

    parser.add_argument(
        "-p",
        "--prompt",
        type=str,
        default="<|grounding|>Convert the document to markdown",
        help="OCR prompt (default: grounding mode for bounding boxes)",
    )

    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Skip overlay visualization (text output only)",
    )

    parser.add_argument(
        "--json-output",
        type=str,
        help="Save raw OCR response to JSON file",
    )

    parser.add_argument(
        "--box-thickness",
        type=int,
        default=2,
        help="Bounding box line thickness (default: 2)",
    )

    parser.add_argument(
        "--font-size",
        type=int,
        default=12,
        help="Label font size (default: 12)",
    )

    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Don't show text labels on bounding boxes",
    )

    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream response from Ollama (shows progress dots)",
    )

    args = parser.parse_args()

    # Validate image path
    image_path = Path(args.image_path)
    if not image_path.exists():
        print(f"❌ Error: Image not found: {image_path}", file=sys.stderr)
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{image_path.stem}_annotated.jpg"

    print(f"📸 Input image: {image_path}")
    if not args.no_overlay:
        print(f"💾 Output will be saved to: {output_path}")
    print(f"🔍 Prompt: {args.prompt}")
    print()

    # Read image
    try:
        image_data = image_path.read_bytes()
    except Exception as e:
        print(f"❌ Error reading image: {e}", file=sys.stderr)
        return 1

    # Run OCR
    print("⏳ Running OCR via Ollama (this may take several minutes on CPU)...")
    print("   DeepSeek-OCR model processing...")

    try:
        ocr_response = run_deepseek_ocr_via_ollama(
            image_data, args.prompt, str(image_path), stream=args.stream
        )
    except Exception as e:
        print(f"❌ Error during OCR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    # Check response
    if "response" not in ocr_response:
        print(f"❌ Error: No 'response' field in OCR output", file=sys.stderr)
        print(f"Available fields: {list(ocr_response.keys())}")
        if "error" in ocr_response:
            print(f"Error message: {ocr_response['error']}")
        return 1

    print("✅ OCR complete!")
    print()

    # Save JSON if requested
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(ocr_response, indent=2, ensure_ascii=False))
        print(f"💾 Saved raw JSON to: {json_path}")

    # Show response preview
    response_text = ocr_response["response"]
    print("=" * 80)
    print("OCR RESPONSE PREVIEW (first 500 characters)")
    print("=" * 80)
    preview = response_text[:500]
    if len(response_text) > 500:
        preview += f"\n... ({len(response_text) - 500} more characters)"
    print(preview)
    print("=" * 80)
    print()

    # Create overlay if requested
    if not args.no_overlay:
        print("🎨 Creating bounding box overlay...")

        try:
            overlay = OCRBoundingBoxOverlay(font_size=args.font_size)

            parsed_items = overlay.process_ocr_and_overlay(
                image_path=str(image_path),
                ocr_response=ocr_response,
                output_path=str(output_path),
                box_thickness=args.box_thickness,
                show_labels=not args.no_labels,
                label_background=True,
                auto_scale_coords=True,
            )

            # Show statistics
            stats = overlay.get_statistics(parsed_items)
            print()
            print("=" * 80)
            print("STATISTICS")
            print("=" * 80)
            print(f"Total items detected:    {stats['total_items']}")
            print(f"  - Text items:          {stats['text_items']}")
            print(f"  - Image items:         {stats['image_items']}")
            print(
                f"Average bbox size:       {stats['average_bbox_width']:.1f} × {stats['average_bbox_height']:.1f} pixels"
            )
            print("=" * 80)
            print()

            # Show first few items
            if parsed_items:
                print("DETECTED ITEMS (first 10):")
                for i, item in enumerate(parsed_items[:10]):
                    bbox = item["bbox"]
                    text_preview = (
                        item["text"][:40] + "..." if len(item["text"]) > 40 else item["text"]
                    )
                    print(
                        f"  {i + 1:2d}. [{item['type']:5s}] '{text_preview}' @ [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]"
                    )

                if len(parsed_items) > 10:
                    print(f"  ... and {len(parsed_items) - 10} more items")
                print()

            print(f"✅ Annotated image saved to: {output_path}")

        except Exception as e:
            print(f"❌ Error creating overlay: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            return 1

    print()
    print("✅ Done!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
