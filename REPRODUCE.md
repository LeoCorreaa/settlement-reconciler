# Reproduction guide

Everything below assumes a clean environment. Total runtime for the full
evaluation is roughly 30-60 minutes and costs a few USD in API usage
(numbers below).

## 1. Requirements

- Python 3.11+ (developed on 3.12)
- An Anthropic API key: https://console.anthropic.com

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
  full findings per case.
- Approximate cost per full 12-case run (claude-sonnet-5): baseline < $1,
  agent variants $1-4 each. _Exact numbers to be updated from our runs._
- LLM outputs are not bit-deterministic; scores may vary by a few points
  between runs. The dataset, tools and scoring are fully deterministic.

## 7. Versions

- anthropic (Python SDK) - see requirements.txt
- Dataset generator seed: fixed per case (see datagen/generate.py)
