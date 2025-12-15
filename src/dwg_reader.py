#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal

import ezdxf  # pip install ezdxf

# ---------------------------
# Data structures
# ---------------------------


@dataclass
class PIDNode:
    """A P&ID component (valve, pump, instrument, etc.)."""

    id: str
    type: str  # JSON-LD type IRI (e.g., "pid:Valve")
    name: str | None  # Display name
    tag: str | None  # Tag number / identifier
    layer: str | None
    x: float
    y: float
    block_name: str | None  # DXF block name
    line_number: str | None  # If captured from attributes


@dataclass
class PipeVertex:
    """A vertex in a pipe polyline or endpoint of a line."""

    id: str
    x: float
    y: float
    layer: str | None


@dataclass
class PIDEdge:
    """A connectivity edge between two nodes (via a pipe)."""

    source: str  # PIDNode.id
    target: str  # PIDNode.id
    predicate: str = "pid:connectedTo"  # JSON-LD predicate


# ---------------------------
# Configuration (heuristics)
# ---------------------------

# Map block name patterns to P&ID component types
DEFAULT_BLOCK_NAME_TO_TYPE: list[tuple[str, str]] = [
    (r"\bVALVE\b", "pid:Valve"),
    (r"\bBALLVALVE\b", "pid:BallValve"),
    (r"\bGATEVALVE\b", "pid:GateValve"),
    (r"\bCHECKVALVE\b", "pid:CheckValve"),
    (r"\bPUMP\b", "pid:Pump"),
    (r"\bCOMPRESSOR\b", "pid:Compressor"),
    (r"\bFILTER\b", "pid:Filter"),
    (r"\bSTRAINER\b", "pid:Strainer"),
    (r"\bMETER\b", "pid:FlowMeter"),
    (r"\bINSTR\b", "pid:Instrument"),
    (r"\bTRANSMITTER\b", "pid:Transmitter"),
    (r"\bSENSOR\b", "pid:Sensor"),
    (r"\bFLANGE\b", "pid:Flange"),
    (r"\bTEE\b", "pid:Tee"),
    (r"\bREDUCER\b", "pid:Reducer"),
]

# Layers used to identify pipes
DEFAULT_PIPE_LAYER_PATTERNS: list[str] = [
    r"\bPIPE\b",
    r"\bPROCESS\b",
    r"\bLINE\b",
    r"^PIPING",
]

# Attribute names to harvest from INSERTs
ATTR_PRIORITY = {
    "TAG": "tag",
    "NAME": "name",
    "DESC": "name",
    "DESCRIPTION": "name",
    "LINE": "line_number",
    "LINE_NO": "line_number",
    "LINENO": "line_number",
}


# ---------------------------
# Utility functions
# ---------------------------


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _match_any(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _map_block_type(block_name: str, rules: list[tuple[str, str]]) -> str | None:
    for pattern, type_iri in rules:
        if re.search(pattern, block_name, flags=re.IGNORECASE):
            return type_iri
    return None


# ---------------------------
# Core extraction
# ---------------------------


def extract_nodes_from_inserts(
    doc: ezdxf.EZDXF,
    block_type_rules: list[tuple[str, str]] = DEFAULT_BLOCK_NAME_TO_TYPE,
) -> list[PIDNode]:
    """Extract PID components from INSERT entities (block references)."""
    msp = doc.modelspace()
    nodes: list[PIDNode] = []

    for insert in msp.query("INSERT"):
        block_name: str = insert.dxf.name or ""
        comp_type = _map_block_type(block_name, block_type_rules)
        if not comp_type:
            # Skip blocks we can't classify; you can change this to include all.
            continue

        # Position
        x, y, _ = insert.dxf.insert  # (x, y, z)

        # Harvest attributes
        name: str | None = None
        tag: str | None = None
        line_number: str | None = None

        for attrib in insert.attribs:
            raw_tag = (attrib.dxf.tag or "").strip().upper()
            val_text = (attrib.dxf.text or "").strip()
            if raw_tag in ATTR_PRIORITY:
                field = ATTR_PRIORITY[raw_tag]
                if field == "name":
                    name = name or val_text
                elif field == "tag":
                    tag = tag or val_text
                elif field == "line_number":
                    line_number = line_number or val_text

        # Fallbacks
        if not name and tag:
            name = tag
        if not name and block_name:
            name = block_name

        node = PIDNode(
            id=f"pid:{block_name}_{len(nodes) + 1}",
            type=comp_type,
            name=name,
            tag=tag,
            layer=insert.dxf.layer,
            x=float(x),
            y=float(y),
            block_name=block_name,
            line_number=line_number,
        )
        nodes.append(node)

    return nodes


def extract_pipe_vertices(
    doc: ezdxf.EZDXF,
    pipe_layer_patterns: list[str] = DEFAULT_PIPE_LAYER_PATTERNS,
) -> list[PipeVertex]:
    """Collect endpoints/vertices of pipe geometry from LINE and LWPOLYLINE."""
    msp = doc.modelspace()
    vertices: list[PipeVertex] = []
    counter = 0

    # LINE entities
    for line in msp.query("LINE"):
        layer = line.dxf.layer or ""
        if not _match_any(pipe_layer_patterns, layer):
            continue
        start = (float(line.dxf.start.x), float(line.dxf.start.y))
        end = (float(line.dxf.end.x), float(line.dxf.end.y))
        counter += 1
        vertices.append(PipeVertex(id=f"pipev:{counter}", x=start[0], y=start[1], layer=layer))
        counter += 1
        vertices.append(PipeVertex(id=f"pipev:{counter}", x=end[0], y=end[1], layer=layer))

    # LWPOLYLINE entities
    for pl in msp.query("LWPOLYLINE"):
        layer = pl.dxf.layer or ""
        if not _match_any(pipe_layer_patterns, layer):
            continue
        pts = [(float(x), float(y)) for x, y, *_ in pl.get_points()]
        for x, y in pts:
            counter += 1
            vertices.append(PipeVertex(id=f"pipev:{counter}", x=x, y=y, layer=layer))

    return vertices


def infer_connectivity(
    nodes: list[PIDNode],
    pipe_vertices: list[PipeVertex],
    snap_tolerance: float = 5.0,  # drawing units; tweak per your CAD unit scale
) -> list[PIDEdge]:
    """
    Infer edges by snapping nodes to nearest pipe vertices and connecting
    nodes that share the same snapped vertex (i.e., meet at the same pipe junction).
    """
    edges: list[PIDEdge] = []

    # Map: snapped vertex key -> list of node ids
    junctions: dict[str, list[str]] = {}

    def nearest_vertex_key(x: float, y: float) -> str | None:
        best_key: str | None = None
        best_dist: float = float("inf")
        for v in pipe_vertices:
            d = _distance((x, y), (v.x, v.y))
            if d < best_dist and d <= snap_tolerance:
                best_dist = d
                best_key = f"{round(v.x, 3)}:{round(v.y, 3)}"
        return best_key

    for node in nodes:
        key = nearest_vertex_key(node.x, node.y)
        if key:
            junctions.setdefault(key, []).append(node.id)

    # Create edges for nodes sharing the same junction
    for node_ids in junctions.values():
        if len(node_ids) < 2:
            continue
        # fully connect nodes in the junction (undirected implied)
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                edges.append(PIDEdge(source=node_ids[i], target=node_ids[j]))

    return edges


# ---------------------------
# JSON-LD serialization
# ---------------------------


def make_jsonld(
    nodes: list[PIDNode],
    edges: list[PIDEdge],
    base_context_iri: str = "https://example.com/pid#",
) -> dict:
    """
    Construct a JSON-LD graph for the given nodes and edges.
    """
    context = {
        "@context": {
            "schema": "https://schema.org/",
            "pid": base_context_iri,
            "connectedTo": {"@id": "pid:connectedTo", "@type": "@id"},
            "name": "schema:name",
            "tag": "pid:tag",
            "lineNumber": "pid:lineNumber",
            "layer": "pid:layer",
            "blockName": "pid:blockName",
            "x": "pid:x",
            "y": "pid:y",
        }
    }

    graph: list[dict] = []

    for n in nodes:
        graph.append(
            {
                "@id": n.id,
                "@type": n.type,
                "name": n.name,
                "tag": n.tag,
                "lineNumber": n.line_number,
                "layer": n.layer,
                "blockName": n.block_name,
                "x": n.x,
                "y": n.y,
            }
        )

    for e in edges:
        graph.append(
            {
                "@id": f"{e.source}--{e.target}",
                "@type": "pid:Connection",
                "connectedTo": [e.source, e.target],
            }
        )

    context["@graph"] = graph
    return context


# ---------------------------
# DWG → DXF (optional)
# ---------------------------


def maybe_convert_dwg_to_dxf(input_path: Path) -> Path:
    """
    If input is DWG, use dwg2dxf to convert and return the DXF path.
    Otherwise, return the original path.
    """
    if input_path.suffix.lower() != ".dwg":
        return input_path

    dxf_path = input_path.with_suffix(".dxf")
    if dxf_path.exists():
        return dxf_path

    # dwg2dxf syntax: dwg2dxf <input> [-b] <-version> <output>
    # Using -v2007 as a reasonable default version
    cmd = ["dwg2dxf", str(input_path), "-v2007", str(dxf_path)]
    subprocess.run(cmd, check=True)
    return dxf_path


# ---------------------------
# CLI
# ---------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert DXF (or DWG via dwg2dxf) P&ID to JSON-LD (heuristic)."
    )
    parser.add_argument("input", type=Path, help="Path to DXF (or DWG) file.")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON-LD file path.")
    parser.add_argument(
        "--snap",
        type=float,
        default=5.0,
        help="Snap tolerance (drawing units) for node-to-pipe junction.",
    )
    parser.add_argument(
        "--context",
        type=str,
        default="https://example.com/pid#",
        help="Base IRI for the JSON-LD pid: namespace.",
    )
    parser.add_argument(
        "--include-unknown-blocks",
        action="store_true",
        help="Include blocks with unknown types as pid:Component.",
    )
    parser.add_argument(
        "--pipe-layer-pattern",
        action="append",
        default=None,
        help="Regex pattern for pipe layers (can be passed multiple times).",
    )
    parser.add_argument(
        "--type-rule",
        action="append",
        default=None,
        help="Add block type rule as 'regex=pid:Type' (can be passed multiple times).",
    )
    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    # DWG → DXF if needed
    dxf_path = maybe_convert_dwg_to_dxf(input_path)

    # Load DXF
    doc = ezdxf.readfile(str(dxf_path))

    # Build type rules
    type_rules = list(DEFAULT_BLOCK_NAME_TO_TYPE)
    if args.type_rule:
        for rule in args.type_rule:
            if "=" not in rule:
                raise ValueError("type-rule must look like 'regex=pid:Type'")
            regex, iri = rule.split("=", 1)
            type_rules.append((regex, iri))

    # Extract nodes
    nodes = extract_nodes_from_inserts(doc, block_type_rules=type_rules)

    # Optionally include unknown blocks
    if args.include_unknown_blocks:
        msp = doc.modelspace()
        for insert in msp.query("INSERT"):
            block_name = insert.dxf.name or ""
            if _map_block_type(block_name, type_rules):
                continue
            x, y, _ = insert.dxf.insert
            name = block_name
            nodes.append(
                PIDNode(
                    id=f"pid:{block_name}_{len(nodes) + 1}",
                    type="pid:Component",
                    name=name,
                    tag=None,
                    layer=insert.dxf.layer,
                    x=float(x),
                    y=float(y),
                    block_name=block_name,
                    line_number=None,
                )
            )

    # Pipe vertices
    pipe_patterns = args.pipe_layer_pattern or DEFAULT_PIPE_LAYER_PATTERNS
    pipe_vertices = extract_pipe_vertices(doc, pipe_layer_patterns=pipe_patterns)

    # Connectivity
    edges = infer_connectivity(nodes, pipe_vertices, snap_tolerance=args.snap)

    # JSON-LD
    jsonld_obj = make_jsonld(nodes, edges, base_context_iri=args.context)

    # Write output
    out_path = args.output or dxf_path.with_suffix(".jsonld")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(jsonld_obj, f, indent=2)

    print(f"Nodes: {len(nodes)}, Edges: {len(edges)}")
    print(f"JSON-LD written to: {out_path}")


if __name__ == "__main__":
    main()
