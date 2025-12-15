# JSON-LD P&ID Comparison Guide

This guide explains how to use the `compare_pnid_jsonld.py` script to compare two P&ID JSON-LD files and analyze their differences.

## Overview

The comparison script identifies differences between two P&ID JSON-LD files, including:
- **Missing/Added Components**: Components present in one file but not the other
- **Component Attribute Differences**: Changes in type, name, or position
- **Missing/Added Connections**: Pipe connections present in one file but not the other
- **Connection Endpoint Differences**: Changes in connection source/target

This is particularly useful for:
- Validating extraction accuracy (original vs. extracted)
- Comparing different extraction methods (OCR vs. LLM vs. CAD)
- Analyzing generated P&ID variations
- Testing robustness of extraction pipelines

---

## Installation

The script uses standard dependencies already in the project:

```bash
# Ensure project is installed
uv pip install -e .
```

---

## Basic Usage

### Compare Two Files (Human-Readable Output)

```bash
python src/compare_pnid_jsonld.py <file1.json> <file2.json>
```

**Example:**
```bash
python src/compare_pnid_jsonld.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_001_remove_components_medium.json
```

**Output:**
```
================================================================================
P&ID JSON-LD Comparison
================================================================================
File 1: data/output/pnid_dexpi_final.json
File 2: data/variations/pnid_c01_var_001_remove_components_medium.json

🔍 DIFFERENCES FOUND

📦 Components only in File 1 (9):
  - pid:Nozzle-11 (pid:Component)
  - pid:GlobeValve-1 (pid:Component)
  - pid:Chamber-3 (pid:Component)
  ...

================================================================================
Summary:
  Components only in File 1: 9
  Components only in File 2: 0
  Components with differences: 0
  Connections only in File 1: 0
  Connections only in File 2: 0
  Connections with differences: 0
================================================================================
```

---

### JSON Output (Machine-Readable)

For programmatic processing or integration with other tools:

```bash
python src/compare_pnid_jsonld.py <file1.json> <file2.json> --json
```

**Example:**
```bash
python src/compare_pnid_jsonld.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_003_modify_names_medium.json \
  --json > comparison_result.json
```

**Output Structure:**
```json
{
  "file1": "data/output/pnid_dexpi_final.json",
  "file2": "data/variations/pnid_c01_var_003_modify_names_medium.json",
  "has_differences": true,
  "components_only_in_1": [...],
  "components_only_in_2": [...],
  "component_diffs": [
    {
      "id": "pid:BallValve-3",
      "type_diff": null,
      "name_diff": ["BALL_VALVE_SHAPE", "BALL_VALVE_SHAPE_MOD"],
      "position_diff": null,
      "other_diffs": {}
    }
  ],
  "connections_only_in_1": 0,
  "connections_only_in_2": 0,
  "connection_diffs": 0,
  "summary": {
    "components_only_in_1": 0,
    "components_only_in_2": 0,
    "components_with_differences": 30,
    "connections_only_in_1": 0,
    "connections_only_in_2": 0,
    "connections_with_differences": 0
  }
}
```

---

## Use Cases

### 1. Validate Extraction Accuracy

Compare original DEXPI P&ID with extracted version:

```bash
python src/compare_pnid_jsonld.py \
  data/output/pnid_dexpi_final.json \
  data/output/pnid_dwg.json
```

This helps identify:
- Missing components (extraction missed)
- Incorrect component types
- Position errors
- Missing connections

---

### 2. Compare Extraction Methods

Compare OCR-based vs. LLM-based extraction:

```bash
python src/compare_pnid_jsonld.py \
  data/output/pnid_three_step.json \
  data/output/pnid_llm_only.json
```

Useful for:
- Evaluating extraction method trade-offs
- Identifying method-specific errors
- Hybrid approach validation

---

### 3. Analyze P&ID Variations

Compare base P&ID with generated variations:

```bash
# Compare with variation that removes components
python src/compare_pnid_jsonld.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_001_remove_components_medium.json

# Compare with variation that modifies names
python src/compare_pnid_jsonld.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_003_modify_names_medium.json

# Compare with variation that perturbs positions
python src/compare_pnid_jsonld.py \
  data/output/pnid_dexpi_final.json \
  data/variations/pnid_c01_var_009_perturb_positions_medium.json
```

Useful for:
- Testing extraction robustness
- Benchmarking correction algorithms
- Validating error handling

---

### 4. Batch Comparison of All Variations

Compare all variations against the base and generate a summary report:

```bash
#!/bin/bash
# batch_compare.sh

BASE="data/output/pnid_dexpi_final.json"
OUTPUT_DIR="data/comparison_reports"
mkdir -p "$OUTPUT_DIR"

for var in data/variations/pnid_c01_var_*.json; do
    var_name=$(basename "$var" .json)
    echo "Comparing $var_name..."
    
    python src/compare_pnid_jsonld.py "$BASE" "$var" --json \
      > "$OUTPUT_DIR/${var_name}_comparison.json"
done

echo "✅ Comparison complete. Reports saved in $OUTPUT_DIR/"
```

---

## Understanding Output

### Component Differences

**Missing Components:**
- `Components only in File 1`: Present in first file, missing in second (potential extraction miss)
- `Components only in File 2`: Present in second file, missing in first (potential false positive)

**Attribute Changes:**
- `type_diff`: Component type changed (e.g., `pid:Valve` → `pid:Pump`)
- `name_diff`: Component name/label changed
- `position_diff`: Position changed beyond threshold (>1.0 units distance)
- `other_diffs`: Other attribute changes (description, category, etc.)

### Connection Differences

- `Connections only in File 1/2`: Edges present in one graph but not the other
- `Connection diffs`: Same endpoints but different attributes

### Position Comparison

Position differences are reported when:
- Both files have positions AND distance > 1.0 units
- One file has position, the other doesn't

Distance calculation:
```python
dist = sqrt((x1 - x2)^2 + (y1 - y2)^2)
```

---

## Integration Examples

### Python Script Integration

```python
from pathlib import Path
from src.compare_pnid_jsonld import compare_pnids

# Compare two files
result = compare_pnids(
    Path("data/output/pnid_base.json"),
    Path("data/variations/pnid_var_001.json")
)

# Check for differences
if result.has_differences():
    print(f"Found {len(result.component_diffs)} component differences")
    print(f"Missing components: {len(result.components_only_in_1)}")
    print(f"Added components: {len(result.components_only_in_2)}")
    
    # Analyze specific differences
    for diff in result.component_diffs:
        if diff.type_diff:
            print(f"Component {diff.id}: type changed from {diff.type_diff[0]} to {diff.type_diff[1]}")
```

### Test Harness Example

```python
import json
from pathlib import Path
from src.compare_pnid_jsonld import compare_pnids

def test_all_variations(base_path, variations_dir):
    """Test all variations and generate report."""
    base = Path(base_path)
    variations = sorted(Path(variations_dir).glob("pnid_c01_var_*.json"))
    
    results = []
    for var_path in variations:
        result = compare_pnids(base, var_path)
        results.append({
            "variation": var_path.name,
            "has_differences": result.has_differences(),
            "summary": {
                "components_missing": len(result.components_only_in_1),
                "components_added": len(result.components_only_in_2),
                "components_changed": len(result.component_diffs),
                "connections_missing": len(result.connections_only_in_1),
                "connections_added": len(result.connections_only_in_2),
            }
        })
    
    # Save report
    with open("variation_test_report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Tested {len(variations)} variations")
    print(f"Report saved to variation_test_report.json")

# Run test
test_all_variations(
    "data/output/pnid_dexpi_final.json",
    "data/variations"
)
```

---

## Troubleshooting

### Common Issues

**File Not Found:**
```bash
❌ Error: File not found: data/output/pnid_missing.json
```
→ Check file path and ensure file exists

**No Differences Found:**
```
✅ No differences found — P&IDs are identical.
```
→ Files are identical (byte-level or semantically)

**Large Position Differences:**
```
Position: (100.0, 200.0) → (150.0, 250.0) (distance: 70.71)
```
→ Check coordinate systems (normalized vs. pixel coordinates)

### Coordinate System Considerations

Different sources may use different coordinate systems:

| Source | X Range | Y Range | Notes |
|--------|---------|---------|-------|
| DEXPI | [0, ~400] | [0, ~250] | Absolute mm coordinates |
| DeepSeek-OCR | [0, 1000] | [0, 1000] | Normalized 1000-bin |
| Image-based | [0, width] | [0, height] | Pixel coordinates |

Convert before comparison if needed.

---

## Advanced Usage

### Custom Position Threshold

Modify `src/compare_pnid_jsonld.py` to adjust position difference threshold:

```python
# Line ~147 in compare_components()
if dist > 1.0:  # Change this threshold
    diff.position_diff = (pos1, pos2)
```

### Filter Specific Differences

```python
from src.compare_pnid_jsonld import compare_pnids

result = compare_pnids(path1, path2)

# Only report type changes
type_changes = [d for d in result.component_diffs if d.type_diff]

# Only report significant position changes
position_changes = [d for d in result.component_diffs 
                   if d.position_diff and 
                   calculate_distance(d.position_diff[0], d.position_diff[1]) > 10.0]
```

---

## Next Steps

1. **Batch Testing**: Use the script to test all variations and generate a comprehensive report
2. **Metrics Dashboard**: Build a dashboard to visualize comparison metrics over time
3. **Automated Testing**: Integrate into CI/CD pipeline to validate extraction quality
4. **Error Analysis**: Analyze patterns in differences to improve extraction algorithms

---

## Related Documentation

- [Generate P&ID Variations](../src/generate_pnid_variations.py) - Generate synthetic test variations
- [DEXPI Reader](../src/dexpi_reader.py) - Extract P&IDs from DEXPI XML
- [DWG Reader](../src/dwg_reader.py) - Extract P&IDs from CAD files
- [Workflow Guide](WORKFLOW_AND_COMPARISON.md) - Complete extraction workflows

---

**Last Updated**: 2025-12-15  
**Script Version**: 1.0.0  
**Maintainer**: Bouvet ASA