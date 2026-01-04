#!/usr/bin/env python3
"""
Generate API documentation using pdoc.

Usage:
    python scripts/generate_docs.py

Output:
    docs/api/ - HTML documentation
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Generate API documentation for fiscal_model package."""
    # Get project root
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "docs" / "api"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run pdoc (modern version uses -o for output)
    cmd = [
        sys.executable, "-m", "pdoc",
        "-o", str(output_dir),
        "fiscal_model",
    ]

    print(f"Generating API documentation...")
    print(f"Output directory: {output_dir}")
    print(f"Command: {' '.join(cmd)}")
    print()

    # Change to project root for imports to work
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error generating docs:")
        print(result.stderr)
        sys.exit(1)

    if result.stdout:
        print(result.stdout)

    print(f"\nDocumentation generated successfully!")
    print(f"Open {output_dir / 'index.html'} to view.")


if __name__ == "__main__":
    main()
