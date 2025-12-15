#!/usr/bin/env python3
"""
Convert DWG files to DXF format using ODA File Converter.

This script uses the installed ODA File Converter at /usr/local/bin/ODAFileConverter
to convert AutoCAD DWG files (including newer formats like 2018/2019/2020) to DXF.

Usage:
    python src/convert_dwg_to_dxf.py <input.dwg> [<output.dxf>]
    python src/convert_dwg_to_dxf.py "data/input/Diagramas P&ID.dwg"
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Configuration
ODA_FILE_CONVERTER_PATH = "/usr/local/bin/ODAFileConverter"
OUTVER = "ACAD2018"
OUTFORMAT = "DXF"
RECURSIVE = "0"
AUDIT = "1"
INPUTFILTER = "*.DWG"


def convert_dwg_to_dxf(
    input_file: Path,
    output_file: Path | None = None,
    output_version: str = OUTVER,
    audit: bool = True,
) -> Path:
    """
    Convert a DWG file to DXF using ODA File Converter.

    Args:
        input_file: Path to input DWG file
        output_file: Optional path to output DXF file (defaults to same name with .dxf extension)
        output_version: DXF version to output (ACAD2018, ACAD2013, ACAD2010, etc.)
        audit: Whether to audit/repair the file during conversion

    Returns:
        Path to the created DXF file

    Raises:
        FileNotFoundError: If input file or ODA converter not found
        RuntimeError: If conversion fails
    """
    # Validate input
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if not Path(ODA_FILE_CONVERTER_PATH).exists():
        raise FileNotFoundError(f"ODA File Converter not found at: {ODA_FILE_CONVERTER_PATH}")

    # Determine output file
    if output_file is None:
        output_file = input_file.with_suffix(".dxf")

    # ODA File Converter works with folders, not individual files
    # We need to create temp folders for input and output
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        temp_input_dir = temp_path / "input"
        temp_output_dir = temp_path / "output"
        temp_input_dir.mkdir()
        temp_output_dir.mkdir()

        # Copy input file to temp input directory
        temp_input_file = temp_input_dir / input_file.name
        shutil.copy2(input_file, temp_input_file)

        # Build command
        # ODA syntax: ODAFileConverter <input_folder> <output_folder> <output_version> <output_format> <recursive> <audit> [<input_filter>]
        cmd = [
            ODA_FILE_CONVERTER_PATH,
            str(temp_input_dir),
            str(temp_output_dir),
            output_version,
            OUTFORMAT,
            RECURSIVE,
            "1" if audit else "0",
            INPUTFILTER,
        ]

        print(f"Converting {input_file.name} to DXF...")
        print(f"Command: {' '.join(cmd)}")

        try:
            # Note: Do NOT use shell=True with a list of arguments
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            print("Conversion output:", result.stdout)
            if result.stderr:
                print("Conversion stderr:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion:")
            print(f"  Exit code: {e.returncode}")
            print(f"  stdout: {e.stdout}")
            print(f"  stderr: {e.stderr}")
            raise RuntimeError(f"ODA File Converter failed: {e}") from e

        # Find the converted file in temp output directory
        converted_files = list(temp_output_dir.glob("*.dxf"))
        if not converted_files:
            raise RuntimeError(f"No DXF files found in output directory: {temp_output_dir}")

        # Copy the converted file to the desired output location
        converted_file = converted_files[0]
        shutil.copy2(converted_file, output_file)

        print(f"✅ Successfully converted to: {output_file}")
        print(f"   Size: {output_file.stat().st_size:,} bytes")

    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert DWG files to DXF using ODA File Converter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert to same directory with .dxf extension
  python src/convert_dwg_to_dxf.py "data/input/Diagramas P&ID.dwg"

  # Specify output file
  python src/convert_dwg_to_dxf.py input.dwg output.dxf

  # Use different DXF version
  python src/convert_dwg_to_dxf.py input.dwg -v ACAD2010
        """,
    )
    parser.add_argument("input", type=Path, help="Path to input DWG file")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="Path to output DXF file (default: same as input with .dxf extension)",
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        default=OUTVER,
        choices=[
            "ACAD9",
            "ACAD10",
            "ACAD12",
            "ACAD13",
            "ACAD14",
            "ACAD2000",
            "ACAD2004",
            "ACAD2007",
            "ACAD2010",
            "ACAD2013",
            "ACAD2018",
        ],
        help=f"DXF output version (default: {OUTVER})",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip audit/repair during conversion",
    )

    args = parser.parse_args()

    try:
        convert_dwg_to_dxf(
            input_file=args.input,
            output_file=args.output,
            output_version=args.version,
            audit=not args.no_audit,
        )
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
