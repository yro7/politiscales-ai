"""
Scoring engine — Python port of questions-weights.ts + axes.ts logic.

Axes:
  Paired  (8 active pairs → 16 axes): each pair normalized to [0, 1]
  Unpaired (7 axes): normalized by max possible score per axis

Axis taxonomy:
  - **Paired axes** are measured by dedicated questions on each side
    (e.g. constructivism vs essentialism).
  - **Unpaired (badge) axes** either have their own dedicated question
    (e.g. anarchism_state_abolition → anarchism) or are *parasitic*:
    they accumulate points from questions primarily designed for paired axes.

  In particular, ``feminism`` is a parasitic axis — it has NO dedicated
  question key.  Its score is entirely derived from identity-pair and
  culture-pair questions that carry feminism as a secondary weight
  (e.g. constructivism_becoming_woman, essentialism_gender_biology,
  progressive_marriage_abolition, conservative_abortion_restriction).

  Two additional pairs (``perspective`` and ``development``) are defined
  in the original PolitiScales spec, but no question in the weight table
  feeds them.  They are intentionally **excluded** from output to avoid
  polluting results with null values.
"""
from __future__ import annotations

import functools
import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional

from runner.types import Answer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Answer value → multiplier
# ---------------------------------------------------------------------------
ANSWER_MULTIPLIERS: Dict[Answer, tuple[float, float]] = {
    # (yes_mult, no_mult)
    Answer.STRONGLY_AGREE:    (1.0, 0.0),
    Answer.AGREE:             (0.5, 0.0),
    Answer.NEUTRAL:           (0.0, 0.0),
    Answer.DISAGREE:          (0.0, 0.5),
    Answer.STRONGLY_DISAGREE: (0.0, 1.0),
}


# ---------------------------------------------------------------------------
# Paired axes (pair_name → (left_axis, right_axis))
# ---------------------------------------------------------------------------
PAIRED_AXES: Dict[str, tuple[str, str]] = {
    "identity":    ("constructivism", "essentialism"),
    "justice":     ("rehabilitative_justice", "punitive_justice"),
    "culture":     ("progressive", "conservative"),
    "globalism":   ("internationalism", "nationalism"),
    "economy":     ("communism", "capitalism"),
    "markets":     ("regulation", "laissez_faire"),
    "environment": ("ecology", "production"),
    "radicalism":  ("revolution", "reform"),
    # NOTE: "perspective" (materialism/idealism) and "development"
    # (sustainability/growth_at_all_costs) are defined in the original
    # PolitiScales but have zero questions feeding them.  They are
    # intentionally omitted here so they don't appear as null in output.
}

# Unpaired axes and their badge thresholds (from axes.ts).
# See module docstring for notes on parasitic axes (feminism).
UNPAIRED_AXES: Dict[str, float] = {
    "anarchism":  0.9,
    "pragmatism": 0.5,
    "feminism":   0.9,  # Parasitic — no dedicated question; see docstring.
    "complotism": 0.9,
    "veganism":   0.5,
    "monarchism": 0.5,
    "religion":   0.5,
}


# ---------------------------------------------------------------------------
# Question weights — loaded lazily from bundled JSON data
# ---------------------------------------------------------------------------
_WEIGHTS_PATH = Path(__file__).parent / "data" / "weights.json"


@functools.lru_cache(maxsize=1)
def _load_weights() -> dict:
    """Load question weights from the bundled JSON data file.

    The file is read once and cached for the process lifetime.
    """
    with _WEIGHTS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def _compute_max_scores() -> Dict[str, float]:
    """
    Compute the maximum achievable raw score for each axis.

    For each question, only valuesYes OR valuesNo can fire (not both).
    So for each axis, we take the max contribution from each question.
    """
    weights_data = _load_weights()
    max_scores: Dict[str, float] = {}

    for weights in weights_data.values():
        yes_contribs: Dict[str, float] = {}
        no_contribs: Dict[str, float] = {}

        for entry in weights["valuesYes"]:
            yes_contribs[entry["axis"]] = (
                yes_contribs.get(entry["axis"], 0.0) + float(entry["value"])
            )
        for entry in weights["valuesNo"]:
            no_contribs[entry["axis"]] = (
                no_contribs.get(entry["axis"], 0.0) + float(entry["value"])
            )

        all_axes = set(yes_contribs) | set(no_contribs)
        for axis in all_axes:
            best = max(yes_contribs.get(axis, 0.0), no_contribs.get(axis, 0.0))
            max_scores[axis] = max_scores.get(axis, 0.0) + best

    return max_scores


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_scores(answers: Dict[str, str]) -> Dict:
    """
    Compute PolitiScales axis scores from a dict of {question_key: answer_string}.

    Returns::

        {
          "paired": {
            "identity": {"constructivism": 0.87, "essentialism": 0.13},
            ...
          },
          "unpaired": {
            "anarchism": 0.12,
            ...
          },
          "raw": {
            "constructivism": 24.0,
            ...
          }
        }
    """
    weights_data = _load_weights()
    max_scores = _compute_max_scores()

    raw: Dict[str, float] = {}
    skipped: List[str] = []

    for question_key, answer in answers.items():
        parsed = Answer.from_str(answer)
        if parsed is None:
            skipped.append(question_key)
            continue
        yes_mult, no_mult = ANSWER_MULTIPLIERS[parsed]

        weights = weights_data.get(question_key)
        if weights is None:
            continue

        if yes_mult > 0:
            for entry in weights["valuesYes"]:
                axis = entry["axis"]
                raw[axis] = raw.get(axis, 0.0) + entry["value"] * yes_mult

        if no_mult > 0:
            for entry in weights["valuesNo"]:
                axis = entry["axis"]
                raw[axis] = raw.get(axis, 0.0) + entry["value"] * no_mult

    if skipped:
        logger.warning(
            f"{len(skipped)} answers could not be parsed and were skipped: "
            f"{skipped[:5]}{'…' if len(skipped) > 5 else ''}"
        )

    # --- Paired axes normalization ---
    paired: Dict[str, Dict[str, Optional[float]]] = {}
    for pair_name, (left, right) in PAIRED_AXES.items():
        left_score  = raw.get(left,  0.0)
        right_score = raw.get(right, 0.0)
        total = left_score + right_score
        if total == 0:
            paired[pair_name] = {left: None, right: None}
        else:
            paired[pair_name] = {
                left:  round(left_score  / total, 4),
                right: round(right_score / total, 4),
            }

    # --- Unpaired axes normalization ---
    unpaired: Dict[str, Optional[float]] = {}
    for axis, _threshold in UNPAIRED_AXES.items():
        axis_raw = raw.get(axis, 0.0)
        max_possible = max_scores.get(axis, 0.0)
        if max_possible == 0:
            unpaired[axis] = None
        else:
            unpaired[axis] = round(axis_raw / max_possible, 4)

    return {
        "paired":   paired,
        "unpaired": unpaired,
        "raw":      {k: round(v, 4) for k, v in raw.items()},
    }


def aggregate_scores(all_scores: List[Dict]) -> Dict:
    """
    Aggregate scores across multiple runs.
    Each element of all_scores is the output of compute_scores().

    Returns per-axis mean, std, and list of values.
    """

    def _stats(values: List[float]) -> Dict:
        n = len(values)
        mean = sum(values) / n
        # Sample standard deviation (n-1) for small N
        variance = (
            sum((v - mean) ** 2 for v in values) / (n - 1)
            if n > 1 else 0.0
        )
        return {
            "mean":   round(mean, 4),
            "std":    round(math.sqrt(variance), 4),
            "values": [round(v, 4) for v in values],
        }

    # Gather all axis names
    paired_keys: Dict[str, tuple[str, str]] = {}
    for pair_name, pair_axes in PAIRED_AXES.items():
        left, right = pair_axes
        if any(
            all_scores[i]["paired"].get(pair_name, {}).get(left) is not None
            for i in range(len(all_scores))
        ):
            paired_keys[pair_name] = pair_axes

    agg_paired: Dict = {}
    for pair_name, (left, right) in paired_keys.items():
        left_vals  = [s["paired"][pair_name][left]  for s in all_scores if s["paired"][pair_name][left]  is not None]
        right_vals = [s["paired"][pair_name][right] for s in all_scores if s["paired"][pair_name][right] is not None]
        agg_paired[pair_name] = {}
        if left_vals:
            agg_paired[pair_name][left]  = _stats(left_vals)
        if right_vals:
            agg_paired[pair_name][right] = _stats(right_vals)

    agg_unpaired: Dict = {}
    for axis in UNPAIRED_AXES:
        vals = [s["unpaired"][axis] for s in all_scores if s["unpaired"].get(axis) is not None]
        if vals:
            agg_unpaired[axis] = _stats(vals)

    return {
        "runs_count": len(all_scores),
        "paired":     agg_paired,
        "unpaired":   agg_unpaired,
    }
