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
from concurrent.futures import ThreadPoolExecutor

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
        ("models",      ", ".join(config.models)),
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

    # Resolve mode runner (typed via ModeRunner protocol)
    mode_runners: dict[str, ModeRunner] = {
        "no_history": modes.no_history.run,
        "sequential": modes.sequential.run,
        "batch":      modes.batch.run,
    }
    run_fn = mode_runners[config.mode]

    def _execute_run(model: str, run_id: int) -> dict | None:
        """Helper to execute a single run for a model and return its record."""
        try:
            # Instantiate a client for this specific thread/model
            model_client = OpenRouterClient(
                api_key=config.api_key,
                api_base=config.api_base,
                model=model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
            )

            result: RunResult = run_fn(model_client, config, questions, config.dry_run, run_id=run_id, model_name=model)
            
            record = build_run_record(
                run_id=run_id,
                answers=result.answers,
                explanations=result.explanations,
                duration_s=result.duration_s,
                tokens_used=result.tokens_used,
                fallback_count=result.fallback_count,
                fallback_keys=result.fallback_keys,
            )
            # Inject model name into the record for saving later
            record["meta"] = {
                "model": model,
                "language": config.language,
                "mode": config.mode,
                "prompt_type": config.prompt_type,
            }
            return record
        except Exception as exc:
            print(f"\n[ERROR] [{model}] Run {run_id} failed: {exc}", file=sys.stderr)
            return None

    # Prepare all work items (model, run_id pairs)
    tasks = []
    for model in config.models:
        for run_id in range(1, config.runs + 1):
            tasks.append((model, run_id))

    # Execute all benchmarks in parallel
    run_records: list[dict] = []
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        results = list(executor.map(lambda t: _execute_run(*t), tasks))
        run_records = [r for r in results if r is not None]

    if not run_records:
        print("[ERROR] All runs failed. No results saved.", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Finished {len(run_records)} benchmark jobs across {len(config.models)} models.")

    # Show summaries per model
    for model in config.models:
        model_records = [r for r in run_records if r["meta"]["model"] == model]
        if not model_records:
            continue
            
        print(f"\n{'='*60}")
        print(f" MODEL: {model}")
        print(f"{'='*60}")
        
        for record in model_records:
            print(f"\n--- Run {record['run_id']} Summary ---")
            print(f"  Duration: {record['duration_seconds']:.1f}s")
            print(f"  Tokens:   {record['total_tokens']}")
            
            fallback_count = record.get("fallback_count", 0)
            if fallback_count > 0:
                print(f"  WARNING: {fallback_count} answer(s) used fallback parsing.")
            
            _print_scores_summary(record["scores"])

        # Save model-specific results
        # We need to temporarily pass a modified config to save_results for each model
        class _ModelConfigShim:
            def __getattr__(self, name): return getattr(config, name)
            @property
            def model(self): return model
            
        output_path = save_results(_ModelConfigShim(), model_records)
        print(f"\n  Results for {model} saved -> {output_path}")

    print("\n✅ All benchmarks completed.")


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
