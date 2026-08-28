"""Global configuration for the settlement reconciler project."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"
RESULTS_DIR = ROOT / "results"
TRAJECTORIES_DIR = ROOT / "trajectories"
FEE_RULES_PATH = ROOT / "datagen" / "fee_rules.md"


def load_dotenv() -> None:
    """Load ROOT/.env into the environment (existing variables win)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv()

MODEL = os.environ.get("RECONCILER_MODEL", "claude-sonnet-5")

# USD per million tokens (input, output). Source: Anthropic pricing, Aug 2026.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

DIVERGENCE_TYPES = [
    "MISSING_SETTLEMENT",
    "DUPLICATE_SETTLEMENT",
    "ORPHAN_SETTLEMENT",
    "FEE_OVERCHARGE",
    "WRONG_SHIPPING_DEDUCTION",
    "REFUND_NOT_SETTLED",
    "REFUND_AMOUNT_MISMATCH",
    "CANCELLED_BUT_SETTLED",
]


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int,
                      cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> float:
    """Cache reads bill at 10% of input price, cache writes at 125%."""
    input_price, output_price = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    return (
        input_tokens * input_price
        + cache_read_tokens * input_price * 0.10
        + cache_write_tokens * input_price * 1.25
        + output_tokens * output_price
    ) / 1_000_000
