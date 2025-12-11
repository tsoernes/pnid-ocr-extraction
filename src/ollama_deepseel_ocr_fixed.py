import requests
import base64
import json
import re
from html.parser import HTMLParser

def run_deepseek_ocr_via_ollama(image_data, prompt="Extract text from image", image_path=None):
    """
    Sends an image and a prompt to the DeepSeek-OCR model running on Ollama.
    
    Args:
        image_data: Either bytes (raw image data) or str (base64 encoded image)
        prompt: Text prompt for the OCR model
    """
    url = "http://localhost:11434/api/generate"
    
    # Convert bytes to base64 if needed
    if isinstance(image_data, bytes):
        image_data_base64 = base64.b64encode(image_data).decode("utf-8")

    print(image_data_base64[:100])
    print(image_path)
    payload = {
        "model": "deepseek-ocr",
        "prompt": prompt,
        "images": [image_data_base64],  # Base64 encoded image data
        #"images": [image_path],  # Base64 encoded image data
        "stream": False
    }
    response = requests.post(url, json=payload)
    return response.json()


if __name__ == "__main__":
    # Example usage - update paths as needed
    # Example usage - update paths as needed
    # Example usage - update paths as needed
    # Example usage - update paths as needed
    with open(image_path, "rb") as f:
        image_data = f.read()

    prompt = "<|grounding|> Convert the document to markdown"
    #prompt = "Free OCR."

    print("Running OCR via Ollama...")

    extracted_text = run_deepseek_ocr_via_ollama(image_data, prompt, image_path)
    
    print("=== RAW OCR RESPONSE ===")
    print(json.dumps(extracted_text, indent=2))
    
    print("\n=== EXTRACTED TEXT ===")
    print(extracted_text['response'])
    