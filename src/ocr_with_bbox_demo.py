#!/usr/bin/env python3
"""
Demo script that combines the DeepSeek OCR with bounding box overlay visualization.
"""

import os
from ollama_deepseel_ocr_fixed import run_deepseek_ocr_via_ollama
from ocr_bbox_overlay import OCRBoundingBoxOverlay


def main():
    # Image path - update this to your image
    #image_path = "/Users/christoph.imler/Documents/pid-legend-small-small-small.png"
    image_path = "/Users/christoph.imler/Documents/brewary.png"
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        print("Please update the image_path variable in the script.")
        return
    
    # Output path for annotated image
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_path = f"{base_name}_annotated.jpg"
    
    print(f"Processing image: {image_path}")
    print(f"Output will be saved to: {output_path}")
    
    # Read image data
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Run OCR with grounding to get bounding boxes
    prompt = "<|grounding|>Convert the document to markdown"
    print("\nRunning OCR via Ollama...")
    
    try:
        ocr_response = run_deepseek_ocr_via_ollama(image_data, prompt, image_path)
        
        print("\n=== OCR Response Summary ===")
        if 'response' in ocr_response:
            response_length = len(ocr_response['response'])
            print(f"Response length: {response_length} characters")
            
            # Show first 200 characters of response
            preview = ocr_response['response'][:200]
            if len(ocr_response['response']) > 200:
                preview += "..."
            print(f"Preview: {preview}")
        else:
            print("No 'response' field in OCR output")
            print("Available fields:", list(ocr_response.keys()))
            return
        
        # Initialize the bounding box overlay class
        overlay = OCRBoundingBoxOverlay(font_size=12)
        
        print("\n=== Processing Bounding Boxes ===")
        
        # Process OCR output and create annotated image
        parsed_items = overlay.process_ocr_and_overlay(
            image_path=image_path,
            ocr_response=ocr_response,
            output_path=output_path,
            box_thickness=2,
            show_labels=True,
            label_background=True,
            auto_scale_coords=True  # Enable coordinate auto-scaling
        )
        
        # Show statistics
        stats = overlay.get_statistics(parsed_items)
        print("\n=== Statistics ===")
        print(f"Total items found: {stats['total_items']}")
        print(f"Text items: {stats['text_items']}")
        print(f"Image items: {stats['image_items']}")
        print(f"Average bounding box size: {stats['average_bbox_width']}x{stats['average_bbox_height']} pixels")
        
        # Show detailed items
        print("\n=== Detected Items ===")
        for i, item in enumerate(parsed_items[:10]):  # Show first 10 items
            bbox = item['bbox']
            text_preview = item['text'][:30] + "..." if len(item['text']) > 30 else item['text']
            print(f"{i+1:2d}. [{item['type']:5s}] '{text_preview}' at [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")
        
        if len(parsed_items) > 10:
            print(f"... and {len(parsed_items) - 10} more items")
        
        print(f"\n✅ Successfully created annotated image: {output_path}")
        
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
