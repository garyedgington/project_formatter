"""
MCP server adapter - DualRail Rail 2 (fiat billing via MCP-Hive).
Rail 1 (x402 USDC) is unchanged - both channels co-exist.

Transport: SSE via app.mount("/mcp", mcp.sse_app()) in main.py
Tools: format_data
"""

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from app.formatter import convert, validate_output
from app.models import VALID_PAIRS

mcp = FastMCP(
    name="x402-formatter",
    instructions=(
        "Data format conversion tool from the x402 task market. "
        "Use format_data to convert CSV, XML, or Markdown to JSON or HTML. "
        "Optional structural validation pass available via validate=true."
    ),
)


@mcp.tool()
async def format_data(
    input: str,
    from_format: str,
    to_format: str,
    validate: bool = False,
) -> str:
    """Convert structured data between formats using Claude AI.

    Supported conversion pairs: csv->json, xml->json, markdown->html.
    Set validate=true to run a structural validation pass after conversion
    and receive valid (bool) and errors (list) alongside the result.

    Args:
        input: Raw content to convert.
        from_format: Source format - csv, xml, or markdown.
        to_format: Target format - json or html.
        validate: If true, validate the converted output and return errors.

    Returns:
        JSON string: {"result": "..."} or with validate=true:
        {"result": "...", "valid": true/false, "errors": [...]}
    """
    pair = (from_format.lower(), to_format.lower())

    if pair not in VALID_PAIRS:
        return json.dumps({
            "error": (
                "Unsupported conversion: " + from_format + " to " + to_format + ". "
                "Supported: csv->json, xml->json, markdown->html."
            )
        })

    if not input or not input.strip():
        return json.dumps({"error": "input is empty"})

    try:
        result = await asyncio.to_thread(convert, input, pair)
    except Exception as exc:
        return json.dumps({"error": "Conversion failed: " + str(exc)})

    if validate:
        try:
            valid, errors = await asyncio.to_thread(validate_output, result, pair[1])
        except Exception as exc:
            return json.dumps({"error": "Validation failed: " + str(exc)})
        return json.dumps({"result": result, "valid": valid, "errors": errors})

    return json.dumps({"result": result})
