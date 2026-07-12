# Experiment: single-shot rekey (0.90 recipe + working Anthropic key)

Branch: `experiments/single-shot-rekey`

## Goal
Restore the official **0.90** `:single-shot` path after the previous baked
Anthropic key ran out of credits.

## Same as 0.90
- Claude Sonnet describe → one caption/style (no selector)
- Same prompts/personas as `experiments/single-shot-no-selector`

## Reliability changes (required for this key)
This Anthropic org is ~**5 RPM / 10k input TPM**. The old image used
`MAX_WORKERS=6` + parallel styles and will 429→empty on the board.
This build uses:
- `MAX_WORKERS=1`
- sequential styles
- Claude 429/5xx retries with backoff

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot
digest: (pending push)
```

Also tagged conceptually as the rekeyed 0.90 scorer. Overwrites previous
`:single-shot` digest (old one had a dead key).
