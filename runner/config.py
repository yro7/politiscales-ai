"""
Configuration dataclass and CLI argument parsing.
"""
from __future__ import annotations

import argparse
import os
import json
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_LANGUAGES = ["en", "fr", "es", "it", "ru", "zh", "ar"]
SUPPORTED_MODES = ["no_history", "sequential", "batch"]
SUPPORTED_PROMPT_TYPES = ["survey", "incognito"]

_PROMPTS_FILE = Path(__file__).parent / "data" / "prompts.json"


def _load_prompts() -> dict[str, dict[str, str]]:
    """Load the centralized system prompts mapping."""
    if not _PROMPTS_FILE.exists():
        return {"survey": {"en": "You are participating in a political opinion survey."}}
    with _PROMPTS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def get_default_system_prompt(prompt_type: str, lang: str) -> str:
    """Resolve the localized system prompt for a given type and language."""
    prompts = _load_prompts()
    type_prompts = prompts.get(prompt_type, prompts.get("survey", {}))
    return type_prompts.get(lang, type_prompts.get("en", ""))


AVAILABLE_MODELS = [
    # OpenAI
    "openai/gpt-4.1", "openai/gpt-4.1-mini", "openai/gpt-4.1-nano", "openai/gpt-4o",
    # Google
    "google/gemini-2.5-flash", "google/gemini-2.5-pro",
    # DeepSeek
    "deepseek/deepseek-chat-v3-0324", "deepseek/deepseek-r1",
    # Anthropic
    "anthropic/claude-sonnet-4", "anthropic/claude-haiku-3.5", "anthropic/claude-opus-4",
    # Mistral
    "mistralai/mistral-large", "mistralai/mistral-small-3.1-24b-instruct",
    # Meta
    "meta-llama/llama-4-maverick", "meta-llama/llama-4-scout",
    # xAI
    "x-ai/grok-3", "x-ai/grok-3-mini",
    # Other
    "qwen/qwen3-235b-a22b", "microsoft/phi-4",
]


@dataclass
class RunConfig:
    """All parameters that define a single test run."""

    models: list[str]
    language: str
    mode: str
    prompt_type: str
    temperature: float
    max_tokens: int
    top_p: float
    system_prompt: str
    runs: int
    concurrency: int
    max_history: int
    output_dir: str
    dry_run: bool
    api_key: str
    compare_langs: bool = False
    compare_modes: bool = False
    compare_prompts: bool = False
    api_base: str = "https://openrouter.ai/api/v1"
    notes: str | None = None


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Make AI models take the PolitiScales political test via the OpenRouter API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--model", nargs="+", default=["openai/gpt-4.1"],
                        help=f"Model ID(s) (provider/model format). Accepts multiple models. Known: {', '.join(AVAILABLE_MODELS)}")
    parser.add_argument("--lang", default="en", choices=SUPPORTED_LANGUAGES,
                        help="Language of the questionnaire.")
    parser.add_argument("--mode", default="sequential", choices=SUPPORTED_MODES,
                        help=(
                            "no_history: each question is a fresh call | "
                            "sequential: one-by-one with chat history | "
                            "batch: all questions in one prompt"
                        ))
    parser.add_argument("--prompt-type", default="survey", choices=SUPPORTED_PROMPT_TYPES,
                        help="The 'style' of the system prompt (survey vs incognito).")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Sampling temperature (0.0-2.0).")
    parser.add_argument("--max-tokens", type=int, default=512,
                        help="Max tokens per API response.")
    parser.add_argument("--top-p", type=float, default=1.0,
                        help="Nucleus sampling probability.")
    parser.add_argument("--system-prompt", default=None,
                        help="System prompt sent to the model (defaults to localized prompt if not set).")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of times to repeat the full test. Results are aggregated into one file.")
    parser.add_argument("--concurrency", type=int, default=10,
                        help="Max parallel API calls (for no_history mode and multi-runs).")
    parser.add_argument("--output-dir", default="./results",
                        help="Directory to save result JSON files.")
    parser.add_argument("--max-history", type=int, default=0,
                        help=(
                            "Max Q&A pairs to keep in sequential mode history. "
                            "0 = unlimited (send full history). Recommended: 10-20 "
                            "for small-context models to avoid token overflow."
                        ))
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without calling the API.")
    parser.add_argument("--notes", default=None,
                        help="Optional freeform notes stored in the result metadata.")
    parser.add_argument("--api-key", default=None,
                        help="OpenRouter API key. Defaults to OPENROUTER_API_KEY env var.")
    parser.add_argument("--api-base", default="https://openrouter.ai/api/v1",
                        help="API base URL (override for testing).")

    # Comparison flags
    parser.add_argument("--compare-langs", action="store_true",
                        help="Run benchmark for all supported languages.")
    parser.add_argument("--compare-modes", action="store_true",
                        help="Run benchmark for all supported execution modes.")
    parser.add_argument("--compare-prompts", action="store_true",
                        help="Run benchmark for all supported system prompt types.")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.dry_run:
        parser.error(
            "No API key provided. Set OPENROUTER_API_KEY env variable or use --api-key."
        )

    # Automatically select localized system prompt if not overridden
    system_prompt = args.system_prompt
    if system_prompt is None:
        system_prompt = get_default_system_prompt(args.prompt_type, args.lang)

    return RunConfig(
        models=args.model,
        language=args.lang,
        mode=args.mode,
        prompt_type=args.prompt_type,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        system_prompt=system_prompt,
        runs=args.runs,
        concurrency=args.concurrency,
        max_history=args.max_history,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        notes=args.notes,
        api_key=api_key,
        compare_langs=args.compare_langs,
        compare_modes=args.compare_modes,
        compare_prompts=args.compare_prompts,
        api_base=args.api_base,
    )
