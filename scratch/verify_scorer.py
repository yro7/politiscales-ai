
from runner.scorer import compute_scores
import json
from pathlib import Path

# Load results
file_path = Path("results/2026-04-18_08-20-43_openai-gpt-4.1_en_sequential_t0_70.json")
with file_path.open() as f:
    data = json.load(f)

answers = {k: v["answer"] for k, v in data["runs"][0]["answers"].items()}

# Re-compute scores
scores = compute_scores(answers)

print("--- Identity ---")
print(json.dumps(scores["paired"]["identity"], indent=2))

print("\n--- Globalism ---")
print(json.dumps(scores["paired"]["globalism"], indent=2))

print("\n--- Regulation (Markets) ---")
print(json.dumps(scores["paired"]["markets"], indent=2))
