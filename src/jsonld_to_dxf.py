#!/usr/bin/env python3
"""
Convert JSON-LD P&ID data to DXF format.

This script takes JSON-LD P&ID data (from dexpi_reader.py, dwg_reader.py, etc.)
and creates a DXF file with the components and connections.

Usage:
    python src/jsonld_to_dxf.py <input.json> [-o output.dxf]
    python src/jsonld_to_dxf.py data/output/pnid_dexpi_complete.json -o data/output/pnid_converted.dxf
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import units

# Map P&ID types to DXF block definitions
PID_TYPE_TO_BLOCK: dict[str, str] = {
    "pid:Valve": "VALVE",
    "pid:BallValve": "VALVE",
    "pid:GateValve": "VALVE",
    "pid:GlobeValve": "VALVE",
    "pid:ButterflyValve": "VALVE",
    "pid:CheckValve": "VALVE",
    "pid:ControlValve": "VALVE",
    "pid:SafetyValve": "VALVE",
    "pid:Pump": "PUMP",
    "pid:Tank": "TANK",
    "pid:Vessel": "TANK",
    "pid:HeatExchanger": "HEAT_EXCHANGER",
    "pid:FlowMeter": "FLOW_METER",
    "pid:Instrument": "INSTRUMENT",
    "pid:Component": "COMPONENT",
}


def create_standard_blocks(doc: ezdxf.document.Drawing) -> None:
    """Create standard P&ID symbol blocks."""
    blocks = doc.blocks

    # Valve block (simple cross with circle)
    if "VALVE" not in blocks:
        valve = blocks.new("VALVE")
        valve.add_lwpolyline([(0, -8), (0, 8)])  # Vertical line
        valve.add_lwpolyline([(-8, 0), (8, 0)])  # Horizontal line
        valve.add_circle((0, 0), 6)  # Circle

    # Pump block (circle with shaft)
    if "PUMP" not in blocks:
        pump = blocks.new("PUMP")
        pump.add_circle((0, 0), 12)
        pump.add_lwpolyline([(-10, 0), (10, 0)])  # Horizontal shaft
        pump.add_lwpolyline([(0, -10), (0, 10)])  # Vertical impeller

    # Tank block (rectangle)
    if "TANK" not in blocks:
        tank = blocks.new("TANK")
        tank.add_lwpolyline([(-20, -25), (-20, 25), (20, 25), (20, -25), (-20, -25)])  # Rectangle

    # Heat exchanger (two circles)
    if "HEAT_EXCHANGER" not in blocks:
        hex_block = blocks.new("HEAT_EXCHANGER")
        hex_block.add_circle((-8, 0), 10)
        hex_block.add_circle((8, 0), 10)

    # Flow meter (circle with diamond)
    if "FLOW_METER" not in blocks:
        fm = blocks.new("FLOW_METER")
        fm.add_circle((0, 0), 10)
        fm.add_lwpolyline([(0, -12), (12, 0), (0, 12), (-12, 0), (0, -12)])

    # Generic instrument (circle)
    if "INSTRUMENT" not in blocks:
        inst = blocks.new("INSTRUMENT")
        inst.add_circle((0, 0), 10)
        inst.add_text("I", dxfattribs={"height": 8, "insert": (-3, -4)})

    # Generic component (square)
    if "COMPONENT" not in blocks:
        comp = blocks.new("COMPONENT")
        comp.add_lwpolyline([(-10, -10), (-10, 10), (10, 10), (10, -10), (-10, -10)])


def convert_jsonld_to_dxf(jsonld_path: Path, output_path: Path, spacing: float = 100.0) -> None:
    """
    Convert JSON-LD P&ID data to DXF format.

    Args:
        jsonld_path: Path to JSON-LD input file
        output_path: Path to output DXF file
        spacing: Grid spacing for auto-layout if no coordinates (default: 100.0)
    """
    print(f"Loading JSON-LD: {jsonld_path}")

    # Load JSON-LD data
    with jsonld_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    graph = data.get("@graph", [])
    if not graph:
        raise ValueError("No @graph found in JSON-LD data")

    # Separate nodes and edges
    nodes = [n for n in graph if n.get("@type") != "pid:Connection"]
    edges = [n for n in graph if n.get("@type") == "pid:Connection"]

    print(f"Found {len(nodes)} components and {len(edges)} connections")

    # Create new DXF document
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    # Create layers
    doc.layers.add("COMPONENTS", color=1)  # Red
    doc.layers.add("CONNECTIONS", color=2)  # Yellow
    doc.layers.add("LABELS", color=7)  # White

    # Create standard blocks
    create_standard_blocks(doc)

    # Track positions for connection drawing
    component_positions: dict[str, tuple[float, float]] = {}

    # Auto-layout: assign positions if missing
    has_coordinates = any(n.get("x") is not None and n.get("y") is not None for n in nodes)

    if not has_coordinates:
        print("No spatial coordinates found, using grid layout")
        cols = int(len(nodes) ** 0.5) + 1
        for i, node in enumerate(nodes):
            row = i // cols
            col = i % cols
            node["x"] = col * spacing
            node["y"] = row * spacing

    # Insert components
    print("Inserting components...")
    for node in nodes:
        node_id = node.get("@id", "")
        node_type = node.get("@type", "pid:Component")
        name = node.get("name") or node.get("tag") or node_id.split(":")[-1]

        # Get or assign position
        x = node.get("x", 0.0)
        y = node.get("y", 0.0)

        if x is None:
            x = 0.0
        if y is None:
            y = 0.0

        # Convert to float
        x = float(x)
        y = float(y)

        component_positions[node_id] = (x, y)

        # Determine block type
        block_name = PID_TYPE_TO_BLOCK.get(node_type, "COMPONENT")

        # Insert block reference
        msp.add_blockref(block_name, (x, y), dxfattribs={"layer": "COMPONENTS"})

        # Add label
        label_y_offset = -15 if block_name == "TANK" else -20
        msp.add_text(
            name,
            dxfattribs={
                "layer": "LABELS",
                "height": 8,
                "insert": (x, y + label_y_offset),
            },
        )

    # Draw connections
    print("Drawing connections...")
    for edge in edges:
        connected_to = edge.get("connectedTo", [])
        if len(connected_to) >= 2:
            source_id = connected_to[0]
            target_id = connected_to[1]

            # Get positions
            source_pos = component_positions.get(source_id)
            target_pos = component_positions.get(target_id)

            if source_pos and target_pos:
                # Draw line between components
                msp.add_line(source_pos, target_pos, dxfattribs={"layer": "CONNECTIONS"})

    # Add title
    msp.add_text(
        "P&ID - Converted from JSON-LD",
        dxfattribs={"layer": "LABELS", "height": 15, "insert": (0, -100)},
    )

    # Save DXF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output_path))

    print(f"\n✅ Successfully created DXF file")
    print(f"   Components: {len(nodes)}")
    print(f"   Connections: {len(edges)}")
    print(f"   Output: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert JSON-LD P&ID data to DXF format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert JSON-LD to DXF
  python src/jsonld_to_dxf.py data/output/pnid_dexpi_complete.json

  # Specify output file
  python src/jsonld_to_dxf.py data/output/pnid_dexpi_complete.json -o data/output/converted.dxf

  # Adjust grid spacing for auto-layout
  python src/jsonld_to_dxf.py input.json -o output.dxf --spacing 150
        """,
    )
    parser.add_argument("input", type=Path, help="Path to JSON-LD file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to output DXF file (default: input with .dxf extension)",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=100.0,
        help="Grid spacing for auto-layout when no coordinates (default: 100.0)",
    )

    args = parser.parse_args()

    try:
        # Determine output path
        output_path = args.output or args.input.with_suffix(".dxf")

        # Convert
        convert_jsonld_to_dxf(args.input, output_path, spacing=args.spacing)

        sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
