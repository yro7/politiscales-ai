
import json
from runner.scorer import compute_scores, aggregate_scores

# Mock runs
run1_answers = {"internationalism_border_removal": "neutral", "internationalism_ideals_country": "agree"}
run2_answers = {"internationalism_border_removal": "agree", "internationalism_ideals_country": "strongly agree"}

scores1 = compute_scores(run1_answers)
scores2 = compute_scores(run2_answers)

print("Run 1 Neutral (Globalism):", scores1["paired"]["globalism"].get("neutral"))
print("Run 2 Neutral (Globalism):", scores2["paired"]["globalism"].get("neutral"))

agg = aggregate_scores([scores1, scores2])
print("\nAggregate (Globalism):")
print(json.dumps(agg["paired"]["globalism"], indent=2))
