"""
Mode: sequential
Questions are asked one by one. The model's previous answers are kept in the
chat history, so it can maintain consistency with its earlier positions.

A sliding window (--max-history) prevents token overflow on smaller models.
"""
from __future__ import annotations

import json
import logging
import time

from runner.client import OpenRouterClient
from runner.config import RunConfig
from runner.types import RunResult

logger = logging.getLogger(__name__)


def run(
    client: OpenRouterClient,
    config: RunConfig,
    questions: dict[str, str],
    dry_run: bool = False,
    run_id: int = 1,
) -> RunResult:
    """
    Run the test in sequential mode.

    Questions are asked one-by-one with growing chat history.
    """
    answers: dict[str, str] = {}
    explanations: dict[str, str] = {}
    history: list[dict[str, str]] = []  # growing chat context
    fallback_keys: list[str] = []
    total_tokens = 0

    # Context for logging
    model_slug = config.model.split("/")[-1]
    prefix = f"[{model_slug}][Run {run_id}]"

    # max_history = 0 means unlimited; otherwise keep last N exchanges (2 msgs each)
    max_pairs = config.max_history

    start = time.monotonic()
    total = len(questions)

    for idx, (key, text) in enumerate(questions.items(), 1):
        print(f"  {prefix} [{idx:3}/{total}] {key[:40]:<40}", end="", flush=True)

        if dry_run:
            print(f"  [DRY-RUN] Would ask: {text[:80]}")
            answers[key] = "neutral"
            explanations[key] = "[dry-run]"
            history.append({"role": "user",      "content": text})
            history.append({"role": "assistant",  "content": '{"explanation":"[dry-run]","answer":"neutral"}'})
            continue

        # Apply sliding window: keep only the last N Q&A pairs
        if max_pairs > 0:
            window = history[-(max_pairs * 2):]
        else:
            window = history

        result, tokens, was_fallback = client.ask_single(
            system_prompt=config.system_prompt,
            messages=window,
            question_text=text,
        )
        total_tokens += tokens
        if was_fallback:
            fallback_keys.append(key)

        answer = result.get("answer", "neutral")
        explanation = result.get("explanation", "")

        answers[key] = answer
        explanations[key] = explanation

        # Append this exchange to the full history
        history.append({"role": "user", "content": text})
        history.append({
            "role": "assistant",
            "content": json.dumps({"explanation": explanation, "answer": answer}),
        })

        print(f"  → {answer}")

    if max_pairs > 0:
        logger.info(
            f"Sequential mode used sliding window of {max_pairs} Q&A pairs "
            f"(out of {len(history) // 2} total)"
        )

    duration = time.monotonic() - start
    return RunResult(answers, explanations, duration, total_tokens, len(fallback_keys), fallback_keys)
