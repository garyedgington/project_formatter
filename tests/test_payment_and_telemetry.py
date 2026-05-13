import importlib

from fastapi.testclient import TestClient


VALID_FORMAT_REQUEST = {
    "from": "csv",
    "to": "json",
    "input": "name,age\nAlice,30\nBob,25",
}


def _reload_app(monkeypatch, payment_mode: str):
    monkeypatch.setenv("FORMATTER_PAYMENT_MODE", payment_mode)
    import app.config
    import app.payment
    import app.main

    importlib.reload(app.config)
    importlib.reload(app.payment)
    importlib.reload(app.main)
    return app.main.app


def test_payment_gate_disabled_by_default(monkeypatch):
    """Disabled mode — request passes through payment gate (hits 501 until formatter is implemented)."""
    application = _reload_app(monkeypatch, "disabled")
    client = TestClient(application)
    response = client.post("/v1/format", json=VALID_FORMAT_REQUEST)
    # 501 means the gate passed and formatter stub was hit — payment gate is open
    assert response.status_code in (200, 501)


def test_x402_gate_requires_payment(monkeypatch):
    """x402 mode — unpaid request must return 402."""
    application = _reload_app(monkeypatch, "x402")
    client = TestClient(application)
    response = client.post("/v1/format", json=VALID_FORMAT_REQUEST)
    assert response.status_code == 402


def test_request_id_response_header(monkeypatch):
    """X-Request-ID sent in request must be echoed in response."""
    application = _reload_app(monkeypatch, "disabled")
    client = TestClient(application)
    response = client.get("/health", headers={"X-Request-ID": "req-test-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-123"
