"""Core format conversion logic — calls the Anthropic API."""

from __future__ import annotations

import json
from typing import Optional

import anthropic

from app.config import get_settings
from app.prompts import CONVERSION_PROMPTS, VALIDATION_PROMPTS

MODEL = "claude-haiku-4-5-20251001"


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the model returns them despite instructions."""
    import re
    # Strip ```json ... ``` or ``` ... ``` blocks
    fenced = re.match(r"^```[a-zA-Z]*\n?(.*?)```$", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return text


def _client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def convert(input_text: str, pair: tuple[str, str]) -> str:
    """Convert input_text from pair[0] format to pair[1] format.

    Calls the Claude API using the appropriate system prompt.
    Returns the raw converted output string.
    """
    system_prompt = CONVERSION_PROMPTS.get(pair)
    if system_prompt is None:
        raise ValueError(f"Unsupported conversion pair: {pair}")

    message = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": input_text}],
    )
    return _strip_code_fences(message.content[0].text.strip())


def validate_output(output: str, to_format: str) -> tuple[bool, Optional[list[str]]]:
    """Run a structural validation pass on the converted output.

    Returns (valid, errors) where errors is None if valid=True.
    """
    system_prompt = VALIDATION_PROMPTS.get(to_format)
    if system_prompt is None:
        raise ValueError(f"No validation prompt for format: {to_format}")

    message = _client().messages.create(
        model=MODEL,
        max_tokens=256,
        system=system_prompt,
        messages=[{"role": "user", "content": output}],
    )
    raw = message.content[0].text.strip()

    try:
        result = json.loads(raw)
        valid = bool(result.get("valid", False))
        errors = result.get("errors") or []
        return valid, (errors if errors else None)
    except json.JSONDecodeError:
        return False, ["validation parse failed — model returned non-JSON"]
