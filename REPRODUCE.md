# Reproduction guide

Everything below assumes a clean environment. Total runtime for the full
evaluation is roughly 30-60 minutes and costs a few USD in API usage
(numbers below).

## 1. Requirements

- Python 3.11+ (developed on 3.12)
- An Anthropic API key: https://console.anthropic.com
- Windows note: clone into a SHORT path (e.g. `C:\src`) or enable Windows
  long-path support - the Anthropic SDK ships some very long file names and
  `pip install` can hit the legacy 260-character path limit inside deep
  directories. Line endings are pinned to LF via `.gitattributes`, so the
  determinism check below works on every platform.

## 2. Setup

```bash
git clone <REPO_URL>
cd settlement-reconciler
python -m venv .venv
.venv\Scripts\activate        # Windows (use `source .venv/bin/activate` on Linux/macOS)
pip install -r requirements.txt
```

Provide the API key (either way works):

```bash
set ANTHROPIC_API_KEY=sk-ant-...      # Windows cmd; use $env: syntax on PowerShell
```

or copy `.env.example` to `.env` and fill it in.

## 3. Regenerate the dataset (optional - cases/ is committed)

```bash
python -m datagen.generate
```

Deterministic: running it twice produces byte-identical files. 12 cases,
42 planted divergences, ground truth in each case's `truth.json`.

## 4. Sanity-check the pipeline without an API key

```bash
python -m eval.run --solver mock
```

Expected: F1 = 0.0, recall = 0.0 (the mock reports nothing), 0 errors.

## 5. Run the baseline and the agent

```bash
python -m eval.run --solver baseline
python -m eval.run --solver agent --variant v1
python -m eval.run --solver agent --variant v2
python -m eval.run --solver agent --variant v3
```

Each command prints per-case detail plus the aggregate line and writes
`results/<label>.json`. Agent runs also write one JSONL trajectory per case
under `trajectories/`.

Model selection: defaults to `claude-sonnet-5`; override with the
`RECONCILER_MODEL` environment variable.

## 6. What to expect

- `results/<label>.json` holds precision/recall/F1, token usage, cost and the
  full findings per case; agent runs write one JSONL trajectory per case
  under `trajectories/` (render them with `python -m scripts.render_trajectory`).
- Measured costs and wall-clock from our runs (your numbers should be close):

| Run | Model | Cost | Time |
|---|---|---|---|
| baseline, 12 cases | claude-sonnet-5 | $3.75 | ~40 min |
| agent v1, 3 cases (50/120/250) | claude-sonnet-5 | $0.78 | ~6 min |
| agent v2, 12 cases | claude-sonnet-5 | $1.01 | ~13 min |
| agent v3, 12 cases | claude-sonnet-5 | $0.85 | ~12 min |
| agent v2, 12 cases | claude-haiku-4-5 | $0.49 | ~12 min |
| agent v3, 12 cases | claude-haiku-4-5 | $0.55 | ~7 min |

  Reproducing every table in the README costs about $7-8 of API usage; the
  headline comparison alone (baseline + agent v3 on claude-sonnet-5) is ~$4.60.
- LLM outputs are not bit-deterministic; scores may vary by a few points
  between runs (our agent v3 sonnet run had zero errors and F1 1.000; treat
  small deviations as normal). The dataset, tools, verification and scoring
  are fully deterministic.
- The per-case seller report is rendered with
  `python -m scripts.render_report --run results/agent_v3_sonnet-5.json --case case_12`.

## 7. Versions

- anthropic (Python SDK) - see requirements.txt
- Dataset generator seed: fixed per case (see datagen/generate.py)
