"""
MCP server adapter — Phase 4b of DualRail build.

Rail 2 of DualRail: MCP/MCP-Hive fiat billing channel.
Rail 1 (x402 USDC micropayments) is unchanged — both channels co-exist.

MCP-Hive handles billing at the marketplace layer. This server has no payment gate.
Tools call formatter logic directly — no x402 required from the MCP side.

Transport: SSE, mounted in FastAPI via app.mount("/mcp", mcp.sse_app())
Directories to list on: Smithery, LobeHub, mcp.so, MCP-Hive

Tools:
  format_data      — CSV/XML/Markdown → JSON/HTML
                     calls app.formatter.convert() + app.formatter.validate_output()
                     via asyncio.to_thread (both are sync Anthropic SDK calls)
  validate_schema  — JSON Schema Draft 7 validation
                     calls project_x402 /v1/schema-check/trial via HTTP
  get_capabilities — full x402 task market capability manifest
                     calls project_a2a /v1/capabilities via HTTP

Environment variables (set in Railway):
  MCP_SCHEMA_CHECKER_TRIAL_URL  — defaults to schema-checker /trial endpoint
  MCP_A2A_CAPABILITIES_URL      — defaults to A2A hub /v1/capabilities (must set live URL)
"""

import asyncio
import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

from app.formatter import convert, validate_output
from app.models import VALID_PAIRS

# ── FastMCP instance ───────────────────────────────────────────────────────────

mcp = FastMCP(
    name="x402-formatter",
    instructions=(
        "This MCP server provides data transformation and validation tools powered by "
        "the x402 task market pipeline. "
        "Use format_data to convert CSV, XML, or Markdown to JSON or HTML — with optional "
        "self-validation. "
        "Use validate_schema to check any JSON payload against a JSON Schema Draft 7 definition. "
        "Use get_capabilities to discover all available services, endpoints, and pricing."
    ),
)


# ── External service URLs ──────────────────────────────────────────────────────

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


# ── Tool: format_data ──────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Convert structured data between formats using Claude AI. "
        "Accepts CSV, XML, or Markdown as input and returns JSON or HTML. "
        "Supported pairs: csv→json, xml→json, markdown→html. "
        "Set validate=true to run a structural validation pass after conversion — "
        "the response will include valid (bool) and errors (list of strings) alongside result."
    )
)
async def format_data(
    input: str,
    from_format: str,
    to_format: str,
    validate: bool = False,
) -> str:
    """
    Convert input from one format to another.

    Args:
        input:       Raw content to convert (CSV rows, XML string, or Markdown text).
        from_format: Source format. One of: csv, xml, markdown.
        to_format:   Target format. One of: json, html.
        validate:    If True, run a structural validation pass and return valid + errors[].

    Returns:
        JSON-encoded dict: {"result": "<converted output>"}
        With validate=True: {"result": "...", "valid": true|false, "errors": [...]}
        On error:           {"error": "<description>"}
    """
    pair = (from_format.lower(), to_format.lower())

    if pair not in VALID_PAIRS:
        return json.dumps({
            "error": (
                f"Unsupported conversion: {from_format!r} → {to_format!r}. "
                "Supported pairs: csv→json, xml→json, markdown→html."
            )
        })

    if not input or not input.strip():
        return json.dumps({"error": "input is empty"})

    # convert() is a sync Anthropic SDK call — run in a thread to avoid blocking the event loop
    try:
        result = await asyncio.to_thread(convert, input, pair)
    except Exception as exc:
        return json.dumps({"error": f"Conversion failed: {exc}"})

    if validate:
        # validate_output() is also sync — same pattern
        try:
            valid, errors = await asyncio.to_thread(validate_output, result, pair[1])
        except Exception as exc:
            return json.dumps({"error": f"Validation failed: {exc}"})
        return json.dumps({"result": result, "valid": valid, "errors": errors})

    return json.dumps({"result": result})


# ── Tool: validate_schema ──────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Validate a JSON payload against a JSON Schema Draft 7 definition. "
        "Returns valid/invalid status with field-level error paths for each violation. "
        "Optionally returns a suggested repaired payload when validation fails. "
        "Calls the schema-checker trial endpoint — no x402 payment required."
    )
)
async def validate_schema(
    payload: dict,
    schema: dict,
) -> str:
    """
    Validate a JSON payload against a JSON Schema.

    Args:
        payload: JSON object to validate.
        schema:  JSON Schema Draft 7 definition.

    Returns:
        JSON-encoded dict from the schema-checker service:
            {"valid": bool, "errors": [...], "suggested_payload": {...}}
        On error: {"error": "<description>"}
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                _schema_checker_trial_url(),
                json={"payload": payload, "schema": schema},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.text
        except httpx.TimeoutException:
            return json.dumps({"error": "schema-checker timed out after 30 s"})
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            return json.dumps({
                "error": f"schema-checker returned HTTP {exc.response.status_code}",
                "detail": body,
            })
        except Exception as exc:
            return json.dumps({"error": f"validate_schema failed: {exc}"})


# ── Tool: get_capabilities ─────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Retrieve the full capability manifest for the x402 task market. "
        "Returns every available service with its endpoint URL, supported input/output formats, "
        "x402 payment details (network, price, asset), and free trial endpoint. "
        "Use this to discover what the pipeline can do before calling specific tools."
    )
)
async def get_capabilities() -> str:
    """
    Fetch the A2A hub capability manifest.

    Returns:
        JSON-encoded capability manifest with all services and their metadata.
        On error: {"error": "<description>"}
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(_a2a_capabilities_url())
            resp.raise_for_status()
            return resp.text
        except httpx.TimeoutException:
            return json.dumps({"error": "A2A hub timed out after 10 s"})
        except httpx.HTTPStatusError as exc:
            return json.dumps({
                "error": f"A2A hub returned HTTP {exc.response.status_code}"
            })
        except Exception as exc:
            return json.dumps({"error": f"get_capabilities failed: {exc}"})
