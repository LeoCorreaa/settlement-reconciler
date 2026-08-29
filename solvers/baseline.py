"""Baseline solver: ONE direct prompt, no tools, no iteration.

This represents the reasonable basic way to attack the task with an LLM
today: paste the fee rules and both files into a single prompt and ask for
the divergences as JSON. Same model and same information as the agent -
the only difference is the engineering around it.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic

import config
from solvers import common

PROMPT_TEMPLATE = """You are a marketplace settlement reconciliation analyst.

Below are the contractual fee rules, the seller's order book (orders.csv) and
the payment processor's settlement statement (settlement.csv) for one month.

Compare every order against its settlement rows and find ALL divergences:
cases where the settlement does not follow the rules. Classify each divergence
as exactly one of:
{types}

Rules document:
<fee_rules>
{fee_rules}
</fee_rules>
{notices_block}
<orders_csv>
{orders_csv}
</orders_csv>

<settlement_csv>
{settlement_csv}
</settlement_csv>

Reply with ONLY a JSON array (no prose before or after). One element per
divergence:
[{{"order_id": "...", "type": "...", "explanation": "...", "impact_brl": "..."}}]

impact_brl is the signed amount by which the seller was hurt (positive) or
unduly favored (negative). If there are no divergences, reply with [].
Remember: split settlements are legitimate, legitimate chargebacks are not
divergences, and net differences of up to 0.02 are rounding noise."""


def solve(case_dir: Path, model: str) -> dict:
    orders_csv, settlement_csv = common.read_raw_csvs(case_dir)
    notices_path = case_dir / "notices.md"
    notices_block = ""
    if notices_path.exists():
        notices_block = ("\nMonth-specific marketplace notices (may supersede the standard "
                         "rules for specific orders):\n<notices>\n"
                         + notices_path.read_text(encoding="utf-8")
                         + "\n</notices>\n")
    prompt = PROMPT_TEMPLATE.format(
        types="\n".join(f"- {t}" for t in config.DIVERGENCE_TYPES),
        fee_rules=common.fee_rules_text(),
        notices_block=notices_block,
        orders_csv=orders_csv,
        settlement_csv=settlement_csv,
    )

    client = anthropic.Anthropic()
    # Generous output ceiling (streamed): the baseline must never lose because
    # we starved it of thinking room.
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()
    text = "".join(block.text for block in response.content if block.type == "text")

    try:
        raw = common.extract_json(text)
    except ValueError:
        raw = []
    findings, errors = common.validate_findings(raw)

    return {
        "findings": findings,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "steps": 1,
        "notes": "; ".join(errors) if errors else "",
        "raw_text": text,
    }
