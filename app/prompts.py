"""System prompts for the formatter and validator Claude API calls.

Rules that apply to ALL conversion prompts:
- Return ONLY the converted output — no explanation, no markdown code fences, no commentary
- Handle empty input gracefully — return empty object {} or empty string, not an error trace
- Do not wrap HTML output in <html> or <body> tags
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Conversion prompts
# ---------------------------------------------------------------------------

CSV_TO_JSON = """\
Convert the following CSV data to a JSON array of objects.
Rules:
- Infer column names from the first row (header row)
- Each subsequent row becomes one JSON object
- Handle quoted fields and commas within quoted values correctly
- If a value is empty, use null
- Your entire response must be the raw JSON and nothing else
- Do NOT use markdown code fences (no ```json or ``` anywhere)
- Do NOT include any explanation, commentary, or text before or after the JSON
"""

XML_TO_JSON = """\
Convert the following XML to a JSON object.
Rules:
- Flatten XML attributes into the object alongside child elements
- Treat repeated sibling elements with the same tag as a JSON array
- Preserve text content in a "text" key when an element has both attributes and text
- Your entire response must be the raw JSON and nothing else
- Do NOT use markdown code fences (no ```json or ``` anywhere)
- Do NOT include any explanation, commentary, or text before or after the JSON
"""

MARKDOWN_TO_HTML = """\
Convert the following Markdown to HTML using CommonMark rules.
Rules:
- Do NOT wrap output in <html>, <head>, or <body> tags — return only the inner content
- Preserve all formatting: headings, bold, italic, lists, code blocks, links, images, tables
- Your entire response must be the raw HTML and nothing else
- Do NOT use markdown code fences (no ``` anywhere)
- Do NOT include any explanation, commentary, or text before or after the HTML
"""

CONVERSION_PROMPTS: dict[tuple[str, str], str] = {
    ("csv",      "json"): CSV_TO_JSON,
    ("xml",      "json"): XML_TO_JSON,
    ("markdown", "html"): MARKDOWN_TO_HTML,
}


# ---------------------------------------------------------------------------
# Validation prompts
# ---------------------------------------------------------------------------

VALIDATE_JSON = """\
Inspect the following JSON and determine whether it is structurally valid.
Rules:
- Check: valid JSON syntax, all arrays and objects properly closed, no trailing commas
- Return ONLY a JSON object in this exact format, nothing else:
  {"valid": true, "errors": []}
  or
  {"valid": false, "errors": ["description of error 1", "description of error 2"]}
- No explanation, no code fences, no commentary — only the JSON object
"""

VALIDATE_HTML = """\
Inspect the following HTML fragment and determine whether it is structurally valid.
Rules:
- Check: all opened tags are properly closed, no malformed attributes, no unclosed quotes
- Return ONLY a JSON object in this exact format, nothing else:
  {"valid": true, "errors": []}
  or
  {"valid": false, "errors": ["description of error 1", "description of error 2"]}
- No explanation, no code fences, no commentary — only the JSON object
"""

VALIDATION_PROMPTS: dict[str, str] = {
    "json": VALIDATE_JSON,
    "html": VALIDATE_HTML,
}
