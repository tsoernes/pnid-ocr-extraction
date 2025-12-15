#!/usr/bin/env python3
"""
Generate variations of the C01 Reference P&ID with controlled differences.

This script creates multiple P&ID variants from the DEXPI C01 Reference P&ID,
introducing controlled variations for testing extraction algorithms:
- Add extra components
- Remove random components
- Remove random edges (connections)
- Modify component names
- Perturb component positions
- Change component types

Usage:
    python src/generate_pnid_variations.py -i data/output/pnid_dexpi_final.json -o data/variations/ -n 20
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


def load_pnid(path: Path) -> dict[str, Any]:
    """Load P&ID from JSON-LD file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_pnid(pnid: dict[str, Any], path: Path) -> None:
    """Save P&ID to JSON-LD file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(pnid, f, indent=2)


def separate_nodes_edges(graph: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate graph into nodes and edges."""
    nodes = [n for n in graph if n.get("@type") != "pid:Connection"]
    edges = [e for e in graph if e.get("@type") == "pid:Connection"]
    return nodes, edges


def add_random_components(pnid: dict[str, Any], count: int = 3) -> dict[str, Any]:
    """Add random components to the P&ID."""
    pnid = json.loads(json.dumps(pnid))  # Deep copy
    graph = pnid["@graph"]
    nodes, edges = separate_nodes_edges(graph)

    # Component types to add
    component_types = [
        ("pid:Valve", "VALVE"),
        ("pid:Pump", "PUMP"),
        ("pid:Tank", "TANK"),
        ("pid:FlowMeter", "FM"),
        ("pid:Instrument", "INSTR"),
    ]

    # Find max coordinates
    max_x = max((n.get("x", 0) or 0 for n in nodes), default=300)
    max_y = max((n.get("y", 0) or 0 for n in nodes), default=300)

    next_id = len(nodes) + 1

    for i in range(count):
        comp_type, prefix = random.choice(component_types)
        new_comp = {
            "@id": f"pid:Added{prefix}-{next_id + i}",
            "@type": comp_type,
            "name": f"{prefix}-{next_id + i}",
            "dexpiClass": f"Added{prefix}",
            "x": random.uniform(50, max_x + 50),
            "y": random.uniform(50, max_y + 50),
        }
        graph.append(new_comp)

    pnid["@graph"] = graph
    return pnid


def remove_random_components(pnid: dict[str, Any], count: int = 5) -> dict[str, Any]:
    """Remove random components from the P&ID."""
    pnid = json.loads(json.dumps(pnid))  # Deep copy
    graph = pnid["@graph"]
    nodes, edges = separate_nodes_edges(graph)

    if len(nodes) <= count:
        count = max(1, len(nodes) // 2)

    # Select random nodes to remove
    to_remove = random.sample(nodes, count)
    remove_ids = {n["@id"] for n in to_remove}

    # Remove nodes and their associated edges
    new_graph = []
    for item in graph:
        if item["@id"] in remove_ids:
            continue
        if item.get("@type") == "pid:Connection":
            connected = item.get("connectedTo", [])
            if any(node_id in remove_ids for node_id in connected):
                continue
        new_graph.append(item)

    pnid["@graph"] = new_graph
    return pnid


def remove_random_edges(pnid: dict[str, Any], fraction: float = 0.3) -> dict[str, Any]:
    """Remove a fraction of random edges from the P&ID."""
    pnid = json.loads(json.dumps(pnid))  # Deep copy
    graph = pnid["@graph"]
    nodes, edges = separate_nodes_edges(graph)

    if not edges:
        return pnid

    count = max(1, int(len(edges) * fraction))
    # Sample edges and collect their IDs (avoid trying to put dicts into a set)
    sampled_edges = random.sample(edges, min(count, len(edges)))
    remove_ids = {e["@id"] for e in sampled_edges if "@id" in e}

    # Remove only connection objects whose @id is in remove_ids
    new_graph = []
    for item in graph:
        if item.get("@type") == "pid:Connection" and item.get("@id") in remove_ids:
            continue
        new_graph.append(item)

    pnid["@graph"] = new_graph
    return pnid


def modify_component_names(pnid: dict[str, Any], fraction: float = 0.5) -> dict[str, Any]:
    """Modify component names randomly."""
    pnid = json.loads(json.dumps(pnid))  # Deep copy
    graph = pnid["@graph"]
    nodes, edges = separate_nodes_edges(graph)

    count = int(len(nodes) * fraction)
    to_modify = random.sample(nodes, min(count, len(nodes)))

    suffixes = ["_MOD", "_ALT", "_V2", "_NEW", ""]
    prefixes = ["NEW_", "ALT_", ""]

    for node in to_modify:
        original_name = node.get("name", "COMPONENT")
        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)
        node["name"] = f"{prefix}{original_name}{suffix}"

    pnid["@graph"] = graph
    return pnid


def perturb_positions(pnid: dict[str, Any], max_offset: float = 20.0) -> dict[str, Any]:
    """Randomly perturb component positions."""
    pnid = json.loads(json.dumps(pnid))  # Deep copy
    graph = pnid["@graph"]

    for node in graph:
        if node.get("@type") == "pid:Connection":
            continue

        x = node.get("x")
        y = node.get("y")

        if x is not None and y is not None:
            node["x"] = x + random.uniform(-max_offset, max_offset)
            node["y"] = y + random.uniform(-max_offset, max_offset)

    pnid["@graph"] = graph
    return pnid


def change_component_types(pnid: dict[str, Any], fraction: float = 0.2) -> dict[str, Any]:
    """Randomly change component types."""
    pnid = json.loads(json.dumps(pnid))  # Deep copy
    graph = pnid["@graph"]
    nodes, edges = separate_nodes_edges(graph)

    component_types = [
        "pid:Valve",
        "pid:Pump",
        "pid:Tank",
        "pid:FlowMeter",
        "pid:Instrument",
        "pid:HeatExchanger",
        "pid:Component",
    ]

    count = int(len(nodes) * fraction)
    to_modify = random.sample(nodes, min(count, len(nodes)))

    for node in to_modify:
        node["@type"] = random.choice(component_types)

    pnid["@graph"] = graph
    return pnid


def generate_variation(
    base_pnid: dict[str, Any],
    variation_type: str,
    intensity: str = "medium",
) -> dict[str, Any]:
    """
    Generate a single P&ID variation.

    Args:
        base_pnid: Base P&ID to modify
        variation_type: Type of variation to apply
        intensity: 'low', 'medium', or 'high'

    Returns:
        Modified P&ID
    """
    intensity_params = {
        "low": {
            "add": 1,
            "remove": 2,
            "edge_frac": 0.1,
            "name_frac": 0.2,
            "pos_offset": 5.0,
            "type_frac": 0.1,
        },
        "medium": {
            "add": 3,
            "remove": 5,
            "edge_frac": 0.3,
            "name_frac": 0.5,
            "pos_offset": 15.0,
            "type_frac": 0.2,
        },
        "high": {
            "add": 8,
            "remove": 10,
            "edge_frac": 0.5,
            "name_frac": 0.7,
            "pos_offset": 30.0,
            "type_frac": 0.4,
        },
    }

    params = intensity_params[intensity]

    if variation_type == "add_components":
        return add_random_components(base_pnid, count=params["add"])

    elif variation_type == "remove_components":
        return remove_random_components(base_pnid, count=params["remove"])

    elif variation_type == "remove_edges":
        return remove_random_edges(base_pnid, fraction=params["edge_frac"])

    elif variation_type == "modify_names":
        return modify_component_names(base_pnid, fraction=params["name_frac"])

    elif variation_type == "perturb_positions":
        return perturb_positions(base_pnid, max_offset=params["pos_offset"])

    elif variation_type == "change_types":
        return change_component_types(base_pnid, fraction=params["type_frac"])

    elif variation_type == "combined_light":
        # Apply multiple light modifications
        modified = add_random_components(base_pnid, count=params["add"] // 2)
        modified = remove_random_edges(modified, fraction=params["edge_frac"] / 2)
        modified = modify_component_names(modified, fraction=params["name_frac"] / 2)
        return perturb_positions(modified, max_offset=params["pos_offset"] / 2)

    elif variation_type == "combined_heavy":
        # Apply multiple heavy modifications
        modified = add_random_components(base_pnid, count=params["add"])
        modified = remove_random_components(modified, count=params["remove"] // 2)
        modified = remove_random_edges(modified, fraction=params["edge_frac"])
        modified = modify_component_names(modified, fraction=params["name_frac"])
        modified = perturb_positions(modified, max_offset=params["pos_offset"])
        return change_component_types(modified, fraction=params["type_frac"])

    else:
        raise ValueError(f"Unknown variation type: {variation_type}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate P&ID variations for testing extraction algorithms.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Variation Types:
  add_components      Add random new components
  remove_components   Remove random components
  remove_edges        Remove random connections
  modify_names        Change component names
  perturb_positions   Randomly shift component positions
  change_types        Change component types
  combined_light      Apply multiple light modifications
  combined_heavy      Apply multiple heavy modifications

Intensity Levels:
  low                 Minimal changes (1-2 components, 10% edges)
  medium              Moderate changes (3-5 components, 30% edges)
  high                Heavy changes (8-10 components, 50% edges)

Examples:
  # Generate 10 variations with different types
  python src/generate_pnid_variations.py -i pnid.json -o data/variations/ -n 10

  # Generate 5 heavy combined variations
  python src/generate_pnid_variations.py -i pnid.json -o data/variations/ -n 5 --type combined_heavy --intensity high

  # Generate one of each variation type
  python src/generate_pnid_variations.py -i pnid.json -o data/variations/ --all-types
        """,
    )
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input P&ID JSON-LD file")
    parser.add_argument(
        "-o", "--output", type=Path, required=True, help="Output directory for variations"
    )
    parser.add_argument(
        "-n", "--num-variations", type=int, default=10, help="Number of variations to generate"
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        choices=[
            "add_components",
            "remove_components",
            "remove_edges",
            "modify_names",
            "perturb_positions",
            "change_types",
            "combined_light",
            "combined_heavy",
        ],
        help="Specific variation type (if not specified, random)",
    )
    parser.add_argument(
        "--intensity",
        type=str,
        default="medium",
        choices=["low", "medium", "high"],
        help="Intensity of modifications (default: medium)",
    )
    parser.add_argument(
        "--all-types",
        action="store_true",
        help="Generate one variation of each type (ignores -n)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")

    args = parser.parse_args()

    # Set random seed
    if args.seed is not None:
        random.seed(args.seed)

    try:
        # Load base P&ID
        print(f"Loading base P&ID: {args.input}")
        base_pnid = load_pnid(args.input)

        base_graph = base_pnid.get("@graph", [])
        base_nodes, base_edges = separate_nodes_edges(base_graph)
        print(f"  Components: {len(base_nodes)}")
        print(f"  Connections: {len(base_edges)}")

        # Determine variation types to generate
        if args.all_types:
            variation_types = [
                "add_components",
                "remove_components",
                "remove_edges",
                "modify_names",
                "perturb_positions",
                "change_types",
                "combined_light",
                "combined_heavy",
            ]
            num_variations = len(variation_types)
        else:
            variation_types = [args.type] * args.num_variations if args.type else None
            num_variations = args.num_variations

        print(f"\nGenerating {num_variations} variations...")

        # Generate variations
        for i in range(num_variations):
            if variation_types:
                var_type = variation_types[i]
            else:
                # Random variation type
                var_type = random.choice(
                    [
                        "add_components",
                        "remove_components",
                        "remove_edges",
                        "modify_names",
                        "perturb_positions",
                        "change_types",
                        "combined_light",
                        "combined_heavy",
                    ]
                )

            # Generate variation
            variant = generate_variation(base_pnid, var_type, intensity=args.intensity)

            # Generate filename
            if args.all_types:
                filename = f"pnid_c01_var_{var_type}_{args.intensity}.json"
            else:
                filename = f"pnid_c01_var_{i + 1:03d}_{var_type}_{args.intensity}.json"

            output_path = args.output / filename

            # Save variation
            save_pnid(variant, output_path)

            # Print stats
            var_graph = variant.get("@graph", [])
            var_nodes, var_edges = separate_nodes_edges(var_graph)

            delta_nodes = len(var_nodes) - len(base_nodes)
            delta_edges = len(var_edges) - len(base_edges)

            print(
                f"  [{i + 1:2}/{num_variations}] {filename:50} "
                f"({len(var_nodes):2} components {delta_nodes:+3}, {len(var_edges):2} edges {delta_edges:+3})"
            )

        print(f"\n✅ Successfully generated {num_variations} P&ID variations")
        print(f"   Output directory: {args.output}")

        # Generate index file
        index_path = args.output / "index.json"
        index_data = {
            "base_pnid": str(args.input),
            "num_variations": num_variations,
            "intensity": args.intensity,
            "base_stats": {"components": len(base_nodes), "connections": len(base_edges)},
            "variations": [],
        }

        for i in range(num_variations):
            if args.all_types:
                var_type = variation_types[i]
                filename = f"pnid_c01_var_{var_type}_{args.intensity}.json"
            else:
                var_type = variation_types[i] if variation_types else "random"
                filename = f"pnid_c01_var_{i + 1:03d}_{var_type}_{args.intensity}.json"

            var_path = args.output / filename
            if var_path.exists():
                variant = load_pnid(var_path)
                var_graph = variant.get("@graph", [])
                var_nodes, var_edges = separate_nodes_edges(var_graph)

                index_data["variations"].append(
                    {
                        "filename": filename,
                        "type": var_type,
                        "intensity": args.intensity,
                        "components": len(var_nodes),
                        "connections": len(var_edges),
                        "delta_components": len(var_nodes) - len(base_nodes),
                        "delta_connections": len(var_edges) - len(base_edges),
                    }
                )

        with index_path.open("w") as f:
            json.dump(index_data, f, indent=2)

        print(f"   Index file: {index_path}")

        sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
