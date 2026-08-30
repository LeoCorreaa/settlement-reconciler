# Development trajectories (coding-agent evidence)

This project was built end to end with **Claude Code** (Anthropic) as the
coding agent, model **Claude Fable 5**, over 2026-08-28 to 2026-08-30. This
directory documents that collaboration, as required by the challenge.

## What is here

- `DEVELOPMENT-DIGEST.md` - a faithful, chronological digest of the
  human/agent collaboration: every major decision, the evidence that drove
  it, and what the agent actually did at each step.

## Where the rest of the evidence lives

- **Every commit in this repository is co-authored by the coding agent**
  (`git log --format="%h %s" --grep="Co-Authored-By" --all` or just read the
  trailers) and the commit messages themselves narrate the iterations.
- **The solution's own agent trajectories** (53 runs, instructions through
  tool calls to final result, including verification rounds, retries and the
  archived reward-hack run) are in `trajectories/` with readable renderings
  in `trajectories/rendered/`.

## About the raw session transcript

The raw Claude Code session transcript (~3 MB JSONL) interleaves the
project work with personal memory context from the participant's unrelated
client work (injected automatically by the tool at session start). In line
with rule 8 of the challenge (keep credentials and private information out
of the submission), it is retained privately rather than committed here.
Organizers may request it and will receive it with credentials and
third-party-client references redacted; everything project-relevant in it is
reflected faithfully in `DEVELOPMENT-DIGEST.md`.
