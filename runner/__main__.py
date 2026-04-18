"""
Entry point — python -m runner [args]
"""
from __future__ import annotations

import logging
import sys
from typing import Dict

from dotenv import load_dotenv

from runner.client import OpenRouterClient
from runner.config import parse_args
from runner.output import build_run_record, save_results
from runner.questions import load_questions
from runner.types import ModeRunner, RunResult
from runner import modes

# Load .env before anything reads environment variables
load_dotenv()

# Configure logging — show warnings and above to stderr
logging.basicConfig(
    level=logging.WARNING,
    format="  WARNING %(name)s: %(message)s",
    stream=sys.stderr,
)

_LABEL_WIDTH = 14


def main() -> None:
    config = parse_args()

    print(f"\n{'PolitiScales-AI':>20}")
    for label, value in [
        ("model",       config.model),
        ("language",    config.language),
        ("mode",        config.mode),
        ("prompt_type", config.prompt_type),
        ("temperature", config.temperature),
        ("max_tokens",  config.max_tokens),
        ("top_p",       config.top_p),
        ("runs",        config.runs),
    ]:
        print(f"  {label:>{_LABEL_WIDTH}} : {value}")
    if config.mode == "sequential" and config.max_history > 0:
        print(f"  {'max_history':>{_LABEL_WIDTH}} : {config.max_history}")
    print(f"  {'dry_run':>{_LABEL_WIDTH}} : {config.dry_run}")
    if config.notes:
        print(f"  {'notes':>{_LABEL_WIDTH}} : {config.notes}")
    print()

    # Load questions for the requested language
    try:
        questions = load_questions(config.language)
    except (FileNotFoundError, KeyError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"  Loaded {len(questions)} questions in '{config.language}'.")
    print()

    # Instantiate the API client
    client = OpenRouterClient(
        api_key=config.api_key,
        api_base=config.api_base,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        top_p=config.top_p,
    )

    # Resolve mode runner (typed via ModeRunner protocol)
    mode_runners: dict[str, ModeRunner] = {
        "no_history": modes.no_history.run,
        "sequential": modes.sequential.run,
        "batch":      modes.batch.run,
    }
    run_fn = mode_runners[config.mode]

    # Execute runs
    run_records: list[dict] = []
    for run_id in range(1, config.runs + 1):
        if config.runs > 1:
            print(f"--- Run {run_id}/{config.runs} ---")

        try:
            result: RunResult = run_fn(client, config, questions, config.dry_run)
        except RuntimeError as exc:
            print(f"\n[ERROR] Run {run_id} failed: {exc}", file=sys.stderr)
            continue

        record = build_run_record(
            run_id=run_id,
            answers=result.answers,
            explanations=result.explanations,
            duration_s=result.duration_s,
            tokens_used=result.tokens_used,
            fallback_count=result.fallback_count,
            fallback_keys=result.fallback_keys,
        )
        run_records.append(record)

        print(f"\n  Run {run_id} done in {result.duration_s:.1f}s  ({result.tokens_used} tokens)")
        if result.fallback_count > 0:
            print(
                f"  WARNING: {result.fallback_count} answer(s) used fallback parsing "
                f"(structured output was not valid JSON)"
            )
            if result.fallback_count <= 10:
                print(f"  Questions concernées : {result.fallback_keys}")
            else:
                print(f"  Questions concernées : {result.fallback_keys[:10]} ... (+{result.fallback_count - 10} autres)")
        _print_scores_summary(record["scores"])
        print()

    if not run_records:
        print("[ERROR] All runs failed. No results saved.", file=sys.stderr)
        sys.exit(1)

    # Save everything to JSON
    output_path = save_results(config, run_records)
    print(f"\n  Results saved -> {output_path}\n")


def _print_scores_summary(scores: dict) -> None:
    """Print a brief score table to stdout."""
    print("\n  -- Paired axes --")
    for pair_name, pair_scores in scores["paired"].items():
        parts = []
        for axis, val in pair_scores.items():
            if val is not None:
                # Use different color or label for neutral in CLI is hard, 
                # just ensure it's listed.
                bar = "#" * int(val * 20)
                label = f"({axis})" if axis == "neutral" else f"{axis:<30}"
                parts.append(f"    {label:<30} {val:.2f}  {bar}")
        if parts:
            print(f"  {pair_name.upper()}")
            print("\n".join(parts))

    print("\n  -- Unpaired axes (badges) --")
    for axis, val in scores["unpaired"].items():
        if val is not None:
            bar = "#" * int(val * 20)
            print(f"    {axis:<25} {val:.2f}  {bar}")


if __name__ == "__main__":
    main()
