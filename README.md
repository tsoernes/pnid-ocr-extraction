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

# Install dependencies
pip install -r requirements.txt

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
```

### Basic Usage

```bash
# Run OCR with bounding box overlay
python src/run_overlay_demo.py

# Extract P&ID graph using Gemini
python src/gemini_agent.py

# Generate interactive visualization
python src/plot_pnid_graph.py
```

## 📚 Documentation

- [OCR Bounding Box Guide](README_OCR_BoundingBox.md) - Detailed OCR overlay documentation
- [Technical Details](.rules) - Comprehensive project documentation

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
