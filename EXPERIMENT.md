# Experiment: qwen-direct-v3-w2 (rate-limit safe, mild parallelism)

Branch: `experiments/qwen-direct-v3-serial` (w2 bump)

## Diagnosis (Fireworks analytics)
Credits remaining (~$34) ≠ RPM headroom. Analytics show **orange 429** spikes
aligned with Jul 10–12 request bursts. That matches the old image:
`MAX_WORKERS=6` × 4 parallel styles ≈ up to **24 concurrent** vision calls →
empty captions → board collapse (~0.47) despite same 0.93 digest.

## IV vs 0.93 recipe
- **Same** model/prompts/4@1024/temp/reasoning/XML
- `MAX_WORKERS=2` (clips)
- Styles **sequential** (peak **2** concurrent API calls)
- Explicit 429/5xx backoff retries
- Rebuilt with a fresh Fireworks key (not committed; build-arg only)

## Pass/fail
Target restore **≥0.90**, ideally ~**0.93**. If 429s persist, drop to workers=1.

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3-w2
digest: sha256:d2733f6e3d2c612e856b8dd567c7d6e0822d44c37179382b3ba31afd36398ed7
```
