# Experiment: direct style multimodal (Opus high-upside amended primary)

Branch: `experiments/direct-style-multimodal`

## IV
`CAPTION_ASSEMBLY=direct`: one frame-grounded call per style with personas.
**No** prose description stage, **no** best-of-2, **no** selector.

Hold fixed vs SVG 0.88: model (Sonnet), uniform 8–20 @ 768, personas/STYLE_GUIDE,
concurrency, output schema. Fallback describe-path only if a style comes back empty.

## Why
Opus collision: reported 0.89–0.92 systems are simpler/voice-first. Constraint/
grounding stacks scored 0.82–0.86. Distinct from `:single-shot` (still keeps describe).

## Pass/fail
Official **≥0.90** = promote. 0.88–0.89 ambiguous. ≤0.87 fail → rollback to SVG.

## Expected band (manager prior)
**0.87–0.91**, mode ~**0.89–0.90**. Highest upside among same-model ships; still
may not match a different-family 0.92 winner.

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:direct-style
digest: REPLACE
```
