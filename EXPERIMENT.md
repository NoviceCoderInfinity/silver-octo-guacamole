# Experiment: Gemini native-video direct (credit-efficient)

Branch: `experiments/gemini-video-direct`

## Competitor takeaway
Public top agents (PADAYON 0.92, VeloCap 0.91, MasterCinator 0.89, DescribeX)
use **Fireworks frame VLMs** (MiniMax/Kimi/etc), not Gemini. DescribeX LabLab
tags mention Gemini but graded code is Fireworks. **Native video is an open lane.**

## Architecture (max Gemini, conserve credits)
- Provider: **Google Gemini** (`gemini-3.5-flash`)
- Input: **full MP4** (not 4 frames) — Gemini's unique edge vs Fireworks stacks
- Assembly: **one call per clip** returning all 4 styles as JSON (VeloCap-shaped)
- Personas: Himawari short imperatives (same geometry as Qwen-direct-v3; original prose)
- Fallback: single-style video call only if a key is missing
- Concurrency: `MAX_WORKERS=2`
- Retries on 429/5xx

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:gemini-video
digest: sha256:79a9679c015ed9933f4bb725d4094e1a64c05be47db213ac3edcfd7771951e1a
harness: 3/3 sample clips OK (no -e)
```
