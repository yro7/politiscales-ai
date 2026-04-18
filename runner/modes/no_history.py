"""
Mode: no_history
Each question is sent in a fresh API call with zero memory of previous answers.
"""
from __future__ import annotations

import time

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
    Run the test in no_history mode.

    Each question is a fresh call with an empty message history.
    """
    answers: dict[str, str] = {}
    explanations: dict[str, str] = {}
    fallback_count = 0
    total_tokens = 0

    start = time.monotonic()
    total = len(questions)

    for idx, (key, text) in enumerate(questions.items(), 1):
        print(f"  [{idx:3}/{total}] {key[:55]:<55}", end="", flush=True)

        if dry_run:
            print(f"  [DRY-RUN] Would ask: {text[:80]}")
            answers[key] = "neutral"
            explanations[key] = "[dry-run]"
            continue

        result, tokens, was_fallback = client.ask_single(
            system_prompt=config.system_prompt,
            messages=[],          # <-- no history, fresh every time
            question_text=text,
        )
        total_tokens += tokens
        if was_fallback:
            fallback_count += 1

        answers[key] = result.get("answer", "neutral")
        explanations[key] = result.get("explanation", "")
        print(f"  → {answers[key]}")

    duration = time.monotonic() - start
    return RunResult(answers, explanations, duration, total_tokens, fallback_count)
