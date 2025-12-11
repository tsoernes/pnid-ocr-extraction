#!/usr/bin/env python3
"""
Compare bounding box overlay with and without coordinate scaling.
"""

from ollama_deepseel_ocr_fixed import run_deepseek_ocr_via_ollama
from ocr_bbox_overlay import OCRBoundingBoxOverlay

def main():
    image_path = "../data/input/pid-legend-small-small-small.png"
    
    # Read image data
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Run OCR
    prompt = "<|grounding|>Convert the document to markdown"
    print("Running OCR...")
    ocr_response = run_deepseek_ocr_via_ollama(image_data, prompt, image_path)
    
    # Initialize overlay
    overlay = OCRBoundingBoxOverlay(font_size=10)
    
    # Create version WITHOUT scaling
    print("\n=== Creating version WITHOUT coordinate scaling ===")
    try:
        parsed_items_unscaled = overlay.process_ocr_and_overlay(
            image_path=image_path,
            ocr_response=ocr_response,
            output_path="unscaled_bbox.jpg",
            auto_scale_coords=False,
            box_thickness=1,
            show_labels=True
        )
        print("✅ Created unscaled_bbox.jpg")
    except Exception as e:
        print(f"❌ Failed to create unscaled version: {e}")
    
    # Create version WITH scaling
    print("\n=== Creating version WITH coordinate scaling ===")
    parsed_items_scaled = overlay.process_ocr_and_overlay(
        image_path=image_path,
        ocr_response=ocr_response,
        output_path="scaled_bbox.jpg",
        auto_scale_coords=True,
        box_thickness=2,
        show_labels=True,
        label_background=True
    )
    print("✅ Created scaled_bbox.jpg")
    
    # Compare a few sample coordinates
    print("\n=== Coordinate Comparison (first 5 items) ===")
    if 'parsed_items_unscaled' in locals():
        for i in range(min(5, len(parsed_items_scaled))):
            unscaled_bbox = parsed_items_unscaled[i]['bbox'] if i < len(parsed_items_unscaled) else "N/A"
            scaled_bbox = parsed_items_scaled[i]['bbox']
            text = parsed_items_scaled[i]['text'][:20] + "..." if len(parsed_items_scaled[i]['text']) > 20 else parsed_items_scaled[i]['text']
            
            print(f"{i+1}. '{text}'")
            print(f"   Unscaled: {unscaled_bbox}")
            print(f"   Scaled:   {scaled_bbox}")
    else:
        print("Unscaled version failed, showing only scaled coordinates:")
        for i in range(min(5, len(parsed_items_scaled))):
            scaled_bbox = parsed_items_scaled[i]['bbox']
            text = parsed_items_scaled[i]['text'][:20] + "..." if len(parsed_items_scaled[i]['text']) > 20 else parsed_items_scaled[i]['text']
            print(f"{i+1}. '{text}' -> {scaled_bbox}")

if __name__ == "__main__":
    main()
