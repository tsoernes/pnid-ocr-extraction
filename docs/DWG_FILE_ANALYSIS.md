# DWG File Analysis - Diagramas P&ID.dwg

**Date**: 2025-01-XX  
**File**: `data/input/Diagramas P&ID.dwg`  
**Status**: ⚠️ Conversion blocked by DWG format version

---

## 📁 File Information

- **Path**: `data/input/Diagramas P&ID.dwg`
- **Size**: 167 KB
- **Format**: DWG AutoCAD 2018/2019/2020 (format 18)
- **Created**: 2024-03-07 17:09

---

## 🔧 Analysis Tools & Status

### DWG Reader Script

**File**: `src/dwg_reader.py`

**Purpose**: Convert DXF/DWG P&ID files to JSON-LD with heuristic component and pipe extraction.

**Features**:
- Extracts P&ID nodes (components) from INSERT entities (block references)
- Maps block names to component types (Valve, Pump, Filter, Instrument, etc.)
- Extracts pipe geometry from LINE and LWPOLYLINE entities
- Infers connectivity by snapping components to pipe vertices
- Outputs JSON-LD with spatial coordinates (x, y)
- Supports DWG → DXF conversion via external converter

**Heuristics**:
- Block name pattern matching (e.g., `\bVALVE\b` → `pid:Valve`)
- Pipe layer patterns (e.g., `\bPIPE\b`, `\bPROCESS\b`, `\bLINE\b`)
- Attribute harvesting (TAG, NAME, DESC, LINE_NO)
- Snap tolerance for junction detection (default: 5.0 drawing units)

**Data Models**:
```python
@dataclass
class PIDNode:
    id: str
    type: str              # JSON-LD type IRI (e.g., "pid:Valve")
    name: str | None
    tag: str | None
    layer: str | None
    x: float
    y: float
    block_name: str | None
    line_number: str | None

@dataclass
class PipeVertex:
    id: str
    x: float
    y: float
    layer: str | None

@dataclass
class PIDEdge:
    source: str            # PIDNode.id
    target: str            # PIDNode.id
    predicate: str = "pid:connectedTo"
```

---

## ⚠️ Conversion Issues

### Issue 1: dwg2dxf Format Incompatibility

**Tool**: `/usr/sbin/dwg2dxf`

**Error**:
```
DWG file error: format 18 error 3
Error reading file data/input/Diagramas P&ID.dwg
Conversion failed
```

**Root Cause**:
- The DWG file is in AutoCAD 2018/2019/2020 format (format 18)
- The installed `dwg2dxf` tool cannot parse this newer format
- Format 18 was introduced in AutoCAD 2018 and is not supported by older converters

**Original Script Syntax Issue**:
The original `maybe_convert_dwg_to_dxf()` function had incorrect command syntax:
```python
# Original (incorrect):
cmd = ["dwg2dxf", str(input_path), "-o", str(dxf_path)]

# Fixed:
cmd = ["dwg2dxf", str(input_path), "-v2007", str(dxf_path)]
```

The tool expects: `dwg2dxf <input> [-b] <-version> <output>`

---

## 🔄 Alternative Solutions

### Option 1: ODA File Converter (Recommended)

**Overview**:
- Open Design Alliance (ODA) File Converter
- Handles all DWG formats including 2018/2019/2020
- Free download from: https://www.opendesign.com/guestfiles/oda_file_converter
- Available for Linux (Qt6 version)

**Integration with ezdxf**:
```python
from ezdxf.addons import odafc

# Load DWG directly
doc = odafc.readfile('data/input/Diagramas P&ID.dwg')
print(f'Document loaded as DXF version: {doc.dxfversion}.')
```

**Installation**:
```bash
# Download from ODA website (requires registration)
wget https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_lnxX64_8.3dll_25.11.deb

# Install (Fedora - convert .deb to .rpm)
alien -r ODAFileConverter_QT6_lnxX64_8.3dll_25.11.deb
sudo dnf install ODAFileConverter-*.rpm

# Or extract manually
ar x ODAFileConverter_QT6_lnxX64_8.3dll_25.11.deb
tar xf data.tar.xz
sudo mv usr/bin/ODAFileConverter /usr/local/bin/
```

**Modified Script**:
```python
def maybe_convert_dwg_to_dxf(input_path: Path) -> Path:
    """
    If input is DWG, use ODA File Converter to convert.
    Falls back to dwg2dxf if ODA not available.
    """
    if input_path.suffix.lower() != ".dwg":
        return input_path

    dxf_path = input_path.with_suffix(".dxf")
    if dxf_path.exists():
        return dxf_path

    # Try ODA File Converter first
    oda_cmd = shutil.which("ODAFileConverter")
    if oda_cmd:
        # ODA syntax: ODAFileConverter <input_folder> <output_folder> <output_version> <output_format> <recurse> <audit>
        # For single file, use input file's directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir)
            cmd = [oda_cmd, str(input_path.parent), str(tmp_out), "ACAD2018", "DXF", "0", "1"]
            subprocess.run(cmd, check=True)
            # Move output to expected location
            converted = tmp_out / input_path.with_suffix(".dxf").name
            shutil.move(str(converted), str(dxf_path))
        return dxf_path

    # Fallback to dwg2dxf
    cmd = ["dwg2dxf", str(input_path), "-v2007", str(dxf_path)]
    subprocess.run(cmd, check=True)
    return dxf_path
```

### Option 2: LibreDWG (Open Source)

**Overview**:
- Free and open-source library
- GPL 3.0 licensed
- Supports R2010+ formats
- Command-line tools: `dwgread`, `dwg2dxf`, `dxf2dwg`

**Installation (Fedora)**:
```bash
sudo dnf install libredwg libredwg-tools
```

**Usage**:
```bash
dwgread "data/input/Diagramas P&ID.dwg" > dwg_info.txt
dwg2dxf "data/input/Diagramas P&ID.dwg" -o "data/input/Diagramas P&ID.dxf"
```

**Python Bindings**:
```bash
pip install python-libredwg
```

### Option 3: Online Conversion Services

**Services**:
- Autodesk Viewer (free, web-based)
- CloudConvert (API available)
- Zamzar
- AnyConv

**Pros**:
- No local installation needed
- Handles all DWG versions
- Quick for single files

**Cons**:
- Requires internet connection
- Privacy concerns (uploads proprietary diagrams)
- Not suitable for batch processing
- May have file size limits

### Option 4: Direct Python Parsing (Limited)

**Library**: `pydwg` (https://github.com/mghohoo/pydwg)

**Status**: Experimental, incomplete support

**Pros**:
- Pure Python
- No external dependencies

**Cons**:
- Limited format support
- May not parse all entities correctly
- Not actively maintained

---

## 🎯 Recommended Workflow

### Immediate Solution (Manual)

1. **Use AutoCAD/AutoCAD LT** (if available):
   ```
   Open "Diagramas P&ID.dwg" in AutoCAD
   File → Save As → DXF → Version 2007 or 2018
   Save to: data/input/Diagramas P&ID.dxf
   ```

2. **Use FreeCAD** (free, open-source):
   ```bash
   sudo dnf install freecad
   freecad --console
   > import importDWG
   > importDWG.open("data/input/Diagramas P&ID.dwg")
   > # Inspect and export as DXF
   ```

3. **Use Online Converter**:
   - Upload to https://www.autodesk.com/viewer
   - Download as DXF
   - Move to `data/input/Diagramas P&ID.dxf`

### Automated Solution (Long-term)

1. **Install ODA File Converter**:
   ```bash
   # Download from ODA website
   # Install system-wide
   ```

2. **Update `dwg_reader.py`**:
   - Add ODA File Converter support
   - Fall back to dwg2dxf for older formats
   - Add format detection and error handling

3. **Test with converted file**:
   ```bash
   uv run src/dwg_reader.py \
     "data/input/Diagramas P&ID.dxf" \
     -o data/output/pnid_dwg.json \
     --snap 5.0 \
     --include-unknown-blocks
   ```

---

## 📊 Expected Output Structure

Once conversion succeeds, the output JSON-LD will contain:

```json
{
  "@context": {
    "pid": "https://example.com/pid#",
    "connectedTo": {"@id": "pid:connectedTo", "@type": "@id"},
    "name": "schema:name",
    ...
  },
  "@graph": [
    {
      "@id": "pid:VALVE_1",
      "@type": "pid:Valve",
      "name": "V-101",
      "tag": "V-101",
      "layer": "PIPING",
      "blockName": "BALLVALVE",
      "x": 125.5,
      "y": 89.3
    },
    {
      "@id": "pid:PUMP_1",
      "@type": "pid:Pump",
      "name": "P-201",
      "tag": "P-201",
      "layer": "EQUIPMENT",
      "x": 200.0,
      "y": 150.0
    },
    {
      "@id": "pid:VALVE_1--pid:PUMP_1",
      "@type": "pid:Connection",
      "connectedTo": ["pid:VALVE_1", "pid:PUMP_1"]
    }
  ]
}
```

---

## 🔍 Next Steps

### Priority 1: Convert DWG to DXF

**Options** (pick one):
- [ ] Manual conversion via AutoCAD/FreeCAD/Online service
- [ ] Install ODA File Converter (requires sudo)
- [ ] Install LibreDWG tools: `sudo dnf install libredwg-tools`

### Priority 2: Run DWG Reader

Once DXF is available:
```bash
uv run src/dwg_reader.py \
  "data/input/Diagramas P&ID.dxf" \
  -o data/output/pnid_dwg.json \
  --snap 5.0 \
  --include-unknown-blocks
```

### Priority 3: Visualize Results

```bash
# Adapt plot_pnid_graph.py to handle JSON-LD format
# Or convert JSON-LD to PNID JSON format first

# Visualization command (after format conversion):
uv run src/plot_pnid_graph.py \
  --json data/output/pnid_dwg.json \
  --out data/output/pnid_dwg_graph.html
```

### Priority 4: Compare Approaches

Once DWG extraction works:
- Compare DWG-based extraction vs. OCR-based extraction
- Evaluate accuracy, completeness, spatial coordinates
- Determine best workflow for production use

---

## 📝 Notes

- The DWG file likely contains proper CAD entities (blocks, lines, polylines)
- This should provide **more accurate** geometry than image-based OCR
- Connectivity inference may need tuning (snap tolerance parameter)
- Block name patterns may need customization for this specific diagram
- Layer names in the DWG will guide pipe vs. component classification

---

## 🔗 References

- **ezdxf Documentation**: https://ezdxf.readthedocs.io/
- **ODA File Converter**: https://www.opendesign.com/guestfiles/oda_file_converter
- **ezdxf ODA Support**: https://ezdxf.readthedocs.io/en/stable/addons/odafc.html
- **LibreDWG**: https://www.gnu.org/software/libredwg/
- **DWG Format Spec**: https://www.opendesign.com/files/guestdownloads/OpenDesign_Specification_for_.dwg_files.pdf

---

**Summary**: The DWG file analysis is blocked by format incompatibility with the installed `dwg2dxf` tool. The recommended solution is to either (1) manually convert the DWG to DXF using AutoCAD/FreeCAD/online service, or (2) install ODA File Converter or LibreDWG for automated conversion. Once converted, the existing `dwg_reader.py` script should successfully extract P&ID components and pipes with spatial coordinates.