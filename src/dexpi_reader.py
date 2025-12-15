#!/usr/bin/env python3
"""
Convert DEXPI XML files (Proteus Schema) to JSON-LD format.

DEXPI (Data Exchange in the Process Industry) is an ISO 15926-based standard
for exchanging P&ID data. This script parses DEXPI XML files and converts them
to JSON-LD format compatible with the dwg_reader.py output.

Usage:
    python src/dexpi_reader.py <input.xml> [-o output.json]
    python src/dexpi_reader.py dexpi_example.xml -o pnid_dexpi.json
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# DEXPI/Proteus XML namespaces
NAMESPACES = {
    "proteus": "http://www.proteusxml.org/2011/ProteusXML",
    "iso": "http://www.iso.org/15926/2003/part2",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


# Map DEXPI component classes to P&ID types
DEXPI_CLASS_TO_TYPE = {
    # Equipment
    "Vessel": "pid:Vessel",
    "Tank": "pid:Tank",
    "Column": "pid:Column",
    "Reactor": "pid:Reactor",
    "HeatExchanger": "pid:HeatExchanger",
    "Pump": "pid:Pump",
    "Compressor": "pid:Compressor",
    "Turbine": "pid:Turbine",
    "Motor": "pid:Motor",
    # Piping components
    "Valve": "pid:Valve",
    "BallValve": "pid:BallValve",
    "GateValve": "pid:GateValve",
    "CheckValve": "pid:CheckValve",
    "ControlValve": "pid:ControlValve",
    "SafetyValve": "pid:SafetyValve",
    "ReliefValve": "pid:ReliefValve",
    "Flange": "pid:Flange",
    "Tee": "pid:Tee",
    "Elbow": "pid:Elbow",
    "Reducer": "pid:Reducer",
    # Instrumentation
    "Instrument": "pid:Instrument",
    "FlowMeter": "pid:FlowMeter",
    "PressureGauge": "pid:PressureGauge",
    "TemperatureSensor": "pid:TemperatureSensor",
    "LevelSensor": "pid:LevelSensor",
    "Controller": "pid:Controller",
    "Transmitter": "pid:Transmitter",
    "Indicator": "pid:Indicator",
}


def parse_dexpi_xml(xml_path: Path) -> dict[str, Any]:
    """
    Parse a DEXPI XML file and convert to JSON-LD.

    Args:
        xml_path: Path to DEXPI XML file

    Returns:
        JSON-LD dictionary with @context and @graph
    """
    print(f"Parsing DEXPI XML: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    nodes = []
    edges = []

    # Try to find elements with and without namespace
    # DEXPI files may use different namespace prefixes

    # Find all elements that look like equipment/components
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]  # Remove namespace
        elem_id = elem.get("ID") or elem.get("id")

        if not elem_id:
            continue

        # Extract component data
        component_name = elem.get("ComponentName") or elem.get("Name") or elem.get("name")
        component_class = elem.get("ComponentClass") or elem.get("Class") or tag
        tag_name = elem.get("TagName") or elem.get("Tag")

        # Get text content for tag/description
        if not tag_name:
            for child in elem:
                child_tag = child.tag.split("}")[-1]
                if "tag" in child_tag.lower() and child.text:
                    tag_name = child.text.strip()
                    break

        # Extract position if available
        x, y = None, None
        for child in elem:
            child_tag = child.tag.split("}")[-1]
            if "position" in child_tag.lower() or "location" in child_tag.lower():
                x_val = child.get("X") or child.get("x")
                y_val = child.get("Y") or child.get("y")
                if x_val:
                    x = float(x_val)
                if y_val:
                    y = float(y_val)
                break

        # Determine if this is a component worth extracting
        if tag in [
            "Equipment",
            "PipingComponent",
            "ProcessInstrument",
            "Valve",
            "Pump",
            "Vessel",
            "Tank",
            "Instrument",
            "HeatExchanger",
        ]:
            # Map to P&ID type
            pid_type = DEXPI_CLASS_TO_TYPE.get(component_class, "pid:Component")

            node = {
                "@id": f"pid:{elem_id}",
                "@type": pid_type,
                "name": component_name or tag_name or elem_id,
                "tag": tag_name,
                "dexpiClass": component_class,
                "x": x,
                "y": y,
            }

            # Remove None values
            node = {k: v for k, v in node.items() if v is not None}
            nodes.append(node)

    # Look for connections/associations
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]

        if "association" in tag.lower() or "connection" in tag.lower() or "nozzle" in tag.lower():
            elem_id = elem.get("ID") or elem.get("id")
            from_ref = elem.get("FromID") or elem.get("From") or elem.get("Source")
            to_ref = elem.get("ToID") or elem.get("To") or elem.get("Target")

            if elem_id and from_ref and to_ref:
                edge = {
                    "@id": f"pid:{elem_id}",
                    "@type": "pid:Connection",
                    "connectedTo": [f"pid:{from_ref}", f"pid:{to_ref}"],
                }
                edges.append(edge)

    # Build JSON-LD structure
    jsonld = {
        "@context": {
            "pid": "https://example.com/pid#",
            "schema": "https://schema.org/",
            "connectedTo": {"@id": "pid:connectedTo", "@type": "@id"},
            "name": "schema:name",
            "tag": "pid:tag",
            "dexpiClass": "pid:dexpiClass",
            "x": "pid:x",
            "y": "pid:y",
        },
        "@graph": nodes + edges,
    }

    return jsonld


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert DEXPI XML files to JSON-LD format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert DEXPI XML to JSON-LD
  python src/dexpi_reader.py dexpi_example.xml

  # Specify output file
  python src/dexpi_reader.py dexpi_example.xml -o pnid_dexpi.json
        """,
    )
    parser.add_argument("input", type=Path, help="Path to DEXPI XML file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to output JSON-LD file (default: input with .json extension)",
    )

    args = parser.parse_args()

    try:
        # Parse DEXPI XML
        jsonld = parse_dexpi_xml(args.input)

        # Determine output path
        output_path = args.output or args.input.with_suffix(".json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON-LD
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(jsonld, f, indent=2)

        # Print statistics
        graph = jsonld.get("@graph", [])
        nodes = [n for n in graph if n.get("@type") != "pid:Connection"]
        edges = [n for n in graph if n.get("@type") == "pid:Connection"]

        print(f"\n✅ Successfully converted DEXPI to JSON-LD")
        print(f"   Components: {len(nodes)}")
        print(f"   Connections: {len(edges)}")
        print(f"   Output: {output_path}")

        sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
