# P&ID Agent Usage Guide

## Overview

The `pnid_agent` module provides a **unified interface** for extracting structured information from Process & Instrumentation Diagrams (P&IDs) using multiple AI providers. It supports:

- **Google Gemini** (via API key or VertexAI)
- **Azure Anthropic Claude**
- **Azure DeepSeek**
- **Anthropic** (direct API)
- **OpenAI**

All providers use the same data models (Component, Pipe, PNID) with spatial coordinates (x, y).

---

## Quick Start

### Python API

```python
from src.pnid_agent import extract_pnid, Provider

# Extract using Google Gemini (default)
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.GOOGLE_GEMINI,
    output_path="data/output/pnid.json"
)

print(f"Components: {len(result['output']['components'])}")
print(f"Pipes: {len(result['output']['pipes'])}")
```

### Command Line

```bash
# Using Google Gemini (default)
uv run python -m src.pnid_agent data/input/brewery.jpg

# Using Azure Anthropic Claude
uv run python -m src.pnid_agent data/input/brewery.jpg \
    --provider azure-anthropic \
    --output data/output/pnid.json

# Using Azure DeepSeek with custom output
uv run python -m src.pnid_agent data/input/brewery.jpg \
    --provider azure-deepseek \
    --output results/brewery_deepseek.json

# See all options
uv run python -m src.pnid_agent --help
```

### Legacy Agent Scripts

The original agent scripts still work but now use the generalized module:

```bash
# Google Gemini
uv run src/gemini_agent.py

# Azure Anthropic
uv run src/azure_antropic_agent.py

# Azure DeepSeek
uv run src/azure_deepseek_agent.py
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with your API keys:

```bash
# Google Gemini
GOOGLE_API_KEY=your_google_api_key_here

# Azure Anthropic
AZURE_ANTROPIC_API_KEY=your_azure_anthropic_key_here
# OR
ANTHROPIC_FOUNDRY_API_KEY=your_foundry_key_here

# Azure DeepSeek
AZURE_OPENAI_API_KEY=your_azure_openai_key_here

# Direct Anthropic API (optional)
ANTHROPIC_API_KEY=your_anthropic_key_here

# OpenAI (optional)
OPENAI_API_KEY=your_openai_key_here
```

**Note**: The `.env` file is gitignored for security.

---

## Supported Providers

### 1. Google Gemini

**Provider**: `Provider.GOOGLE_GEMINI`

**Default Model**: `gemini-2.0-flash-exp`

**Environment Variable**: `GOOGLE_API_KEY`

**Example**:
```python
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.GOOGLE_GEMINI,
    model_name="gemini-2.0-flash-exp"  # Optional override
)
```

**CLI**:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg --provider google
```

---

### 2. Azure Anthropic Claude

**Provider**: `Provider.AZURE_ANTHROPIC`

**Default Model**: `claude-opus-4-5`

**Environment Variables**: `AZURE_ANTROPIC_API_KEY` or `ANTHROPIC_FOUNDRY_API_KEY`

**Endpoint**: `https://aif-minside.services.ai.azure.com/anthropic/`

**Example**:
```python
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.AZURE_ANTHROPIC,
    model_name="claude-opus-4-5"  # Optional override
)
```

**CLI**:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg --provider azure-anthropic
```

---

### 3. Azure DeepSeek

**Provider**: `Provider.AZURE_DEEPSEEK`

**Default Model**: `DeepSeek-V3.1`

**Environment Variable**: `AZURE_OPENAI_API_KEY`

**Endpoint**: `https://aif-minside.cognitiveservices.azure.com/`

**Example**:
```python
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.AZURE_DEEPSEEK,
    model_name="DeepSeek-V3.1"  # Optional override
)
```

**CLI**:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg --provider azure-deepseek
```

---

### 4. Anthropic (Direct API)

**Provider**: `Provider.ANTHROPIC`

**Default Model**: `claude-sonnet-4-5`

**Environment Variable**: `ANTHROPIC_API_KEY`

**Example**:
```python
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.ANTHROPIC,
    model_name="claude-sonnet-4-5"  # Optional override
)
```

**CLI**:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg --provider anthropic
```

---

### 5. OpenAI

**Provider**: `Provider.OPENAI`

**Default Model**: `gpt-5`

**Environment Variable**: `OPENAI_API_KEY`

**Example**:
```python
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.OPENAI,
    model_name="gpt-5"  # Optional override
)
```

**CLI**:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg --provider openai
```

---

## Data Models

### Component

```python
class Component(BaseModel):
    label: str           # Component label (e.g., "MAK", "WOK")
    id: str              # Unique ID (label + number if needed)
    category: str        # Category (e.g., "Vessel", "Heat Exchanger")
    description: str     # Detailed description with parameters
    x: float             # X coordinate of component center (pixels)
    y: float             # Y coordinate of component center (pixels)
```

### Pipe

```python
class Pipe(BaseModel):
    label: str           # Pipe/stream label
    source: str          # Source component ID
    target: str          # Target component ID
    description: str     # Stream properties (temp, composition)
    x: float             # X coordinate of pipe label/midpoint (pixels)
    y: float             # Y coordinate of pipe label/midpoint (pixels)
```

### PNID

```python
class PNID(BaseModel):
    components: list[Component]  # All components in the diagram
    pipes: list[Pipe]            # All pipes/streams
```

---

## Output Format

The `extract_pnid()` function returns a dictionary:

```python
{
    "output": {
        "components": [
            {
                "label": "MAK",
                "id": "MAK-1",
                "category": "Vessel",
                "description": "Mashing vessel for Malt, Corn, Water at 40-78°C",
                "x": 120.5,
                "y": 180.3
            },
            ...
        ],
        "pipes": [
            {
                "label": "Malt",
                "source": "source",
                "target": "MAK-1",
                "description": "Malt stream at ambient temperature",
                "x": 100.0,
                "y": 150.0
            },
            ...
        ]
    },
    "provider": "google",
    "model": "gemini-2.0-flash-exp",
    "image_path": "data/input/brewery.jpg"
}
```

The output is also saved as JSON if `output_path` is specified.

---

## Advanced Usage

### Custom Model Selection

Override the default model for any provider:

```python
# Use a different Gemini model
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.GOOGLE_GEMINI,
    model_name="gemini-1.5-pro"
)

# Use Claude Sonnet instead of Opus
result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.AZURE_ANTHROPIC,
    model_name="claude-sonnet-4-5"
)
```

### Multiple Providers Comparison

```python
from src.pnid_agent import extract_pnid, Provider

providers = [
    Provider.GOOGLE_GEMINI,
    Provider.AZURE_ANTHROPIC,
    Provider.AZURE_DEEPSEEK,
]

for provider in providers:
    result = extract_pnid(
        image_path="data/input/brewery.jpg",
        provider=provider,
        output_path=f"data/output/pnid_{provider.value}.json"
    )
    print(f"{provider.value}: {len(result['output']['components'])} components")
```

### Programmatic Agent Creation

For more control, use `create_agent()` directly:

```python
from src.pnid_agent import create_agent, Provider

agent = create_agent(
    provider=Provider.GOOGLE_GEMINI,
    model_name="gemini-2.0-flash-exp"
)

# Use the agent with custom logic
from pydantic_ai import BinaryContent
with open("data/input/brewery.jpg", "rb") as f:
    image_content = f.read()

binary_content = BinaryContent(data=image_content, media_type="image/jpeg")
result = agent.run_sync([binary_content])
print(result.output.components)
```

---

## Error Handling

The module raises clear exceptions for common issues:

```python
from src.pnid_agent import extract_pnid, Provider

try:
    result = extract_pnid(
        image_path="data/input/brewery.jpg",
        provider=Provider.AZURE_ANTHROPIC
    )
except FileNotFoundError as e:
    print(f"Image not found: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
except ImportError as e:
    print(f"Missing dependency: {e}")
```

**Common Errors**:

1. **Missing API Key**:
   ```
   ValueError: GOOGLE_API_KEY environment variable is required for Google Gemini
   ```
   → Add the key to your `.env` file

2. **Image Not Found**:
   ```
   FileNotFoundError: Image not found: data/input/brewery.jpg
   ```
   → Check the image path

3. **Missing Dependencies**:
   ```
   ImportError: No module named 'anthropic'
   ```
   → Run `uv pip install -e .`

---

## Performance Comparison

Based on testing with the brewery diagram (620×345px):

| Provider | Model | Latency | Cost (est.) | Accuracy |
|----------|-------|---------|-------------|----------|
| Google Gemini | gemini-2.0-flash-exp | ~1-2s | Low | High |
| Azure Anthropic | claude-opus-4-5 | ~2-3s | High | Very High |
| Azure DeepSeek | DeepSeek-V3.1 | ~1s | Very Low | High |
| OpenAI | gpt-5 | ~2s | Medium | High |

**Recommendations**:
- **Best Quality**: Azure Anthropic Claude Opus 4.5
- **Best Speed**: Azure DeepSeek V3.1
- **Best Cost**: Azure DeepSeek V3.1
- **Best Privacy**: Local Ollama DeepSeek-OCR (see `run_overlay_demo.py`)

---

## Troubleshooting

### Issue: "No module named 'pydantic_ai'"

**Solution**: Use `uv` to run scripts:
```bash
uv run python -m src.pnid_agent data/input/brewery.jpg
```

### Issue: "GOOGLE_API_KEY environment variable is required"

**Solution**: Add the API key to `.env`:
```bash
echo "GOOGLE_API_KEY=your_key_here" >> .env
```

### Issue: "Image not found"

**Solution**: Use the correct path relative to project root:
```python
extract_pnid(image_path="data/input/brewery.jpg")  # ✅ Correct
extract_pnid(image_path="brewery.jpg")              # ❌ Wrong
```

### Issue: OAuth2 error with Gemini

**Solution**: The module uses API key authentication (`vertexai=False`), not OAuth2. Ensure `GOOGLE_API_KEY` is set.

---

## Migration from Legacy Scripts

If you were using the old individual agent files, migration is simple:

**Old**:
```python
# In gemini_agent.py
from pydantic_ai.models.google import GoogleModel
model = GoogleModel("gemini-3-pro-preview", provider=provider)
agent = Agent(model, output_type=PNID)
result = agent.run_sync([binary_content])
```

**New**:
```python
from src.pnid_agent import extract_pnid, Provider

result = extract_pnid(
    image_path="data/input/brewery.jpg",
    provider=Provider.GOOGLE_GEMINI
)
```

The legacy scripts (`gemini_agent.py`, `azure_antropic_agent.py`, `azure_deepseek_agent.py`) still work but now use the generalized module internally.

---

## Related Documentation

- **Main README**: [README.md](../README.md)
- **Project Status**: [docs/STATUS_SUMMARY.md](STATUS_SUMMARY.md)
- **Complete Workflows**: [docs/WORKFLOW_AND_COMPARISON.md](WORKFLOW_AND_COMPARISON.md)
- **OCR with Bounding Boxes**: [docs/README_OCR_BoundingBox.md](README_OCR_BoundingBox.md)

---

## Future Enhancements

Planned improvements:

1. **Async Support**: Use `agent.run()` for async execution
2. **Batch Processing**: Process multiple diagrams in parallel
3. **Coordinate Validation**: Verify x/y coordinates are within image bounds
4. **Result Caching**: Cache results to avoid re-processing
5. **Model Fallback**: Auto-retry with different provider if one fails
6. **Streaming**: Stream partial results for large diagrams
7. **Fine-tuning**: Support for custom fine-tuned models

---

**Last Updated**: 2025-12-12  
**Version**: 0.1.0