# Local DeepSeek OCR Guide

## Overview

This guide shows you how to run DeepSeek-OCR locally via Ollama for extracting text and bounding boxes from P&ID diagrams.

**Why use local OCR?**
- ✅ **Privacy**: Data stays on your machine
- ✅ **No API costs**: Free to run
- ✅ **Offline capability**: No internet required
- ❌ **Slow on CPU**: 10-40 minutes per image without GPU
- ❌ **Requires setup**: Need to install Ollama and model

---

## Prerequisites

### 1. Install Ollama

**Fedora/RHEL**:
```bash
sudo dnf install ollama
```

**Or download latest binary** (recommended):
```bash
# Download and install Ollama v0.13.2 or later
curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o /tmp/ollama
sudo mv /tmp/ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama
```

**Verify installation**:
```bash
ollama --version
# Should show v0.13.2 or higher
```

### 2. Pull DeepSeek-OCR Model

Download the 6.7 GB model:
```bash
ollama pull deepseek-ocr
```

Verify:
```bash
ollama list
# Should show: deepseek-ocr:latest    6.7 GB
```

### 3. Start Ollama Server

```bash
ollama serve
```

Keep this terminal open. The server runs on `http://localhost:11434`.

---

## Quick Start

### Method 1: Simple CLI (Recommended)

```bash
# Basic OCR with bounding box overlay
uv run python src/ocr_cli.py data/input/brewery.png

# With streaming (shows progress dots)
uv run python src/ocr_cli.py data/input/brewery.png --stream

# Text-only output (no visualization)
uv run python src/ocr_cli.py data/input/brewery.png --no-overlay

# Custom output path
uv run python src/ocr_cli.py data/input/brewery.png --output results/my_output.jpg

# Save raw JSON response
uv run python src/ocr_cli.py data/input/brewery.png --json-output data/output/ocr.json
```

### Method 2: Demo Script

```bash
uv run python src/run_overlay_demo.py
```

This processes `data/input/brewery.png` and creates:
- `data/output/brewery_annotated.jpg` (image with bounding boxes)
- Console output with statistics and detected items

---

## CLI Reference

### Basic Usage

```bash
uv run python src/ocr_cli.py <image_path> [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output PATH` | Output path for annotated image | `data/output/<name>_annotated.jpg` |
| `-p, --prompt TEXT` | OCR prompt | `<|grounding|>Convert to markdown` |
| `--no-overlay` | Skip visualization (text only) | False |
| `--json-output PATH` | Save raw JSON response | None |
| `--box-thickness N` | Bounding box line thickness | 2 |
| `--font-size N` | Label font size | 12 |
| `--no-labels` | Hide text labels on boxes | False |
| `--stream` | Stream response (shows progress dots) | False |

### Examples

**1. Basic OCR with overlay**:
```bash
uv run python src/ocr_cli.py data/input/brewery.png
```

**2. With streaming progress (recommended)**:
```bash
uv run python src/ocr_cli.py data/input/brewery.png --stream
```

**3. Text extraction only**:
```bash
uv run python src/ocr_cli.py data/input/brewery.png --no-overlay
```

**4. Custom styling**:
```bash
uv run python src/ocr_cli.py data/input/brewery.png \
    --box-thickness 3 \
    --font-size 14 \
    --output results/styled.jpg
```

**5. Save all outputs with streaming**:
```bash
uv run python src/ocr_cli.py data/input/brewery.png \
    --stream \
    --output data/output/annotated.jpg \
    --json-output data/output/ocr.json
```

---

## Understanding the Output

### Console Output

The CLI shows:
1. **OCR Response Preview**: First 500 characters of extracted text
2. **Statistics**: Total items, text/image counts, average bbox size
3. **Detected Items**: List of first 10 items with positions

Example:
```
📸 Input image: data/input/brewery.png
💾 Output will be saved to: data/output/brewery_annotated.jpg
🔍 Prompt: <|grounding|>Convert the document to markdown

⏳ Running OCR via Ollama (this may take several minutes on CPU)...
   DeepSeek-OCR model processing...
   [Streaming response................] ✓
✅ OCR complete!

================================================================================
OCR RESPONSE PREVIEW (first 500 characters)
================================================================================
Text<|ref|>MAK<|/ref|><|det|>[[120,180,140,200]]<|/det|>
Text<|ref|>MAT<|/ref|><|det|>[[220,180,240,200]]<|/det|>
...
================================================================================

🎨 Creating bounding box overlay...

================================================================================
STATISTICS
================================================================================
Total items detected:    42
  - Text items:          40
  - Image items:         2
Average bbox size:       45.2 × 18.3 pixels
================================================================================

DETECTED ITEMS (first 10):
   1. [Text ] 'MAK' @ [120, 180, 140, 200]
   2. [Text ] 'MAT' @ [220, 180, 240, 200]
   ...

✅ Annotated image saved to: data/output/brewery_annotated.jpg

✅ Done!
```

### Annotated Image Output

The annotated image shows:
- **Red bounding boxes** around detected text/images
- **Labels** showing the extracted text
- **Coordinates** in 1000-bin normalized format (auto-scaled to pixels)

---

## OCR Prompts

DeepSeek-OCR supports different prompts:

### 1. Grounding Mode (with bounding boxes)
```bash
uv run python src/ocr_cli.py data/input/brewery.png \
    --prompt "<|grounding|>Convert the document to markdown"
```

Output format:
```
Text<|ref|>MAK<|/ref|><|det|>[[x1,y1,x2,y2]]<|/det|>
```

### 2. Free OCR (text only, no bounding boxes)
```bash
uv run python src/ocr_cli.py data/input/brewery.png \
    --prompt "Extract all text from this image" \
    --no-overlay
```

### 3. Structured Extraction
```bash
uv run python src/ocr_cli.py data/input/brewery.png \
    --prompt "<|grounding|>Extract all component labels and their coordinates"
```

---

## Performance Tips

### CPU-Only Inference (Current Setup)

**Hardware**: Intel Core i7-1365U (12 cores, no dedicated GPU)

**Expected Performance**:
- Small images (620×345px): **10-20 minutes**
- Medium images (1920×1080px): **30-60 minutes**
- Large images (4K): **1-2 hours**

**Monitor progress**:

Option 1: Use streaming mode (recommended):
```bash
uv run python src/ocr_cli.py data/input/brewery.png --stream
# Shows progress dots as Ollama generates output
```

Option 2: Monitor process in another terminal:
```bash
watch -n 5 "ps aux | grep ollama | grep -v grep"
```

You'll see:
- CPU: 150-200% (using ~2 cores fully)
- Memory: 7-9 GB

### With GPU (Future)

If you add a dedicated GPU:
- **Expected speedup**: 10-50x faster
- **Typical time**: 10-60 seconds per image
- **Requirement**: NVIDIA GPU with CUDA support

To use GPU with Ollama:
```bash
# Ollama automatically uses GPU if available
ollama run deepseek-ocr
```

---

## Troubleshooting

### Issue: "Connection refused" to localhost:11434

**Cause**: Ollama server not running

**Solution**:
```bash
# Start the server
ollama serve
```

Keep this terminal open.

### Issue: "Model not supported by your version"

**Cause**: Ollama version too old

**Solution**: Upgrade to v0.13.2+
```bash
# Download latest
curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o /tmp/ollama
sudo mv /tmp/ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama

# Verify
ollama --version
```

### Issue: "Model 'deepseek-ocr' not found"

**Cause**: Model not downloaded

**Solution**:
```bash
ollama pull deepseek-ocr
```

### Issue: OCR takes too long / hangs

**Causes**:
- CPU-only inference is slow (expected)
- Insufficient memory
- Large image size

**Solutions**:
1. **Be patient**: 10-40 minutes is normal on CPU
2. **Reduce image size**:
   ```bash
   convert data/input/brewery.png -resize 50% data/input/brewery_small.png
   uv run python src/ocr_cli.py data/input/brewery_small.png
   ```
3. **Monitor progress**:
   ```bash
   # Watch CPU/memory usage
   htop
   # Or
   top -p $(pgrep -f "ollama runner")
   ```

### Issue: Process dies unexpectedly

**Causes**:
- Out of memory (OOM killer)
- Timeout
- Model incompatibility

**Solutions**:
1. **Check system logs**:
   ```bash
   journalctl -xe | grep -i oom
   dmesg | grep -i kill
   ```

2. **Increase available memory**: Close other applications

3. **Use cloud alternative**: See `docs/PNID_AGENT_USAGE.md`

---

## Coordinate System

DeepSeek-OCR returns **1000-bin normalized coordinates**:

### Input Format
```
Text<|ref|>MAK<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
```

Where:
- `x1, y1` = top-left corner (range: 0-1000)
- `x2, y2` = bottom-right corner (range: 0-1000)

### Conversion to Pixels

The `ocr_bbox_overlay.py` module automatically converts:

```python
image_width = 620   # pixels
image_height = 345  # pixels

# Scaling factors
scale_x = image_width / 1000.0   # 0.62
scale_y = image_height / 1000.0  # 0.345

# Convert normalized → pixel
pixel_x1 = x1 * scale_x
pixel_y1 = y1 * scale_y
pixel_x2 = x2 * scale_x
pixel_y2 = y2 * scale_y
```

The CLI automatically handles this with `auto_scale_coords=True`.

---

## Comparison: Local vs Cloud

| Feature | Local DeepSeek-OCR | Cloud Models |
|---------|-------------------|--------------|
| **Speed** | 10-40 min (CPU) | 1-3 seconds |
| **Cost** | Free | $0.001-0.01 per image |
| **Privacy** | Full (local) | Data sent to cloud |
| **Offline** | ✅ Yes | ❌ No |
| **Bounding Boxes** | ✅ Yes | ❌ No (most) |
| **Setup** | Complex | Simple (API key) |
| **Quality** | Good | Very Good |

**Recommendation**:
- **For privacy/offline**: Use local OCR
- **For production/speed**: Use cloud (see `src/pnid_agent.py`)

---

## Python API

For programmatic use:

```python
from pathlib import Path
from ollama_deepseel_ocr_fixed import run_deepseek_ocr_via_ollama
from ocr_bbox_overlay import OCRBoundingBoxOverlay

# Read image
image_path = Path("data/input/brewery.png")
image_data = image_path.read_bytes()

# Run OCR
prompt = "<|grounding|>Convert the document to markdown"
ocr_response = run_deepseek_ocr_via_ollama(image_data, prompt, str(image_path))

# Parse and overlay
overlay = OCRBoundingBoxOverlay(font_size=12)
parsed_items = overlay.process_ocr_and_overlay(
    image_path=str(image_path),
    ocr_response=ocr_response,
    output_path="data/output/annotated.jpg",
    auto_scale_coords=True
)

# Get statistics
stats = overlay.get_statistics(parsed_items)
print(f"Found {stats['total_items']} items")
```

---

## Next Steps

After running local OCR:

1. **Compare with cloud models**:
   ```bash
   # Run cloud extraction
   uv run python -m src.pnid_agent data/input/brewery.jpg --provider google
   
   # Compare results
   diff data/output/pnid.json data/output/ocr.json
   ```

2. **Visualize extracted graph**:
   ```bash
   uv run python src/plot_pnid_graph.py
   xdg-open data/output/pnid_graph.html
   ```

3. **Use coordinates for P&ID extraction**: The bounding boxes can help train or validate component position extraction

---

## Related Documentation

- **Main README**: [README.md](../README.md)
- **Cloud P&ID Extraction**: [docs/PNID_AGENT_USAGE.md](PNID_AGENT_USAGE.md)
- **OCR Technical Details**: [docs/README_OCR_BoundingBox.md](README_OCR_BoundingBox.md)
- **Complete Workflows**: [docs/WORKFLOW_AND_COMPARISON.md](WORKFLOW_AND_COMPARISON.md)

---

**Last Updated**: 2025-12-12  
**Ollama Version**: 0.13.2+  
**DeepSeek-OCR Model**: 6.7 GB (latest)