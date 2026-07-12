# Experiment: single-shot full-quality parallel (high-tier key)

Branch: `experiments/single-shot-rekey`

## Intent
Restore the original **0.90-quality** single-shot recipe with **max parallelism**.
High-tier Anthropic key — do not throttle for RPM.

## Recipe (no quality cuts)
- Describe → one multimodal caption/style (frames on describe **and** specialists)
- Frames: 8–20 @ width 768 (`SECONDS_PER_FRAME=5`)
- Parallel styles (4) + `MAX_WORKERS=6` clip concurrency
- No selector / no best-of-2
- Fast 429 retries only as safety net

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot
digest: sha256:ff60fc273cb4a710e06f01a00023a82fbc10682cf0af97d863202336779d5153
harness: 3/3 @ 2vCPU/4GB OK (full multimodal parallel)
```
