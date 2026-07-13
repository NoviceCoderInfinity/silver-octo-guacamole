# Experiment: MiniMax-direct (board-pattern climb)

Branch: `experiments/minimax-direct`
Tag: `ghcr.io/novicecoderinfinity/silver-octo-guacamole:minimax-direct`

## Why this plan
- Himawari Claude `:single-shot` → **0.79** (ops/recipe churn under one tag)
- Our Qwen-direct-v3 hit **0.93** then collapsed on Fireworks 429 empties
- Quiptionary (Qwen) now **0.81** on board — Qwen ceiling looks contested
- Current leaders (PADAYON 0.92, SwiftCap/VeloCap 0.91) use **Fireworks MiniMax**,
  dense frames, **one vision call → all 4 styles JSON**, no describe/selector

## Recipe
1. Sample **16 frames @ 640px** (VeloCap uses 24; we trade a bit for wall-clock)
2. **MiniMax M3** one multimodal call → JSON `{formal, sarcastic, humorous_tech, humorous_non_tech}`
3. Validate length + style distinctness; retry up to 3×
4. Fill gaps: **Qwen-direct** (our 0.93 personas) → **Claude** multimodal
5. `MAX_WORKERS=5`, bake Fireworks + Anthropic keys

## Learnings applied
- Don’t mutate `:single-shot`; ship a **new tag**
- Don’t serialize for RPM fear when key is healthy
- Don’t empty on failure — always fill
- Match winner geometry (MiniMax one-shot) with Himawari-original briefs

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:minimax-direct
digest: (pending)
```
