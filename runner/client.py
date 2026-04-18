"""
OpenRouter API client — OpenAI-compatible endpoint.

Uses the ``openai`` Python SDK pointed at https://openrouter.ai/api/v1.
Structured output (JSON schema) is used for every question response.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from runner.types import Answer, ANSWER_VALUES_LONGEST_FIRST

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry

# ---------------------------------------------------------------------------
# Structured output schema for a single-question response
# ---------------------------------------------------------------------------
SINGLE_Q_SCHEMA = {
    "name": "politiscales_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "explanation": {
                "type": "string",
                "description": (
                    "A clear justification for your position on this statement "
                    "(2–4 sentences)."
                ),
            },
            "answer": {
                "type": "string",
                "enum": [a.value for a in Answer],
                "description": "Your stance on the statement.",
            },
        },
        "required": ["explanation", "answer"],
        "additionalProperties": False,
    },
}

# Schema used by batch mode — answers keyed by question ID
def batch_schema(question_keys: list[str]) -> dict:
    return {
        "name": "politiscales_batch_answers",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                q: {
                    "type": "object",
                    "properties": {
                        "explanation": {"type": "string"},
                        "answer": {
                            "type": "string",
                            "enum": [a.value for a in Answer],
                        },
                    },
                    "required": ["explanation", "answer"],
                    "additionalProperties": False,
                }
                for q in question_keys
            },
            "required": question_keys,
            "additionalProperties": False,
        },
    }


class OpenRouterClient:
    """Thin wrapper around the OpenAI SDK configured for OpenRouter."""

    def __init__(self, api_key: str, api_base: str, model: str,
                 temperature: float, max_tokens: int, top_p: float):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={
                "HTTP-Referer": "https://github.com/politiscales-ai",
                "X-Title": "PolitiScales-AI",
            },
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

    def _call(
        self,
        messages: list[dict[str, str]],
        response_format: None | dict = None,
        max_tokens_override: None | int = None,
    ) -> tuple[str, int]:
        """
        Call the chat completions endpoint with retry logic.
        Returns (content_string, tokens_used).
        """
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens_override if max_tokens_override is not None else self.max_tokens,
            top_p=self.top_p,
        )
        if response_format is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": response_format,
            }

        last_error: None | Exception = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                tokens = resp.usage.total_tokens if resp.usage else 0
                return content, tokens
            except RateLimitError as e:
                last_error = e
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"Rate limited (attempt {attempt}/{MAX_RETRIES}), "
                    f"retrying in {delay:.0f}s…"
                )
                time.sleep(delay)
            except (APIError, APIConnectionError, APITimeoutError) as e:
                last_error = e
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"API error: {e} (attempt {attempt}/{MAX_RETRIES}), "
                    f"retrying in {delay:.0f}s…"
                )
                time.sleep(delay)

        # All retries exhausted
        raise RuntimeError(
            f"API call failed after {MAX_RETRIES} retries: {last_error}"
        ) from last_error

    def ask_single(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        question_text: str,
    ) -> tuple[dict[str, str], int, bool]:
        """
        Ask a single question.
        Appends the question as a new user message and calls the API.

        Returns:
            ({"explanation": "...", "answer": "..."}, tokens, fallback_used)
        """
        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)
        full_messages.append({"role": "user", "content": question_text})

        content, tokens = self._call(full_messages, response_format=SINGLE_Q_SCHEMA)
        try:
            parsed = json.loads(content)
            # Validate that the answer is actually one of the enum values
            if Answer.from_str(parsed.get("answer", "")) is None:
                logger.warning(
                    f"Structured response contained invalid answer "
                    f"'{parsed.get('answer')}', treating as fallback"
                )
                return _fallback_parse_single(content), tokens, True
            return parsed, tokens, False
        except json.JSONDecodeError:
            # Graceful fallback — extract answer with heuristics
            return _fallback_parse_single(content), tokens, True

    def ask_batch(
        self,
        system_prompt: str,
        questions: dict[str, str],
    ) -> tuple[dict[str, dict[str, str]], int, bool]:
        """
        Send all questions in one prompt.

        Returns:
            ({question_key: {"explanation": ..., "answer": ...}}, tokens, fallback_used)
        """
        question_keys = list(questions.keys())
        lines = [
            "Please answer each of the following political statements.\n"
            "Return a JSON object where each key is a question ID, "
            "and each value contains 'explanation' and 'answer'.\n"
        ]
        for key, text in questions.items():
            lines.append(f"[{key}] {text}")

        user_content = "\n".join(lines)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ]

        schema = batch_schema(question_keys)
        # Batch mode needs much more output tokens (117 questions × ~100 tokens each)
        batch_max_tokens = max(self.max_tokens, len(question_keys) * 150)
        content, tokens = self._call(
            messages, response_format=schema, max_tokens_override=batch_max_tokens
        )
        try:
            parsed = json.loads(content)
            return parsed, tokens, False
        except json.JSONDecodeError:
            logger.warning(
                "Batch response was not valid JSON, falling back to heuristic parsing. "
                f"Response length: {len(content)} chars"
            )
            return _fallback_parse_batch(content, question_keys), tokens, True


# ---------------------------------------------------------------------------
# Fallback parsers (in case structured output is not supported by the model)
# ---------------------------------------------------------------------------

def _fallback_parse_single(text: str) -> dict[str, str]:
    """Try to extract answer from free-form text."""
    text_lower = text.lower()
    answer = Answer.NEUTRAL.value
    for candidate in ANSWER_VALUES_LONGEST_FIRST:
        if candidate in text_lower:
            answer = candidate
            break
    logger.warning(f"Fallback parser used — extracted '{answer}' from model output")
    return {"explanation": text.strip(), "answer": answer}


def _fallback_parse_batch(text: str, keys: list[str]) -> dict[str, dict[str, str]]:
    """Attempt JSON parse of batch response, defaulting to neutral on failure."""
    result: dict[str, dict[str, str]] = {}
    try:
        parsed = json.loads(text)
        for key in keys:
            if key in parsed and isinstance(parsed[key], dict):
                result[key] = parsed[key]
            else:
                result[key] = {"explanation": "", "answer": Answer.NEUTRAL.value}
    except json.JSONDecodeError:
        for key in keys:
            result[key] = {"explanation": "", "answer": Answer.NEUTRAL.value}
    return result
