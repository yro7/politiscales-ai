"""
Output — serialize and save test results to JSON.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from runner.config import RunConfig
from runner.scorer import compute_scores, aggregate_scores


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_run_record(
    run_id: int,
    answers: Dict[str, str],
    explanations: Dict[str, str],
    duration_s: float,
    tokens_used: int,
) -> Dict:
    """Build the per-run record (answers + scores + metadata)."""
    scores = compute_scores(answers)
    return {
        "run_id":          run_id,
        "duration_seconds": round(duration_s, 2),
        "total_tokens":    tokens_used,
        "answers": {
            key: {
                "answer":      answers[key],
                "explanation": explanations.get(key, ""),
            }
            for key in answers
        },
        "scores": scores,
    }


def save_results(
    config: RunConfig,
    run_records: List[Dict],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Aggregate all run_records and write the final JSON file.

    Filename format:  {date}_{model}_{lang}_{mode}_t{temp}.json
    """
    os.makedirs(config.output_dir, exist_ok=True)

    date_str  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    temp_str  = f"t{config.temperature:.2f}".replace(".", "_")
    # Sanitize model name for filename
    model_slug = config.model.replace("/", "-").replace(":", "-")
    filename  = f"{date_str}_{model_slug}_{config.language}_{config.mode}_{temp_str}.json"

    if output_path is None:
        output_path = Path(config.output_dir) / filename

    all_scores = [r["scores"] for r in run_records]
    aggregate  = aggregate_scores(all_scores) if len(all_scores) > 1 else None

    payload = {
        "meta": {
            "model":          config.model,
            "language":       config.language,
            "mode":           config.mode,
            "temperature":    config.temperature,
            "max_tokens":     config.max_tokens,
            "top_p":          config.top_p,
            "system_prompt":  config.system_prompt,
            "runs":           config.runs,
            "notes":          config.notes,
            "timestamp":      _iso_now(),
            "version":        "1.0.0",
        },
        "runs":      run_records,
        "aggregate": aggregate,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return output_path
