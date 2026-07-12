# Experiment: single-shot timeout fix

Branch: `experiments/single-shot-rekey`

## What went wrong
`:single-shot` resubmit with the fresh key returned **TIMEOUT**.

Root cause: the rekey image set `MAX_WORKERS=1` and ran the 4 style
specialists **sequentially** (RPM paranoia). Local timing was ~40–45s/clip,
so a full hidden set cannot finish in the graded wall-clock.

The original 0.90 recipe used `MAX_WORKERS=6` + parallel styles.

## Fix (keep single-shot; finish in time)
- Restore **parallel styles** (ThreadPoolExecutor over the 4 styles)
- `MAX_WORKERS=4` (clip-level parallelism; 2 vCPU graded box)
- Cap frames: **4–6** @ width 640 (was 8–20 @ 768) — same describe→one-caption path
- Faster 429 retries (2s → max 12s, 5 attempts) so backoff cannot eat the budget

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:single-shot
digest: (pending push)
```
