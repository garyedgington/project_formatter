"""Tests for the /v1/format endpoint."""

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "formatter-agent"


def test_health_head():
    """HEAD /health must return 200 (required for UptimeRobot)."""
    response = client.head("/health")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Input validation — conversion pair
# ---------------------------------------------------------------------------

def test_unsupported_from_format_returns_400():
    response = client.post("/v1/format", json={"from": "pdf", "to": "json", "input": "data"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_CONVERSION"


def test_unsupported_to_format_returns_400():
    response = client.post("/v1/format", json={"from": "csv", "to": "xml", "input": "data"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_CONVERSION"


def test_unsupported_pair_cross_returns_400():
    """csv→html is not a supported pair even though both formats exist."""
    response = client.post("/v1/format", json={"from": "csv", "to": "html", "input": "data"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_CONVERSION"


# ---------------------------------------------------------------------------
# Input validation — size limit
# ---------------------------------------------------------------------------

def test_oversized_input_returns_413():
    big_input = "a" * (102_401)  # 1 byte over 100KB limit
    response = client.post("/v1/format", json={"from": "csv", "to": "json", "input": big_input})
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "INPUT_TOO_LARGE"


# ---------------------------------------------------------------------------
# Trial endpoint
# ---------------------------------------------------------------------------

def test_trial_no_payment_required():
    """Trial endpoint must be reachable without any payment header."""
    response = client.post("/v1/format/trial", json={"from": "csv", "to": "json", "input": "name\nAlice"})
    # 501 means the gate passed and the stub was hit — payment gate is open
    assert response.status_code in (200, 501)


def test_trial_oversized_input_returns_413():
    big_input = "a" * (32_769)  # 1 byte over 32KB trial limit
    response = client.post("/v1/format/trial", json={"from": "csv", "to": "json", "input": big_input})
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "TRIAL_PAYLOAD_TOO_LARGE"


def test_trial_unsupported_pair_returns_400():
    response = client.post("/v1/format/trial", json={"from": "csv", "to": "html", "input": "data"})
    assert response.status_code == 400


def test_trial_validate_flag_returns_400():
    """Trial endpoint must reject ?validate=true."""
    response = client.post(
        "/v1/format/trial?validate=true",
        json={"from": "csv", "to": "json", "input": "name\nAlice"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATE_NOT_SUPPORTED_ON_TRIAL"


# ---------------------------------------------------------------------------
# Live conversion tests — require ANTHROPIC_API_KEY in environment
# ---------------------------------------------------------------------------

def test_csv_to_json():
    response = client.post("/v1/format", json={
        "from": "csv", "to": "json",
        "input": "name,age\nAlice,30\nBob,25",
    })
    assert response.status_code == 200
    result = json.loads(response.json()["result"])
    assert isinstance(result, list)
    assert result[0]["name"] == "Alice"
    assert result[1]["name"] == "Bob"


def test_xml_to_json():
    response = client.post("/v1/format", json={
        "from": "xml", "to": "json",
        "input": "<items><item><name>Widget</name></item></items>",
    })
    assert response.status_code == 200
    result = json.loads(response.json()["result"])
    assert isinstance(result, dict)


def test_markdown_to_html():
    response = client.post("/v1/format", json={
        "from": "markdown", "to": "html",
        "input": "# Hello\n\nThis is **bold**.",
    })
    assert response.status_code == 200
    result = response.json()["result"]
    assert "<h1>" in result
    assert "<strong>" in result or "<b>" in result


def test_validate_flag_valid_output():
    """?validate=true on valid CSV should return valid=True with no errors."""
    response = client.post("/v1/format?validate=true", json={
        "from": "csv", "to": "json",
        "input": "name,age\nAlice,30",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] is None


def test_validate_flag_no_extra_fields_without_flag():
    """Without ?validate, valid and errors must not appear in response."""
    response = client.post("/v1/format", json={
        "from": "csv", "to": "json",
        "input": "name,age\nAlice,30",
    })
    assert response.status_code == 200
    body = response.json()
    assert body.get("valid") is None
    assert body.get("errors") is None
