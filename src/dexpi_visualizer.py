#!/usr/bin/env python3
"""
DEXPI Visualizer - Simple SVG extraction and visualization

This script handles DEXPI (Proteus XML) P&ID visualization through two approaches:
1. Copy companion SVG files if they exist alongside XML
2. Use existing SVG files in the DEXPI distribution

DEXPI training examples typically include pre-rendered SVG files.

Usage:
    python src/dexpi_visualizer.py <input.xml> [--output output.svg] [--open]
    python src/dexpi_visualizer.py data/input/example.xml
    python src/dexpi_visualizer.py data/input/example.xml --output data/output/diagram.svg
    python src/dexpi_visualizer.py data/input/example.xml --open
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


class DexpiVisualizer:
    """Simple DEXPI visualizer that finds and copies SVG files."""

    def find_svg_file(self, xml_path: Path) -> Path | None:
        """
        Find companion SVG file for DEXPI XML.

        DEXPI distributions often include pre-rendered SVG files alongside XML files.
        This method looks for SVG files with matching base names or in the same directory.

        Args:
            xml_path: Path to DEXPI XML file

        Returns:
            Path to SVG file if found, None otherwise
        """
        # Strategy 1: Same base name (e.g., C01V01.xml -> C01V01.svg)
        svg_same_name = xml_path.with_suffix(".svg")
        if svg_same_name.exists():
            return svg_same_name

        # Strategy 2: Look for any SVG in the same directory
        parent_dir = xml_path.parent
        svg_files = list(parent_dir.glob("*.svg"))

        if svg_files:
            # Prefer SVG with similar name
            xml_base = xml_path.stem.split("-")[0]  # e.g., C01V01-HEX.EX01 -> C01V01
            for svg_file in svg_files:
                if svg_file.stem.startswith(xml_base):
                    return svg_file

            # Return first SVG found
            return svg_files[0]

        return None

    def visualize(
        self,
        input_xml: Path,
        output_file: Path | None = None,
        open_output: bool = False,
    ) -> Path:
        """
        Visualize DEXPI XML by finding and copying companion SVG file.

        Args:
            input_xml: Path to DEXPI XML file
            output_file: Path to output SVG file (default: data/output/<name>.svg)
            open_output: Open SVG in default viewer after extraction

        Returns:
            Path to output SVG file

        Raises:
            FileNotFoundError: If input file or companion SVG not found
        """
        input_xml = Path(input_xml)

        if not input_xml.exists():
            raise FileNotFoundError(f"Input file not found: {input_xml}")

        print(f"🔍 Looking for SVG file for: {input_xml.name}")

        # Find companion SVG
        svg_source = self.find_svg_file(input_xml)

        if svg_source is None:
            raise FileNotFoundError(
                f"No companion SVG file found for: {input_xml}\n"
                f"DEXPI files typically come with pre-rendered SVG files.\n"
                f"Checked directory: {input_xml.parent}\n"
                f"\nTo generate SVG from scratch, you need the full GraphicBuilder tool."
            )

        print(f"📋 Found companion SVG: {svg_source.name}")

        # Determine output file
        if output_file is None:
            output_file = Path("data/output") / f"{input_xml.stem}.svg"
        else:
            output_file = Path(output_file)

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Copy SVG file
        print(f"📄 Copying to: {output_file}")
        shutil.copy(svg_source, output_file)

        file_size = output_file.stat().st_size
        print(f"✅ Successfully copied SVG ({file_size:,} bytes)")

        # Open if requested
        if open_output:
            self.open_file(output_file)

        return output_file

    def open_file(self, file_path: Path):
        """Open file in default application."""
        print(f"🌐 Opening {file_path.name}...")
        try:
            subprocess.run(["xdg-open", str(file_path)], check=False)
        except Exception as e:
            print(f"⚠️  Could not open file: {e}", file=sys.stderr)
            print(f"   Open manually: {file_path.absolute()}")


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Extract and visualize SVG from DEXPI (Proteus XML) P&ID files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find and copy companion SVG
  python src/dexpi_visualizer.py "data/input/example.xml"

  # Specify output location
  python src/dexpi_visualizer.py "data/input/example.xml" --output data/output/diagram.svg

  # Copy and open in viewer
  python src/dexpi_visualizer.py "data/input/example.xml" --open

  # Visualize C01 reference P&ID
  python src/dexpi_visualizer.py \\
    "data/input/TrainingTestCases-master/dexpi 1.2/example pids/C01 the complete DEXPI PnID/C01V01-HEX.EX02.xml"

Notes:
  - DEXPI training examples include pre-rendered SVG files
  - This script finds and copies the companion SVG for easy viewing
  - For generating SVG from XML, use the full GraphicBuilder Java tool
""",
    )

    parser.add_argument("input", type=Path, help="Input DEXPI XML file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output SVG file (default: data/output/<input_name>.svg)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open SVG in default viewer after extraction",
    )

    args = parser.parse_args()

    try:
        visualizer = DexpiVisualizer()

        output_file = visualizer.visualize(
            input_xml=args.input,
            output_file=args.output,
            open_output=args.open,
        )

        print(f"\n✅ Visualization complete: {output_file}")

        if not args.open:
            print(f"\n💡 Tip: Use --open to view immediately, or open manually:")
            print(f"   xdg-open {output_file}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
