import re
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional


class OCRBoundingBoxOverlay:
    """
    A class to parse OCR output with bounding boxes and overlay them on the original image.
    """
    
    def __init__(self, font_size: int = 12, font_path: Optional[str] = None):
        """
        Initialize the OCR bounding box overlay class.
        
        Args:
            font_size: Size of the font for text labels
            font_path: Path to a custom font file (optional)
        """
        self.font_size = font_size
        self.font_path = font_path
        self.colors = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
            '#FFA500', '#800080', '#008000', '#FFC0CB', '#A52A2A', '#808080'
        ]
        
    def parse_ocr_output(self, ocr_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse the OCR response to extract text and bounding boxes.
        
        Args:
            ocr_response: The JSON response from the OCR model
            
        Returns:
            List of dictionaries containing text and bounding box information
        """
        if 'response' not in ocr_response:
            raise ValueError("OCR response must contain 'response' field")
            
        response_text = ocr_response['response']
        
        # Use regex to find all text/image references with their bounding boxes
        # Pattern matches: text content followed by <|ref|>type<|/ref|><|det|>[[coords]]<|/det|>
        pattern = r'([^<]*?)<\|ref\|>(text|image)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>'
        
        matches = re.findall(pattern, response_text, re.DOTALL)
        parsed_items = []
        
        for match in matches:
            text_content, ref_type, x1, y1, x2, y2 = match
            
            # Clean up the text content
            text_content = text_content.strip()
            
            # Remove any leading/trailing whitespace and newlines
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # If no text content and it's an image, use 'IMAGE'
            if not text_content and ref_type == 'image':
                text_content = 'IMAGE'
            elif not text_content:
                text_content = 'TEXT'
            
            parsed_items.append({
                'text': text_content,
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'type': ref_type
            })
            
        return parsed_items
    
    def overlay_bounding_boxes(self, 
                             image_path: str, 
                             parsed_items: List[Dict[str, Any]], 
                             output_path: str,
                             box_thickness: int = 2,
                             show_labels: bool = True,
                             label_background: bool = True,
                             auto_scale_coords: bool = True) -> None:
        """
        Overlay bounding boxes on the original image.
        
        Args:
            image_path: Path to the original image
            parsed_items: List of parsed OCR items with bounding boxes
            output_path: Path to save the output image
            box_thickness: Thickness of the bounding box lines
            show_labels: Whether to show text labels
            label_background: Whether to add background to text labels
        """
        # Open the original image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Get actual image dimensions
        img_width, img_height = image.size
        
        # Auto-scale coordinates - OCR uses 1000-bin normalization
        if auto_scale_coords and parsed_items:
            # OCR coordinates are normalized to 1000 bins, convert to actual image pixels
            print(f"Converting from 1000-bin normalized coordinates to image pixels ({img_width}x{img_height})")
            
            # Scale factors: from 1000-bin space to actual image dimensions
            scale_x = img_width / 1000.0
            scale_y = img_height / 1000.0
            
            print(f"Coordinate scaling: scale_x={scale_x:.3f}, scale_y={scale_y:.3f}")
            
            # Scale all bounding boxes from 1000-bin space to pixel space
            for item in parsed_items:
                bbox = item['bbox']
                item['bbox'] = [
                    int(bbox[0] * scale_x),
                    int(bbox[1] * scale_y),
                    int(bbox[2] * scale_x),
                    int(bbox[3] * scale_y)
                ]
        
        # Try to load a font
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, self.font_size)
            else:
                # Try to use a default system font
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", self.font_size)
        except (OSError, IOError):
            # Fall back to default font
            font = ImageFont.load_default()
        
        # Draw bounding boxes and labels
        for i, item in enumerate(parsed_items):
            bbox = item['bbox']
            text = item['text']
            item_type = item['type']
            
            # Get color for this item
            color = self.colors[i % len(self.colors)]
            
            # Draw bounding box
            x1, y1, x2, y2 = bbox
            draw.rectangle([x1, y1, x2, y2], outline=color, width=box_thickness)
            
            if show_labels and text:
                # Calculate text position (above the box if possible)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Position text above the box, or inside if not enough space
                if y1 - text_height - 5 >= 0:
                    text_x = x1
                    text_y = y1 - text_height - 5
                else:
                    text_x = x1 + 5
                    text_y = y1 + 5
                
                # Add background to text if requested
                if label_background:
                    bg_x1 = text_x - 2
                    bg_y1 = text_y - 2
                    bg_x2 = text_x + text_width + 2
                    bg_y2 = text_y + text_height + 2
                    draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill='white', outline=color)
                
                # Draw text
                draw.text((text_x, text_y), text, fill=color, font=font)
                
                # Add type indicator for images
                if item_type == 'image':
                    type_text = f"[{item_type.upper()}]"
                    draw.text((text_x, text_y + text_height + 2), type_text, fill=color, font=font)
        
        # Convert RGBA to RGB if saving as JPEG
        if output_path.lower().endswith(('.jpg', '.jpeg')) and image.mode == 'RGBA':
            # Create a white background and paste the RGBA image on it
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
            image = rgb_image
        
        # Save the result
        image.save(output_path)
        print(f"Saved annotated image to: {output_path}")
    
    def process_ocr_and_overlay(self, 
                              image_path: str, 
                              ocr_response: Dict[str, Any], 
                              output_path: str,
                              **overlay_kwargs) -> List[Dict[str, Any]]:
        """
        Complete pipeline: parse OCR output and overlay bounding boxes.
        
        Args:
            image_path: Path to the original image
            ocr_response: The JSON response from the OCR model
            output_path: Path to save the annotated image
            **overlay_kwargs: Additional arguments for overlay_bounding_boxes
            
        Returns:
            List of parsed OCR items
        """
        # Parse OCR output
        parsed_items = self.parse_ocr_output(ocr_response)
        
        print(f"Found {len(parsed_items)} items with bounding boxes:")
        for i, item in enumerate(parsed_items):
            print(f"  {i+1}. {item['type']}: '{item['text'][:50]}...' at {item['bbox']}")
        
        # Overlay bounding boxes
        self.overlay_bounding_boxes(image_path, parsed_items, output_path, **overlay_kwargs)
        
        return parsed_items
    
    def get_statistics(self, parsed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about the parsed OCR items.
        
        Args:
            parsed_items: List of parsed OCR items
            
        Returns:
            Dictionary with statistics
        """
        total_items = len(parsed_items)
        text_items = sum(1 for item in parsed_items if item['type'] == 'text')
        image_items = sum(1 for item in parsed_items if item['type'] == 'image')
        
        # Calculate average bounding box size
        if parsed_items:
            avg_width = sum((item['bbox'][2] - item['bbox'][0]) for item in parsed_items) / total_items
            avg_height = sum((item['bbox'][3] - item['bbox'][1]) for item in parsed_items) / total_items
        else:
            avg_width = avg_height = 0
        
        return {
            'total_items': total_items,
            'text_items': text_items,
            'image_items': image_items,
            'average_bbox_width': round(avg_width, 2),
            'average_bbox_height': round(avg_height, 2)
        }


# Example usage
if __name__ == "__main__":
    # Example OCR response (you would get this from your OCR function)
    sample_ocr_response = {
        "response": """下列哪项不是计算机辅助设计（CAD）软件？<|ref|>text<|/ref|><|det|>[[141, 59, 227, 103]]<|/det|>
Indicator<|ref|>text<|/ref|><|det|>[[141, 210, 286, 252]]<|/det|>
Behind Control<|ref|>text<|/ref|><|det|>[[141, 353, 249, 440]]<|/det|>
<|ref|>image<|/ref|><|det|>[[370, 0, 468, 999]]<|/det|>"""
    }
    
    # Initialize the overlay class
    overlay = OCRBoundingBoxOverlay(font_size=14)
    
    # Process and overlay (you would use your actual image path and OCR response)
    image_path = "/path/to/your/image.jpg"
    output_path = "/path/to/output/annotated_image.jpg"
    
    # This would be called with real data:
    # parsed_items = overlay.process_ocr_and_overlay(image_path, ocr_response, output_path)
    # stats = overlay.get_statistics(parsed_items)
    # print("Statistics:", stats)
