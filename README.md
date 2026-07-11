# Multi-style video captioning agent

Docker agent that reads `/input/tasks.json`, captions each clip in four styles
(`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`), and writes
`/output/results.json`. Built for a graded Track 2 harness that injects **no**
env vars at runtime — credentials must be baked into the image at build time.

**Repo:** [NoviceCoderInfinity/silver-octo-guacamole](https://github.com/NoviceCoderInfinity/silver-octo-guacamole)  
**Graded image:** `ghcr.io/novicecoderinfinity/silver-octo-guacamole:latest`  
**Team:** Himawari

---

## Status (pick-up snapshot)

| Signal | Value | Notes |
| --- | ---: | --- |
| Official leaderboard (Himawari) | **~0.86** | Hidden ~12-clip set; last confirmed after `scene_frames` resubmit |
| Top of board (competitors) | **~0.90–0.91** | Gap ≈ **−0.04 to −0.05** |
| Friend lean baseline (Arush) | **0.87** on board | Describe → per-style best-of-2 → frame selection |
| Current shipped code on `main` | `CAPTION_MODE=formal_grounded` | Uniform frames + Claude describe; critique/repair **off** |
| Best local Δ vs Arush (Fireworks) | **`formal_grounded` +0.027** | 12 public clips; did **not** yet prove on the hidden board |
| Prior ship that flatlined on board | `scene_frames` local **+0.019** → board still **~0.86** | Treat local absolute scores (~0.97–0.99) as saturated |

If you are new here: optimize for **hidden-board movement**, not local Fireworks
absolute scores. Prefer **Δ vs Arush** on the 12-clip suite, then resubmit and
check the official board.

---

## How ranking works

### Official (what the leaderboard uses)

- Hidden evaluation set (~12 clips).
- Score mixes **caption accuracy** (does the text match the video) and **style
  match** (does it fit `formal` / `sarcastic` / humor variants).
- Your container is run with mounts for `/input` and `/output` only — **no**
  `-e` API keys. The image must already contain credentials.
- Output contract: list of `{ "task_id", "captions": { style: string } }`.

### Local ranking (what we use to choose arms)

1. **Baseline:** Arush lean 0.87 pipeline (friend repo / worktree), same clips.
2. **Judge:** Fireworks `qwen3p7-plus` only — **never Claude judging Claude**.
3. **Metric:** per caption `accuracy` and `tone_fit` (1–5) → combined 0–1 score;
   report **Δ vs Arush**, not the absolute 0.98.
4. **Eval set:** `eval_input/tasks_gcs12.json` (12 clips × 4 styles).
5. **Caveat:** `scene_frames` won locally (+0.019) and **did not move** the
   official ~0.86 score. Local wins are hypotheses until the board confirms.

Artifacts:

- `sample_output/exp_novel_v1/SCOREBOARD.md` — v1 arms (`scene_frames` led)
- v2 summary below (suite lived on `experiments/novel-arms-v2` / stash)

| Arm | Combined | Δ vs Arush | Mechanism |
| --- | ---: | ---: | --- |
| **formal_grounded** (shipped) | 0.994 | **+0.027** | Formal first; other styles locked to its entities |
| anchor_facts | 0.988 | +0.021 | 5 main-subject facts, then style |
| motion_budget | 0.988 | +0.021 | Adaptive frame count + scene mix |
| scene_frames (shipped earlier) | 0.985 | +0.019 | Scene-change peaks + uniform fill |
| claim_audit / gemini_humor | 0.979 | +0.013 | Gemini assist on claims / humor |

---

## Branches (this remote: `personal` → silver-octo-guacamole)

| Branch | What it is |
| --- | --- |
| **`main`** | Graded path. Defaults: Claude describe, **uniform** frames, **`formal_grounded`**, critique off. Pin: `submit/formal-grounded` (same commit family). |
| `submit/formal-grounded` | Explicit submit pin for the current image. |
| `submit/scene-frames` | Prior ship: `FRAME_SAMPLE_MODE=scene`. Local +0.019; board unchanged (~0.86). |
| `submit/gemini-describe-hybrid` | Gemini full-video describe → Claude specialists. Local 3-clip A/B tied Arush (0.917). |
| `experiments/novel-arms-v1` | Fireworks suite + scoreboard for scene/claim/cross-family/… |
| `experiments/novel-arms-v2` | WIP / stash: formal_grounded, anchor_facts, motion_budget, … |
| Friend `Arush777/himawari-fanboys` `main` | Lean **0.87** reference — **do not push here** unless asked. Local remote name is often `origin`. |

Work on **`NoviceCoderInfinity/silver-octo-guacamole` only** (`git remote` name:
`personal`) unless someone explicitly says otherwise.

---

## Current pipeline (what `main` runs)

1. Download clip (`clip://…` sample refs resolve in `video_utils.resolve_video_url`).
2. Sample frames (default **uniform**; optional `FRAME_SAMPLE_MODE=scene`).
3. Claude vision **describe**.
4. **`formal_grounded`:** write `formal` first (specialist + selection), then write
   the other styles with an entity lock to that formal caption.
5. Write `/output/results.json`.

Key knobs (`config.py` / Docker `ARG`/`ENV`):

| Var | Graded default | Meaning |
| --- | --- | --- |
| `DESCRIBE_BACKEND` | `claude` | `claude` frames or `gemini` full-video describe |
| `FRAME_SAMPLE_MODE` | `uniform` | `uniform` or `scene` |
| `CAPTION_MODE` | `formal_grounded` | or `default` (all styles in parallel) |
| `ENABLE_CRITIQUE_REPAIR` | `false` | Post-selection critique/repair |
| `CLAUDE_MODEL_ID` | `claude-sonnet-5` | Generator model |
| `ANTHROPIC_API_KEY` | baked at build | Required in the graded image |

---

## Quick start

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY (and optional CLAUDE_MODEL_ID)
pip install -r requirements.txt

export INPUT_PATH="$(pwd)/sample_input/tasks.json"
export OUTPUT_PATH="$(pwd)/sample_output/results.json"
python3 main.py
```

Sample task URLs use `clip://<object>.mp4` so sponsor bucket names are not
hard-coded in JSON; `download_video` expands them.

### Docker (graded shape)

```bash
# Build for the harness CPU (x86_64)
docker buildx build --platform linux/amd64 \
  --build-arg ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)" \
  --build-arg DESCRIBE_BACKEND=claude \
  --build-arg FRAME_SAMPLE_MODE=uniform \
  --build-arg CAPTION_MODE=formal_grounded \
  --build-arg ENABLE_CRITIQUE_REPAIR=false \
  --tag ghcr.io/novicecoderinfinity/silver-octo-guacamole:latest \
  --push .

# Harness-style verify: no -e
docker run --rm --platform linux/amd64 \
  -v "$(pwd)/sample_input:/input:ro" \
  -v "$(pwd)/sample_output:/output" \
  ghcr.io/novicecoderinfinity/silver-octo-guacamole:latest
```

### Local judge (dev only)

```bash
export RESULTS_PATH="$(pwd)/sample_output/results.json"
export JUDGE_OUTPUT_PATH="$(pwd)/sample_output/judged_results.json"
export JUDGE_PROVIDER=fireworks   # default; keep Claude off the judge seat for A/Bs
python3 judge.py
```

Novel-arm suite (on experiment branches): `.venv/bin/python -m exp_arms.run_suite`

### Streamlit demo

```bash
streamlit run app.py
```

---

## Layout

```
main.py              graded entry: /input/tasks.json → /output/results.json
pipeline.py          describe + specialists/selection + formal_grounded
llm_client.py        Claude (+ Fireworks for judge/dev)
gemini_client.py     optional full-video describe
video_utils.py       download, frames, clip:// resolution
config.py            env defaults
judge.py             local LLM judge (not graded)
app.py               Streamlit UI
exp_arms/            novel-arm experiment harness
eval_input/          12-clip local eval tasks
sample_input/        3-clip smoke tasks
Dockerfile           what gets pushed to GHCR
```

---

## What not to do

- Do not trust Claude-self-judging for ship decisions.
- Do not stack perception tricks after a board flatline without a new mechanism.
- Do not commit `.env` or push to the friend’s remote by default.
- Do not treat local combined ≈ 0.99 as a leaderboard forecast — use **Δ** and
  then the official score.
