"""
Entry point — python -m runner [args]
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from runner.client import OpenRouterClient
from runner.config import parse_args
from runner.output import build_run_record, save_results
from runner.questions import load_questions
from runner import modes

# Configure logging — show warnings and above to stderr
logging.basicConfig(
    level=logging.WARNING,
    format="  ⚠  %(name)s: %(message)s",
    stream=sys.stderr,
)


def main() -> None:
    config = parse_args()

    print("\n🏛️  PolitiScales-AI")
    print(f"  model       : {config.model}")
    print(f"  language    : {config.language}")
    print(f"  mode        : {config.mode}")
    print(f"  temperature : {config.temperature}")
    print(f"  max_tokens  : {config.max_tokens}")
    print(f"  top_p       : {config.top_p}")
    print(f"  runs        : {config.runs}")
    if config.mode == "sequential" and config.max_history > 0:
        print(f"  max_history : {config.max_history}")
    print(f"  dry_run     : {config.dry_run}")
    if config.notes:
        print(f"  notes       : {config.notes}")
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

    # Resolve mode runner
    mode_runners = {
        "no_history": modes.no_history.run,
        "sequential": modes.sequential.run,
        "batch":      modes.batch.run,
    }
    run_fn = mode_runners[config.mode]

    # Execute runs
    run_records = []
    for run_id in range(1, config.runs + 1):
        if config.runs > 1:
            print(f"━━━ Run {run_id}/{config.runs} ━━━")

        tokens_before = client.total_tokens

        try:
            answers, explanations, duration = run_fn(client, config, questions, config.dry_run)
        except RuntimeError as exc:
            print(f"\n[ERROR] Run {run_id} failed: {exc}", file=sys.stderr)
            continue

        tokens_this_run = client.total_tokens - tokens_before

        record = build_run_record(
            run_id=run_id,
            answers=answers,
            explanations=explanations,
            duration_s=duration,
            tokens_used=tokens_this_run,
        )
        run_records.append(record)

        print(f"\n  Run {run_id} done in {duration:.1f}s  ({tokens_this_run} tokens)")
        _print_scores_summary(record["scores"])
        print()

    if not run_records:
        print("[ERROR] All runs failed. No results saved.", file=sys.stderr)
        sys.exit(1)

    # Save everything to JSON
    output_path = save_results(config, run_records)
    print(f"\n✅  Results saved → {output_path}\n")


def _print_scores_summary(scores: dict) -> None:
    """Print a brief score table to stdout."""
    print("\n  ── Paired axes ─────────────────────────────────────")
    for pair_name, pair_scores in scores["paired"].items():
        parts = []
        for axis, val in pair_scores.items():
            if val is not None:
                bar = "█" * int(val * 20)
                parts.append(f"    {axis:<30} {val:.2f}  {bar}")
        if parts:
            print(f"  {pair_name.upper()}")
            print("\n".join(parts))

    print("\n  ── Unpaired axes (badges) ──────────────────────────")
    for axis, val in scores["unpaired"].items():
        if val is not None:
            bar = "█" * int(val * 20)
            print(f"    {axis:<25} {val:.2f}  {bar}")


if __name__ == "__main__":
    main()
