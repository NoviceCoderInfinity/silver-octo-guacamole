# Experiment: single-shot rekey (0.90 recipe + working Anthropic key)

Branch: `experiments/single-shot-rekey`

## Goal
Restore the official **0.90** `:single-shot` path after the previous baked
Anthropic key ran out of credits.

## Same as 0.90
- Claude Sonnet describe → one caption/style (no selector)
- Same prompts/personas as `experiments/single-shot-no-selector`

## Reliability changes
Keep serial to avoid 429→empty captions on the board:
- `MAX_WORKERS=1`
- sequential styles
- Claude 429/5xx retries with backoff

New key (1-day expiry) smoke: `claude-sonnet-5` OK; 6 rapid text calls OK;
local 1-clip single-shot OK; harness 2/2 sample clips OK (no `-e`).

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot
digest: sha256:22677460f6a49156d1188ce662ff90d820de0826e99a52dcf60929e8899fcf98
harness: 2/2 sample clips OK (no -e)
also: :single-shot-rekey (same digest)
```

Overwrites previous `:single-shot` digest (old baked key was dead / low-credit).
