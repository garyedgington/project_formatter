"""
MCP server adapter - Phase 4b of DualRail build.

Rail 2: MCP/MCP-Hive fiat billing channel.
Rail 1 (x402 USDC) is unchanged - both channels co-exist.

Transport: SSE via app.mount("/mcp", mcp.sse_app()) in main.py
Tools: format_data, validate_schema, get_capabilities

All parameter annotations use only built-in scalar types (str, bool) to ensure
compatibility with FastMCP's issubclass(param.annotation, Context) check across
all Python versions. Complex inputs (payload, schema) are accepted as JSON strings.
"""

import asyncio
import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

from app.formatter import convert, validate_output
from app.models import VALID_PAIRS

mcp = FastMCP(
    name="x402-formatter",
    instructions=(
        "Data transformation and validation tools from the x402 task market. "
        "Use format_data to convert CSV, XML, or Markdown to JSON or HTML. "
        "Use validate_schema to validate JSON payloads against a JSON Schema. "
        "Use get_capabilities to list all available services and endpoints."
    ),
)


def _schema_checker_trial_url() -> str:
    return os.getenv(
        "MCP_SCHEMA_CHECKER_TRIAL_URL",
        "https://projectx402-production.up.railway.app/v1/schema-check/trial",
    )


def _a2a_capabilities_url() -> str:
    return os.getenv(
        "MCP_A2A_CAPABILITIES_URL",
        "https://project-a2a-production.up.railway.app/v1/capabilities",
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


@mcp.tool()
async def validate_schema(
    payload: str,
    schema: str,
) -> str:
    """Validate a JSON payload against a JSON Schema Draft 7 definition.

    Returns valid/invalid status with field-level error paths for each violation.
    Calls the schema-checker trial endpoint - no x402 payment required.

    Args:
        payload: The JSON object to validate, as a JSON-encoded string.
        schema: The JSON Schema Draft 7 definition, as a JSON-encoded string.

    Returns:
        JSON string: {"valid": true/false, "errors": [...], "suggested_payload": {...}}
    """
    try:
        payload_obj = json.loads(payload)
    except Exception:
        return json.dumps({"error": "payload is not valid JSON"})

    try:
        schema_obj = json.loads(schema)
    except Exception:
        return json.dumps({"error": "schema is not valid JSON"})

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                _schema_checker_trial_url(),
                json={"payload": payload_obj, "schema": schema_obj},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.text
        except httpx.TimeoutException:
            return json.dumps({"error": "schema-checker timed out"})
        except httpx.HTTPStatusError as exc:
            return json.dumps({"error": "schema-checker returned HTTP " + str(exc.response.status_code)})
        except Exception as exc:
            return json.dumps({"error": "validate_schema failed: " + str(exc)})


@mcp.tool()
async def get_capabilities() -> str:
    """Retrieve the full capability manifest for the x402 task market.

    Returns all available services with endpoint URLs, supported formats,
    x402 payment details, and free trial endpoints.

    Returns:
        JSON string with all service capabilities and metadata.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(_a2a_capabilities_url())
            resp.raise_for_status()
            return resp.text
        except httpx.TimeoutException:
            return json.dumps({"error": "A2A hub timed out"})
        except httpx.HTTPStatusError as exc:
            return json.dumps({"error": "A2A hub returned HTTP " + str(exc.response.status_code)})
        except Exception as exc:
            return json.dumps({"error": "get_capabilities failed: " + str(exc)})
