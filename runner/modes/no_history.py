"""
Mode: no_history
Each question is sent in a fresh API call with zero memory of previous answers.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from runner.client import OpenRouterClient
from runner.config import RunConfig
from runner.types import RunResult


def run(
    client: OpenRouterClient,
    config: RunConfig,
    questions: dict[str, str],
    dry_run: bool = False,
    run_id: int = 1,
    model_name: str = "",
) -> RunResult:
    """
    Run the test in no_history mode.

    Each question is a fresh call with an empty message history.
    Parallelized via ThreadPoolExecutor for speed.
    """
    answers: dict[str, str] = {}
    explanations: dict[str, str] = {}
    fallback_keys: list[str] = []
    total_tokens = 0
    
    # Context for logging
    model_slug = model_name.split("/")[-1]
    prefix = f"[{model_slug}][Run {run_id}]"
    
    results_lock = threading.Lock()
    print_lock = threading.Lock()
    
    start = time.monotonic()
    total = len(questions)

    def _process_question(item: tuple[int, tuple[str, str]]):
        idx, (key, text) = item
        
        if dry_run:
            with print_lock:
                print(f"  {prefix} [{idx:3}/{total}] {key[:40]:<40} → [DRY-RUN]")
            with results_lock:
                answers[key] = "neutral"
                explanations[key] = "[dry-run]"
            return

        try:
            result, tokens, was_fallback = client.ask_single(
                system_prompt=config.system_prompt,
                messages=[],          # <-- no history, fresh every time
                question_text=text,
            )
            
            with results_lock:
                nonlocal total_tokens
                total_tokens += tokens
                if was_fallback:
                    fallback_keys.append(key)
                answers[key] = result.get("answer", "neutral")
                explanations[key] = result.get("explanation", "")
            
            with print_lock:
                print(f"  {prefix} [{idx:3}/{total}] {key[:40]:<40} → {answers[key]}")
                
        except Exception as exc:
            with print_lock:
                print(f"  {prefix} [{idx:3}/{total}] {key[:40]:<40} → ERROR: {exc}")
            with results_lock:
                answers[key] = "neutral"
                explanations[key] = f"Error: {exc}"

    # Use ThreadPoolExecutor to run questions in parallel
    items = list(enumerate(questions.items(), 1))
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        executor.map(_process_question, items)

    duration = time.monotonic() - start
    return RunResult(answers, explanations, duration, total_tokens, len(fallback_keys), fallback_keys)
