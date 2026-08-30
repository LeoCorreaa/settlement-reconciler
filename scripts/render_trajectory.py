"""Render agent trajectory JSONL files as readable Markdown.

Judges should be able to follow each run from the agent's instructions to the
final result without tooling. Full raw data stays in the JSONL; very large
tool outputs are truncated in the rendering with a pointer to the source.

Usage:
    python -m scripts.render_trajectory            # render all trajectories
"""

from __future__ import annotations

import json
from pathlib import Path

import config

TRUNCATE_AT = 3000


def _fence(payload: object) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if len(text) > TRUNCATE_AT:
        text = text[:TRUNCATE_AT] + "\n... (truncated for readability; full data in the .jsonl)"
    return f"```json\n{text}\n```\n"


def render(jsonl_path: Path, out_dir: Path) -> Path:
    events = [json.loads(line) for line in
              jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines: list[str] = []
    step = 0

    for event in events:
        kind = event["event"]
        if kind == "start":
            lines.append(f"# Trajectory: {event['case']} - agent {event['variant']}")
            lines.append("")
            lines.append(f"- **Model:** `{event['model']}`")
            lines.append(f"- **Source:** `{jsonl_path.name}`")
            lines.append("")
            lines.append("<details><summary><b>System prompt (agent instructions)</b></summary>")
            lines.append("")
            lines.append("```")
            lines.append(event["system_prompt"])
            lines.append("```")
            lines.append("</details>")
            lines.append("")
            lines.append(f"**Kickoff (user):** {event['kickoff']}")
            lines.append("")
        elif kind == "assistant":
            lines.append("**Agent:**")
            lines.append("")
            for text_line in event["text"].splitlines():
                lines.append(f"> {text_line}")
            lines.append("")
        elif kind == "tool_call":
            step += 1
            lines.append(f"### Step {step}: `{event['tool']}`")
            lines.append("")
            lines.append("Input:")
            lines.append(_fence(event["input"]))
        elif kind == "tool_result":
            lines.append("Result:")
            lines.append(_fence(event["output"]))
        elif kind == "verification":
            lines.append(f"### Deterministic verification: {event['accepted']} accepted, "
                         f"{len(event['rejected'])} rejected")
            lines.append("")
            if event["rejected"]:
                lines.append(_fence(event["rejected"]))
        elif kind == "nudge":
            lines.append(f"**Harness nudge (user):** {event['text']}")
            lines.append("")
        elif kind == "gave_up":
            lines.append(f"**Harness:** gave up - {event['reason']}")
            lines.append("")
        elif kind == "final":
            lines.append("## Final outcome")
            lines.append("")
            lines.append(f"- Findings submitted: **{len(event['findings'])}**")
            lines.append(f"- API calls: {event['steps']}")
            usage = event["usage"]
            lines.append(f"- Tokens: input={usage.get('input_tokens', 0):,}, "
                         f"output={usage.get('output_tokens', 0):,}, "
                         f"cache_read={usage.get('cache_read_input_tokens', 0):,}, "
                         f"cache_write={usage.get('cache_creation_input_tokens', 0):,}")
            if event.get("notes"):
                lines.append(f"- Notes: {event['notes']}")
            lines.append("")
            lines.append("Findings:")
            lines.append(_fence(event["findings"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (jsonl_path.stem + ".md")
    out_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return out_path


def main() -> None:
    out_dir = config.TRAJECTORIES_DIR / "rendered"
    jsonl_files = sorted(config.TRAJECTORIES_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print("no trajectories found")
        return
    index = ["# Agent trajectories", "",
             "One JSONL per run (raw) plus a readable Markdown rendering.", ""]
    for jsonl_path in jsonl_files:
        out_path = render(jsonl_path, out_dir)
        index.append(f"- [{out_path.stem}](rendered/{out_path.name}) "
                     f"(raw: [{jsonl_path.name}](../trajectories/{jsonl_path.name}))")
        print(f"rendered {out_path.name}")
    (config.TRAJECTORIES_DIR / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(jsonl_files)} trajectories rendered to {out_dir}")


if __name__ == "__main__":
    main()
