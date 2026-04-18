"""
CLI Entry point for PolitiScales-AI visualization.
Usage: python -m runner.display_main [result_json]
"""
import argparse
import json
import sys
from pathlib import Path

from runner.display import generate_results_card


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a PolitiScales results card image from a JSON result file."
    )
    parser.add_argument("input", help="Path to the result JSON file.")
    parser.add_argument("--output", "-o", help="Custom output image path.")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
        
    try:
        with input_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse JSON: {e}")
        sys.exit(1)
        
    output_path = Path(args.output) if args.output else input_path.with_suffix(".png")
    
    print(f"  Generating visualization for {input_path.name}...")
    try:
        generate_results_card(data, output_path)
        print(f"  ✅ Image saved to: {output_path}")
    except Exception as e:
        print(f"  ❌ Failed to generate image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
