# Experiment: Qwen-direct ORIGINAL prompts (score-preserving rewrite)

Branch: `experiments/qwen-direct-original`

## Why this branch exists
`:qwen-direct` scored **0.92** on the official board but used **plagiarized persona /
system / guard prose** from Quiptionary. This branch keeps the **winning recipe knobs**
and replaces **all creative text** with Himawari-authored prompts.

## Held fixed (0.92 recipe)
- Fireworks `qwen3p7-plus`
- `CAPTION_ASSEMBLY=qwen_direct` (no describe, no selector)
- Exactly **4 frames @ 1024**
- `reasoning_effort=none`, temperature **0.7**, max_tokens **400**
- One multimodal call per style + XML tag extraction

## Changed (originality)
- All `QWEN_DIRECT_PERSONAS` rewritten (archivist / jaded host / build engineer / diner)
- New `QWEN_DIRECT_SYSTEM` + `QWEN_DIRECT_GUARD`
- Primary tag: `<final_caption>` (legacy `<caption_output>` still parsed as fallback)

## Pass/fail
Official **≥0.90** keep; target **≥0.91** (ideally hold **0.92**). If ≤0.89, diagnose
prompt sharpness before abandoning the recipe.

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v2
digest: sha256:6a20678f10fbddbeb29d27aaafa87d24ed1e7898960eb41ab721b63f29910ba0
```

Do **not** resubmit `:qwen-direct` (plagiarized prompts). Prefer `:qwen-direct-v2`.
