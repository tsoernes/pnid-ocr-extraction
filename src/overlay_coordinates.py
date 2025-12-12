#!/usr/bin/env python3
"""Overlay bounding boxes from AI-extracted P&ID data onto the original image.

This script reads the JSON output from pnid_agent.py and draws bounding boxes
around each detected component and pipe label using the extracted x,y coordinates.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_pnid_data(json_path: Path) -> dict:
    """Load P&ID data from JSON file."""
    with open(json_path, "r") as f:
        data = json.load(f)

    # Handle both old format (direct) and new format (nested in 'output')
    if "output" in data:
        return data["output"]
    return data


def estimate_bbox_size(label: str, base_size: int = 40) -> tuple[int, int]:
    """Estimate bounding box size based on label length.

    Args:
        label: The text label
        base_size: Base size for bbox

    Returns:
        (width, height) tuple
    """
    # Rough estimate: 8 pixels per character
    width = max(base_size, len(label) * 8 + 10)
    height = base_size
    return width, height


def draw_component_boxes(
    image: Image.Image,
    components: list[dict],
    draw: ImageDraw.Draw,
    font: ImageFont.ImageFont,
    box_color: str = "#00FF00",
    text_color: str = "#00FF00",
    box_thickness: int = 3,
) -> int:
    """Draw bounding boxes around components.

    Args:
        image: PIL Image object
        components: List of component dictionaries
        draw: ImageDraw object
        font: Font for labels
        box_color: Color for bounding box
        text_color: Color for text label
        box_thickness: Thickness of box lines

    Returns:
        Number of boxes drawn
    """
    count = 0
    for comp in components:
        x = comp.get("x", 0)
        y = comp.get("y", 0)
        label = comp.get("label", "?")

        # Estimate bbox size based on label
        width, height = estimate_bbox_size(label)

        # Calculate bbox coordinates (x,y is center)
        x1 = int(x - width / 2)
        y1 = int(y - height / 2)
        x2 = int(x + width / 2)
        y2 = int(y + height / 2)

        # Ensure bbox is within image bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.width, x2)
        y2 = min(image.height, y2)

        # Ensure x1 < x2 and y1 < y2
        if x1 >= x2 or y1 >= y2:
            continue  # Skip invalid boxes

        # Draw bounding box
        draw.rectangle([x1, y1, x2, y2], outline=box_color, width=box_thickness)

        # Draw label with background
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Position label above box if possible, otherwise inside
        if y1 - text_height - 5 >= 0:
            text_x = x1
            text_y = y1 - text_height - 5
        else:
            text_x = x1 + 5
            text_y = y1 + 5

        # Draw text background
        bg_x1 = text_x - 2
        bg_y1 = text_y - 2
        bg_x2 = text_x + text_width + 2
        bg_y2 = text_y + text_height + 2
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill="white", outline=box_color)

        # Draw text
        draw.text((text_x, text_y), label, fill=text_color, font=font)

        # Draw center point
        center_size = 3
        draw.ellipse(
            [x - center_size, y - center_size, x + center_size, y + center_size],
            fill=box_color,
            outline=box_color,
        )

        count += 1

    return count


def draw_pipe_markers(
    image: Image.Image,
    pipes: list[dict],
    draw: ImageDraw.Draw,
    font: ImageFont.ImageFont,
    marker_color: str = "#FF0000",
    text_color: str = "#FF0000",
    marker_size: int = 20,
) -> int:
    """Draw markers at pipe label positions.

    Args:
        image: PIL Image object
        pipes: List of pipe dictionaries
        draw: ImageDraw object
        font: Font for labels
        marker_color: Color for marker
        text_color: Color for text
        marker_size: Size of marker

    Returns:
        Number of markers drawn
    """
    count = 0
    for pipe in pipes:
        x = pipe.get("x", 0)
        y = pipe.get("y", 0)
        label = pipe.get("label", "?")

        # Draw diamond marker
        half_size = marker_size // 2
        points = [
            (x, y - half_size),  # top
            (x + half_size, y),  # right
            (x, y + half_size),  # bottom
            (x - half_size, y),  # left
        ]
        draw.polygon(points, outline=marker_color, fill=None, width=2)

        # Draw label
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Position text to the right of marker
        text_x = int(x + half_size + 5)
        text_y = int(y - text_height / 2)

        # Draw text background
        bg_x1 = text_x - 2
        bg_y1 = text_y - 2
        bg_x2 = text_x + text_width + 2
        bg_y2 = text_y + text_height + 2
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill="white", outline=marker_color)

        # Draw text
        draw.text((text_x, text_y), label, fill=text_color, font=font)

        count += 1

    return count


def overlay_coordinates(
    image_path: Path,
    json_path: Path,
    output_path: Path,
    show_components: bool = True,
    show_pipes: bool = True,
    font_size: int = 12,
) -> dict:
    """Overlay bounding boxes from extracted coordinates onto image.

    Args:
        image_path: Path to original P&ID image
        json_path: Path to JSON with extracted data
        output_path: Path to save annotated image
        show_components: Whether to show component boxes
        show_pipes: Whether to show pipe markers
        font_size: Font size for labels

    Returns:
        Dictionary with statistics
    """
    # Load image
    image = Image.open(image_path)

    # Convert to RGB if needed (for JPEG output)
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Load P&ID data
    data = load_pnid_data(json_path)
    components = data.get("components", [])
    pipes = data.get("pipes", [])

    # Create draw object
    draw = ImageDraw.Draw(image)

    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Draw components
    component_count = 0
    if show_components:
        component_count = draw_component_boxes(
            image,
            components,
            draw,
            font,
            box_color="#00FF00",
            text_color="#006600",
            box_thickness=3,
        )

    # Draw pipes
    pipe_count = 0
    if show_pipes:
        pipe_count = draw_pipe_markers(
            image, pipes, draw, font, marker_color="#FF0000", text_color="#880000", marker_size=16
        )

    # Add info text in corner
    info_text = f"Components: {component_count} | Pipes: {pipe_count}"
    info_bbox = draw.textbbox((0, 0), info_text, font=font)
    info_width = info_bbox[2] - info_bbox[0]
    info_height = info_bbox[3] - info_bbox[1]

    info_x = 10
    info_y = 10

    # Draw info background
    draw.rectangle(
        [info_x - 5, info_y - 5, info_x + info_width + 5, info_y + info_height + 5],
        fill="white",
        outline="#0000FF",
        width=2,
    )

    # Draw info text
    draw.text((info_x, info_y), info_text, fill="#0000FF", font=font)

    # Save image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, quality=95)

    return {
        "components": component_count,
        "pipes": pipe_count,
        "output_path": str(output_path),
        "image_size": image.size,
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Overlay bounding boxes from AI extraction onto P&ID image"
    )
    parser.add_argument(
        "-i",
        "--image",
        type=str,
        default="data/input/brewery.jpg",
        help="Path to input image (default: data/input/brewery.jpg)",
    )
    parser.add_argument(
        "-j",
        "--json",
        type=str,
        default="data/output/pnid.json",
        help="Path to JSON with extracted data (default: data/output/pnid.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="data/output/pnid_overlay.jpg",
        help="Path to output image (default: data/output/pnid_overlay.jpg)",
    )
    parser.add_argument(
        "--no-components", action="store_true", help="Don't show component bounding boxes"
    )
    parser.add_argument("--no-pipes", action="store_true", help="Don't show pipe markers")
    parser.add_argument(
        "--font-size", type=int, default=12, help="Font size for labels (default: 12)"
    )

    args = parser.parse_args()

    # Convert to paths
    image_path = Path(args.image)
    json_path = Path(args.json)
    output_path = Path(args.output)

    # Check inputs exist
    if not image_path.exists():
        print(f"❌ Error: Image not found: {image_path}", file=sys.stderr)
        return 1

    if not json_path.exists():
        print(f"❌ Error: JSON not found: {json_path}", file=sys.stderr)
        return 1

    print(f"📸 Input image: {image_path}")
    print(f"📄 Input JSON: {json_path}")
    print(f"💾 Output: {output_path}")
    print()

    # Create overlay
    try:
        stats = overlay_coordinates(
            image_path=image_path,
            json_path=json_path,
            output_path=output_path,
            show_components=not args.no_components,
            show_pipes=not args.no_pipes,
            font_size=args.font_size,
        )

        print("✅ Success!")
        print(f"   Components drawn: {stats['components']}")
        print(f"   Pipe markers drawn: {stats['pipes']}")
        print(f"   Image size: {stats['image_size'][0]}x{stats['image_size'][1]}")
        print(f"   Saved to: {stats['output_path']}")
        print()
        print("Legend:")
        print("  🟩 Green boxes = Components (with center dots)")
        print("  🔶 Red diamonds = Pipe labels")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
