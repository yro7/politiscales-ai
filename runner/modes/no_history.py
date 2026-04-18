"""
Mode: no_history
Each question is sent in a fresh API call with zero memory of previous answers.
"""
from __future__ import annotations

import time
from typing import Dict, Tuple

from runner.client import OpenRouterClient
from runner.config import RunConfig


def run(
    client: OpenRouterClient,
    config: RunConfig,
    questions: Dict[str, str],
    dry_run: bool = False,
) -> Tuple[Dict[str, str], Dict[str, str], float]:
    """
    Run the test in no_history mode.

    Returns:
        answers      : {question_key: "strongly agree" | ...}
        explanations : {question_key: "explanation text"}
        duration_s   : wall-clock seconds
    """
    answers: Dict[str, str] = {}
    explanations: Dict[str, str] = {}

    start = time.time()
    total = len(questions)

    for idx, (key, text) in enumerate(questions.items(), 1):
        print(f"  [{idx:3}/{total}] {key[:55]:<55}", end="", flush=True)

        if dry_run:
            print(f"  [DRY-RUN] Would ask: {text[:80]}")
            answers[key] = "neutral"
            explanations[key] = "[dry-run]"
            continue

        result = client.ask_single(
            system_prompt=config.system_prompt,
            messages=[],          # <-- no history, fresh every time
            question_text=text,
        )
        answers[key] = result.get("answer", "neutral")
        explanations[key] = result.get("explanation", "")
        print(f"  → {answers[key]}")

    duration = time.time() - start
    return answers, explanations, duration
