# x402 Data Formatter

Convert CSV, XML, or Markdown to JSON or HTML using Claude AI. Optional structural validation. Part of the [x402 micropayment task market](https://project-a2a-production.up.railway.app/v1/capabilities).

**Live service:** `https://project-formatter-production.up.railway.app`  
**Smithery:** [gary-edgington/x402-data-formatter](https://smithery.ai/server/gary-edgington/x402-data-formatter)  
**Payment:** $0.005 USDC per call · x402 v2 · Base mainnet

---

## Supported Conversions

| Input | Output |
|---|---|
| CSV | JSON |
| XML | JSON |
| Markdown | HTML |

---

## Endpoints

### `POST /v1/format` — Paid

Requires x402 payment header. $0.005 USDC on Base mainnet.

**Request body:**
```json
{
  "input": "<raw input string>",
  "from": "csv" | "xml" | "markdown",
  "to": "json" | "html"
}
```

**Query params:**
- `?validate=true` — run a structural validation pass after conversion. Adds `valid` (bool) and `errors` (list) to the response.

**Response (200):**
```json
{ "result": "<converted output>" }
```

**Response with `?validate=true`:**
```json
{ "result": "<converted output>", "valid": true, "errors": [] }
```

**Response (402 — no payment):**
```json
{
  "x402Version": 2,
  "accepts": [{
    "scheme": "exact",
    "network": "eip155:8453",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "amount": "5000",
    "payTo": "0x8fC4006534801c17A3368075A1Fb3b3C511EdB1F",
    "maxTimeoutSeconds": 300
  }],
  "error": "Payment required"
}
```

---

### `POST /v1/format/trial` — Free

No payment required. Same conversion logic. Limits: 32KB max input, no `?validate` support.

---

### `GET /health`

```json
{ "status": "ok", "service": "formatter-agent", "version": "0.1.0" }
```

---

## MCP Tool

This service exposes a single MCP tool via SSE transport for use with MCP-compatible agents and Claude Desktop.

**SSE endpoint:** `https://project-formatter-production.up.railway.app/sse`

### `format_data`

Convert structured data between formats using Claude AI.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `input` | string | ✅ | Raw content to convert |
| `from_format` | string | ✅ | `csv`, `xml`, or `markdown` |
| `to_format` | string | ✅ | `json` or `html` |
| `validate` | boolean | — | If true, validate output and return errors |

---

## x402 Payment Details

| Setting | Value |
|---|---|
| Network | Base mainnet (`eip155:8453`) |
| USDC contract | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Amount | `5000` atomic units ($0.005) |
| Receiving wallet | `0x8fC4006534801c17A3368075A1Fb3b3C511EdB1F` |
| Facilitator | `https://api.cdp.coinbase.com/platform/v2/x402` |
| EIP-712 domain | `USD Coin` |

---

## Ecosystem

This service is part of a three-service x402 task market:

- **Formatter** (this service) — data format conversion
- **[SchemaCheck Agent](https://projectx402-production.up.railway.app)** — JSON Schema validation
- **[A2A Hub](https://project-a2a-production.up.railway.app)** — service discovery

Full capability manifest: `GET https://project-a2a-production.up.railway.app/v1/capabilities`
