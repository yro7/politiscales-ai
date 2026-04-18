"""
Shared types for the PolitiScales-AI runner.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, NamedTuple, Protocol

if TYPE_CHECKING:
    from runner.client import OpenRouterClient
    from runner.config import RunConfig


# ---------------------------------------------------------------------------
# Answer enum — single source of truth for the five PolitiScales values
# ---------------------------------------------------------------------------

class Answer(str, Enum):
    """The five possible PolitiScales response values."""

    STRONGLY_AGREE = "strongly agree"
    AGREE = "agree"
    NEUTRAL = "neutral"
    DISAGREE = "disagree"
    STRONGLY_DISAGREE = "strongly disagree"

    @classmethod
    def from_str(cls, value: str) -> Answer | None:
        """Parse a free-form string into an Answer, returning None if invalid."""
        try:
            return cls(value.strip().lower())
        except ValueError:
            return None


# Ordered longest-first so that substring fallback matching in client.py
# doesn't false-match "agree" before "strongly agree" or "disagree".
ANSWER_VALUES_LONGEST_FIRST: list[str] = [
    Answer.STRONGLY_DISAGREE.value,
    Answer.STRONGLY_AGREE.value,
    Answer.DISAGREE.value,
    Answer.AGREE.value,
    Answer.NEUTRAL.value,
]


# ---------------------------------------------------------------------------
# RunResult — return type for all mode runner functions
# ---------------------------------------------------------------------------

class RunResult(NamedTuple):
    """Return type for all mode runner functions."""

    answers: Dict[str, str]
    explanations: Dict[str, str]
    duration_s: float
    fallback_count: int = 0


# ---------------------------------------------------------------------------
# ModeRunner protocol — structural type that all mode .run() functions satisfy
# ---------------------------------------------------------------------------

class ModeRunner(Protocol):
    """Protocol that every mode runner function must conform to."""

    def __call__(
        self,
        client: OpenRouterClient,
        config: RunConfig,
        questions: Dict[str, str],
        dry_run: bool = ...,
    ) -> RunResult: ...
