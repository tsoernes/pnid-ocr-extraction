#!/usr/bin/env python3
"""
Debug script to analyze the bounding box coordinates and see what's happening.
"""

from ollama_deepseel_ocr_fixed import run_deepseek_ocr_via_ollama
from ocr_bbox_overlay import OCRBoundingBoxOverlay
from PIL import Image

def main():
    image_path = "../data/input/pid-legend-small-small-small.png"
    
    # Get image dimensions
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        print(f"Image dimensions: {img_width} x {img_height}")
    
    # Read image data
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Run OCR
    prompt = "<|grounding|>Convert the document to markdown"
    ocr_response = run_deepseek_ocr_via_ollama(image_data, prompt, image_path)
    
    # Parse the response
    overlay = OCRBoundingBoxOverlay()
    parsed_items = overlay.parse_ocr_output(ocr_response)
    
    print(f"\n=== DETAILED ANALYSIS ===")
    print(f"Found {len(parsed_items)} items")
    
    for i, item in enumerate(parsed_items):
        bbox = item['bbox']
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        # Check if coordinates are reasonable
        valid_coords = (0 <= x1 < img_width and 0 <= y1 < img_height and 
                       0 <= x2 <= img_width and 0 <= y2 <= img_height and
                       x1 < x2 and y1 < y2)
        
        print(f"\n{i+1:2d}. [{item['type']:5s}] '{item['text'][:30]}{'...' if len(item['text']) > 30 else ''}'")
        print(f"    Bbox: [{x1:3d}, {y1:3d}, {x2:3d}, {y2:3d}] -> {width:3d}x{height:3d} pixels")
        print(f"    Valid: {valid_coords}")
        
        # Flag suspicious boxes
        if width > img_width * 0.8:
            print(f"    ⚠️  Very wide box ({width}/{img_width})")
        if height > img_height * 0.8:
            print(f"    ⚠️  Very tall box ({height}/{img_height})")
        if width < 10 or height < 10:
            print(f"    ⚠️  Very small box")
    
    # Look for patterns in coordinates
    print(f"\n=== COORDINATE PATTERNS ===")
    x_coords = []
    y_coords = []
    for item in parsed_items:
        x1, y1, x2, y2 = item['bbox']
        x_coords.extend([x1, x2])
        y_coords.extend([y1, y2])
    
    print(f"X range: {min(x_coords)} - {max(x_coords)} (image width: {img_width})")
    print(f"Y range: {min(y_coords)} - {max(y_coords)} (image height: {img_height})")
    
    # Check for common X coordinates (might indicate columns)
    from collections import Counter
    x_counter = Counter(x_coords)
    common_x = [x for x, count in x_counter.most_common(5) if count > 1]
    print(f"Common X coordinates: {common_x}")

if __name__ == "__main__":
    main()
