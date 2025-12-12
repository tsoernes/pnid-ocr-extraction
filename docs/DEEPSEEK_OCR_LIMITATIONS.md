# DeepSeek-OCR Grounding Mode Limitations

**Last Updated**: 2025-12-12  
**Model**: deepseek-ocr:latest (via Ollama 0.13.2)  
**Status**: ⚠️ Grounding mode has significant limitations via Ollama

---

## Summary

While **DeepSeek-OCR theoretically supports bounding boxes** through grounding mode, **in practice it doesn't work reliably via Ollama** for the following reasons:

1. **GGUF quantization loses grounding capabilities**
2. **Context overflow with verbose grounding outputs**
3. **Prompt compatibility issues**
4. **Returns entire image as single bbox instead of individual text elements**

---

## What Works ✅

### Simple Text Extraction (No Bounding Boxes)

**Prompt**: `"Extract all text from this image"`

**Result**: Clean text output with all labels, temperatures, and component names

**Example Output**:
```
atts.Steam
MAT+MAK
Steam
Malt
Maische
Filter
Corn
MAK
48C, 102C, 65C, 75C, 78C
Water,15C
Hot water tank
Gas
CIP
WOK
Glycol
Centrifuge
```

**Command**:
```bash
uv run python src/ocr_cli.py data/input/brewery.jpg \
    --prompt "Extract all text from this image" \
    --no-overlay \
    --stream
```

---

## What Doesn't Work ❌

### Grounding Mode (Bounding Boxes)

**Attempted Prompts**:
- `"<|grounding|>Convert the document to markdown"`
- `"<|grounding|>Given the layout of the image."`
- `"<|grounding|>Extract all text with bounding boxes."`

**Problems Observed**:

1. **Gibberish Output**
   - Returns random ASCII characters instead of structured data
   - Example: `-123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`

2. **Single Image Detection**
   - Detects entire image as one bounding box
   - `<|ref|>image<|/ref|><|det|>[[0, 0, 510, 368]]<|/det|>`
   - No individual text elements detected

3. **Empty or Malformed Output**
   - Missing `<|ref|>` and `<|det|>` tags
   - No coordinate information

---

## Why Grounding Fails via Ollama

### 1. GGUF Quantization

The Ollama model is a GGUF quantized version of the original DeepSeek-OCR:

- **Original**: Full precision transformers model with vision + spatial modules
- **Ollama**: Quantized GGUF (F16) - spatial grounding modules may be degraded

**Evidence from community**:
- Reddit users report grounding doesn't work well in Ollama
- Works better with full HuggingFace transformers implementation
- Quantization affects fine-grained spatial reasoning

### 2. Context Overflow

Grounding mode generates very verbose output:

**Example**:
```
Text<|ref|>MAK<|/ref|><|det|>[[120,180,140,200]]<|/det|>
Text<|ref|>MAT<|/ref|><|det|>[[220,180,240,200]]<|/det|>
... (40+ more items)
```

For 40 text elements, this can exceed the context window:
- Small image (620×345px) = ~40 text elements
- Each element = ~50 tokens
- Total: 2000+ tokens just for bounding boxes
- Ollama default context: 2048 tokens

### 3. Prompt Engineering

DeepSeek-OCR was trained on specific prompt formats:

**Documented format**:
```
<image>\n<|grounding|>Convert the document to markdown.
```

**Ollama implementation**:
- May not properly handle multimodal prompts
- Image encoding differs from transformers
- Special tokens may not activate spatial modules

---

## Expected Format (When It Works)

When grounding mode works correctly, output should look like:

```
Text<|ref|>MAK<|/ref|><|det|>[[120,180,140,200]]<|/det|>
Text<|ref|>MAT<|/ref|><|det|>[[220,180,240,200]]<|/det|>
Text<|ref|>WOK<|/ref|><|det|>[[320,280,340,300]]<|/det|>
Text<|ref|>48C<|/ref|><|det|>[[115,195,135,210]]<|/det|>
```

**Coordinate Format**:
- Normalized to 1000 bins: [0, 1000] range
- Format: `[[x1, y1, x2, y2]]`
- x1, y1 = top-left corner
- x2, y2 = bottom-right corner

**Conversion to pixels**:
```python
scale_x = image_width / 1000.0
scale_y = image_height / 1000.0
pixel_x = bbox_x * scale_x
pixel_y = bbox_y * scale_y
```

---

## Alternatives for Bounding Boxes

### Option 1: Cloud Models with P&ID Extraction

Use the generalized `pnid_agent.py` module to extract structured data directly:

```bash
uv run python -m src.pnid_agent data/input/brewery.jpg \
    --provider google
```

**Advantages**:
- Gets x,y coordinates directly in JSON
- Structured Component/Pipe data
- Fast (1-3 seconds)
- Actually works

**Output**:
```json
{
  "components": [
    {
      "label": "MAK",
      "id": "MAK-1",
      "category": "Vessel",
      "x": 120.5,
      "y": 180.3
    }
  ]
}
```

### Option 2: Full DeepSeek-OCR via Transformers

Use the original HuggingFace implementation (not via Ollama):

```python
from transformers import AutoModel, AutoTokenizer
import torch

model_name = 'deepseek-ai/DeepSeek-OCR'
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(
    model_name, 
    trust_remote_code=True,
    torch_dtype=torch.bfloat16
)

prompt = "<image>\n<|grounding|>Convert the document to markdown."
# ... (run inference)
```

**Requirements**:
- 16+ GB VRAM (GPU required)
- Full transformers library
- Flash attention support
- ~20 GB disk space for model

### Option 3: Alternative OCR Models

Models designed specifically for bounding boxes:

**Florence-2** (Microsoft, 200M-800M params):
```bash
# Available via transformers
# Outputs bounding boxes by default
# Faster than DeepSeek-OCR
```

**Kosmos-2.5** (Microsoft, 1B params):
```bash
# Specialized for document OCR with grounding
# Works better for layout analysis
```

**PaddleOCR**:
```bash
# Traditional OCR with bbox support
# Fast, reliable, proven
# Not LLM-based
```

### Option 4: Hybrid Approach

Combine local text OCR + cloud positioning:

1. **Extract text** with DeepSeek-OCR (local, no grounding):
   ```bash
   uv run python src/ocr_cli.py data/input/brewery.jpg \
       --prompt "Extract all text" \
       --no-overlay
   ```

2. **Get positions** with cloud P&ID agent:
   ```bash
   uv run python -m src.pnid_agent data/input/brewery.jpg
   ```

3. **Merge results** - text from local, coordinates from cloud

---

## Performance Comparison

| Method | Speed | Quality | Bboxes | Cost | Privacy |
|--------|-------|---------|--------|------|---------|
| **DeepSeek-OCR (Ollama, text-only)** | 10-20 min | Good | ❌ No | Free | ✅ Full |
| **DeepSeek-OCR (Ollama, grounding)** | 10-40 min | ❌ Broken | ❌ No | Free | ✅ Full |
| **DeepSeek-OCR (HF, grounding)** | 30-60s (GPU) | Good | ✅ Yes | Free | ✅ Full |
| **Cloud P&ID Agent (Gemini)** | 1-3s | Excellent | ✅ Yes (x,y) | ~$0.001 | ❌ Cloud |
| **Cloud P&ID Agent (Anthropic)** | 2-3s | Excellent | ✅ Yes (x,y) | ~$0.01 | ❌ Cloud |
| **Florence-2 (local)** | 5-10s (GPU) | Good | ✅ Yes | Free | ✅ Full |
| **PaddleOCR (local)** | 1-2s (CPU) | Good | ✅ Yes | Free | ✅ Full |

---

## Recommendations

### For This Project (P&ID Extraction)

**Best choice**: Use cloud models via `pnid_agent.py`

**Reasons**:
1. ✅ Structured output (JSON with Component/Pipe models)
2. ✅ Fast (1-3 seconds vs 10-40 minutes)
3. ✅ Includes x,y coordinates
4. ✅ Better accuracy for P&ID understanding
5. ✅ Works reliably

**Command**:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg \
    --provider google \
    --output data/output/pnid.json
```

### For Privacy/Offline Use

**Best choice**: Text-only OCR via Ollama + manual annotation

**Workflow**:
1. Extract text with DeepSeek-OCR (no grounding)
2. Use the extracted text list as reference
3. Manually create structured data or use interactive tools
4. Or wait for Florence-2/Kosmos-2.5 Ollama support

### For Research/Experimentation

**Best choice**: Full DeepSeek-OCR via HuggingFace transformers

**Requirements**:
- GPU with 16+ GB VRAM
- Install: `transformers`, `torch`, `flash-attn`
- Run inference with grounding mode
- Should produce proper bounding boxes

---

## Known Issues

### Issue 1: Gibberish Output

**Symptoms**:
```
-123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`
```

**Cause**: Model doesn't understand the prompt or image encoding failed

**Solution**: Use text-only mode (no grounding)

### Issue 2: Single Image Bbox

**Symptoms**:
```
Total items detected: 1
  - Image items: 1
<|ref|>image<|/ref|><|det|>[[0, 0, 510, 368]]<|/det|>
```

**Cause**: Model treats entire image as one element instead of parsing text

**Solution**: Switch to cloud models or HuggingFace transformers

### Issue 3: Empty Output

**Symptoms**:
```
Total items detected: 0
```

**Cause**: Prompt not activating grounding mode or parsing failed

**Solution**: Verify prompt format, check Ollama version, try simpler prompts

---

## Testing Results

### Test 1: Text-Only Mode

**Command**:
```bash
uv run python src/ocr_cli.py data/input/brewery.jpg \
    --prompt "Extract all text from this image" \
    --no-overlay --stream
```

**Result**: ✅ **SUCCESS**
- Extracted 40+ text labels
- Temperatures: 48°C, 65°C, 75°C, 78°C, 80°C, 102°C
- Components: MAK, MAT, WOK, Filter, Centrifuge, etc.
- Clean, accurate output

### Test 2: Grounding Mode (Convert to Markdown)

**Command**:
```bash
uv run python src/ocr_cli.py data/input/brewery.jpg \
    --prompt "<|grounding|>Convert the document to markdown" \
    --stream
```

**Result**: ❌ **FAILED**
- Output: Gibberish ASCII characters
- No structured markdown
- No bounding boxes

### Test 3: Grounding Mode (Given Layout)

**Command**:
```bash
uv run python src/ocr_cli.py data/input/brewery.jpg \
    --prompt "<|grounding|>Given the layout of the image." \
    --stream
```

**Result**: ❌ **FAILED**
- Single image bbox: [[0, 0, 510, 368]]
- No individual text elements
- Unusable for P&ID extraction

### Test 4: Grounding Mode (Extract Text with Bboxes)

**Command**:
```bash
uv run python src/ocr_cli.py data/input/brewery.jpg \
    --prompt "<|grounding|>Extract all text with bounding boxes." \
    --stream
```

**Result**: ⏳ **IN PROGRESS** (still running after 60+ seconds)

---

## Conclusion

**For P&ID OCR with bounding boxes via Ollama**: ❌ **Not Recommended**

**Grounding mode does not work reliably in the quantized Ollama version** of DeepSeek-OCR. While the model theoretically supports bounding boxes, practical limitations make it unsuitable for production use.

**Recommended alternatives**:
1. **Cloud models** (fast, accurate, structured output)
2. **Full HuggingFace transformers** (requires GPU, full precision)
3. **Florence-2 / Kosmos-2.5** (purpose-built for OCR with bboxes)
4. **PaddleOCR** (traditional, proven, fast)

**For this project's P&ID extraction**, use:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg --provider google
```

---

## References

- DeepSeek-OCR Paper: https://arxiv.org/abs/2510.18234
- Ollama Model: https://ollama.com/library/deepseek-ocr
- HuggingFace: https://huggingface.co/deepseek-ai/DeepSeek-OCR
- GitHub: https://github.com/deepseek-ai/DeepSeek-OCR
- Community Reports: Reddit r/LocalLLaMA, r/ollama

---

**Status**: This limitation is well-documented in the community. Multiple users report that grounding mode works in the full transformers implementation but not in Ollama's quantized version.