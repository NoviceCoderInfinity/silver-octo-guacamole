# Team Himawari — Track 2 Handoff

**Repo (graded only):** [NoviceCoderInfinity/silver-octo-guacamole](https://github.com/NoviceCoderInfinity/silver-octo-guacamole) (`personal` remote)  
**Friend tree (read-only baseline):** `Arush777/himawari-fanboys` (`origin`) — do **not** push graded work there  
**Working branch after this handoff:** `submission-main` → tracks `personal/main`  
**Date:** 2026-07-12

---

## Current board status (official)

| Image / stack | Official score | Notes |
|---|---:|---|
| Lean Claude describe→best-of-2→selector (Arush SVG era) | **0.87–0.88** | Selector suspected voice-averaging |
| `:single-shot` | **0.90** | Describe + one caption/style, **no selector**. Confirms selector leak. |
| `:qwen-direct` | **0.92** | Recipe wins, but **prompts were plagiarized** — **do not resubmit** |
| `:qwen-direct-v2` | **pending** | Same recipe, **original** Himawari prompts. **Submit this next.** |

Promote bar historically discussed: ≥0.90. Stretch: hold/beat **0.92** cleanly.

---

## What to submit next

1. **`ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v2`**  
   digest `sha256:6a20678f10fbddbeb29d27aaafa87d24ed1e7898960eb41ab721b63f29910ba0`  
   Branch: `experiments/qwen-direct-original` @ `9f70c4e`  
   Harness verify: 3/3 sample clips, no empties, no env inject.

2. Optional Claude follow-ups (only after v2 score lands): `:direct-style`, then micro-IVs.

**Do not overwrite `:latest` until board confirms.** Do not resubmit `:qwen-direct`.

---

## Experiment branch ↔ image ledger

All on `personal` (`NoviceCoderInfinity/silver-octo-guacamole`). None on friend’s `origin`.

| Branch | Tag | Digest | IV (one line) | Official |
|---|---|---|---|---|
| `experiments/single-shot-no-selector` | `:single-shot` | `sha256:2b955e255df0d27d62d40dc575173d9356b5e665a68c82644a915eb84ad404c5` | Drop selector; keep describe + one caption/style | **0.90** |
| `experiments/direct-style-multimodal` | `:direct-style` | `sha256:fa4b66cd8c468a0e05622c7c38735becd76ee9d1025d171a6310edb0109a4bce` | Claude: no describe, no selector; 8–20@768 | pending |
| `experiments/frame-width-1024` | `:frame-1024` | `sha256:9e9c049936d4cefaaeda4ca57af673a422e5fb1a6a73e1c2329cdf1b7f289d64` | SVG path width 768→1024 | pending |
| `experiments/fixed-frames-6` | `:frames-6` | `sha256:9b53c591bba5d7594b699a06a641b73bd8877b5c7becd5dd147c7db46cc37653` | Fixed 6 frames @768 | pending |
| `experiments/output-safety-refilter` | `:safety-refilter` | `sha256:b8456fc54583424f705c801efa9d22e2a5e540d992bd2094a6c0fcb520fd6735` | Deterministic meta/tech cleanup | pending |
| `experiments/qwen-direct-quiptionary` | `:qwen-direct` | `sha256:2250f33798e7171d3c40bcfb962c534f8683acf3de296dab7ab8ab36fa601c6a` | Qwen 4@1024 direct — **PLAGIARIZED prompts** | **0.92 — DO NOT RESUBMIT** |
| `experiments/qwen-direct-original` | `:qwen-direct-v2` | `sha256:6a20678f10fbddbeb29d27aaafa87d24ed1e7898960eb41ab721b63f29910ba0` | Same knobs; **original** personas/system/guard; tag `<final_caption>` | **submit / pending** |

---

## Lessons learned (short)

1. **Selector hurts.** Best-of-2 + copy-only selector peaked ~0.88; dropping it → **0.90**.
2. **Model family matters more than Claude staging.** Qwen direct recipe → **0.92**. Opus swap historically **0.80**. Constraint/ledger stacks ≤**0.86**.
3. **Local Fireworks Δ ≠ board.** Use local only as a smoke/Δ filter; ship decisions need official scores.
4. **Architecture ≠ plagiarism.** Reusing 4@1024 / Qwen / no-describe / XML tags is fine. Copying competitor **persona/system/guard prose** is not. Deep check found exact HAL-9000 / “mere mortals” / millennial-workload / “strict data-formatting pipeline” / `### CRITICAL INSTRUCTIONS ###` matches on `:qwen-direct`.
5. **Track 2 bakes keys.** Harness injects no env; `FIREWORKS_API_KEY` / `ANTHROPIC_API_KEY` via build-arg. Never commit keys. Never push secrets to friend’s repo.

---

## Winning clean recipe (`:qwen-direct-v2`)

Held fixed from the 0.92 run:
- Model: Fireworks `accounts/fireworks/models/qwen3p7-plus`
- Assembly: `CAPTION_ASSEMBLY=qwen_direct` (no describe, no selector)
- Frames: `MIN_FRAMES=MAX_FRAMES=4`, `FRAME_MAX_WIDTH=1024`
- `reasoning_effort=none`, temperature `0.7`, max_tokens `400`
- One multimodal call per style + XML extract

Changed for originality:
- Personas: archivist / jaded travel host / build engineer / diner regular
- New system + guard prose
- Primary tags: `<final_caption>…</final_caption>` (legacy `<caption_output>` still parsed)

Plagiarism grep clean for: `HAL-9000`, `mere mortals`, `millenial of workload`, `man who is in his 50s`, `strict data-formatting`, `CRITICAL INSTRUCTIONS`.

---

## Failed / weak classes (do not revive without new evidence)

- Claude Opus generator (~0.80)
- formal_grounded / scene_frames / evidence-ledger / heavy critique-repair (≤0.86 or flat)
- Assuming local judge absolute scores (~0.97–0.99) transfer to board

---

## Next improvement ideas (not yet shipped as images)

| Idea | Priority | Notes |
|---|---|---|
| Per-style temperature on Claude path | Medium | Free knob; formal cold / comedy hot |
| Forensic dense describe on Claude SVG/single-shot | Medium | XO-class; only if staying on Claude |
| Apply 1024 / temp schedule **on top of** clean Qwen-direct | High after v2 score | Single-IV stacks only |
| Audio / native video backends | Speculative | Some 0.92 blurbs claim this; no verified code path in our tree |

Process: one IV per branch → GHCR tag + digest in `EXPERIMENT.md` → official score → then stack.

---

## Ops cheatsheet

```bash
# Graded remote
git remote -v   # personal = NoviceCoderInfinity/silver-octo-guacamole

# Build clean Qwen image (key from .env, never commit)
set -a && source .env && set +a
docker buildx build --platform linux/amd64 \
  --build-arg FIREWORKS_API_KEY="$FIREWORKS_API_KEY" \
  --tag ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v2 \
  --push .

# Harness-style verify (no -e)
docker run --rm --platform linux/amd64 \
  -v "$PWD/sample_input:/input:ro" \
  -v "$PWD/.verify_out:/output" \
  ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v2
```

Scratch / cleanroom notes (gitignored): `.scratch/cleanroom/out/` (Opus ideas, manager GO notes, plagiarism audit context).

---

## Co-manager pickup

See **`ARUSH_PICKUP.md`** in this repo for a paste-ready prompt.
