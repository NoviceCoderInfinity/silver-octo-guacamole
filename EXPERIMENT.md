# Experiment: Qwen-direct v3 — surgical originality (CHAMPION)

Branch: `experiments/qwen-direct-v3`

## Official result
**0.93** on the graded board.

Beats plagiarized `:qwen-direct` (0.92) and collapses the failed `:qwen-direct-v2` (0.74).
This is the **current Himawari champion** — treat as control for further IVs.

## What went wrong with v2 (0.74)
Kept recipe knobs but replaced short imperative personas + rigid formatter +
`<caption_output>` with long roleplay, soft narrator system, and `<final_caption>`.

## What v3 did
Restored **prompt geometry** of the 0.92 run with **Himawari-original wording**.

Banned fragments avoided: HAL-9000, mere mortals, millennial-of-workload,
man-in-his-50s, “strict data-formatting pipeline”, `### CRITICAL INSTRUCTIONS ###`.

## Held fixed
Qwen3.7-Plus, 4@1024, temp 0.7, reasoning off, no describe/selector, max_tokens 400,
`<caption_output>` extraction.

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3
digest: sha256:57189838befccc6f71164988535a527b3167fdbcef18972eb59c909636e11a99
```

## Next
Single-IV stacks only (e.g. per-style temperature). Promote only if official ≥0.93.
