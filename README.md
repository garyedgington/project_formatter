# x402 Data Formatter

Convert CSV, XML, or Markdown to JSON or HTML using Claude AI. Optional structural validation. Part of the x402 micropayment task market.

**Live service:** `https://project-formatter-production.up.railway.app`

---

## Two access channels (DualRail)

### Rail 1 — x402 micropayments (USDC)

Agents pay $0.005 USDC per call via the x402 protocol on Base mainnet. No API key required — payment is the credential.

```
POST https://project-formatter-production.up.railway.app/v1/format
```

**Request body:**
```json
{
  "input": "name,age\nAlice,30\nBob,25",
  "from": "csv",
  "to": "json"
}
```

**Supported conversion pairs:**
- `csv` → `json`
- `xml` → `json`
- `markdown` → `html`

**Optional validation:** append `?validate=true` to get `{ result, valid, errors[] }` in the response.

**Free trial** (no payment, 32KB limit, no validation):
```
POST https://project-formatter-production.up.railway.app/v1/format/trial
```

### Rail 2 — MCP (fiat billing via MCP-Hive)

Connect any MCP-compatible agent or IDE to the SSE endpoint:

```
https://project-formatter-production.up.railway.app/mcp/sse
```

Listed on Smithery: [gary-edgington/x402-data-formatter](https://smithery.ai/server/gary-edgington/x402-data-formatter)

**Available MCP tools:**
- `format_data` — convert CSV, XML, or Markdown to JSON or HTML
- `validate_schema` — validate JSON against a JSON Schema Draft 7 definition (free, calls schema-checker trial)
- `get_capabilities` — retrieve the full x402 task market capability manifest

---

## Discovery

- **Bazaar:** indexed after first mainnet payment (CDP discovery API)
- **Smithery:** `gary-edgington/x402-data-formatter`
- **Server card:** `/.well-known/mcp/server-card.json`
- **x402 discovery:** `/.well-known/x402`
- **LLM agents:** `/llms.txt`

---

## Stack

- FastAPI + Uvicorn
- Anthropic Claude API (conversion and validation)
- x402 Python SDK (`x402[evm]`)
- FastMCP (`mcp`) for SSE transport
- Deployed on Railway

---

## Related

- **A2A Hub:** `https://project-a2a-production.up.railway.app` — capability manifest and discovery hub
- **Schema Checker:** `https://projectx402-production.up.railway.app` — JSON Schema validation service
