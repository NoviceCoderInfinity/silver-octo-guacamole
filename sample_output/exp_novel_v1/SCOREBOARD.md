# Novel arms scoreboard (vs Arush 0.87 baseline)

**Branch:** `experiments/novel-arms-v1`  
**Eval set:** `eval_input/tasks_gcs12.json` (12 clips × 4 styles = 48 scores)  
**Judge:** Fireworks `qwen3p7-plus` only — **not Claude** (generators are Claude-primary; Gemini assists some arms).  
**Empty captions:** 0 across all arms.

## Ranking

| Rank | Arm | Combined | Δ vs Arush | Acc | Tone |
| ---: | --- | ---: | ---: | ---: | ---: |
| — | **arush_baseline** | 0.9667 | 0 | 4.750 | 4.917 |
| 1 | **scene_frames** | **0.9854** | **+0.0187** | 4.875 | 4.979 |
| 2 | claim_audit | 0.9792 | +0.0125 | 4.812 | 4.979 |
| 3 | cross_family_select | 0.9771 | +0.0104 | 4.812 | 4.958 |
| 4 | gemini_temporal | 0.9646 | −0.0021 | 4.708 | 4.938 |
| 5 | verifiability | 0.9583 | −0.0084 | 4.688 | 4.896 |

## What each arm does

1. **scene_frames** — scene-change peaks + uniform frames (perception only; Arush specialists/selection unchanged).
2. **claim_audit** — Arush captions, then Gemini audits/repairs unverifiable claims on non-formal styles.
3. **cross_family_select** — Claude writes best-of-2; Gemini picks winners from frames.
4. **gemini_temporal** — Gemini motion/event notes injected into Claude describe.
5. **verifiability** — prompt-only ban on background colours / counts / fleeting details.

## How to plug in a winner

- Re-run suite: `.venv/bin/python -m exp_arms.run_suite`
- Graded path: set `FRAME_SAMPLE_MODE=scene` (wires arm #1 into `pipeline.py`).
- Submit pin branch: `submit/scene-frames` (same commit family, scene sampling defaulted in Docker).

## Caveat

Local Fireworks absolute scores are high on this set; use **Δ vs Arush** and ranking, not the absolute 0.98 as a leaderboard forecast. Still stronger evidence than 3-clip Claude-self-judging.
