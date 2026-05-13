from __future__ import annotations

from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off", ""}


@dataclass(frozen=True)
class Settings:
    app_version: str
    payment_mode: str
    log_requests: bool
    anthropic_api_key: str
    max_input_bytes: int
    trial_max_bytes: int
    x402_pay_to: str
    x402_network: str
    x402_scheme: str
    x402_asset: str          # USDC contract address on the target network
    x402_amount: str         # Payment amount in atomic units (USDC has 6 decimals)
    x402_max_timeout_seconds: int
    x402_facilitator_url: str
    x402_real_verification_enabled: bool


def get_settings() -> Settings:
    return Settings(
        app_version=os.getenv("FORMATTER_APP_VERSION", "0.1.0"),
        payment_mode=os.getenv("FORMATTER_PAYMENT_MODE", "disabled").lower(),
        log_requests=_as_bool(os.getenv("FORMATTER_LOG_REQUESTS"), True),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        max_input_bytes=int(os.getenv("FORMATTER_MAX_INPUT_BYTES", "102400")),   # 100 KB paid
        trial_max_bytes=int(os.getenv("FORMATTER_TRIAL_MAX_BYTES", "32768")),    # 32 KB trial
        x402_pay_to=os.getenv("FORMATTER_X402_PAY_TO", "0x8fC4006534801c17A3368075A1Fb3b3C511EdB1F"),
        x402_network=os.getenv("FORMATTER_X402_NETWORK", "eip155:8453"),
        x402_scheme=os.getenv("FORMATTER_X402_SCHEME", "exact"),
        # USDC on Base mainnet: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
        # $0.005 = 5000 atomic units (6 decimals)
        x402_asset=os.getenv("FORMATTER_X402_ASSET", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        x402_amount=os.getenv("FORMATTER_X402_AMOUNT", "5000"),
        x402_max_timeout_seconds=int(os.getenv("FORMATTER_X402_MAX_TIMEOUT_SECONDS", "300")),
        x402_facilitator_url=os.getenv("FORMATTER_X402_FACILITATOR_URL", "https://api.cdp.coinbase.com/platform/v2/x402"),
        x402_real_verification_enabled=_as_bool(os.getenv("FORMATTER_X402_REAL_VERIFICATION_ENABLED"), False),
    )
