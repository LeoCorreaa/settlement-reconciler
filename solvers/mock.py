"""Mock solver: reports nothing. Exists to test the evaluation pipeline
end-to-end without an API key (and doubles as a floor reference)."""

from __future__ import annotations

from pathlib import Path


def solve(case_dir: Path, model: str) -> dict:
    return {
        "findings": [],
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "steps": 0,
        "notes": "mock solver, reports nothing",
    }
