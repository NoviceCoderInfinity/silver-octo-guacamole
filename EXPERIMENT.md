# Experiment: single-shot (no selector)

Branch: `experiments/single-shot-no-selector`

## Hypothesis

SVG 0.88 pays for best-of-2 candidates plus a copy-only selector. That machinery
may average away distinctive voice the official judge rewards. Collapse assembly
to **one multimodal specialist caption per style** and drop the selector.

## Control vs treatment (single IV)

| | Control (SVG 0.88) | This branch |
| --- | --- | --- |
| Describe | Claude frames → prose | same |
| Specialists | frames + description, best-of-2 | frames + description, **one** caption |
| Selector | frame-grounded, copy-only | **none** |
| Frames | uniform 8–20 @ 768 | same |
| Model | Claude Sonnet | same |

Knob: `CAPTION_ASSEMBLY=single_shot` (default here) vs `portfolio_select` (SVG).

## Official pass / fail (pre-declared)

- Pass: official ≥ **0.90** (≥ +0.02 vs SVG 0.88)
- Ambiguous: 0.88–0.89 — do not ship as new champion
- Fail: ≤ 0.87 or schema/runtime regression — rollback to SVG image
- Note: **0.95 is not a credible one-step target** from 0.88

## Manager note

Clean-room proposal (motion/event-aware frames) was **NO-GO**: same class as
prior scene-frame ship that did not move the board; recalibrated upside ~+0.005–0.01.

## Image

```text
ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot
digest: sha256:2b955e255df0d27d62d40dc575173d9356b5e665a68c82644a915eb84ad404c5
```

Also tagged `:latest` only if intentionally promoted after official score.

## Build / verify

```bash
KEY=$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)
docker buildx build --platform linux/amd64 \
  --build-arg ANTHROPIC_API_KEY="$KEY" \
  --build-arg CAPTION_ASSEMBLY=single_shot \
  --tag ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot \
  --push .

docker run --rm --platform linux/amd64 \
  -v "$(pwd)/sample_input:/input:ro" \
  -v "$(pwd)/sample_output:/output" \
  ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot
```

Harness injects no env vars — key must be baked at build time.
