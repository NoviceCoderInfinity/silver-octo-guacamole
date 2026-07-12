# Experiment: qwen-direct-v3-serial (rate-limit safe)

Branch: `experiments/qwen-direct-v3-serial`

## Why
`:qwen-direct-v3` scored **0.93**, then a resubmit scored **~0.47** with the **same
image digest**. Local re-run of that image showed Fireworks **429 rate limit** and
empty captions. Credits remaining ($34) does **not** mean RPM/TPM headroom.

v3 concurrency was:
- `MAX_WORKERS=6` (clips in parallel)
- 4 styles in parallel per clip
→ up to **~24 concurrent** vision calls → easy 429.

## IV (only change vs 0.93 recipe)
1. `MAX_WORKERS=1` (clips sequential)
2. Styles sequential inside `qwen_direct`
3. Explicit 429/5xx backoff retries in `FireworksClient`

**Unchanged:** model, prompts, 4@1024, temp 0.7, reasoning off, XML tags.

## Pass/fail
Official **≥0.90** keep; target restore **~0.93**. If still ≤0.50 with no 429s in
logs, look elsewhere (wrong tag submitted, key auth, etc.).

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3-serial
digest: sha256:68e27ab4d57ccad764eb5ad3e186e09261ce15e5ec44de192be165b8d5ed2b49
```
