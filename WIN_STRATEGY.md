# Win strategy — what we were missing vs competitors

## Board reality (Himawari)
| Submit | Score | Real failure |
|--------|------:|--------------|
| Qwen-direct | **0.43** | Empty/unparsed cells (~half). Tags missing or 429 → `""` scored as 0 |
| Claude single-shot | **0.74** | Degraded digest / reliability; not top-band quality |
| MiniMax one-shot JSON | **0.71** | Style collapse (joint 4-voice call) + low-res frames; copying VeloCap README ≠ their score |
| Qwen-direct-v3 (earlier) | **0.93** | Proof we can win — when cells are filled |

## What competitors actually have that we lost
1. **Zero empty cells** under full hidden concurrency (VeloCap even writes placeholders; we wrote `""`)
2. **Parse robustness** — we required `<caption_output>`; if Qwen omitted tags → empty → 0.43
3. **Stable concurrency** for their provider (we ran workers=6 into Fireworks storms)
4. **Not** “MiniMax magic” — our MiniMax clone scored **worse** than broken Claude

## Winning recipe for this submit (`:win-hardened`)
Restore **0.93 mechanism** + kill the empty-cell bug:

1. Qwen3.7-Plus, **4 frames @1024**, **one vision call per style**, short personas
2. If tags missing → **use raw text** (do not zero the cell)
3. If still short → **Claude multimodal fill**
4. `MAX_WORKERS=2` + Fireworks 429 retries
5. Bake Fireworks + Anthropic keys
6. New tag — do not overwrite old digests

## Kill criterion
Official **&lt; 0.85 with short_or_empty_cells=0 in local preflight** → 0.93 not reproducible; pivot to Claude/Gemini-only.

## Submit
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:win-hardened
```
