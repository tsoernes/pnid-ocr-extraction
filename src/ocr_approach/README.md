# OCR-Based P&ID Extraction Approach

This directory contains scripts and tools for extracting P&ID information using **image-based OCR approaches** combined with OpenCV edge detection and skeleton mapping.

## Overview

The OCR approach extracts P&IDs through a multi-step pipeline:

1. **OCR Text Extraction**: Extract text with bounding boxes using various OCR engines
2. **Edge Detection**: Use OpenCV to detect lines, shapes, and connections
3. **Skeleton Mapping**: Convert detected edges to graph topology
4. **Integration**: Combine OCR text with detected connections
5. **LLM Enhancement**: Use LLMs to interpret and structure the results

This approach is **complementary** to the direct LLM-based extraction in the parent directory.

---

## Core Scripts

### OCR Engines

| Script | Engine | Features |
|--------|--------|----------|
| `ollama_deepseel_ocr_fixed.py` | DeepSeek-OCR (local) | Bounding boxes, 1000-bin coordinates, offline |
| `paddle_ocr_extract.py` | PaddleOCR | Fast, multilingual, box coordinates |
| `easyocr_extract.py` | EasyOCR | 80+ languages, GPU support |
| `opencv_test.py` | Tesseract | Legacy, basic text extraction |
| `ocr_cli.py` | Generic CLI | Unified interface for multiple engines |

### Bounding Box Processing

| Script | Purpose |
|--------|---------|
| `ocr_bbox_overlay.py` | Parse OCR output and overlay bounding boxes on images |
| `run_overlay_demo.py` | Demo script for DeepSeek-OCR with visualization |
| `ocr_with_bbox_demo.py` | Original bbox demo (deprecated) |
| `compare_bbox_scaling.py` | Compare different coordinate scaling approaches |
| `debug_bbox.py` | Debug bounding box coordinate issues |
| `overlay_coordinates.py` | Overlay coordinates on images for validation |

### Image Processing & Edge Detection

| Script | Purpose |
|--------|---------|
| `opencv_edge_extraction.py` | Extract lines and shapes using OpenCV |
| `skeleton_path_mapping.py` | Convert detected edges to skeleton graph |
| `route_to_pipe_mapper.py` | Map routes to pipe connections |

### Pipeline Integration

| Script | Purpose |
|--------|---------|
| `three_step_pipeline.py` | Complete OCR → Edge → LLM pipeline |
| `pnid_from_paddle_anthropic.py` | PaddleOCR + Anthropic Claude integration |
| `add_missing_edges.py` | Post-processing to add deterministic connections |
| `focus_viz.py` | Generate focused subgraph visualizations |

---

## Workflows

### Workflow 1: Local OCR with Bounding Boxes (DeepSeek-OCR)

**Status**: ⚠️ Blocked (Ollama version incompatible)

```bash
# 1. Start Ollama server
ollama serve &

# 2. Run OCR with bounding box overlay
uv run src/ocr_approach/run_overlay_demo.py

# Expected Output:
# - data/output/brewery_annotated.jpg
# - Console statistics
```

**Features**:
- Completely offline (local inference)
- 1000-bin normalized coordinates
- Bounding box visualization
- ~2-5 seconds per image (CPU only)

---

### Workflow 2: Three-Step Pipeline (OCR + Edge + LLM)

**Status**: ⚠️ Requires API keys

```bash
# Run complete pipeline
uv run src/ocr_approach/three_step_pipeline.py

# Steps:
# 1. PaddleOCR extracts text with boxes
# 2. OpenCV detects edges and lines
# 3. Skeleton mapper creates graph topology
# 4. LLM interprets and structures output
```

**Output**: `data/output/pnid_three_step.json`

---

### Workflow 3: PaddleOCR + Anthropic

**Status**: ⚠️ Requires Anthropic API key

```bash
# Extract with PaddleOCR, structure with Claude
uv run src/ocr_approach/pnid_from_paddle_anthropic.py
```

**Output**: `data/output/pnid_from_paddle_anthropic.json`

---

## Key Concepts

### Bounding Box Coordinates

Different OCR engines use different coordinate systems:

| Engine | X Range | Y Range | Notes |
|--------|---------|---------|-------|
| DeepSeek-OCR | [0, 1000] | [0, 1000] | Normalized, resolution-independent |
| PaddleOCR | [0, width] | [0, height] | Pixel coordinates |
| EasyOCR | [0, width] | [0, height] | Pixel coordinates |
| Tesseract | [0, width] | [0, height] | Pixel coordinates |

**Scaling Formula (DeepSeek)**:
```python
scale_x = image_width / 1000.0
scale_y = image_height / 1000.0
pixel_x = bbox_x * scale_x
pixel_y = bbox_y * scale_y
```

### Skeleton Mapping

Converts OpenCV-detected edges into a graph topology:

1. **Edge Detection**: Canny edge detection + Hough line transform
2. **Thinning**: Skeletonize detected regions
3. **Junction Detection**: Find T-junctions, crossings, endpoints
4. **Path Tracing**: Follow skeleton to create edges
5. **Component Association**: Match OCR text to nearest junctions

---

## Comparison with Direct LLM Approach

| Aspect | OCR Approach | Direct LLM (parent dir) |
|--------|--------------|------------------------|
| **Speed** | Medium (2-10s) | Fast (<2s) or Slow (>30s with reasoning) |
| **Accuracy** | Good for text, weak for connections | Excellent for both |
| **Offline** | ✅ Yes (DeepSeek-OCR) | ❌ No (requires API) |
| **Cost** | Free (local) | $0.01-$0.10 per diagram |
| **Complexity** | High (multi-step pipeline) | Low (single LLM call) |
| **Best For** | Batch processing, offline, budget | Quality, speed, simplicity |

---

## Dependencies

### OCR Engines

```bash
# DeepSeek-OCR (via Ollama)
ollama pull deepseek-ocr

# PaddleOCR
pip install paddleocr paddlepaddle

# EasyOCR
pip install easyocr

# Tesseract (system package)
sudo dnf install tesseract  # Fedora
sudo apt install tesseract-ocr  # Ubuntu
```

### Image Processing

```bash
pip install opencv-python pillow numpy
```

### Already in project dependencies:
- Pillow (image processing)
- requests (HTTP client)
- python-dotenv (environment variables)

---

## Configuration

### Environment Variables

```bash
# For LLM-enhanced pipelines
ANTHROPIC_API_KEY=your_key_here
AZURE_ANTROPIC_API_KEY=your_key_here
```

### Ollama Configuration

```bash
# Start Ollama server
ollama serve &

# Pull DeepSeek-OCR model
ollama pull deepseek-ocr

# Check status
ollama list
```

---

## Common Issues

### Issue: Ollama incompatible with DeepSeek-OCR

**Error**: `Model not supported by your version`

**Solution**: Upgrade Ollama to latest version (requires sudo):
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Issue: Poor connection detection

**Symptom**: Missing pipes in output

**Solutions**:
1. Tune edge detection thresholds in `opencv_edge_extraction.py`
2. Use higher resolution input images
3. Pre-process image (contrast, brightness)
4. Use LLM-based correction in `add_missing_edges.py`

### Issue: Incorrect bounding box positions

**Symptom**: Text labels in wrong locations

**Debug**:
```bash
# Visualize bounding boxes
uv run src/ocr_approach/debug_bbox.py

# Compare scaling approaches
uv run src/ocr_approach/compare_bbox_scaling.py
```

---

## Future Enhancements

1. **Improved Edge Detection**:
   - Use deep learning for line detection (HED, SegNet)
   - Better junction classification
   - Curved line support

2. **Multi-Page Support**:
   - Handle multi-sheet diagrams
   - Cross-page connection tracking

3. **Symbol Recognition**:
   - Train custom models for P&ID symbols
   - Template matching for standard symbols

4. **Integration**:
   - Hybrid approach combining OCR + direct LLM
   - Use OCR for validation/correction

---

## Related Documentation

- **[Main README](../../README.md)** - Project overview
- **[Workflow Guide](../../docs/WORKFLOW_AND_COMPARISON.md)** - Complete workflows
- **[OCR Bounding Box Guide](../../docs/README_OCR_BoundingBox.md)** - Technical details

---

**Last Updated**: 2025-12-15  
**Status**: Development (blocked on Ollama upgrade)  
**Maintainer**: Bouvet ASA