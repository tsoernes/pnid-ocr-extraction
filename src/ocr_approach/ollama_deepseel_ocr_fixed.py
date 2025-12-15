import base64
import json
import re
from html.parser import HTMLParser

import requests


def run_deepseek_ocr_via_ollama(
    image_data, prompt="Extract text from image", image_path=None, stream=False, verbose=False
):
    """
    Sends an image and a prompt to the DeepSeek-OCR model running on Ollama.

    Args:
        image_data: Either bytes (raw image data) or str (base64 encoded image)
        prompt: Text prompt for the OCR model
        image_path: Optional image path for debugging
        stream: If True, stream the response and show progress
        verbose: If True, print debug information

    Returns:
        dict: Response from Ollama with 'response' field containing the OCR result
    """
    url = "http://localhost:11434/api/generate"

    # Convert bytes to base64 if needed
    if isinstance(image_data, bytes):
        image_data_base64 = base64.b64encode(image_data).decode("utf-8")
    else:
        image_data_base64 = image_data

    if verbose:
        print(f"Base64 preview: {image_data_base64[:100]}")
        print(f"Image path: {image_path}")

    payload = {
        "model": "deepseek-ocr",
        "prompt": prompt,
        "images": [image_data_base64],
        "stream": stream,
    }

    if stream:
        # Stream the response and collect chunks
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        full_response = ""
        print("   [Streaming response", end="", flush=True)

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "response" in chunk:
                    full_response += chunk["response"]
                    # Show progress dots
                    print(".", end="", flush=True)

                # Check if done
                if chunk.get("done", False):
                    print("] ✓", flush=True)
                    return {
                        "response": full_response,
                        "model": chunk.get("model", "deepseek-ocr"),
                        "done": True,
                    }

        return {"response": full_response, "done": True}
    else:
        # Non-streaming response
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Example usage - update paths as needed
    with open(image_path, "rb") as f:
        image_data = f.read()

    prompt = "<|grounding|> Convert the document to markdown"
    # prompt = "Free OCR."

    print("Running OCR via Ollama...")

    extracted_text = run_deepseek_ocr_via_ollama(image_data, prompt, image_path)

    print("=== RAW OCR RESPONSE ===")
    print(json.dumps(extracted_text, indent=2))

    print("\n=== EXTRACTED TEXT ===")
    print(extracted_text["response"])
