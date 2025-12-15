#!/usr/bin/env python3
"""
Compare two JSON-LD P&ID files and report differences.

This script compares two P&ID JSON-LD files that are expected to be roughly equal
(e.g., original vs. extracted, or two extraction methods) and reports:
- Missing/added components
- Component attribute differences (type, position, name)
- Missing/added connections
- Connection endpoint differences

Usage:
    python src/compare_pnid_jsonld.py <file1.json> <file2.json>
    python src/compare_pnid_jsonld.py data/output/pnid_base.json data/variations/var_001.json
    python src/compare_pnid_jsonld.py <file1.json> <file2.json> --json
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ComponentDiff:
    """Differences in a single component."""

    id: str
    type_diff: tuple[str | None, str | None] | None = None
    name_diff: tuple[str | None, str | None] | None = None
    position_diff: tuple[tuple[float, float] | None, tuple[float, float] | None] | None = None
    other_diffs: dict[str, tuple[Any, Any]] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Complete comparison result between two P&IDs."""

    file1: str
    file2: str
    components_only_in_1: list[dict[str, Any]] = field(default_factory=list)
    components_only_in_2: list[dict[str, Any]] = field(default_factory=list)
    component_diffs: list[ComponentDiff] = field(default_factory=list)
    connections_only_in_1: list[dict[str, Any]] = field(default_factory=list)
    connections_only_in_2: list[dict[str, Any]] = field(default_factory=list)
    connection_diffs: list[dict[str, Any]] = field(default_factory=list)

    def has_differences(self) -> bool:
        """Check if any differences exist."""
        return bool(
            self.components_only_in_1
            or self.components_only_in_2
            or self.component_diffs
            or self.connections_only_in_1
            or self.connections_only_in_2
            or self.connection_diffs
        )


def load_jsonld(path: Path) -> dict[str, Any]:
    """Load JSON-LD P&ID file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_components(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract components as dict keyed by @id."""
    components = {}
    graph = data.get("@graph", [])
    for item in graph:
        if item.get("@type") not in ["pnid:Connection", "pnid:Pipe"]:
            comp_id = item.get("@id")
            if comp_id:
                components[comp_id] = item
    return components


def extract_connections(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract connections/pipes from JSON-LD."""
    connections = []
    graph = data.get("@graph", [])
    for item in graph:
        item_type = item.get("@type")
        if item_type in ["pnid:Connection", "pnid:Pipe"]:
            connections.append(item)
    return connections


def normalize_connection(conn: dict[str, Any]) -> tuple[str, str]:
    """Return normalized (source, target) tuple for connection matching."""
    source = conn.get("pnid:connectsFrom", {}).get("@id", "")
    target = conn.get("pnid:connectsTo", {}).get("@id", "")
    # Normalize order (bidirectional edges)
    return tuple(sorted([source, target]))


def get_position(comp: dict[str, Any]) -> tuple[float, float] | None:
    """Extract (x, y) position from component."""
    x = comp.get("pnid:x")
    y = comp.get("pnid:y")
    if x is not None and y is not None:
        return (float(x), float(y))
    return None


def compare_components(
    comps1: dict[str, dict[str, Any]], comps2: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[ComponentDiff]]:
    """
    Compare two component dictionaries.

    Returns:
        - Components only in 1
        - Components only in 2
        - Component differences (for IDs present in both)
    """
    ids1 = set(comps1.keys())
    ids2 = set(comps2.keys())

    only_in_1 = [comps1[cid] for cid in ids1 - ids2]
    only_in_2 = [comps2[cid] for cid in ids2 - ids1]

    diffs = []
    for cid in ids1 & ids2:
        c1 = comps1[cid]
        c2 = comps2[cid]

        diff = ComponentDiff(id=cid)
        has_diff = False

        # Check type
        t1 = c1.get("@type")
        t2 = c2.get("@type")
        if t1 != t2:
            diff.type_diff = (t1, t2)
            has_diff = True

        # Check name
        n1 = c1.get("pnid:name") or c1.get("rdfs:label")
        n2 = c2.get("pnid:name") or c2.get("rdfs:label")
        if n1 != n2:
            diff.name_diff = (n1, n2)
            has_diff = True

        # Check position
        pos1 = get_position(c1)
        pos2 = get_position(c2)
        if pos1 != pos2:
            # Only report if both have positions or positions differ significantly
            if pos1 is not None and pos2 is not None:
                dist = ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
                if dist > 1.0:  # Threshold for "significant" position change
                    diff.position_diff = (pos1, pos2)
                    has_diff = True
            elif pos1 != pos2:
                diff.position_diff = (pos1, pos2)
                has_diff = True

        # Check other attributes (description, category, etc.)
        keys = set(c1.keys()) | set(c2.keys())
        ignore_keys = {"@id", "@type", "pnid:name", "rdfs:label", "pnid:x", "pnid:y"}
        for key in keys - ignore_keys:
            v1 = c1.get(key)
            v2 = c2.get(key)
            if v1 != v2:
                diff.other_diffs[key] = (v1, v2)
                has_diff = True

        if has_diff:
            diffs.append(diff)

    return only_in_1, only_in_2, diffs


def compare_connections(
    conns1: list[dict[str, Any]], conns2: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Compare two connection lists.

    Returns:
        - Connections only in 1
        - Connections only in 2
        - Connection differences (mismatched endpoints with same ID)
    """
    # Build sets of normalized connections
    norm1 = {normalize_connection(c): c for c in conns1}
    norm2 = {normalize_connection(c): c for c in conns2}

    keys1 = set(norm1.keys())
    keys2 = set(norm2.keys())

    only_in_1 = [norm1[k] for k in keys1 - keys2]
    only_in_2 = [norm2[k] for k in keys2 - keys1]

    # For connections in both, check for attribute differences
    conn_diffs = []
    for key in keys1 & keys2:
        c1 = norm1[key]
        c2 = norm2[key]
        # Simple check: if any attribute differs, report it
        if c1 != c2:
            conn_diffs.append({"from_file1": c1, "from_file2": c2})

    return only_in_1, only_in_2, conn_diffs


def compare_pnids(path1: Path, path2: Path) -> ComparisonResult:
    """Compare two JSON-LD P&ID files."""
    data1 = load_jsonld(path1)
    data2 = load_jsonld(path2)

    comps1 = extract_components(data1)
    comps2 = extract_components(data2)

    conns1 = extract_connections(data1)
    conns2 = extract_connections(data2)

    only_c1, only_c2, c_diffs = compare_components(comps1, comps2)
    only_conn1, only_conn2, conn_diffs = compare_connections(conns1, conns2)

    return ComparisonResult(
        file1=str(path1),
        file2=str(path2),
        components_only_in_1=only_c1,
        components_only_in_2=only_c2,
        component_diffs=c_diffs,
        connections_only_in_1=only_conn1,
        connections_only_in_2=only_conn2,
        connection_diffs=conn_diffs,
    )


def print_comparison(result: ComparisonResult) -> None:
    """Print comparison results in a human-readable format."""
    print("=" * 80)
    print("P&ID JSON-LD Comparison")
    print("=" * 80)
    print(f"File 1: {result.file1}")
    print(f"File 2: {result.file2}")
    print()

    if not result.has_differences():
        print("✅ No differences found — P&IDs are identical.")
        return

    print("🔍 DIFFERENCES FOUND\n")

    # Components only in file 1
    if result.components_only_in_1:
        print(f"📦 Components only in File 1 ({len(result.components_only_in_1)}):")
        for comp in result.components_only_in_1:
            comp_id = comp.get("@id", "unknown")
            comp_type = comp.get("@type", "unknown")
            comp_name = comp.get("pnid:name") or comp.get("rdfs:label") or ""
            print(f"  - {comp_id} ({comp_type}) {comp_name}")
        print()

    # Components only in file 2
    if result.components_only_in_2:
        print(f"📦 Components only in File 2 ({len(result.components_only_in_2)}):")
        for comp in result.components_only_in_2:
            comp_id = comp.get("@id", "unknown")
            comp_type = comp.get("@type", "unknown")
            comp_name = comp.get("pnid:name") or comp.get("rdfs:label") or ""
            print(f"  - {comp_id} ({comp_type}) {comp_name}")
        print()

    # Component differences
    if result.component_diffs:
        print(f"🔄 Component Differences ({len(result.component_diffs)}):")
        for diff in result.component_diffs:
            print(f"  Component: {diff.id}")
            if diff.type_diff:
                print(f"    Type:     {diff.type_diff[0]} → {diff.type_diff[1]}")
            if diff.name_diff:
                print(f"    Name:     {diff.name_diff[0]} → {diff.name_diff[1]}")
            if diff.position_diff:
                p1, p2 = diff.position_diff
                if p1 and p2:
                    dist = ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
                    print(f"    Position: {p1} → {p2} (distance: {dist:.2f})")
                else:
                    print(f"    Position: {p1} → {p2}")
            for key, (v1, v2) in diff.other_diffs.items():
                print(f"    {key}: {v1} → {v2}")
            print()

    # Connections only in file 1
    if result.connections_only_in_1:
        print(f"🔗 Connections only in File 1 ({len(result.connections_only_in_1)}):")
        for conn in result.connections_only_in_1:
            src = conn.get("pnid:connectsFrom", {}).get("@id", "?")
            tgt = conn.get("pnid:connectsTo", {}).get("@id", "?")
            conn_id = conn.get("@id", "")
            print(f"  - {src} → {tgt} ({conn_id})")
        print()

    # Connections only in file 2
    if result.connections_only_in_2:
        print(f"🔗 Connections only in File 2 ({len(result.connections_only_in_2)}):")
        for conn in result.connections_only_in_2:
            src = conn.get("pnid:connectsFrom", {}).get("@id", "?")
            tgt = conn.get("pnid:connectsTo", {}).get("@id", "?")
            conn_id = conn.get("@id", "")
            print(f"  - {src} → {tgt} ({conn_id})")
        print()

    # Connection attribute differences
    if result.connection_diffs:
        print(f"🔄 Connection Attribute Differences ({len(result.connection_diffs)}):")
        for diff in result.connection_diffs:
            c1 = diff["from_file1"]
            c2 = diff["from_file2"]
            src1 = c1.get("pnid:connectsFrom", {}).get("@id", "?")
            tgt1 = c1.get("pnid:connectsTo", {}).get("@id", "?")
            print(f"  Connection: {src1} → {tgt1}")
            print(f"    File 1: {c1}")
            print(f"    File 2: {c2}")
        print()

    # Summary
    print("=" * 80)
    print("Summary:")
    print(f"  Components only in File 1: {len(result.components_only_in_1)}")
    print(f"  Components only in File 2: {len(result.components_only_in_2)}")
    print(f"  Components with differences: {len(result.component_diffs)}")
    print(f"  Connections only in File 1: {len(result.connections_only_in_1)}")
    print(f"  Connections only in File 2: {len(result.connections_only_in_2)}")
    print(f"  Connections with differences: {len(result.connection_diffs)}")
    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python src/compare_pnid_jsonld.py <file1.json> <file2.json> [--json]")
        print("\nExample:")
        print(
            "  python src/compare_pnid_jsonld.py data/output/pnid_base.json data/variations/var_001.json"
        )
        print(
            "  python src/compare_pnid_jsonld.py data/output/pnid_base.json data/variations/var_001.json --json"
        )
        sys.exit(1)

    path1 = Path(sys.argv[1])
    path2 = Path(sys.argv[2])
    json_output = "--json" in sys.argv

    if not path1.exists():
        print(f"❌ Error: File not found: {path1}")
        sys.exit(1)

    if not path2.exists():
        print(f"❌ Error: File not found: {path2}")
        sys.exit(1)

    result = compare_pnids(path1, path2)

    if json_output:
        # Output as JSON for programmatic consumption
        output = {
            "file1": result.file1,
            "file2": result.file2,
            "has_differences": result.has_differences(),
            "components_only_in_1": [
                {
                    "id": c.get("@id"),
                    "type": c.get("@type"),
                    "name": c.get("pnid:name") or c.get("rdfs:label"),
                }
                for c in result.components_only_in_1
            ],
            "components_only_in_2": [
                {
                    "id": c.get("@id"),
                    "type": c.get("@type"),
                    "name": c.get("pnid:name") or c.get("rdfs:label"),
                }
                for c in result.components_only_in_2
            ],
            "component_diffs": [
                {
                    "id": d.id,
                    "type_diff": d.type_diff,
                    "name_diff": d.name_diff,
                    "position_diff": d.position_diff,
                    "other_diffs": d.other_diffs,
                }
                for d in result.component_diffs
            ],
            "connections_only_in_1": len(result.connections_only_in_1),
            "connections_only_in_2": len(result.connections_only_in_2),
            "connection_diffs": len(result.connection_diffs),
            "summary": {
                "components_only_in_1": len(result.components_only_in_1),
                "components_only_in_2": len(result.components_only_in_2),
                "components_with_differences": len(result.component_diffs),
                "connections_only_in_1": len(result.connections_only_in_1),
                "connections_only_in_2": len(result.connections_only_in_2),
                "connections_with_differences": len(result.connection_diffs),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print_comparison(result)


if __name__ == "__main__":
    main()
