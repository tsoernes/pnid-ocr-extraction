# OCR Bounding Box Overlay

This module provides functionality to parse OCR output with bounding box coordinates and overlay them on the original image for visualization.

## Features

- **Parse OCR Output**: Extracts text and bounding box coordinates from DeepSeek OCR responses
- **Visual Overlay**: Draws bounding boxes and labels on the original image
- **Auto-Scaling**: Automatically scales coordinates to match actual image dimensions
- **Multiple Formats**: Handles both text and image regions
- **Customizable**: Configurable colors, fonts, and styling options
- **Format Support**: Automatically handles RGBA to RGB conversion for JPEG output

## Files

- `ocr_bbox_overlay.py` - Main class for parsing and overlaying bounding boxes
- `ocr_with_bbox_demo.py` - Complete demo script using the existing OCR function
- `simple_bbox_example.py` - Standalone example for direct usage
- `bbox_requirements.txt` - Required Python packages

## Installation

```bash
pip install -r bbox_requirements.txt
```

## Usage

### Quick Start with Demo Script

```bash
python ocr_with_bbox_demo.py
```

This will:
1. Run OCR on a sample image using DeepSeek OCR via Ollama
2. Parse the bounding box coordinates
3. Create an annotated image with overlaid bounding boxes

### Using the Class Directly

```python
from ocr_bbox_overlay import OCRBoundingBoxOverlay

# Initialize the overlay class
overlay = OCRBoundingBoxOverlay(font_size=14)

# Your OCR response from DeepSeek OCR
ocr_response = {
    "response": "Your text<|ref|>text<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>"
}

# Parse and overlay in one step
parsed_items = overlay.process_ocr_and_overlay(
    image_path="input.jpg",
    ocr_response=ocr_response,
    output_path="annotated.jpg"
)

# Or do it step by step
parsed_items = overlay.parse_ocr_output(ocr_response)
overlay.overlay_bounding_boxes("input.jpg", parsed_items, "output.jpg")
```

### Customization Options

```python
overlay = OCRBoundingBoxOverlay(
    font_size=16,
    font_path="/path/to/custom/font.ttf"  # Optional custom font
)

overlay.overlay_bounding_boxes(
    image_path="input.jpg",
    parsed_items=parsed_items,
    output_path="output.jpg",
    box_thickness=3,           # Thicker bounding boxes
    show_labels=True,          # Show text labels
    label_background=True,     # Add background to labels
    auto_scale_coords=True     # Auto-scale coordinates (default: True)
)
```

## OCR Output Format

The class expects OCR output in the DeepSeek format:

```
Text content<|ref|>text<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
More text<|ref|>text<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
<|ref|>image<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
```

Where:
- `<|ref|>text<|/ref|>` indicates a text region
- `<|ref|>image<|/ref|>` indicates an image region
- `<|det|>[[x1, y1, x2, y2]]<|/det|>` contains the bounding box coordinates

## Class Methods

### `OCRBoundingBoxOverlay`

#### `__init__(font_size=12, font_path=None)`
Initialize the overlay class with optional font settings.

#### `parse_ocr_output(ocr_response)`
Parse OCR response and extract text with bounding boxes.
- **Returns**: List of dictionaries with 'text', 'bbox', and 'type' fields

#### `overlay_bounding_boxes(image_path, parsed_items, output_path, **kwargs)`
Draw bounding boxes and labels on the image.
- **Parameters**:
  - `box_thickness`: Line thickness for bounding boxes (default: 2)
  - `show_labels`: Whether to show text labels (default: True)
  - `label_background`: Add background to text labels (default: True)

#### `process_ocr_and_overlay(image_path, ocr_response, output_path, **kwargs)`
Complete pipeline: parse OCR output and create annotated image.

#### `get_statistics(parsed_items)`
Get statistics about the parsed items (counts, average sizes, etc.).

## Example Output

The script will output:
- Number of detected items (text and image regions)
- Statistics about bounding box sizes
- List of detected items with their coordinates
- Annotated image with colored bounding boxes and labels

## Color Scheme

The class uses a predefined set of colors for bounding boxes:
- Red, Green, Blue, Yellow, Magenta, Cyan
- Orange, Purple, Dark Green, Pink, Brown, Gray

Colors are assigned cyclically to ensure visual distinction between adjacent items.

## Coordinate Scaling

The DeepSeek OCR model uses **1000-bin normalized coordinates** as described in their paper. All coordinates are normalized into 1000 bins regardless of the actual image dimensions. The class automatically converts these normalized coordinates to actual pixel coordinates:

- **1000-bin normalization**: OCR coordinates are in range 0-1000
- **Automatic conversion**: Scales coordinates to actual image pixel dimensions
- **Proportional scaling**: Maintains aspect ratios and relative positions
- **Optional**: Can be disabled by setting `auto_scale_coords=False`

Example scaling output:
```
Converting from 1000-bin normalized coordinates to image pixels (620x345)
Coordinate scaling: scale_x=0.620, scale_y=0.345
```

This means:
- X coordinates: 1000-bin → 620 pixels (scale_x = 620/1000 = 0.620)
- Y coordinates: 1000-bin → 345 pixels (scale_y = 345/1000 = 0.345)

## Error Handling

- Automatically converts RGBA images to RGB when saving as JPEG
- Falls back to default font if custom font loading fails
- Validates OCR response format and provides clear error messages
- Handles coordinate scaling when OCR coordinates exceed image dimensions

## Integration with Existing OCR

The demo script shows how to integrate with the existing `ollama_deepseel_ocr_fixed.py` OCR function:

```python
from ollama_deepseel_ocr_fixed import run_deepseek_ocr_via_ollama
from ocr_bbox_overlay import OCRBoundingBoxOverlay

# Run OCR with grounding
ocr_response = run_deepseek_ocr_via_ollama(
    image_data, 
    "<|grounding|>Convert the document to markdown"
)

# Create annotated image
overlay = OCRBoundingBoxOverlay()
overlay.process_ocr_and_overlay(image_path, ocr_response, output_path)
```

## Requirements

- Python 3.7+
- Pillow (PIL) for image processing
- requests (for OCR integration)

## Notes

- The parsing logic handles the specific format output by DeepSeek OCR with grounding
- Bounding box coordinates are expected in [x1, y1, x2, y2] format
- The class automatically handles different image formats and color modes
- Text labels are positioned above bounding boxes when possible, inside when space is limited
