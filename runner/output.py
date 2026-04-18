"""
Output — serialize and save test results to JSON.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from runner.config import RunConfig
from runner.scorer import compute_scores, aggregate_scores
from runner.display import generate_results_card


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_run_record(
    run_id: int,
    answers: dict[str, str],
    explanations: dict[str, str],
    duration_s: float,
    tokens_used: int,
    fallback_count: int = 0,
    fallback_keys: list[str] | None = None,
) -> dict:
    """Build the per-run record (answers + scores + metadata)."""
    scores = compute_scores(answers)
    return {
        "run_id":           run_id,
        "duration_seconds": round(duration_s, 2),
        "total_tokens":     tokens_used,
        "fallback_count":   fallback_count,
        "fallback_keys":    fallback_keys or [],
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
    run_records: list[dict],
    output_path: Path | None = None,
) -> dict:
    """Aggregate all run_records, optionally write to disk, and return payload.

    Filename format:  ``{date}_{model}_{lang}_{mode}_t{temp}.json``
    """
    json_dir = Path(config.output_dir) / "json"
    png_dir = Path(config.output_dir) / "png"

    # Use UTC for the filename so it is reproducible across timezones
    date_str  = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    temp_str  = f"t{config.temperature:.2f}".replace(".", "_")
    # Sanitize model name for filename
    model_slug = config.model.replace("/", "-").replace(":", "-")
    filename  = f"{date_str}_{model_slug}_{config.language}_{config.mode}_{temp_str}.json"

    if output_path is None:
        output_path = json_dir / filename

    all_scores = [r["scores"] for r in run_records]
    aggregate  = aggregate_scores(all_scores)

    total_fallbacks = sum(r.get("fallback_count", 0) for r in run_records)
    all_fallback_keys = sorted(list(set().union(*(r.get("fallback_keys", []) for r in run_records))))

    payload = {
        "meta": {
            "model":          config.model,
            "language":       config.language,
            "mode":           config.mode,
            "prompt_type":    config.prompt_type,
            "temperature":    config.temperature,
            "max_tokens":     config.max_tokens,
            "top_p":          config.top_p,
            "system_prompt":  config.system_prompt,
            "runs":           config.runs,
            "notes":          config.notes,
            "total_fallbacks": total_fallbacks,
            "fallback_keys":   all_fallback_keys,
            "timestamp":      _iso_now(),
            "version":        "1.2.0",
        },
        "runs":      run_records,
        "aggregate": aggregate,
    }

    if config.dry_run:
        print("  [DRY-RUN] Skipping file saving (JSON & PNG).")
        return payload

    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n  Results for {config.model} saved -> {output_path}")

    # Automatically generate the visualization PNG
    try:
        # Save PNG in the specialized png/ directory
        image_filename = output_path.with_suffix(".png").name
        image_path = png_dir / image_filename
        
        generate_results_card(payload, image_path)
        print(f"  Visualization saved -> {image_path}")
    except Exception as exc:
        print(f"  WARNING: Could not generate visualization: {exc}")

    return payload
