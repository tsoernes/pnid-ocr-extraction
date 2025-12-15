#!/usr/bin/env python3
"""
DEXPI SVG Extractor and Visualizer

This script extracts and displays SVG graphics from DEXPI (Proteus XML) P&ID files.
DEXPI files typically contain embedded SVG representations that can be extracted
and viewed directly without requiring Java compilation.

Usage:
    python src/dexpi_visualizer.py <input.xml> [--output output.svg]
    python src/dexpi_visualizer.py data/input/example.xml
    python src/dexpi_visualizer.py data/input/example.xml --output data/output/diagram.svg --open

Requirements:
    - Python 3.12+
    - No external dependencies (uses stdlib only)
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


class DexpiVisualizer:
    """Extract and visualize SVG from DEXPI Proteus XML files."""

    def __init__(self):
        """Initialize the DEXPI visualizer."""
        pass

    def extract_svg(self, input_xml: Path, output_file: Path) -> Path:
        """
        Extract embedded SVG from DEXPI XML file.

        Args:
            input_xml: Input DEXPI XML file
            output_file: Output SVG file

        Returns:
            Path to output file

        Raises:
            RuntimeError: If no SVG found
        """
        import xml.etree.ElementTree as ET

        print(f"🔍 Extracting SVG from DEXPI XML: {input_xml.name}")

        try:
            tree = ET.parse(input_xml)
            root = tree.getroot()

            # Look for SVG content - DEXPI may embed SVG in different ways
            # Try common namespaces
            svg_namespaces = [
                "{http://www.w3.org/2000/svg}svg",
                "svg",
            ]

            svg_element = None
            for ns in svg_namespaces:
                svg_element = root.find(f".//{ns}")
                if svg_element is not None:
                    break

            if svg_element is not None:
                # Create proper SVG document with namespace
                svg_tree = ET.ElementTree(svg_element)

                # Ensure SVG namespace is declared
                if "xmlns" not in svg_element.attrib:
                    svg_element.set("xmlns", "http://www.w3.org/2000/svg")

                # Write SVG to file
                output_file.parent.mkdir(parents=True, exist_ok=True)
                svg_tree.write(output_file, encoding="utf-8", xml_declaration=True, method="xml")

                print(f"✅ Extracted SVG ({output_file.stat().st_size} bytes)")
                return output_file
            else:
                # Check if there's already an SVG file with same name
                svg_file = input_xml.with_suffix(".svg")
                if svg_file.exists():
                    print(f"📋 Found companion SVG file: {svg_file.name}")
                    shutil.copy(svg_file, output_file)
                    return output_file

                raise RuntimeError(
                    f"No embedded SVG found in {input_xml.name}.\n"
                    f"The DEXPI file may not contain SVG graphics, or they may be in a different format.\n"
                    f"Check if there's a companion .svg file in the same directory."
                )

        except ET.ParseError as e:
            raise RuntimeError(f"Failed to parse XML file: {e}")

    def visualize(
        self,
        input_xml: Path,
        output_file: Path | None = None,
        open_browser: bool = False,
    ) -> Path:
        """
        Extract and visualize SVG from DEXPI XML file.

        Args:
            input_xml: Path to DEXPI (Proteus XML) input file
            output_file: Path to output file (default: input name with .svg)
            open_browser: Open SVG in default browser after extraction

        Returns:
            Path to generated output file

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If visualization fails
        """
        input_xml = Path(input_xml)

        if not input_xml.exists():
            raise FileNotFoundError(f"Input file not found: {input_xml}")

        # Determine output file
        if output_file is None:
            output_file = input_xml.parent / f"{input_xml.stem}_extracted.svg"
        else:
            output_file = Path(output_file)

        # Extract SVG
        result_file = self.extract_svg(input_xml, output_file)

        # Open in browser if requested
        if open_browser:
            self.open_in_browser(result_file)

        return result_file

    def open_in_browser(self, svg_file: Path):
        """Open SVG file in default browser."""
        import webbrowser

        print(f"🌐 Opening in browser...")
        try:
            url = svg_file.absolute().as_uri()
            webbrowser.open(url)
        except Exception as e:
            print(f"⚠️  Could not open browser: {e}", file=sys.stderr)
            print(f"   Open manually: {svg_file.absolute()}")


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Extract and visualize SVG from DEXPI (Proteus XML) P&ID files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract SVG from DEXPI XML
  python src/dexpi_visualizer.py data/input/example.xml

  # Specify output file
  python src/dexpi_visualizer.py data/input/example.xml --output data/output/diagram.svg

  # Extract and open in browser
  python src/dexpi_visualizer.py data/input/example.xml --open

  # Visualize C01 reference P&ID
  python src/dexpi_visualizer.py "data/input/TrainingTestCases-master/dexpi 1.2/example pids/C01 the complete DEXPI PnID/C01V01-HEX.EX01.xml"
""",
    )

    parser.add_argument("input", type=Path, help="Input DEXPI XML file")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output SVG file (default: <input>_extracted.svg)"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open SVG in default browser after extraction",
    )

    args = parser.parse_args()

    try:
        visualizer = DexpiVisualizer()

        output_file = visualizer.visualize(
            input_xml=args.input,
            output_file=args.output,
            open_browser=args.open,
        )

        print(f"\n✅ SVG extraction complete: {output_file}")
        print(f"   File size: {output_file.stat().st_size:,} bytes")

        if not args.open:
            print(f"\n💡 Tip: Use --open to view in browser, or open manually:")
            print(f"   xdg-open {output_file}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
