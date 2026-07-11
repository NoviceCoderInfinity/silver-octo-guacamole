# Experiment: Qwen-direct Quiptionary parity

Branch: `experiments/qwen-direct-quiptionary`

## IV (productized recipe)
`CAPTION_ASSEMBLY=qwen_direct`: Fireworks **Qwen3.7-Plus**, **4 frames @ 1024**,
one multimodal call per style, hard personas + `<caption_output>` tags,
`reasoning_effort=none`, temperature **0.7**. No describe, no selector, no Claude.

This is intentionally a multi-knob parity package matching the verified **0.91**
Quiptionary stack (code + GHCR image), not a single Claude-path micro-IV.

## Why (manager override)
Opus rejected a Qwen swap citing local Fireworks non-transfer. Override: Quiptionary
scored **0.91 on the official board** with this recipe — board evidence beats local Δ.
Our Claude ceiling so far is **0.88** (SVG).

## Pass/fail
Official **≥0.90** = promote candidate. ≤0.87 fail. Do not overwrite `:latest` until confirmed.

## Expected band (manager prior)
**0.88–0.92**, mode ~**0.90–0.91** if parity holds; lower if Fireworks key/model drift or
tag extraction fails on the hidden set.

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct
digest: (pending push)
```
