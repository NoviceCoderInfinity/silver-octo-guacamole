# Team Himawari — Track 2 Handoff

**Repo (graded only):** [NoviceCoderInfinity/silver-octo-guacamole](https://github.com/NoviceCoderInfinity/silver-octo-guacamole) (`personal` remote)  
**Friend tree (read-only baseline):** `Arush777/himawari-fanboys` (`origin`) — do **not** push graded work there  
**Champion (graded):** `:qwen-direct-v3` @ **0.93** official  
**Working branch:** `submission-main` → tracks `personal/main` (**now = `:qwen-direct-v3` champion code**; no image rebuild in this sync)  
**Date:** 2026-07-12 (updated after v3 = 0.93)

---

## Current board status (official)

| Image / stack | Official score | Notes |
|---|---:|---|
| Lean Claude describe→best-of-2→selector (SVG era) | **0.87–0.88** | Selector voice-averaging |
| `:single-shot` | **0.90** | Claude; drop selector. Strong clean Claude floor |
| `:qwen-direct` | **0.92** | Plagiarized prompts — **never resubmit** |
| `:qwen-direct-v2` | **0.74** | Over-rewrote (long roleplay) — **never resubmit** |
| **`:qwen-direct-v3`** | **0.93** | **Current champion.** Surgical originality; same recipe geometry |

Promote / protect: treat **0.93** as the control. Stretch: nudge toward **0.94–0.95** with single-IV stacks only.

---

## Graded image (use this)

```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3
digest: sha256:57189838befccc6f71164988535a527b3167fdbcef18972eb59c909636e11a99
```

Branch: `experiments/qwen-direct-v3`  
**Recommend tagging `:latest` to this digest** once Anupam confirms (optional ops step).

Do **not** resubmit `:qwen-direct` or `:qwen-direct-v2`.

---

## Experiment branch ↔ image ledger

All on `personal` (`NoviceCoderInfinity/silver-octo-guacamole`). None on friend’s `origin`.

| Branch | Tag | Digest | IV (one line) | Official |
|---|---|---|---|---|
| `experiments/single-shot-no-selector` | `:single-shot` | `sha256:2b955e255df0d27d62d40dc575173d9356b5e665a68c82644a915eb84ad404c5` | Drop selector; keep describe | **0.90** |
| `experiments/direct-style-multimodal` | `:direct-style` | `sha256:fa4b66cd8c468a0e05622c7c38735becd76ee9d1025d171a6310edb0109a4bce` | Claude: no describe/selector | pending |
| `experiments/frame-width-1024` | `:frame-1024` | `sha256:9e9c049936d4cefaaeda4ca57af673a422e5fb1a6a73e1c2329cdf1b7f289d64` | SVG width 768→1024 | pending |
| `experiments/fixed-frames-6` | `:frames-6` | `sha256:9b53c591bba5d7594b699a06a641b73bd8877b5c7becd5dd147c7db46cc37653` | Fixed 6 @768 | pending |
| `experiments/output-safety-refilter` | `:safety-refilter` | `sha256:b8456fc54583424f705c801efa9d22e2a5e540d992bd2094a6c0fcb520fd6735` | Meta/tech cleanup | pending |
| `experiments/qwen-direct-quiptionary` | `:qwen-direct` | `sha256:2250f33798e7171d3c40bcfb962c534f8683acf3de296dab7ab8ab36fa601c6a` | Qwen direct — **plagiarized prose** | **0.92 — ban** |
| `experiments/qwen-direct-original` | `:qwen-direct-v2` | `sha256:6a20678f10fbddbeb29d27aaafa87d24ed1e7898960eb41ab721b63f29910ba0` | Over-rewritten roleplay | **0.74 — ban** |
| **`experiments/qwen-direct-v3`** | **`:qwen-direct-v3`** | **`sha256:57189838befccc6f71164988535a527b3167fdbcef18972eb59c909636e11a99`** | Restore geometry + original wording | **0.93 — champion** |

---

## Lessons learned (short)

1. **Selector hurts.** Best-of-2 + copy selector ~0.88; drop → **0.90** (`:single-shot`).
2. **Qwen direct wins.** Same family recipe → **0.92–0.93**. Claude staging alone capped lower.
3. **Prompt geometry is load-bearing.** Short imperative personas + rigid formatter + `<caption_output>` scored; long roleplay + soft narrator + `<final_caption>` → **0.74**.
4. **Originality = surgical tweaks, not rewrite-from-scratch.** v3 beat the plagiarized 0.92 (**0.93**) with new wording that kept the shape.
5. **Local Fireworks Δ ≠ board.** Absolute local scores are saturated; ship on official reads.
6. **Track 2 bakes keys.** No harness env; build-arg only. Never commit secrets. Never push graded work to friend’s `origin`.

---

## Champion recipe (`:qwen-direct-v3` @ 0.93)

**Knobs (do not casually change):**
- Fireworks `accounts/fireworks/models/qwen3p7-plus`
- `CAPTION_ASSEMBLY=qwen_direct` (no describe, no selector)
- Exactly **4 frames @ 1024**
- `reasoning_effort=none`, temperature **0.7**, max_tokens **400**
- XML extract via `<caption_output>`

**Prose (Himawari-original; keep geometry):**
- Short imperative personas (clinical log / deadpan sarcasm / burned-out eng / out-of-touch everyday)
- Strict formatter system + numbered `### OUTPUT RULES ###`
- Banlist: HAL-9000, mere mortals, millennial-of-workload, man-in-his-50s, “strict data-formatting pipeline”, `### CRITICAL INSTRUCTIONS ###`

---

## Failed / weak classes (do not revive without new evidence)

- `:qwen-direct-v2` roleplay rewrite (0.74)
- Claude Opus generator (~0.80)
- formal_grounded / scene_frames / evidence-ledger / critique-repair (≤0.86 or flat)
- Plagiarized competitor persona prose (ethics + risk)

---

## Next improvement ideas (post-0.93)

Control = `:qwen-direct-v3`. One IV per branch only.

| Idea | Priority | Notes |
|---|---|---|
| Per-style temperature on Qwen-direct | **High** | formal cold / comedy hot; free knob leaders use |
| Mild persona polish (still short imperatives) | Medium | Only if tone gaps visible in outputs; never long roleplay |
| Frame count / width micro-IV on Qwen path | Medium | e.g. 5@1024 or 4@896 — expect small Δ |
| Claude `:direct-style` / single-shot stacks | Low | Floor is 0.90; unlikely to beat 0.93 |
| Audio / native video | Speculative | No verified path in our tree |

Pass bar for any new ship: official **≥0.93** to promote over champion; **≥0.90** to keep as backup. If a change drops ≤0.90, rollback to v3 immediately.

---

## Ops cheatsheet

```bash
git remote -v   # personal = NoviceCoderInfinity/silver-octo-guacamole

# Rebuild champion image
set -a && source .env && set +a
docker buildx build --platform linux/amd64 \
  --build-arg FIREWORKS_API_KEY="$FIREWORKS_API_KEY" \
  --tag ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3 \
  --push .

# Optional: point :latest at champion (only after explicit OK)
# docker buildx imagetools create \
#   -t ghcr.io/novicecoderinfinity/silver-octo-guacamole:latest \
#   ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3

# Harness verify (no -e)
docker run --rm --platform linux/amd64 \
  -v "$PWD/sample_input:/input:ro" \
  -v "$PWD/.verify_out:/output" \
  ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3
```

Scratch notes (gitignored): `.scratch/cleanroom/out/`

---

## Co-manager pickup

See **`ARUSH_PICKUP.md`** for a paste-ready prompt (updated for 0.93 champion).
