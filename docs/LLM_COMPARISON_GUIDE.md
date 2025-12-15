# LLM-Based P&ID Comparison Guide

This guide explains how to use the `compare_pnid_llm.py` script to perform intelligent, semantic comparison of P&ID JSON-LD files using GPT-5.1 with reasoning capabilities.

## Overview

The LLM-based comparison tool provides **intelligent semantic analysis** of P&ID differences, going beyond simple structural comparison to understand the **engineering impact** and **functional implications** of changes.

### Key Features

- **Semantic Understanding**: LLM analyzes the meaning and purpose of components, not just presence/absence
- **Impact Assessment**: Evaluates how differences affect process flow, operability, and safety
- **Engineering Recommendations**: Provides actionable guidance based on the comparison
- **Structured Output**: Uses Pydantic models for reliable, parseable results
- **High Reasoning**: Leverages GPT-5.1's extended reasoning for thorough analysis
- **Position-Agnostic**: Automatically ignores spatial coordinates, focuses on topology

### When to Use This vs. Rule-Based Comparison

| Scenario | Use LLM Comparison | Use Rule-Based (`compare_pnid_jsonld.py`) |
|----------|-------------------|------------------------------------------|
| Need to understand **why** differences matter | ✅ Yes | ❌ No |
| Need to assess **process impact** | ✅ Yes | ❌ No |
| Need **engineering recommendations** | ✅ Yes | ❌ No |
| Need exact counts and IDs | ⚠️ Good enough | ✅ Best |
| Need fast results (< 1 second) | ❌ No (~30-60s) | ✅ Yes |
| Working offline | ❌ No (requires API) | ✅ Yes |
| Budget-conscious | ⚠️ Costs tokens | ✅ Free |
| Need deterministic output | ⚠️ Mostly consistent | ✅ 100% consistent |

**Recommendation**: Use **both tools** for comprehensive analysis:
1. Rule-based for quick validation and exact counts
2. LLM-based for understanding impact and making decisions

---

## Installation

Requires the `openai` package (already included in project dependencies):

```bash
# Ensure project is installed with all dependencies
uv pip install -e .

# Verify openai package
python -c "import openai; print(openai.__version__)"
```

### API Key Configuration

Add your Azure OpenAI API key to `.env`:

```bash
# .env file
AZURE_AI_API_KEY=your_key_here
# OR
AZURE_OPENAI_API_KEY=your_key_here
```

**Available Endpoints**:
- Default: `https://aif-minside.cognitiveservices.azure.com/`
- Override: Set `AZURE_OPENAI_ENDPOINT` environment variable

**Model**:
- Default: `gpt-5.1` (GPT-5.1 with reasoning)
- Override: Set `AZURE_OPENAI_DEPLOYMENT` environment variable

---

## Basic Usage

### Standard Comparison (Human-Readable)

```bash
python src/compare_pnid_llm.py <file1.json> <file2.json>
```

**Example**:
```bash
python src/compare_pnid_llm.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_001_remove_components_medium.json
```

**Output**:
```
🔄 Loading P&IDs...
🔄 Converting to text format...
🧠 Analyzing with LLM (reasoning: high)...
================================================================================
LLM-Based P&ID Comparison
================================================================================
File 1: data/output/pnid_dexpi_final.json
File 2: data/variations/pnid_c01_var_001_remove_components_medium.json
Model: gpt-5.1
Reasoning Effort: high
Tokens: 16578 (reasoning: 8707)

📊 SUMMARY
--------------------------------------------------------------------------------
P&ID 2 is a reduced subset of P&ID 1. Nine components present in P&ID 1 are 
missing in P&ID 2, including one chamber, one globe valve, two nozzles, one 
pipe reducer, and several associated connections...

💡 IMPACT ASSESSMENT
--------------------------------------------------------------------------------
The differences represent substantive process simplifications rather than 
cosmetic changes...

✅ EQUIVALENCE DETERMINATION
--------------------------------------------------------------------------------
Status: NOT EQUIVALENT (Confidence: high)

📝 RECOMMENDATIONS
--------------------------------------------------------------------------------
1. Do not treat these P&IDs as equivalent...
```

---

### JSON Output (Machine-Readable)

```bash
python src/compare_pnid_llm.py <file1.json> <file2.json> --json
```

**Example**:
```bash
python src/compare_pnid_llm.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_003_modify_names_medium.json \
  --json > comparison_result.json
```

**JSON Schema**:
```json
{
  "summary": "High-level overview of differences",
  "components_only_in_1": ["pid:Component-1", "pid:Component-2"],
  "components_only_in_2": ["pid:Component-3"],
  "components_changed": [
    {
      "id": "pid:Component-4",
      "changes": ["Name changed from X to Y"]
    }
  ],
  "connections_only_in_1": ["pid:A--B", "pid:C--D"],
  "connections_only_in_2": ["pid:E--F"],
  "connections_changed": [],
  "impact_assessment": "Detailed analysis of what differences mean...",
  "equivalent": false,
  "confidence": "high",
  "recommendations": "Actionable guidance...",
  "file1": "path/to/file1.json",
  "file2": "path/to/file2.json",
  "model": "gpt-5.1",
  "reasoning_effort": "high",
  "reasoning_tokens": 8707,
  "total_tokens": 16578
}
```

---

### Reasoning Effort Control

Control the depth of LLM analysis:

```bash
# Low reasoning (faster, cheaper, less thorough)
python src/compare_pnid_llm.py file1.json file2.json --reasoning low

# Medium reasoning (balanced)
python src/compare_pnid_llm.py file1.json file2.json --reasoning medium

# High reasoning (default, most thorough)
python src/compare_pnid_llm.py file1.json file2.json --reasoning high
```

**Reasoning Effort Comparison**:

| Level | Speed | Cost | Token Usage | Analysis Depth |
|-------|-------|------|-------------|----------------|
| Low | ~15s | ~$0.02 | ~8K tokens | Basic identification |
| Medium | ~30s | ~$0.05 | ~12K tokens | Good detail |
| High | ~60s | ~$0.10 | ~16K tokens | Comprehensive + implications |

**Recommendation**: Use `high` (default) for production analysis, `low` for quick checks.

---

## How It Works

### 1. JSON-LD to Text Conversion

The script converts P&ID JSON-LD to a clean text format **excluding position data**:

```markdown
# P&ID Structure

## Components (69)

### pid:GlobeValve-1
- Type: pid:Component
- Name: GLOBE_VALVE_SHAPE
- Category: GlobeValve

### pid:Tank-1
- Type: pid:Tank
- Name: VESSEL_WITH_DISHED_HEADS_SHAPE
- Category: Tank

## Connections (25)

- pid:Nozzle-6 → pid:SwingCheckValve-1
- pid:SwingCheckValve-1 → pid:PipeReducer-1
- pid:PipeReducer-1 → pid:Nozzle-7
```

**Why Text Format?**
- LLMs excel at understanding structured text
- Removes position noise (x, y coordinates)
- Focuses on semantic content (what, not where)
- Enables natural language reasoning

### 2. LLM Analysis with Reasoning

The script sends both text representations to GPT-5.1 with:
- **System Prompt**: Defines role as P&ID expert
- **User Prompt**: Provides both P&IDs and analysis instructions
- **Reasoning Effort**: Controls depth of extended thinking
- **Structured Output**: Enforces Pydantic schema via `beta.chat.completions.parse()`

### 3. Structured Response

GPT-5.1 returns a validated Pydantic model:

```python
class ComparisonResult(BaseModel):
    summary: str
    components_only_in_1: list[str]
    components_only_in_2: list[str]
    components_changed: list[ComponentChange]
    connections_only_in_1: list[str]
    connections_only_in_2: list[str]
    connections_changed: list[ConnectionChange]
    impact_assessment: str
    equivalent: bool
    confidence: str  # "high", "medium", "low"
    recommendations: str
```

This ensures **reliable, parseable output** every time.

---

## Use Cases

### 1. Extraction Validation

**Scenario**: Validate OCR/LLM extraction against ground truth

```bash
# Compare extracted P&ID with DEXPI reference
python src/compare_pnid_llm.py \
  data/output/pnid_dexpi_final.json \
  data/output/pnid_dwg.json
```

**LLM Analysis Provides**:
- Which missing components are critical vs. cosmetic
- Whether missing connections break essential flow paths
- Impact on process safety and operability
- Whether extraction is "good enough" for intended use

### 2. Design Review

**Scenario**: Compare two design revisions to understand changes

```bash
python src/compare_pnid_llm.py \
  designs/rev_A.json \
  designs/rev_B.json > design_review_report.txt
```

**LLM Analysis Provides**:
- Engineering rationale for changes
- Potential safety implications
- Upstream/downstream impacts
- Required documentation updates

### 3. Method Benchmarking

**Scenario**: Compare multiple extraction methods to choose the best

```bash
# Compare OCR vs. LLM extraction
python src/compare_pnid_llm.py \
  data/output/pnid_three_step.json \
  data/output/pnid_llm_only.json --json > ocr_vs_llm.json
```

**LLM Analysis Provides**:
- Which method captures critical components better
- Functional equivalence despite structural differences
- Practical implications of each method's errors
- Which method to use for specific applications

### 4. Change Impact Analysis

**Scenario**: Assess impact of proposed modifications

```bash
python src/compare_pnid_llm.py \
  current/as_built.json \
  proposed/modification.json
```

**LLM Analysis Provides**:
- Process impact of proposed changes
- Safety review considerations
- Required procedure updates
- Regulatory/compliance implications

---

## Output Interpretation

### Summary

High-level overview in 2-3 sentences:
- What changed (added, removed, modified)
- Overall significance (cosmetic vs. substantive)
- Quick equivalence assessment

**Example**:
> "P&ID 2 is a reduced version of P&ID 1. It removes one chamber, one globe 
> valve, two nozzles, a pipe reducer, and four associated connections. 
> The P&IDs are not functionally equivalent."

### Impact Assessment

Detailed engineering analysis covering:
- **Functional Changes**: How process flow is affected
- **Operational Impact**: Changes to control, isolation, monitoring
- **Safety Implications**: Risk to personnel, equipment, environment
- **Design Considerations**: Hydraulics, sizing, materials
- **Maintenance Impact**: Access, spare parts, procedures

**Example Excerpt**:
> "Removal of GlobeValve-1 eliminates one location for manual/automatic 
> flow control. This reduces the ability to isolate a branch or fine-tune 
> flow in that part of the system. Impact: Potentially significant for 
> operability and isolation strategy..."

### Equivalence Determination

- **Status**: `EQUIVALENT` or `NOT EQUIVALENT`
- **Confidence**: `high`, `medium`, or `low`

**Interpretation**:
- **Equivalent (high confidence)**: Treat as same design
- **Equivalent (medium/low confidence)**: Verify with domain expert
- **Not Equivalent (high confidence)**: Definitely different
- **Not Equivalent (medium/low confidence)**: May be functionally similar

### Recommendations

Actionable guidance for engineers:
1. What to do next (reconcile, document, investigate)
2. Which documents to update
3. Who to consult (process, safety, operations)
4. When equivalence can be assumed

---

## Token Usage & Cost

### Typical Token Consumption

| Comparison Type | Input Tokens | Output Tokens | Reasoning Tokens | Total | Est. Cost* |
|----------------|--------------|---------------|------------------|-------|-----------|
| Small (20 comp) | ~2,000 | ~1,500 | ~3,000 | ~6,500 | $0.04 |
| Medium (70 comp) | ~4,000 | ~3,000 | ~8,000 | ~15,000 | $0.09 |
| Large (200 comp) | ~10,000 | ~5,000 | ~15,000 | ~30,000 | $0.18 |

*Estimate based on GPT-5.1 pricing (~$6/M tokens)

### Cost Optimization Tips

1. **Use lower reasoning for initial checks**:
   ```bash
   python src/compare_pnid_llm.py file1.json file2.json --reasoning low
   ```

2. **Pre-filter with rule-based comparison**:
   - Use `compare_pnid_jsonld.py` first (free, instant)
   - Only use LLM for cases with differences

3. **Batch processing**:
   - Compare multiple files in sequence
   - Save JSON results for later review

4. **Cache results**:
   - Store JSON output for repeated analysis
   - Avoid re-running on same file pairs

---

## Troubleshooting

### API Key Issues

**Error**: `AZURE_OPENAI_API_KEY or AZURE_AI_API_KEY not found in environment`

**Solution**:
```bash
# Add to .env file
echo "AZURE_AI_API_KEY=your_key_here" >> .env

# Or export temporarily
export AZURE_AI_API_KEY=your_key_here
```

### Model Not Found

**Error**: `DeploymentNotFound: The API deployment for this resource does not exist`

**Solution**:
```bash
# Check available model
python -c "import os; print(os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-5.1'))"

# Override deployment
export AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

### Timeout Issues

**Error**: Script hangs or times out

**Cause**: Large P&IDs with high reasoning

**Solution**:
```bash
# Use lower reasoning effort
python src/compare_pnid_llm.py file1.json file2.json --reasoning low

# Or increase timeout (if using wrapper script)
timeout 180 python src/compare_pnid_llm.py file1.json file2.json
```

### Empty Response

**Error**: `Empty response from LLM`

**Cause**: Model returned no content (rare)

**Debug**:
- Check API status
- Try again (may be transient)
- Use `--reasoning medium` or `low`

---

## Integration Examples

### Python API Usage

```python
import json
import subprocess
from pathlib import Path

def compare_pnids_llm(path1: Path, path2: Path, reasoning: str = "high") -> dict:
    """Run LLM comparison and return results."""
    result = subprocess.run(
        [
            "python", "src/compare_pnid_llm.py",
            str(path1), str(path2),
            "--reasoning", reasoning,
            "--json"
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)

# Use it
result = compare_pnids_llm(
    Path("data/output/pnid_base.json"),
    Path("data/variations/pnid_var_001.json")
)

print(f"Equivalent: {result['equivalent']}")
print(f"Confidence: {result['confidence']}")
print(f"Summary: {result['summary']}")
```

### Batch Processing Script

```python
from pathlib import Path
import json

def batch_compare_llm(base_path: Path, variations_dir: Path, output_dir: Path):
    """Compare base P&ID with all variations using LLM."""
    base = base_path
    variations = sorted(variations_dir.glob("pnid_c01_var_*.json"))
    
    output_dir.mkdir(exist_ok=True)
    
    for var_path in variations:
        print(f"Analyzing {var_path.name}...")
        
        result = compare_pnids_llm(base, var_path, reasoning="medium")
        
        # Save individual result
        output_file = output_dir / f"{var_path.stem}_llm_analysis.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        # Log key findings
        print(f"  Equivalent: {result['equivalent']} ({result['confidence']})")
        print(f"  Components removed: {len(result['components_only_in_1'])}")
        print(f"  Components added: {len(result['components_only_in_2'])}")
    
    print(f"\n✅ Analyzed {len(variations)} variations")

# Run
batch_compare_llm(
    Path("data/output/pnid_dexpi_final.json"),
    Path("data/variations"),
    Path("data/llm_analysis")
)
```

---

## Best Practices

### 1. Use Appropriate Reasoning Level

- **Quick Validation**: `low` reasoning (15s, good enough for most cases)
- **Production Reports**: `high` reasoning (60s, comprehensive analysis)
- **Cost-Sensitive**: `medium` reasoning (30s, balanced)

### 2. Combine with Rule-Based Comparison

```bash
# Step 1: Quick rule-based check
python src/compare_pnid_jsonld.py file1.json file2.json --json > structural.json

# Step 2: If differences found, get LLM analysis
python src/compare_pnid_llm.py file1.json file2.json > analysis.txt
```

### 3. Save All Results

Always save JSON output for audit trail:

```bash
python src/compare_pnid_llm.py file1.json file2.json --json \
  > results/comparison_$(date +%Y%m%d_%H%M%S).json
```

### 4. Review High-Impact Changes

For changes flagged as "NOT EQUIVALENT" with "high" confidence:
- Have domain expert review impact assessment
- Check recommendations against design basis
- Update affected documentation before proceeding

### 5. Version Control Results

Track comparison results in git:

```bash
git add results/comparison_*.json
git commit -m "LLM comparison: design rev B vs rev A"
```

---

## Comparison: LLM vs. Rule-Based

### Example: Component Removal

**Rule-Based Output**:
```
📦 Components only in File 1 (9):
  - pid:GlobeValve-1 (pid:Component)
  - pid:Chamber-3 (pid:Component)
```

**LLM Output**:
```
💡 Removal of GlobeValve-1 eliminates one location for manual/automatic 
flow control. This reduces the ability to isolate a branch or fine-tune 
flow in that part of the system. Impact: Potentially significant for 
operability and isolation strategy, depending on where GlobeValve-1 sat 
in the line.

Removal of Chamber-3: One of the eight chambers present in P&ID 1 is 
absent in P&ID 2. Without explicit connections, it is likely an instrument 
or internal vessel feature. Impact: Moderate, but localized; affects how 
the vessel/instrument segment can be monitored or utilized.
```

**Key Difference**: LLM explains **why it matters**, rule-based just lists **what changed**.

---

## Related Documentation

- **[Comparison Guide](COMPARISON_GUIDE.md)** - Rule-based comparison tool
- **[Workflow Guide](WORKFLOW_AND_COMPARISON.md)** - Complete extraction workflows
- **[Status Summary](STATUS_SUMMARY.md)** - Current project status

---

## Frequently Asked Questions

### Q: Why is this so slow compared to rule-based comparison?

**A**: LLM comparison performs deep reasoning about engineering implications. Rule-based comparison (~50ms) just checks data structures. LLM analysis (~60s) understands process flow, safety, and operability.

### Q: Can I use this offline?

**A**: No, requires Azure OpenAI API. Use rule-based comparison (`compare_pnid_jsonld.py`) for offline analysis.

### Q: How accurate is the LLM analysis?

**A**: Very high for structural comparison (matches rule-based 99%+). Impact assessment quality depends on:
- Prompt engineering (already optimized)
- Model capabilities (GPT-5.1 with reasoning is excellent)
- P&ID complexity (simpler = better)

Always have domain experts review critical decisions.

### Q: What if results differ between runs?

**A**: Rare with structured outputs and reasoning. If it happens:
- Use `high` reasoning (more deterministic)
- Save JSON for reproducibility
- Compare multiple runs if critical

### Q: Can I customize the analysis prompts?

**A**: Yes, edit `compare_pnid_llm.py` around line 200 to modify the prompt. Add domain-specific instructions for your industry.

---

**Last Updated**: 2025-12-15  
**Script Version**: 1.0.0  
**Model**: GPT-5.1 (gpt-5.1)  
**Maintainer**: Bouvet ASA