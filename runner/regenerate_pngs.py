"""
Batch regeneration script — converts all existing JSON results to HD PNG graphics.
Usage: python3 runner/regenerate_pngs.py [results_dir]
"""
import json
import sys
from pathlib import Path

# Add project root to path so we can import runner modules
sys.path.append(str(Path(__file__).parent.parent))

from runner.display import generate_results_card

def main():
    results_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results")
    json_dir = results_root / "json"
    png_dir = results_root / "png"

    if not json_dir.exists():
        print(f"Error: {json_dir} does not exist.")
        sys.exit(1)

    png_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(json_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {json_dir}")
        return

    print(f"Found {len(json_files)} result files. Regenerating PNGs in HD...")

    for json_path in json_files:
        print(f"Processing: {json_path.name} ... ", end="", flush=True)
        try:
            with json_path.open(encoding="utf-8") as f:
                data = json.load(f)
            
            # Destination path: results/png/filename.png
            image_path = png_dir / json_path.with_suffix(".png").name
            
            generate_results_card(data, image_path)
            print("DONE")
        except Exception as exc:
            print(f"FAILED: {exc}")

    print("\n✅ Regeneration complete.")

if __name__ == "__main__":
    main()
