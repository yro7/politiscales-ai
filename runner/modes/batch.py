"""
Mode: batch
All questions are sent in a single prompt. The model responds with a
JSON object containing explanations and answers for every question at once.
"""
from __future__ import annotations

import time
from collections import Counter
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
    Run the test in batch mode (single API call for all questions).

    Returns:
        answers      : {question_key: "strongly agree" | ...}
        explanations : {question_key: "explanation text"}
        duration_s   : wall-clock seconds
    """
    answers: Dict[str, str] = {}
    explanations: Dict[str, str] = {}

    start = time.time()

    if dry_run:
        print(f"  [DRY-RUN] Would send all {len(questions)} questions in one call.")
        print("  Questions:")
        for key, text in questions.items():
            print(f"    [{key}] {text[:80]}")
        answers = {k: "neutral" for k in questions}
        explanations = {k: "[dry-run]" for k in questions}
        duration = time.time() - start
        return answers, explanations, duration

    print(f"  Sending all {len(questions)} questions in a single API call…", flush=True)

    results = client.ask_batch(
        system_prompt=config.system_prompt,
        questions=questions,
    )

    for key in questions:
        entry = results.get(key, {})
        answers[key] = entry.get("answer", "neutral")
        explanations[key] = entry.get("explanation", "")

    # Print a compact summary
    counts = Counter(answers.values())
    print("  Results summary:", dict(counts))

    duration = time.time() - start
    return answers, explanations, duration
