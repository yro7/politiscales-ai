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
from runner.comparison import get_comparison_grid, print_comparison_summary
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


def run_benchmark(config: RunConfig) -> dict | None:
    """Execute a full benchmark for the given configuration and return the aggregated payload."""
    print(f"\n--- Starting benchmark ---")
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
        return None

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
        return None

    print(f"\n  Finished {len(run_records)} benchmark jobs across {len(config.models)} models.")

    last_payload = None

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
        class _ModelConfigShim:
            def __getattr__(self, name): return getattr(config, name)
            @property
            def model(self): return model
            
        output_path = save_results(_ModelConfigShim(), model_records)
        print(f"\n  Results for {model} saved -> {output_path}")
        
        # Load the payload just saved to return it
        import json
        with open(output_path, "r", encoding="utf-8") as f:
            last_payload = json.load(f)

    return last_payload


def main() -> None:
    config = parse_args()

    print(f"\n{'PolitiScales-AI':>20}")
    
    # If any comparison flag is set, generate grid and loop
    if config.compare_langs or config.compare_modes or config.compare_prompts:
        grid = get_comparison_grid(config)
        print(f"  Comparison mode active: generated {len(grid)} configurations.")
        
        comparison_results = []
        for i, cfg in enumerate(grid, 1):
            print(f"\n[{i}/{len(grid)}] Running configuration...")
            payload = run_benchmark(cfg)
            if payload:
                comparison_results.append((cfg, payload))
        
        if comparison_results:
            print_comparison_summary(comparison_results)
            print("\n✅ All comparison benchmarks completed.")
        else:
            print("\n[ERROR] No comparison results were generated.", file=sys.stderr)
            sys.exit(1)
    else:
        # Standard single run
        payload = run_benchmark(config)
        if payload:
            print("\n✅ Benchmark completed.")
        else:
            sys.exit(1)


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
