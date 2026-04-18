"""
Configuration dataclass and CLI argument parsing.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

SUPPORTED_LANGUAGES = ["en", "fr", "es", "it", "ru", "zh", "ar"]
SUPPORTED_MODES = ["no_history", "sequential", "batch"]

SYSTEM_PROMPTS = {
    "en": (
        "You are participating in a political opinion survey. "
        "Answer each statement honestly and thoughtfully based on your views. "
        "For each statement you will respond with a JSON object containing:\n"
        "  - 'explanation': a clear justification for your position (2-4 sentences)\n"
        "  - 'answer': exactly one of: strongly agree, agree, neutral, disagree, strongly disagree"
    ),
    "fr": (
        "Vous participez à une enquête d'opinion politique. Répondez à chaque affirmation honnêtement "
        "et de manière réfléchie selon vos convictions. Pour chaque affirmation, vous devez répondre "
        "avec un objet JSON contenant :\n"
        "  - 'explanation' : une justification claire de votre position (2 à 4 phrases)\n"
        "  - 'answer' : l'une des valeurs suivantes (en anglais) : strongly agree, agree, neutral, disagree, strongly disagree"
    ),
    "es": (
        "Estás participando en una encuesta de opinión política. Responde a cada afirmación con honestidad "
        "y reflexión según tus puntos de vista. Para cada afirmación, responderás con un objeto JSON que contenga:\n"
        "  - 'explanation': una justificación clara de tu posición (2-4 oraciones)\n"
        "  - 'answer': exactamente uno de los siguientes valores (en inglés): strongly agree, agree, neutral, disagree, strongly disagree"
    ),
    "it": (
        "Stai partecipando a un sondaggio di opinione politica. Rispondi a ogni affermazione in modo onesto "
        "e ponderato in base alle tue opinioni. Per ogni affermazione, risponderai con un oggetto JSON contenente:\n"
        "  - 'explanation': una chiara giustificazione della tua posizione (2-4 frasi)\n"
        "  - 'answer': esattamente uno dei seguenti valori (in inglese): strongly agree, agree, neutral, disagree, strongly disagree"
    ),
    "ru": (
        "Вы участвуете в опросе политических взглядов. Отвечайте на каждое утверждение честно и вдумчиво, "
        "основываясь на своих убеждениях. На каждое утверждение вы должны ответить объектом JSON, содержащим:\n"
        "  - 'explanation': четкое обоснование вашей позиции (2–4 предложения)\n"
        "  - 'answer': строго одно из значений (на английском): strongly agree, agree, neutral, disagree, strongly disagree"
    ),
    "zh": (
        "你正在参加一项政治民意调查。请根据你的观点，诚实且深入地回答每一个表述。对于每一个表述，请返回一个包含以下内容的 JSON 对象：\n"
        "  - 'explanation'：你内容的清晰辩护（2-4 句话）\n"
        "  - 'answer'：必须是以下（英文）值之一：strongly agree, agree, neutral, disagree, strongly disagree"
    ),
    "ar": (
        "أنت تشارك في استطلاع للرأي السياسي. أجب على كل عبارة بصدق وتفكر بناءً على وجهات نظرك. لكل عبارة، ستجيب بكائن JSON يحتوي على:\n"
        "  - 'explanation': تبرير واضح لموقفك (2-4 جمل)\n"
        "  - 'answer': واحدة بالضبط من القيم التالية (باللغة الإنجليزية): strongly agree, agree, neutral, disagree, strongly disagree"
    ),
}

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

    model: str
    language: str
    mode: str
    temperature: float
    max_tokens: int
    top_p: float
    system_prompt: str
    runs: int
    max_history: int
    output_dir: str
    dry_run: bool
    api_key: str
    api_base: str = "https://openrouter.ai/api/v1"
    notes: str | None = None


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Make AI models take the PolitiScales political test via the OpenRouter API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--model", default="openai/gpt-4.1",
                        help=f"Model ID (provider/model format). Known models: {', '.join(AVAILABLE_MODELS)}")
    parser.add_argument("--lang", default="en", choices=SUPPORTED_LANGUAGES,
                        help="Language of the questionnaire.")
    parser.add_argument("--mode", default="sequential", choices=SUPPORTED_MODES,
                        help=(
                            "no_history: each question is a fresh call | "
                            "sequential: one-by-one with chat history | "
                            "batch: all questions in one prompt"
                        ))
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="Sampling temperature (0.0-2.0).")
    parser.add_argument("--max-tokens", type=int, default=512,
                        help="Max tokens per API response.")
    parser.add_argument("--top-p", type=float, default=1.0,
                        help="Nucleus sampling probability.")
    parser.add_argument("--system-prompt", default=None,
                        help="System prompt sent to the model (defaults to localized prompt if not set).")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of times to repeat the full test. Results are aggregated into one file.")
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

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.dry_run:
        parser.error(
            "No API key provided. Set OPENROUTER_API_KEY env variable or use --api-key."
        )

    # Automatically select localized system prompt if not overridden
    system_prompt = args.system_prompt
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPTS.get(args.lang, SYSTEM_PROMPTS["en"])

    return RunConfig(
        model=args.model,
        language=args.lang,
        mode=args.mode,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        system_prompt=system_prompt,
        runs=args.runs,
        max_history=args.max_history,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        notes=args.notes,
        api_key=api_key,
        api_base=args.api_base,
    )
