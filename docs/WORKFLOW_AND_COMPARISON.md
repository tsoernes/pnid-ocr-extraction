# P&ID OCR & Extraction - Complete Workflow & Model Comparison Guide

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [System Requirements & Setup](#system-requirements--setup)
3. [Complete Workflow](#complete-workflow)
4. [Model Comparison](#model-comparison)
5. [Current Status & Limitations](#current-status--limitations)
6. [Troubleshooting](#troubleshooting)
7. [Next Steps](#next-steps)

---

## 📊 Project Overview

This project provides tools for extracting structured information from Process & Instrumentation Diagrams (P&IDs) using multiple AI approaches:

- **Local OCR**: DeepSeek-OCR via Ollama (with bounding box coordinates)
- **Cloud AI**: Google Gemini, Azure Anthropic Claude, Azure DeepSeek
- **Visualization**: Interactive PyVis network graphs with background images

**Test Image**: `data/input/brewary.png` - Brewery mashing process diagram (620×345 pixels)

**Updated Data Models** (as of latest commit):
- `Component`: Added `x`, `y` coordinates for spatial positioning
- `Pipe`: Added `x`, `y` coordinates for label/midpoint positioning

---

## 🔧 System Requirements & Setup

### Hardware
- **CPU**: Intel Core i7-1365U (12 cores) - Used for Ollama inference
- **RAM**: 30.9 GiB available (minimum 12 GB recommended for DeepSeek-OCR)
- **GPU**: Intel Iris Xe Graphics (integrated, no GPU acceleration)
- **OS**: Fedora Linux 42, KDE Plasma Wayland

### Software Dependencies

#### 1. Install System Packages
```bash
# Install Ollama (for local OCR)
sudo dnf install ollama

# Verify installation
ollama --version
```

#### 2. Install Python Dependencies
```bash
# Using UV (recommended) - editable install
uv pip install -e .

# Or using pip
pip install -e .

# Verify installation
python -c "from src.plot_pnid_graph import create_interactive_graph; print('✅ Install successful')"
```

**Requirements:** (defined in `pyproject.toml`)
```toml
dependencies = [
    "Pillow>=9.0.0",
    "requests>=2.25.0",
    "pydantic-ai",
    "python-dotenv",
    "pyvis>=0.3.0",
    "networkx>=3.0",
    "anthropic",
]
```

#### 3. Setup Ollama & DeepSeek-OCR

```bash
# Start Ollama server (run in background)
ollama serve &

# Pull DeepSeek-OCR model (6.7 GB download)
ollama pull deepseek-ocr

# Verify model is available
ollama list | grep deepseek-ocr
```

**Expected Output:**
```
deepseek-ocr:latest    0e7b018b8a22    6.7 GB    X minutes ago
```

#### 4. Configure API Keys (Optional - for cloud models)

Create `.env` file in project root:

```bash
# Google Gemini (requires OAuth2 for VertexAI)
GOOGLE_API_KEY=your_google_api_key

# Azure Anthropic Claude
AZURE_ANTROPIC_API_KEY=your_azure_anthropic_key
ANTHROPIC_FOUNDRY_API_KEY=your_azure_anthropic_key

# Azure DeepSeek
AZURE_OPENAI_API_KEY=your_azure_openai_key
```

---

## 🚀 Complete Workflow

### Workflow 1: Local OCR with Bounding Box Visualization

**Purpose**: Extract text with spatial coordinates and overlay bounding boxes on the original image.

**Steps:**

1. **Ensure Ollama is running:**
   ```bash
   pgrep -a ollama || ollama serve &
   ```

2. **Run the OCR + Overlay demo:**
   ```bash
   # Using uv (recommended)
   uv run src/run_overlay_demo.py
   
   # Or using installed environment
   python src/run_overlay_demo.py
   ```

3. **Expected Output:**
   - Console: OCR statistics (text/image items, bbox dimensions)
   - File: `data/output/brewary_annotated.jpg` (image with colored bboxes)

**⚠️ Current Status: BLOCKED**

**Issue**: Ollama version 0.4.4 does not support DeepSeek-OCR model
```
Error: "llama runner process has terminated: this model is not supported 
by your version of Ollama. You may need to upgrade"
```

**Solution Required**: Upgrade Ollama to latest version (requires sudo access)

---

### Workflow 2: P&ID Graph Extraction with Cloud AI

**Purpose**: Extract structured component and pipe data using multimodal LLMs.

#### Option A: Google Gemini (VertexAI)

**Status**: ⚠️ Requires OAuth2 setup (API key not supported)

```bash
uv run src/gemini_agent.py
```

**Error:**
```
401 UNAUTHENTICATED: API keys are not supported by this API. 
Expected OAuth2 access token
```

**Requirements:**
- Google Cloud Project with VertexAI enabled
- OAuth2 credentials (not simple API key)
- `GOOGLE_API_KEY` in `.env` (currently not sufficient)

#### Option B: Azure Anthropic Claude Opus 4.5

**Status**: ⚠️ Requires API key configuration

```bash
uv run src/azure_antropic_agent.py
```

**Requirements:**
- Azure AI Foundry account
- Endpoint: `https://aif-minside.services.ai.azure.com/anthropic/`
- Environment variable: `AZURE_ANTROPIC_API_KEY` or `ANTHROPIC_FOUNDRY_API_KEY`

**Model**: `claude-opus-4-5`

#### Option C: Azure DeepSeek V3.1

**Status**: ⚠️ Requires API key configuration

```bash
uv run src/azure_deepseek_agent.py
```

**Requirements:**
- Azure Cognitive Services account
- Endpoint: `https://aif-minside.cognitiveservices.azure.com/`
- Environment variable: `AZURE_OPENAI_API_KEY`

**Model**: `DeepSeek-V3.1`

---

### Workflow 3: Interactive Visualization

**Purpose**: Generate interactive HTML graph from extracted P&ID data.

**Prerequisites**: P&ID JSON file (e.g., from previous Gemini extraction)

**Steps:**

1. **Run visualization script:**
   ```bash
   uv run src/plot_pnid_graph.py
   ```

2. **Output:**
   - File: `data/output/pnid_graph.html`
   - Interactive features:
     - Drag nodes to reposition
     - Scroll to zoom
     - Hover for component details
     - Toggle physics simulation
     - Adjust background opacity

3. **Open in browser:**
   ```bash
   xdg-open data/output/pnid_graph.html
   ```

**✅ Current Status: WORKING**

Successfully generates visualization from existing `data/output/pnid.json` (14 components, 33 pipes).

---

## 📊 Model Comparison

### Feature Matrix

| Feature | DeepSeek-OCR (Ollama) | Google Gemini | Azure Claude | Azure DeepSeek |
|---------|----------------------|---------------|--------------|----------------|
| **Status** | ⚠️ Blocked (version issue) | ⚠️ OAuth2 required | ⚠️ API key needed | ⚠️ API key needed |
| **Deployment** | Local (CPU-only) | Cloud | Cloud | Cloud |
| **Cost** | Free | Pay-per-token | Pay-per-token | Pay-per-token |
| **Latency** | 2-5s (CPU inference) | <2s (typical) | <2s (typical) | <1s (typical) |
| **Privacy** | Full (local) | Data sent to Google | Data sent to Azure | Data sent to Azure |
| **Bounding Boxes** | ✅ Yes (1000-bin coords) | ❌ No | ❌ No | ❌ No |
| **Structured Output** | ❌ Manual parsing | ✅ Pydantic models | ✅ Pydantic models | ✅ Pydantic models |
| **Spatial Coords** | ✅ Via bbox coords | ✅ (new x,y fields) | ✅ (new x,y fields) | ✅ (new x,y fields) |
| **Model Size** | 6.7 GB | N/A (cloud) | N/A (cloud) | N/A (cloud) |
| **Setup Complexity** | Medium | High (OAuth2) | Medium | Medium |
| **Offline Capable** | ✅ Yes | ❌ No | ❌ No | ❌ No |

### Performance Characteristics

#### DeepSeek-OCR (Local via Ollama)

**Strengths:**
- ✅ Bounding box coordinates (unique feature)
- ✅ Completely offline
- ✅ No per-request costs
- ✅ Full privacy/security
- ✅ 1000-bin normalized coordinates (resolution-independent)

**Weaknesses:**
- ❌ Requires Ollama version upgrade
- ❌ CPU-only inference (slow on Intel iGPU)
- ❌ Large model download (6.7 GB)
- ❌ Requires manual response parsing
- ❌ No GPU acceleration on Intel integrated graphics
- ❌ Manual structure extraction (no Pydantic)

**Best For:**
- OCR with precise text localization
- Offline/airgapped environments
- Privacy-sensitive applications
- Debugging bbox overlay systems

#### Google Gemini 3 Pro Preview

**Strengths:**
- ✅ Excellent multimodal understanding
- ✅ Structured output via Pydantic
- ✅ Low latency
- ✅ Strong reasoning on complex diagrams

**Weaknesses:**
- ❌ Requires OAuth2 (complex setup)
- ❌ VertexAI dependencies
- ❌ No bounding box coordinates
- ❌ Cloud-only

**Best For:**
- Complex P&ID analysis
- When OAuth2 setup is available
- Production applications with GCP infrastructure

#### Azure Anthropic Claude Opus 4.5

**Strengths:**
- ✅ Excellent reasoning and analysis
- ✅ Structured output via Pydantic
- ✅ Azure integration
- ✅ Strong vision capabilities

**Weaknesses:**
- ❌ Requires Azure subscription
- ❌ No bounding box coordinates
- ❌ Higher cost per token
- ❌ Cloud-only

**Best For:**
- Enterprise Azure environments
- High-quality analysis requirements
- Complex reasoning tasks

#### Azure DeepSeek V3.1

**Strengths:**
- ✅ Very fast inference
- ✅ Lower cost than Claude/Gemini
- ✅ Structured output via Pydantic
- ✅ OpenAI-compatible API

**Weaknesses:**
- ❌ Requires Azure subscription
- ❌ No bounding box coordinates
- ❌ Less mature than Claude/Gemini
- ❌ Cloud-only

**Best For:**
- Cost-sensitive applications
- High-throughput processing
- When OpenAI compatibility is desired

---

## 🔍 Data Model Updates

### New Fields (Added in latest commit)

Both `Component` and `Pipe` models now include spatial coordinates:

```python
class Component(BaseModel):
    label: str = Field(description="The label of the component")
    id: str = Field(description="The id of the component")
    category: str = Field(description="The category of the component")
    description: str = Field(description="The description of the component")
    x: float = Field(description="The x coordinate of the component center")  # NEW
    y: float = Field(description="The y coordinate of the component center")  # NEW

class Pipe(BaseModel):
    label: str = Field(description="The label of the pipe")
    source: str = Field(description="The id of the source component")
    target: str = Field(description="The id of the target component")
    description: str = Field(description="The description of the pipe")
    x: float = Field(description="The x coordinate of the pipe label/midpoint")  # NEW
    y: float = Field(description="The y coordinate of the pipe label/midpoint")  # NEW
```

### Coordinate Systems

**DeepSeek-OCR (1000-bin normalized):**
- Range: [0, 1000] for both x and y
- Resolution-independent
- Requires scaling to actual pixel dimensions:
  ```python
  scale_x = image_width / 1000.0
  scale_y = image_height / 1000.0
  pixel_x = bbox_x * scale_x
  pixel_y = bbox_y * scale_y
  ```

**Gemini/Claude/DeepSeek (pixel coordinates):**
- Range: [0, image_width] for x, [0, image_height] for y
- Direct pixel positions
- Image-specific (not normalized)

---

## ⚠️ Current Status & Limitations

### What's Working ✅

1. **Data Models**: Updated with x,y coordinates
2. **Visualization**: Interactive graph generation from JSON
3. **Dependencies**: All Python packages installed
4. **Ollama Server**: Running and DeepSeek-OCR model downloaded
5. **Project Structure**: Organized and documented

### What's Blocked ⚠️

1. **Local OCR**: 
   - Ollama version 0.4.4 incompatible with DeepSeek-OCR
   - Needs upgrade (requires sudo access)

2. **Cloud Models**:
   - **Gemini**: Requires OAuth2 (not simple API key)
   - **Azure Anthropic**: Needs API key in `.env`
   - **Azure DeepSeek**: Needs API key in `.env`

3. **No Current Extraction**:
   - Can't test updated x,y coordinate extraction
   - Existing `pnid.json` lacks spatial data (old model)

### Known Issues

1. **ROCm Packages**: Already removed (no AMD GPU)
2. **Path Issues**: Fixed in `plot_pnid_graph.py` (uses `parent.parent`)
3. **Import Errors**: Fixed (removed unused `AzureModel` import)
4. **Exit Call**: Removed from `gemini_agent.py`

---

## 🔧 Troubleshooting

### Ollama Version Check

```bash
# Check installed version
ollama --version
dnf info ollama | grep Version

# Expected: 0.4.4 (INCOMPATIBLE)
# Required: Latest (check Ollama GitHub releases)
```

### Upgrade Ollama (Requires Sudo)

```bash
# Method 1: DNF upgrade
sudo dnf upgrade ollama -y

# Method 2: Download latest from GitHub
# Visit: https://github.com/ollama/ollama/releases
curl -fsSL https://ollama.com/install.sh | sh

# Restart server
pkill ollama
ollama serve &

# Verify
ollama list
```

### API Key Configuration

```bash
# Check if .env exists
test -f .env && echo "✅ .env exists" || echo "❌ .env missing"

# Create .env template
cat > .env << 'EOF'
# Google Gemini (VertexAI)
GOOGLE_API_KEY=your_key_here

# Azure Anthropic
AZURE_ANTROPIC_API_KEY=your_key_here
ANTHROPIC_FOUNDRY_API_KEY=your_key_here

# Azure DeepSeek
AZURE_OPENAI_API_KEY=your_key_here
EOF

echo "✅ .env template created - update with real keys"
```

### Test Individual Components

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test Python environment
~/.venv/bin/python3 -c "from PIL import Image; print('✅ Pillow works')"

# Test visualization (with existing data)
~/.venv/bin/python3 src/plot_pnid_graph.py
```

---

## 📈 Next Steps

### Immediate (Unblocked by API keys)

1. **Configure Cloud API Keys**:
   - Choose one provider (Azure Anthropic recommended for quality)
   - Add API key to `.env`
   - Test extraction with updated x,y fields

2. **Run Full Extraction**:
   ```bash
   # Example with Azure Anthropic (once configured)
   uv run src/azure_antropic_agent.py
   ```

3. **Verify Spatial Coordinates**:
   - Check output JSON has `x` and `y` fields
   - Validate coordinate ranges
   - Compare accuracy across models

4. **Update Visualization**:
   - Modify `plot_pnid_graph.py` to use x,y coordinates
   - Position nodes at extracted locations (not random)
   - Compare against original image

### Medium-term (Requires Ollama Upgrade)

1. **Upgrade Ollama**: Request sudo access or install user-local version

2. **Test Local OCR**:
   ```bash
   uv run src/run_overlay_demo.py
   ```

3. **Compare Bbox vs. Structured Coords**:
   - DeepSeek bbox coordinates
   - Gemini/Claude extracted x,y positions
   - Accuracy comparison

4. **Hybrid Approach**:
   - Use DeepSeek for text + bbox
   - Use Claude for structure + semantics
   - Merge results for best accuracy

### Long-term Enhancements

1. **Batch Processing**: Process multiple diagrams

2. **Coordinate Validation**:
   - Cross-reference bbox and structured coords
   - Detect outliers/errors
   - Confidence scoring

3. **Auto-positioning**:
   - Use extracted coords to auto-layout graph
   - Overlay on original image
   - Interactive editing

4. **Model Benchmarking**:
   - Precision/recall metrics
   - Speed comparison
   - Cost analysis
   - Accuracy scoring

5. **Export Formats**:
   - AutoCAD DXF
   - Visio XML
   - GraphML
   - Neo4j import

---

## 📝 Example Outputs

### Existing Data (from old model without x,y coords)

**Components**: 14 total
- 4 Vessels (MAK, MAT, MAT_MAK, WOK, HWT, Mixer)
- 5 Heat Exchangers (various steam heaters, main cooler, glycol HE)
- 2 Separators (Filter, Centrifuge)

**Pipes**: 33 total
- Temperature ranges: 10°C to 102°C
- Stream types: Malt, Corn, Water, Steam, Wort, Dreche (waste)

**Visualization**: `data/output/pnid_graph.html`
- Interactive drag-and-drop nodes
- Color-coded by category
- Background image overlay
- Tooltips with descriptions

### Expected Output (with updated model)

```json
{
  "components": [
    {
      "label": "MAK",
      "id": "MAK",
      "category": "Vessel",
      "description": "Mashing vessel for Malt, Corn and Water",
      "x": 120.5,
      "y": 180.3
    }
  ],
  "pipes": [
    {
      "label": "48°C",
      "source": "MAK",
      "target": "HE_MAK",
      "description": "Output from MAK to heater",
      "x": 250.7,
      "y": 190.2
    }
  ]
}
```

---

## 🔗 Related Documentation

- **OCR Bounding Box Guide**: `README_OCR_BoundingBox.md`
- **Project Rules**: `.rules` (comprehensive repo summary)
- **Requirements**: `requirements.txt`
- **Main README**: `README.md` (if exists)

---

## 📞 Support & Contributions

**Current Blockers**:
1. Ollama upgrade required (sudo access)
2. Cloud API keys needed for testing
3. OAuth2 setup for Gemini (complex)

**Recommended Path Forward**:
1. ✅ Configure Azure Anthropic (simplest cloud option)
2. ✅ Test extraction with x,y coordinates
3. ✅ Update visualization to use spatial data
4. ⏳ Upgrade Ollama when possible
5. ⏳ Compare all models with benchmarks

---

**Last Updated**: 2025-12-11  
**Status**: Ready for cloud API testing, blocked on local OCR  
**Git Commit**: Latest changes include x,y coordinate fields in data models