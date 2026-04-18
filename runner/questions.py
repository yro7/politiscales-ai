"""
Load PolitiScales questions from the i18n locale files in the submodule.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

# Path relative to this file: ../politiscales/i18n/locales/
_LOCALES_DIR = (
    Path(__file__).parent.parent / "politiscales" / "i18n" / "locales"
)


def load_questions(language: str) -> Dict[str, str]:
    """
    Load the question texts for a given language.

    Returns a dict mapping question_key -> question_text.
    Raises FileNotFoundError if the locale file does not exist.
    Raises KeyError if the locale file has no 'questions' section.
    """
    locale_file = _LOCALES_DIR / f"{language}.json"
    if not locale_file.exists():
        available = [p.stem for p in _LOCALES_DIR.glob("*.json")]
        raise FileNotFoundError(
            f"No locale file for language '{language}'. "
            f"Available: {available}"
        )
    with locale_file.open(encoding="utf-8") as f:
        data = json.load(f)

    questions: Dict[str, str] = data.get("questions", {})
    if not questions:
        raise KeyError(
            f"Locale file '{locale_file}' has no 'questions' key or it is empty."
        )
    return questions


def load_ui_strings(language: str) -> Dict[str, str]:
    """Load all UI strings (including questions) for a given language."""
    locale_file = _LOCALES_DIR / f"{language}.json"
    with locale_file.open(encoding="utf-8") as f:
        return json.load(f)
