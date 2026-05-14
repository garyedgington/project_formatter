"""
MCP server adapter - DualRail Rail 2 (fiat billing via MCP-Hive).
Rail 1 (x402 USDC) is unchanged - both channels co-exist.

Transport: SSE via app.mount("/", mcp.sse_app()) in main.py
Tools: format_data
"""

# NOTE: intentionally no "from __future__ import annotations" here.
# FastMCP's tool registration uses inspect.signature() at decoration time
# and calls issubclass(param.annotation, Context) -- which requires live
# type objects, not the lazy strings that the future import produces.
import asyncio

from typing import Any, Dict, List, Literal, Optional, Union
from typing_extensions import TypedDict

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.formatter import convert, validate_output
from app.models import VALID_PAIRS

# ---------------------------------------------------------------------------
# Output type definitions (used by FastMCP to generate outputSchema)
# ---------------------------------------------------------------------------

class FormatResult(TypedDict):
    result: Optional[str]
    valid: Optional[bool]
    errors: Optional[List[str]]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Shared annotations: format_data is read-only and idempotent
# ---------------------------------------------------------------------------

_READONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="x402-formatter",
    instructions=(
        "Data format conversion tool from the x402 task market. "
        "Use format_data to convert CSV, XML, or Markdown to JSON or HTML. "
        "Optional structural validation pass available via validate=true."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def format_data(
    input: str,
    from_format: Literal["csv", "xml", "markdown"],
    to_format: Literal["json", "html"],
    validate: bool = False,
) -> FormatResult:
    """Convert structured data between formats using AI Agents.

    Supported conversion pairs: csv->json, xml->json, markdown->html.
    Set validate=true to run a structural validation pass after conversion
    and receive valid (bool) and errors (list) alongside the result.

    Args:
        input: Raw content to convert (CSV rows, XML string, or Markdown text).
        from_format: Source format. Valid pairs: csv->json, xml->json, markdown->html.
        to_format: Target format. Valid pairs: csv->json, xml->json, markdown->html.
        validate: If true, validate the converted output and return errors.

    Returns:
        result (str), or with validate=true: result (str), valid (bool), errors (list).
        On failure: error (str).
    """
    pair = (from_format.lower(), to_format.lower())

    if pair not in VALID_PAIRS:
        return FormatResult(
            result=None,
            valid=None,
            errors=None,
            error=(
                "Unsupported conversion: " + from_format + " to " + to_format + ". "
                "Supported: csv->json, xml->json, markdown->html."
            ),
        )

    if not input or not input.strip():
        return FormatResult(result=None, valid=None, errors=None, error="input is empty")

    try:
        result = await asyncio.to_thread(convert, input, pair)
    except Exception as exc:
        return FormatResult(result=None, valid=None, errors=None, error="Conversion failed: " + str(exc))

    if validate:
        try:
            valid, errors = await asyncio.to_thread(validate_output, result, pair[1])
        except Exception as exc:
            return FormatResult(result=None, valid=None, errors=None, error="Validation failed: " + str(exc))
        return FormatResult(result=result, valid=valid, errors=errors, error=None)

    return FormatResult(result=result, valid=None, errors=None, error=None)
