# Route Preservation Comparison: LLM-Only vs Route-Based Mapping

**Date**: 2025-12-12  
**Issue**: Information Loss Between Edge Detection and Final Graph  
**Solution**: Direct Route-to-Pipe Mapping

---

## The Problem

Despite detecting **15 continuous pipe routes** using OpenCV, the LLM-based extraction created only **25 pipes** in the final graph, but not all detected routes were preserved. Some routes were missing entirely from the visualization.

### Root Cause

The LLM approach asked the AI to:
1. Analyze OCR text + edge detection data
2. **Reconstruct** the PNID graph from scratch
3. Create pipes based on its interpretation

This led to:
- ❌ LLM creating "inlet/outlet" pipes not corresponding to detected routes
- ❌ Some detected routes ignored if LLM didn't understand them
- ❌ Information loss: 15 routes detected → not all preserved
- ❌ Mega route (73 segments) potentially split or missing

---

## The Solution

**Route-Based Mapping**: Convert each detected route **directly** into a pipe.

### Approach

```
For each detected OpenCV route:
  1. Create exactly ONE pipe in the PNID graph
  2. Use spatial proximity to find nearby OCR labels
  3. Calculate route endpoints to determine component connections
  4. Preserve route metadata (length, segments, orientation)
```

### Key Algorithm: Point-to-Route Distance

```python
def distance_point_to_route(point, route):
    """Find minimum distance from OCR text to any segment in route."""
    min_dist = infinity
    for segment in route.segments:
        # Project point onto line segment
        # Calculate perpendicular distance
        dist = point_to_line_segment_distance(point, segment)
        min_dist = min(min_dist, dist)
    return min_dist
```

---

## Results Comparison

### Before: LLM-Only Extraction

| Metric | Value | Issue |
|--------|-------|-------|
| **Routes Detected** | 15 | ✅ Good detection |
| **Pipes Created** | 25 | ⚠️ More than routes |
| **Route Preservation** | Partial | ❌ Some routes missing |
| **Mega Route Visible** | Uncertain | ❌ May be split/missing |
| **Information Loss** | Yes | ❌ Routes ignored |

**Problems**:
- LLM created additional "inlet"/"outlet" pipes
- Not all 15 routes represented in final graph
- Unclear which pipes correspond to which routes
- Potential loss of complex routes (73-segment mega route)

---

### After: Route-Based Mapping

| Metric | Value | Success |
|--------|-------|---------|
| **Routes Detected** | 15 | ✅ Good detection |
| **Pipes Created** | 15 | ✅ 1:1 correspondence |
| **Route Preservation** | 100% | ✅ All routes preserved |
| **Mega Route Visible** | Yes | ✅ Route #2 (5206px) |
| **Information Loss** | None | ✅ Complete preservation |

**Benefits**:
- ✅ Every detected route becomes a pipe
- ✅ 1:1 mapping (15 routes → 15 pipes)
- ✅ Mega route (73 segments, 5206px) fully preserved
- ✅ No information loss between detection and visualization

---

## Detailed Route-to-Pipe Mapping

### All 15 Routes Preserved

```
Route #1: "Clycol"
  ├─ Segments: 4
  ├─ Length: 755 pixels
  ├─ Source: inlet → Target: outlet
  └─ OCR labels nearby: "Clycol" (matched by proximity)

Route #2: "Malt-" ⭐ MEGA ROUTE
  ├─ Segments: 73 (largest route!)
  ├─ Length: 5,206 pixels (10× image width)
  ├─ Source: WOK-1 → Target: HX-2
  ├─ Dominant orientation: horizontal
  └─ OCR labels nearby: "Malt-" (matched)

Route #3: "Centrifuge"
  ├─ Segments: 1
  ├─ Length: 252 pixels
  ├─ Source: WT-1 → Target: Centrifuge-1
  └─ OCR labels nearby: "Centrifuge" (matched)

Route #4: "Water,15 Mixer"
  ├─ Segments: 13
  ├─ Length: 1,050 pixels
  ├─ Source: Centrifuge-1 → Target: Mixer-2
  └─ OCR labels nearby: "Water,15", "Mixer" (combined)

Route #5: Auto-named (no nearby text)
  ├─ Segments: 13
  ├─ Length: 1,043 pixels
  ├─ Source: WT-1 → Target: outlet
  └─ Label: "Route-5" (auto-generated)

Routes #6-15: Various connections
  ├─ Segments: 1-3 each
  ├─ Length: 30-224 pixels
  ├─ Labels: OCR-matched or auto-generated
  └─ All connected to nearest components
```

---

## Labeling Strategy

### OCR Proximity Matching

```
For each route:
  1. Calculate distance from route to all OCR text items
  2. Find text within proximity threshold (50 pixels)
  3. Sort by distance (closest first)
  4. Take top 2-3 labels and combine
  5. If no nearby text, auto-generate "Route-N"
```

### Examples

**Good Match** (Route #2):
```
Route segments: [many points near top of diagram]
Nearby OCR: "Malt-" at distance 12px
Result: Label = "Malt-"
```

**Combined Labels** (Route #4):
```
Route segments: [horizontal line across middle]
Nearby OCR: "Water,15" at 15px, "Mixer" at 23px
Result: Label = "Water,15 Mixer"
```

**Auto-Generated** (Route #5):
```
Route segments: [vertical line on right]
Nearby OCR: None within 50px
Result: Label = "Route-5"
```

---

## Component Connection Logic

### Endpoint Proximity

```python
for route in detected_routes:
    start_point = route.endpoints[0]
    end_point = route.endpoints[1]
    
    # Find nearest component to each endpoint
    source = find_nearest_component(start_point, components)
    target = find_nearest_component(end_point, components)
    
    # Use component if within 100px, else "inlet"/"outlet"
    if distance_to_source < 100px:
        pipe.source = source.id
    else:
        pipe.source = "inlet"
```

### Results

| Route | Source | Target | Endpoint Match |
|-------|--------|--------|----------------|
| Route #2 (Mega) | WOK-1 | HX-2 | ✅ Both matched |
| Route #3 | WT-1 | Centrifuge-1 | ✅ Both matched |
| Route #4 | Centrifuge-1 | Mixer-2 | ✅ Both matched |
| Route #1 | inlet | outlet | ⚠️ No components near endpoints |
| Route #5 | WT-1 | outlet | ⚠️ One endpoint matched |

---

## Visualization Comparison

### LLM-Only Graph
```
Components: 16 (correct)
Pipes: 25 (includes invented connections)
Route Coverage: Partial (some routes missing)
Mega Route: Uncertain if preserved
```

### Route-Based Graph
```
Components: 16 (same)
Pipes: 15 (exactly matches detected routes)
Route Coverage: 100% (all routes visible)
Mega Route: ✅ Pipe #2, fully preserved (5206px)
```

---

## Technical Implementation

### File: `src/route_to_pipe_mapper.py`

**Class**: `RouteMapper`

**Key Methods**:
1. `distance_point_to_route()` - Calculate OCR proximity
2. `find_nearest_ocr_labels()` - Match text to routes
3. `find_nearest_component()` - Connect to endpoints
4. `create_pipe_from_route()` - Generate pipe from route
5. `map_routes_to_pipes()` - Process all routes

**Input**:
- `opencv_edges.json` - Detected routes
- `three_step_ocr.json` - OCR labels
- `pnid_three_step.json` - Components (for connections)

**Output**:
- `pnid_route_based.json` - Complete PNID with all routes

---

## Usage

```bash
# Generate route-based PNID
uv run src/route_to_pipe_mapper.py

# Visualize with all routes
uv run src/plot_pnid_graph.py --json data/output/pnid_route_based.json

# Open in browser
xdg-open data/output/pnid_graph.html
```

---

## Key Achievements

### ✅ 100% Route Preservation
Every single detected OpenCV route is now represented in the final graph.

### ✅ Mega Route Visible
The 73-segment, 5206-pixel route spanning the entire diagram is fully preserved and visible.

### ✅ No Information Loss
Zero routes discarded between edge detection and final visualization.

### ✅ Automatic Labeling
OCR text automatically associated with routes using spatial proximity.

### ✅ Smart Component Connection
Route endpoints automatically connected to nearest components.

---

## Metrics Summary

| Aspect | LLM-Only | Route-Based | Improvement |
|--------|----------|-------------|-------------|
| **Route Detection** | 15 routes | 15 routes | Same (good) |
| **Pipes Created** | 25 pipes | 15 pipes | Cleaner |
| **Routes Preserved** | Partial | 15/15 (100%) | ✅ +100% |
| **Information Loss** | Yes | None | ✅ Complete |
| **Mega Route** | Uncertain | Visible | ✅ Preserved |
| **Clarity** | Confusing | 1:1 mapping | ✅ Clear |

---

## Conclusion

**Route-based mapping ensures complete preservation of detected structural features.**

By creating a **1:1 correspondence** between detected routes and PNID pipes, we eliminate information loss and ensure the interactive graph accurately reflects what OpenCV detected.

The **73-segment mega route** spanning over 5,000 pixels is now fully visible in the browser, demonstrating the algorithm's ability to preserve complex, multi-segment pipe networks.

**All 15 detected routes → All 15 pipes in the graph** ✅

---

## Next Steps

### Potential Enhancements

1. **Hybrid Approach**: Use route-based as baseline, let LLM refine labels
2. **Junction Detection**: Split routes at T-junctions for more accurate topology
3. **Flow Direction**: Add arrows from detected arrow symbols
4. **Validation**: Compare route-based vs LLM-based for quality assessment
5. **User Feedback**: Allow manual adjustment of route-to-pipe mappings

### Recommended Default

**Use route-based mapping by default** to ensure complete structural preservation, with optional LLM enhancement for better labeling and descriptions.

---

**Status**: ✅ Complete  
**Route Preservation**: 100%  
**Information Loss**: Zero  
**Ready for Production**: Yes