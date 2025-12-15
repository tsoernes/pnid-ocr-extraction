#!/usr/bin/env python3
"""
LLM-based P&ID comparison using GPT-4.5 with reasoning.

This script converts JSON-LD P&IDs to a text format suitable for LLM analysis,
then uses GPT-4.5 with high reasoning effort to perform intelligent comparison.
Position/coordinate differences are ignored.

Usage:
    python src/compare_pnid_llm.py <file1.json> <file2.json>
    python src/compare_pnid_llm.py <file1.json> <file2.json> --reasoning high
    python src/compare_pnid_llm.py <file1.json> <file2.json> --json
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class ComponentSummary(BaseModel):
    """Component summary for LLM comparison."""

    id: str
    type: str
    name: str | None
    category: str | None
    description: str | None


class ConnectionSummary(BaseModel):
    """Connection summary for LLM comparison."""

    source: str
    target: str
    label: str | None


class ComponentChange(BaseModel):
    """Represents a change to a component."""

    id: str
    changes: list[str]


class ConnectionChange(BaseModel):
    """Represents a change to a connection."""

    connection: str
    changes: list[str]


class ComparisonResult(BaseModel):
    """Structured comparison result from LLM."""

    summary: str = Field(description="High-level overview of differences")
    components_only_in_1: list[str] = Field(
        default_factory=list, description="Component IDs only in P&ID 1"
    )
    components_only_in_2: list[str] = Field(
        default_factory=list, description="Component IDs only in P&ID 2"
    )
    components_changed: list[ComponentChange] = Field(
        default_factory=list, description="Components with changed attributes"
    )
    connections_only_in_1: list[str] = Field(
        default_factory=list, description="Connections only in P&ID 1"
    )
    connections_only_in_2: list[str] = Field(
        default_factory=list, description="Connections only in P&ID 2"
    )
    connections_changed: list[ConnectionChange] = Field(
        default_factory=list, description="Connections with changed endpoints"
    )
    impact_assessment: str = Field(description="What these differences mean for the process")
    equivalent: bool = Field(description="Whether P&IDs should be considered equivalent")
    confidence: str = Field(description="Confidence level: high, medium, or low")
    recommendations: str = Field(description="Recommendations based on the comparison")


def load_jsonld(path: Path) -> dict[str, Any]:
    """Load JSON-LD P&ID file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_component_summary(comp: dict[str, Any]) -> ComponentSummary:
    """Extract component information (excluding position)."""
    comp_id = comp.get("@id", "unknown")
    comp_type = comp.get("@type", "unknown")
    name = comp.get("pnid:name") or comp.get("rdfs:label") or comp.get("name")
    category = comp.get("pnid:category") or comp.get("dexpiClass")
    description = comp.get("pnid:description") or comp.get("description")

    return ComponentSummary(
        id=comp_id,
        type=comp_type,
        name=name,
        category=category,
        description=description,
    )


def extract_connection_summary(conn: dict[str, Any]) -> ConnectionSummary:
    """Extract connection information."""
    source = conn.get("pnid:connectsFrom", {}).get("@id", "unknown")
    target = conn.get("pnid:connectsTo", {}).get("@id", "unknown")
    label = conn.get("pnid:label") or conn.get("rdfs:label")

    return ConnectionSummary(source=source, target=target, label=label)


def pnid_to_text(data: dict[str, Any]) -> str:
    """
    Convert JSON-LD P&ID to structured text format for LLM analysis.
    Excludes position/coordinate information.
    """
    lines = []
    lines.append("# P&ID Structure")
    lines.append("")

    # Extract components
    graph = data.get("@graph", [])
    components = []
    connections = []

    for item in graph:
        item_type = item.get("@type")
        if item_type in ["pnid:Connection", "pnid:Pipe"]:
            connections.append(extract_connection_summary(item))
        elif item_type not in ["pnid:Connection", "pnid:Pipe"]:
            components.append(extract_component_summary(item))

    # Format components
    lines.append(f"## Components ({len(components)})")
    lines.append("")
    for comp in sorted(components, key=lambda c: c.id):
        lines.append(f"### {comp.id}")
        lines.append(f"- Type: {comp.type}")
        if comp.name:
            lines.append(f"- Name: {comp.name}")
        if comp.category:
            lines.append(f"- Category: {comp.category}")
        if comp.description:
            lines.append(f"- Description: {comp.description}")
        lines.append("")

    # Format connections
    lines.append(f"## Connections ({len(connections)})")
    lines.append("")
    for conn in sorted(connections, key=lambda c: (c.source, c.target)):
        label_str = f" [{conn.label}]" if conn.label else ""
        lines.append(f"- {conn.source} → {conn.target}{label_str}")

    return "\n".join(lines)


def compare_with_llm(
    text1: str, text2: str, file1: str, file2: str, reasoning_effort: str = "high"
) -> dict[str, Any]:
    """
    Use GPT-4.5 with reasoning to compare two P&ID text representations.

    Args:
        text1: Text representation of first P&ID
        text2: Text representation of second P&ID
        file1: Path to first file (for reference)
        file2: Path to second file (for reference)
        reasoning_effort: OpenAI reasoning effort (low, medium, high)

    Returns:
        dict with comparison results
    """
    # Initialize Azure OpenAI client
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_AI_API_KEY")
    if not api_key:
        raise ValueError(
            "AZURE_OPENAI_API_KEY or AZURE_AI_API_KEY not found in environment. "
            "Please set it in .env file or environment variables."
        )

    endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT", "https://aif-minside.cognitiveservices.azure.com/"
    )
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.1")

    client = AzureOpenAI(
        api_key=api_key,
        api_version="2024-12-01-preview",
        azure_endpoint=endpoint,
    )

    # Construct comparison prompt
    prompt = f"""You are an expert in Process & Instrumentation Diagrams (P&IDs). Compare the two P&ID structures below and identify meaningful differences.

**IGNORE:**
- Position/coordinate differences (not included in the data)
- Trivial formatting differences
- Order of components (focus on presence/absence)

**FOCUS ON:**
- Missing or added components
- Changes in component types
- Changes in component names or categories
- Missing or added connections
- Changes in connection endpoints
- Semantic differences that affect the process flow

**P&ID 1: {file1}**
```
{text1}
```

**P&ID 2: {file2}**
```
{text2}
```

Provide a structured comparison with:
1. Summary: High-level overview of differences
2. Components Analysis:
   - Components only in P&ID 1
   - Components only in P&ID 2
   - Components with changed attributes
3. Connections Analysis:
   - Connections only in P&ID 1
   - Connections only in P&ID 2
   - Connections with changed endpoints
4. Impact Assessment: What do these differences mean for the process?
5. Recommendations: Should these P&IDs be considered equivalent?

Be precise and thorough in your analysis.
"""

    # Call GPT-4.5 with reasoning using structured outputs
    try:
        response = client.beta.chat.completions.parse(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert P&ID analyst. Provide precise, structured comparisons in JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
            reasoning_effort=reasoning_effort,
            response_format=ComparisonResult,
        )

        # Extract parsed response (already structured as Pydantic model)
        message = response.choices[0].message
        parsed = message.parsed

        if not parsed:
            raise ValueError("Empty response from LLM")

        # Convert to dict for compatibility with rest of code
        result = parsed.model_dump()

        # Add metadata
        result["file1"] = file1
        result["file2"] = file2
        result["model"] = deployment
        result["reasoning_effort"] = reasoning_effort
        # Try to get reasoning tokens
        usage_details = getattr(response.usage, "completion_tokens_details", None)
        if usage_details:
            result["reasoning_tokens"] = getattr(usage_details, "reasoning_tokens", 0)
        else:
            result["reasoning_tokens"] = 0
        result["total_tokens"] = response.usage.total_tokens

        return result

    except json.JSONDecodeError as e:
        print(f"⚠️  Warning: LLM returned non-JSON response. Raw output:", file=sys.stderr)
        print(content, file=sys.stderr)
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"LLM comparison failed: {e}")


def print_comparison_results(result: dict[str, Any]) -> None:
    """Print comparison results in human-readable format."""
    print("=" * 80)
    print("LLM-Based P&ID Comparison")
    print("=" * 80)
    print(f"File 1: {result['file1']}")
    print(f"File 2: {result['file2']}")
    print(f"Model: {result['model']}")
    print(f"Reasoning Effort: {result['reasoning_effort']}")
    print(f"Tokens: {result['total_tokens']} (reasoning: {result.get('reasoning_tokens', 0)})")
    print()

    print("📊 SUMMARY")
    print("-" * 80)
    print(result.get("summary", "No summary provided"))
    print()

    # Components
    comp_only_1 = result.get("components_only_in_1", [])
    comp_only_2 = result.get("components_only_in_2", [])
    comp_changed = result.get("components_changed", [])

    if comp_only_1:
        print(f"📦 Components only in File 1 ({len(comp_only_1)}):")
        for comp in comp_only_1:
            print(f"  - {comp}")
        print()

    if comp_only_2:
        print(f"📦 Components only in File 2 ({len(comp_only_2)}):")
        for comp in comp_only_2:
            print(f"  - {comp}")
        print()

    if comp_changed:
        print(f"🔄 Components with Changes ({len(comp_changed)}):")
        for change in comp_changed:
            comp_id = change.get("id", "unknown")
            changes = change.get("changes", [])
            print(f"  Component: {comp_id}")
            for ch in changes:
                print(f"    - {ch}")
        print()

    # Connections
    conn_only_1 = result.get("connections_only_in_1", [])
    conn_only_2 = result.get("connections_only_in_2", [])
    conn_changed = result.get("connections_changed", [])

    if conn_only_1:
        print(f"🔗 Connections only in File 1 ({len(conn_only_1)}):")
        for conn in conn_only_1:
            print(f"  - {conn}")
        print()

    if conn_only_2:
        print(f"🔗 Connections only in File 2 ({len(conn_only_2)}):")
        for conn in conn_only_2:
            print(f"  - {conn}")
        print()

    if conn_changed:
        print(f"🔄 Connections with Changes ({len(conn_changed)}):")
        for change in conn_changed:
            conn = change.get("connection", "unknown")
            changes = change.get("changes", [])
            print(f"  Connection: {conn}")
            for ch in changes:
                print(f"    - {ch}")
        print()

    # Impact & Recommendations
    print("💡 IMPACT ASSESSMENT")
    print("-" * 80)
    print(result.get("impact_assessment", "No impact assessment provided"))
    print()

    print("✅ EQUIVALENCE DETERMINATION")
    print("-" * 80)
    equivalent = result.get("equivalent", False)
    confidence = result.get("confidence", "unknown")
    equiv_str = "EQUIVALENT" if equivalent else "NOT EQUIVALENT"
    print(f"Status: {equiv_str} (Confidence: {confidence})")
    print()

    print("📝 RECOMMENDATIONS")
    print("-" * 80)
    print(result.get("recommendations", "No recommendations provided"))
    print()

    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print(
            "Usage: python src/compare_pnid_llm.py <file1.json> <file2.json> [--reasoning low|medium|high] [--json]"
        )
        print("\nExamples:")
        print(
            "  python src/compare_pnid_llm.py data/output/pnid_base.json data/variations/var_001.json"
        )
        print("  python src/compare_pnid_llm.py file1.json file2.json --reasoning high --json")
        print("\nNote: Requires AZURE_OPENAI_API_KEY or AZURE_AI_API_KEY in .env file")
        sys.exit(1)

    path1 = Path(sys.argv[1])
    path2 = Path(sys.argv[2])

    # Parse optional flags
    json_output = "--json" in sys.argv
    reasoning_effort = "high"  # Default
    if "--reasoning" in sys.argv:
        idx = sys.argv.index("--reasoning")
        if idx + 1 < len(sys.argv):
            reasoning_effort = sys.argv[idx + 1]
            if reasoning_effort not in ["low", "medium", "high"]:
                print(f"⚠️  Invalid reasoning effort: {reasoning_effort}")
                print("   Using default: high")
                reasoning_effort = "high"

    # Validate files
    if not path1.exists():
        print(f"❌ Error: File not found: {path1}")
        sys.exit(1)

    if not path2.exists():
        print(f"❌ Error: File not found: {path2}")
        sys.exit(1)

    # Load and convert P&IDs
    print("🔄 Loading P&IDs...", file=sys.stderr)
    data1 = load_jsonld(path1)
    data2 = load_jsonld(path2)

    print("🔄 Converting to text format...", file=sys.stderr)
    text1 = pnid_to_text(data1)
    text2 = pnid_to_text(data2)

    print(f"🧠 Analyzing with LLM (reasoning: {reasoning_effort})...", file=sys.stderr)
    result = compare_with_llm(text1, text2, str(path1), str(path2), reasoning_effort)

    # Output results
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print_comparison_results(result)


if __name__ == "__main__":
    main()
