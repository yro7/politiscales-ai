"""
Mode: batch
All questions are sent in a single prompt. The model responds with a
JSON object containing explanations and answers for every question at once.
"""
from __future__ import annotations

import time
from collections import Counter

from runner.client import OpenRouterClient
from runner.config import RunConfig
from runner.types import RunResult


def run(
    client: OpenRouterClient,
    config: RunConfig,
    questions: dict[str, str],
    dry_run: bool = False,
) -> RunResult:
    """
    Run the test in batch mode (single API call for all questions).
    """
    answers: dict[str, str] = {}
    explanations: dict[str, str] = {}
    fallback_count = 0
    fallback_keys: list[str] = []
    total_tokens = 0

    start = time.monotonic()

    if dry_run:
        print(f"  [DRY-RUN] Would send all {len(questions)} questions in one call.")
        print("  Questions:")
        for key, text in questions.items():
            print(f"    [{key}] {text[:80]}")
        answers = {k: "neutral" for k in questions}
        explanations = {k: "[dry-run]" for k in questions}
        duration = time.monotonic() - start
        return RunResult(answers, explanations, duration, total_tokens, fallback_count)

    print(f"  Sending all {len(questions)} questions in a single API call…", flush=True)

    results, tokens, was_fallback = client.ask_batch(
        system_prompt=config.system_prompt,
        questions=questions,
    )
    total_tokens += tokens
    if was_fallback:
        # In batch mode fallback, all answers are potentially unreliable
        fallback_count = len(questions)
        fallback_keys = list(questions.keys())

    for key in questions:
        entry = results.get(key, {})
        answers[key] = entry.get("answer", "neutral")
        explanations[key] = entry.get("explanation", "")

    # Print a compact summary
    counts = Counter(answers.values())
    print("  Results summary:", dict(counts))

    duration = time.monotonic() - start
    return RunResult(answers, explanations, duration, total_tokens, fallback_count, fallback_keys)
