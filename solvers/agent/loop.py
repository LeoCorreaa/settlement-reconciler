"""Manual agentic loop with full trajectory logging.

We drive the tool-use loop ourselves (no framework) so every request,
tool call, tool response, verification round and retry is captured in a
JSONL trajectory a judge can read end to end.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import anthropic

import config
from solvers import common
from solvers.agent import prompts
from solvers.agent.tools import CaseTools
from solvers.agent.verify import check_completeness, verify_findings

MAX_STEPS = 60
MAX_TOKENS_PER_TURN = 8000


class Trajectory:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = path.open("w", encoding="utf-8")

    def log(self, event: str, **data) -> None:
        record = {"ts": round(time.time(), 3), "event": event, **data}
        self.fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.fh.flush()

    def close(self) -> None:
        self.fh.close()


def _tool_result(tool_use_id: str, content: str) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}


def run(case_dir: Path, model: str, variant: str = "v2",
        trajectory_path: Path | None = None) -> dict:
    case = common.load_case(case_dir)
    tools = CaseTools(case, variant)
    system = prompts.system_prompt(variant)
    model_tag = model.replace("claude-", "")
    trajectory_path = trajectory_path or (
        config.TRAJECTORIES_DIR / f"{case_dir.name}_agent_{variant}_{model_tag}.jsonl")
    traj = Trajectory(trajectory_path)
    traj.log("start", case=case_dir.name, variant=variant, model=model,
             system_prompt=system, kickoff=prompts.KICKOFF)

    client = anthropic.Anthropic()
    # Prompt caching: stable prefix (tools + system) gets its own breakpoints;
    # a rolling breakpoint on the newest user block re-reads the whole prior
    # transcript from cache each turn (reads cost 10% of normal input).
    tool_defs = tools.defs()
    tool_defs[-1]["cache_control"] = {"type": "ephemeral"}
    system_blocks = [{"type": "text", "text": system,
                      "cache_control": {"type": "ephemeral"}}]
    messages: list[dict] = [{"role": "user", "content": prompts.KICKOFF}]
    usage = {"input_tokens": 0, "output_tokens": 0,
             "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    steps = 0
    nudged = False
    verify_retry_used = False
    notes = ""
    findings: list[dict] | None = None

    cached_block: dict | None = None

    def mark_cache() -> None:
        nonlocal cached_block
        last = messages[-1]
        if last["role"] != "user":
            return
        if isinstance(last["content"], str):
            last["content"] = [{"type": "text", "text": last["content"]}]
        if cached_block is not None:
            cached_block.pop("cache_control", None)
        cached_block = last["content"][-1]
        cached_block["cache_control"] = {"type": "ephemeral"}

    while steps < MAX_STEPS and findings is None:
        steps += 1
        mark_cache()
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS_PER_TURN,
            system=system_blocks,
            tools=tool_defs,
            messages=messages,
        )
        usage["input_tokens"] += response.usage.input_tokens
        usage["output_tokens"] += response.usage.output_tokens
        usage["cache_read_input_tokens"] += getattr(response.usage, "cache_read_input_tokens", 0) or 0
        usage["cache_creation_input_tokens"] += getattr(response.usage, "cache_creation_input_tokens", 0) or 0

        for block in response.content:
            if block.type == "text" and block.text.strip():
                traj.log("assistant", text=block.text)

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            if nudged:
                notes = "ended turn twice without calling submit_findings"
                traj.log("gave_up", reason=notes)
                findings = []
                break
            nudged = True
            messages.append({"role": "assistant", "content": response.content})
            nudge = ("You have not called submit_findings yet. Call it now with "
                     "all your findings (an empty list if the books are clean).")
            messages.append({"role": "user", "content": nudge})
            traj.log("nudge", text=nudge)
            continue

        messages.append({"role": "assistant", "content": response.content})
        results: list[dict] = []
        for block in tool_uses:
            traj.log("tool_call", tool=block.name, input=block.input)

            if block.name != "submit_findings":
                output = tools.execute(block.name, dict(block.input))
                traj.log("tool_result", tool=block.name, output=json.loads(output))
                results.append(_tool_result(block.id, output))
                continue

            output = tools.execute(block.name, dict(block.input))
            parsed = json.loads(output)
            if not parsed.get("accepted"):
                traj.log("tool_result", tool=block.name, output=parsed)
                results.append(_tool_result(block.id, output))
                continue

            submitted = tools.submitted or []
            if variant == "v3":
                ok, rejected = verify_findings(submitted, case)
                completeness = check_completeness(ok, case)
                traj.log("verification", accepted=len(ok),
                         rejected=[{"order_id": r["order_id"], "type": r["type"],
                                    "reason": r["reason"]} for r in rejected],
                         completeness_issues=completeness)
                if (rejected or completeness) and not verify_retry_used:
                    verify_retry_used = True
                    tools.submitted = None
                    feedback = json.dumps({
                        "accepted": False,
                        "rejected_findings": [
                            {"order_id": r["order_id"], "type": r["type"],
                             "reason": r["reason"]} for r in rejected],
                        "unexplained_residuals": completeness,
                        "instruction": ("Deterministic verification failed: rejected "
                                        "findings are not supported by the data, and "
                                        "unexplained residuals mean an order's delta is "
                                        "not fully accounted for (orders can carry MORE "
                                        "THAN ONE divergence). Re-investigate and call "
                                        "submit_findings again with the corrected FULL list."),
                    })
                    traj.log("tool_result", tool=block.name, output=json.loads(feedback))
                    results.append(_tool_result(block.id, feedback))
                    continue
                if rejected or completeness:
                    notes = (f"after retry: {len(rejected)} rejected finding(s) dropped, "
                             f"{len(completeness)} residual(s) left unexplained")
                findings = ok
            else:
                findings = submitted
            traj.log("tool_result", tool=block.name,
                     output={"accepted": True, "count": len(findings)})
            results.append(_tool_result(block.id, output))

        if findings is None and results:
            messages.append({"role": "user", "content": results})

    if findings is None:
        notes = f"hit MAX_STEPS={MAX_STEPS} without submitting"
        traj.log("gave_up", reason=notes)
        findings = []

    traj.log("final", findings=findings, usage=usage, steps=steps, notes=notes)
    traj.close()
    return {
        "findings": findings,
        "usage": usage,
        "steps": steps,
        "notes": notes,
        "trajectory": str(trajectory_path),
    }
