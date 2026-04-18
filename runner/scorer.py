"""
Scoring engine — Python port of questions-weights.ts + axes.ts logic.

Axes:
  Paired  (10 pairs, 20 axes): each pair normalized to [0, 1].
    8 active pairs have questions feeding them.
    2 placeholder pairs (perspective, development) are defined in the
    upstream PolitiScales spec but currently have zero questions.
  Unpaired (7 badge axes): normalized by max possible score per axis.

Axis taxonomy
--------------
*Paired axes* are measured by dedicated questions on each side
(e.g. constructivism vs essentialism).

*Unpaired (badge) axes* either have their own dedicated question
(e.g. ``anarchism_state_abolition`` -> anarchism) or are **parasitic**:
they accumulate points from questions primarily designed for paired axes.

``feminism`` is the main parasitic axis.  It has NO dedicated question
key — its score is entirely derived from identity-pair and culture-pair
questions that carry feminism as a secondary weight.  This matches the
upstream PolitiScales behaviour (see ``questions-weights.ts`` in the
submodule, where feminism only appears as a secondary value on
constructivism/essentialism and progressive/conservative questions).
"""
from __future__ import annotations

import functools
import json
import logging
import math
from pathlib import Path

from runner.types import Answer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Answer value -> multiplier
# ---------------------------------------------------------------------------
ANSWER_MULTIPLIERS: dict[Answer, tuple[float, float]] = {
    # (yes_mult, no_mult)
    Answer.STRONGLY_AGREE:    (1.0, 0.0),
    Answer.AGREE:             (0.5, 0.0),
    Answer.NEUTRAL:           (0.0, 0.0),
    Answer.DISAGREE:          (0.0, 0.5),
    Answer.STRONGLY_DISAGREE: (0.0, 1.0),
}


# ---------------------------------------------------------------------------
# Paired axes (pair_name -> (left_axis, right_axis))
#
# Matches upstream axes.ts exactly — including the two placeholder pairs
# (perspective, development) that have colours defined but no questions
# feeding them yet.  When no question contributes to a pair, both sides
# are reported as null (same behaviour as the original JS serializer
# which encodes them as NaN_VALUE / 101).
# ---------------------------------------------------------------------------
PAIRED_AXES: dict[str, tuple[str, str]] = {
    "identity":    ("constructivism", "essentialism"),
    "justice":     ("rehabilitative_justice", "punitive_justice"),
    "culture":     ("progressive", "conservative"),
    "globalism":   ("internationalism", "nationalism"),
    "economy":     ("communism", "capitalism"),
    "markets":     ("regulation", "laissez_faire"),
    "environment": ("ecology", "production"),
    "radicalism":  ("revolution", "reform"),
    "perspective": ("materialism", "idealism"),
    "development": ("sustainability", "growth_at_all_costs"),
}

# Unpaired axes and their badge thresholds (from axes.ts ``badgeThreshold``).
# feminism is parasitic — see module docstring.
UNPAIRED_AXES: dict[str, float] = {
    "anarchism":  0.9,
    "pragmatism": 0.5,
    "feminism":   0.9,
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
def _compute_max_scores() -> dict[str, float]:
    """Compute the maximum achievable raw score for each axis.

    For each question, only valuesYes OR valuesNo can fire (not both).
    So for each axis, we take the max contribution from each question.
    """
    weights_data = _load_weights()
    max_scores: dict[str, float] = {}

    for weights in weights_data.values():
        yes_contribs: dict[str, float] = {}
        no_contribs: dict[str, float] = {}

        for entry in weights["valuesYes"]:
            axis = entry["axis"]
            yes_contribs[axis] = yes_contribs.get(axis, 0.0) + float(entry["value"])
        for entry in weights["valuesNo"]:
            axis = entry["axis"]
            no_contribs[axis] = no_contribs.get(axis, 0.0) + float(entry["value"])

        all_axes = set(yes_contribs) | set(no_contribs)
        for axis in all_axes:
            best = max(yes_contribs.get(axis, 0.0), no_contribs.get(axis, 0.0))
            max_scores[axis] = max_scores.get(axis, 0.0) + best

    return max_scores


@functools.lru_cache(maxsize=1)
def _compute_max_pair_weights() -> dict[str, float]:
    """Compute the maximum total weight assigned to a pair across all questions.

    This is the sum of (max contribution to left OR right) for every question.
    """
    weights_data = _load_weights()
    max_pairs: dict[str, float] = {}

    # Map axis -> pair_name
    axis_to_pair = {}
    for pair_name, (left, right) in PAIRED_AXES.items():
        axis_to_pair[left] = pair_name
        axis_to_pair[right] = pair_name

    for weights in weights_data.values():
        pair_contribs: dict[str, dict[str, float]] = {}  # pair -> {left_raw: ..., right_raw: ...}

        for entry in weights["valuesYes"]:
            axis = entry["axis"]
            if axis in axis_to_pair:
                p = axis_to_pair[axis]
                if p not in pair_contribs: pair_contribs[p] = {"left": 0.0, "right": 0.0}
                # Find if it's left or right axis for this pair
                if PAIRED_AXES[p][0] == axis:
                    pair_contribs[p]["left"] += entry["value"]
                else:
                    pair_contribs[p]["right"] += entry["value"]

        # Note: We need a temporary copy for valuesNo to compare with valuesYes
        yes_pair_totals = {p: max(v["left"], v["right"]) for p, v in pair_contribs.items()}
        # Wait, the logic is: one question might contribute to BOTH left and right axes of different pairs.
        # But for the SAME pair, it usually only contributes to one side per response (Yes or No).
        # To find "max weight for pair P from question Q":
        # max( (sum of P-axes in valuesYes), (sum of P-axes in valuesNo) )

        q_pair_yes: dict[str, float] = {}
        q_pair_no: dict[str, float] = {}

        for entry in weights["valuesYes"]:
            if entry["axis"] in axis_to_pair:
                p = axis_to_pair[entry["axis"]]
                q_pair_yes[p] = q_pair_yes.get(p, 0.0) + entry["value"]

        for entry in weights["valuesNo"]:
            if entry["axis"] in axis_to_pair:
                p = axis_to_pair[entry["axis"]]
                q_pair_no[p] = q_pair_no.get(p, 0.0) + entry["value"]

        all_q_pairs = set(q_pair_yes) | set(q_pair_no)
        for p in all_q_pairs:
            best = max(q_pair_yes.get(p, 0.0), q_pair_no.get(p, 0.0))
            max_pairs[p] = max_pairs.get(p, 0.0) + best

    return max_pairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_scores(answers: dict[str, str]) -> dict:
    """Compute PolitiScales axis scores from ``{question_key: answer_string}``.

    Returns::

        {
          "paired": {
            "identity": {"constructivism": 0.87, "essentialism": 0.13},
            "perspective": {"materialism": null, "idealism": null},
            ...
          },
          "unpaired": {"anarchism": 0.12, ...},
          "raw": {"constructivism": 24.0, ...}
        }
    """
    weights_data = _load_weights()
    max_scores = _compute_max_scores()

    raw: dict[str, float] = {}
    skipped: list[str] = []

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
            "%d answers could not be parsed and were skipped: %s%s",
            len(skipped),
            skipped[:5],
            "..." if len(skipped) > 5 else "",
        )

    # --- Paired axes normalization ---
    paired: dict[str, dict[str, float | None]] = {}
    max_pair_weights = _compute_max_pair_weights()

    for pair_name, (left, right) in PAIRED_AXES.items():
        left_score  = raw.get(left,  0.0)
        right_score = raw.get(right, 0.0)
        max_pair_weight = max_pair_weights.get(pair_name, 0.0)

        if max_pair_weight == 0:
            paired[pair_name] = {left: None, right: None, "neutral": None}
        else:
            left_p = round(left_score / max_pair_weight, 4)
            right_p = round(right_score / max_pair_weight, 4)
            neutral_p = round(1.0 - left_p - right_p, 4)
            # Ensure no negative due to rounding
            neutral_p = max(0.0, neutral_p)

            paired[pair_name] = {
                left:      left_p,
                right:     right_p,
                "neutral": neutral_p,
            }

    # --- Unpaired axes normalization ---
    unpaired: dict[str, float | None] = {}
    for axis in UNPAIRED_AXES:
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


def aggregate_scores(all_scores: list[dict]) -> dict:
    """Aggregate scores across multiple runs.

    Works for any number of runs >= 1.
    Returns per-axis mean, std (None when n=1), and list of values.
    """
    if not all_scores:
        return {"runs_count": 0, "paired": {}, "unpaired": {}}

    def _stats(values: list[float]) -> dict:
        n = len(values)
        mean = sum(values) / n
        if n > 1:
            variance = sum((v - mean) ** 2 for v in values) / (n - 1)
            std: float | None = round(math.sqrt(variance), 4)
        else:
            # A single sample has no meaningful standard deviation.
            std = None
        return {
            "mean":   round(mean, 4),
            "std":    std,
            "values": [round(v, 4) for v in values],
        }

    # Gather paired axis names that have at least one non-null value
    paired_keys: dict[str, tuple[str, str]] = {}
    for pair_name, pair_axes in PAIRED_AXES.items():
        left, right = pair_axes
        if any(
            s["paired"].get(pair_name, {}).get(left) is not None
            for s in all_scores
        ):
            paired_keys[pair_name] = pair_axes

    agg_paired: dict = {}
    for pair_name, (left, right) in paired_keys.items():
        left_vals    = [s["paired"][pair_name][left]             for s in all_scores if s["paired"][pair_name].get(left)      is not None]
        right_vals   = [s["paired"][pair_name][right]            for s in all_scores if s["paired"][pair_name].get(right)     is not None]
        neutral_vals = [s["paired"][pair_name].get("neutral", 0) for s in all_scores if s["paired"][pair_name].get(left)      is not None] # neutral exists if left exists

        agg_paired[pair_name] = {}
        if left_vals:
            agg_paired[pair_name][left] = _stats(left_vals)
        if right_vals:
            agg_paired[pair_name][right] = _stats(right_vals)
        if neutral_vals:
            agg_paired[pair_name]["neutral"] = _stats(neutral_vals)

    agg_unpaired: dict = {}
    for axis in UNPAIRED_AXES:
        vals = [s["unpaired"][axis] for s in all_scores if s["unpaired"].get(axis) is not None]
        if vals:
            agg_unpaired[axis] = _stats(vals)

    return {
        "runs_count": len(all_scores),
        "paired":     agg_paired,
        "unpaired":   agg_unpaired,
    }
