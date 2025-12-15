#!/usr/bin/env python3
"""
Add missing explicit edges to a merged PNID JSON.

This script ensures three important deterministic connections exist in the
merged PNID produced by earlier processing:

  - Hot water tank -> MAK    (HWT-1 -> MAK-1)
  - Hot water tank -> MAT    (HWT-1 -> MAT-1)
  - Glycol valve -> WT       (V-1 -> WT-1)

It reads `data/output/pnid_merged.json` (the merged LLM + skeleton output),
adds the missing pipes if they are not already present, and writes out a
new file `data/output/pnid_merged_fixed.json`.

Behavior:
- If a component id is not found, the script will still add the pipe but will
  leave source/target as given (it will not rename or invent components).
- If a pipe with the same (source, target) already exists, the script does not
  add a duplicate.
- New pipes get a conservative label ("Hot Water", "Glycol") and a short
  description. X/Y coordinates are computed as the midpoint between component
  coordinates when available; otherwise omitted.

This is intended as a minimal, deterministic post-processing patch to restore
critical connections without altering the rest of the merged PNID structure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Component:
    id: str
    x: float | None = None
    y: float | None = None
    label: str | None = None
    raw: Dict[str, Any] | None = None


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_component_index(components: List[Dict[str, Any]]) -> Dict[str, Component]:
    idx: Dict[str, Component] = {}
    for c in components:
        cid = c.get("id") or c.get("label")
        if not cid:
            continue
        x = c.get("x")
        y = c.get("y")
        label = c.get("label")
        comp = Component(
            id=str(cid),
            x=float(x) if x is not None else None,
            y=float(y) if y is not None else None,
            label=label,
            raw=c,
        )
        idx[comp.id] = comp
    return idx


def pipe_exists(pipes: List[Dict[str, Any]], source: str, target: str) -> bool:
    for p in pipes:
        s = p.get("source") or p.get("from") or p.get("src")
        t = p.get("target") or p.get("to") or p.get("dst")
        if s == source and t == target:
            return True
    return False


def midpoint(a: Tuple[float, float], b: Tuple[float, float]) -> Tuple[float, float]:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def safe_add_pipe(pipes: List[Dict[str, Any]], pipe: Dict[str, Any]) -> None:
    """
    Append a pipe dictionary to the list. This function does not deduplicate:
    deduplication should be done by caller using pipe_exists.
    """
    pipes.append(pipe)


def create_minimal_pipe(
    source: str, target: str, label: str, description: str, pos: Tuple[float, float] | None = None
) -> Dict[str, Any]:
    pipe: Dict[str, Any] = {
        "label": label,
        "source": source,
        "target": target,
        "description": description,
    }
    if pos is not None:
        pipe["x"] = float(pos[0])
        pipe["y"] = float(pos[1])
    return pipe


def main() -> None:
    base = Path(__file__).resolve().parent.parent
    merged_path = base / "data" / "output" / "pnid_merged.json"
    if not merged_path.exists():
        # fall back to enhanced version if merged not present
        merged_path = base / "data" / "output" / "pnid_enhanced.json"

    if not merged_path.exists():
        raise FileNotFoundError(
            f"No merged PNID found at expected locations. Checked: {merged_path}"
        )

    data = load_json(merged_path)

    components = data.get("components", [])
    pipes = data.get("pipes", [])

    comp_index = build_component_index(components)

    # Define the three edges we want to ensure exist
    desired_edges = [
        ("HWT-1", "MAK-1", "Hot Water", "Hot water feed from HWT to MAK"),
        ("HWT-1", "MAT-1", "Hot Water", "Hot water feed from HWT to MAT"),
        ("V-1", "WT-1", "Glycol", "Glycol cooling path from V-1 to WT-1"),
    ]

    added = 0
    for source, target, label, desc in desired_edges:
        if pipe_exists(pipes, source, target):
            # already present in merged graph; skip
            continue

        # attempt to compute a midpoint using component positions
        pos = None
        comp_s = comp_index.get(source)
        comp_t = comp_index.get(target)
        if (
            comp_s
            and comp_t
            and comp_s.x is not None
            and comp_s.y is not None
            and comp_t.x is not None
            and comp_t.y is not None
        ):
            pos = midpoint((comp_s.x, comp_s.y), (comp_t.x, comp_t.y))
        elif comp_s and comp_s.x is not None and comp_s.y is not None:
            pos = (comp_s.x, comp_s.y)
        elif comp_t and comp_t.x is not None and comp_t.y is not None:
            pos = (comp_t.x, comp_t.y)

        new_pipe = create_minimal_pipe(
            source=source,
            target=target,
            label=label,
            description=desc,
            pos=pos,
        )
        safe_add_pipe(pipes, new_pipe)
        added += 1

    # Update data and write out a fixed merged file
    data["pipes"] = pipes
    out_path = base / "data" / "output" / "pnid_merged_fixed.json"
    save_json(data, out_path)

    # Print summary to user
    print("Merged PNID input:", merged_path)
    print("Output with fixed edges:", out_path)
    print(f"Components: {len(components)}")
    print(f"Pipes before add (approx): {len(pipes) - added}")
    print(f"Pipes added: {added}")
    print(
        "If you still see connectivity issues, run the skeleton path mapping and inspect specific component-to-node snapping distances."
    )


# Run main immediately (script intended to be executed)
main()
