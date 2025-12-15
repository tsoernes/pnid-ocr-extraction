# P&ID OCR & Graph Extraction

**Optical Character Recognition and Process & Instrumentation Diagram Analysis**

Extract structured information from P&ID diagrams using local OCR (Ollama + DeepSeek-OCR) and cloud-based AI models (Azure Anthropic, Azure DeepSeek, Google Gemini).

## 🎯 Features

- **OCR with Bounding Boxes**: Extract text with precise location coordinates
- **Local Inference**: Run DeepSeek-OCR locally via Ollama (CPU-only)
- **Cloud AI Integration**: Azure Anthropic Claude, Azure DeepSeek, Google Gemini
- **Graph Extraction**: Convert P&ID diagrams to structured node-edge graphs
- **Interactive Visualization**: Generate interactive HTML network graphs with PyVis
- **Coordinate Auto-Scaling**: Handle DeepSeek's 1000-bin normalized coordinates

## 📁 Project Structure

```
pnid-ocr-extraction/
├── src/                    # Core source code
│   ├── ocr_bbox_overlay.py              # OCR bounding box overlay
│   ├── ollama_deepseel_ocr_fixed.py     # Local Ollama OCR client
│   ├── run_overlay_demo.py              # OCR demo script
│   ├── gemini_agent.py                  # Google Gemini P&ID extraction
│   ├── azure_antropic_agent.py          # Azure Anthropic integration
│   ├── azure_deepseek_agent.py          # Azure DeepSeek integration
│   └── plot_pnid_graph.py               # Interactive graph visualization
├── data/
│   ├── input/              # Source images
│   ├── output/             # Generated outputs
│   └── intermediate/       # Processing intermediates
├── examples/               # Example outputs and data
├── docs/                   # Additional documentation
├── tests/                  # Test scripts
└── .github/workflows/      # CI/CD workflows
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Ollama (for local OCR)
- API keys for cloud services (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/bouvet/pnid-ocr-extraction.git
cd pnid-ocr-extraction

# Install dependencies (using uv - recommended)
uv pip install -e .

# Or using pip
pip install -e .

# Install Ollama (Fedora/RHEL)
sudo dnf install ollama

# OR (macOS)
brew install ollama

# OR (Ubuntu/Debian)
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve &

# Pull DeepSeek-OCR model
ollama pull deepseek-ocr

# Verify installation
python -c "from src.plot_pnid_graph import create_interactive_graph; print('✅ Import successful')"
```

### Basic Usage

```bash
# Run OCR with bounding box overlay
uv run src/run_overlay_demo.py

# Extract P&ID graph using Gemini
uv run src/gemini_agent.py

# Generate interactive visualization
uv run src/plot_pnid_graph.py

# Or using installed environment
python src/plot_pnid_graph.py
```

## 🔍 P&ID Comparison

Two comparison tools are available for different use cases:

### Rule-Based Comparison (Fast, Deterministic)

Compare structural differences with exact counts and IDs:

```bash
# Compare two P&ID files (human-readable output)
python src/compare_pnid_jsonld.py data/output/pnid_base.json data/variations/pnid_var_001.json

# JSON output for programmatic processing
python src/compare_pnid_jsonld.py data/output/pnid_base.json data/variations/pnid_var_001.json --json

# Run comparison demo
./demo_comparison.sh
```

**Features**:
- Instant results (<1 second)
- Missing/added components and connections
- Component attribute changes (type, name)
- Position differences ignored by default
- Works offline, no API required

See **[Comparison Guide](docs/COMPARISON_GUIDE.md)** for detailed usage.

### LLM-Based Comparison (Intelligent, Semantic)

Get engineering insights with GPT-5.1 reasoning:

```bash
# Semantic analysis with impact assessment
python src/compare_pnid_llm.py data/output/pnid_base.json data/variations/pnid_var_001.json

# JSON output with reasoning tokens
python src/compare_pnid_llm.py data/output/pnid_base.json data/variations/pnid_var_001.json --json

# Control reasoning effort (low/medium/high)
python src/compare_pnid_llm.py data/output/pnid_base.json data/variations/pnid_var_001.json --reasoning high
```

**Features**:
- Understands engineering implications
- Process impact assessment
- Equivalence determination with confidence levels
- Actionable recommendations
- Structured output via Pydantic models

**Requirements**: Azure OpenAI API key (set `AZURE_AI_API_KEY` in `.env`)

See **[LLM Comparison Guide](docs/LLM_COMPARISON_GUIDE.md)** for detailed usage.

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) folder:

- **[Documentation Index](docs/README.md)** - Complete guide to all documentation
- **[Status Summary](docs/STATUS_SUMMARY.md)** - Current project status and next steps
- **[Workflow & Comparison](docs/WORKFLOW_AND_COMPARISON.md)** - Complete workflows and model comparison
- **[Comparison Guide](docs/COMPARISON_GUIDE.md)** - Rule-based P&ID comparison tool
- **[LLM Comparison Guide](docs/LLM_COMPARISON_GUIDE.md)** - Intelligent semantic comparison with GPT-5.1
- **[OCR Bounding Box Guide](docs/README_OCR_BoundingBox.md)** - Detailed OCR overlay documentation
- **[Technical Details](.rules)** - Comprehensive repository summary

### Quick Links

- **New to this project?** Start with [Status Summary](docs/STATUS_SUMMARY.md)
- **Want complete workflows?** See [Workflow & Comparison](docs/WORKFLOW_AND_COMPARISON.md)
- **Need technical details?** Check [OCR Bounding Box Guide](docs/README_OCR_BoundingBox.md)

## 🔧 Configuration

Create a `.env` file with your API keys:

```bash
AZURE_ANTROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

TBD - Check with repository owner before commercial use.

## 🏢 Organization

Developed by Bouvet ASA
