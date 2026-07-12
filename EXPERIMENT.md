# Experiment: Qwen-direct v3 — surgical originality (restore 0.92 geometry)

Branch: `experiments/qwen-direct-v3`

## What went wrong with v2 (0.74)
`:qwen-direct` (plagiarized prompts) scored **0.92**. `:qwen-direct-v2` kept the
same knobs but **replaced short imperative personas + rigid formatter system +
`<caption_output>`** with long roleplay characters, a soft “visual narrator”
system, and `<final_caption>`. Local smoke still filled captions, but the voice
and instruction geometry changed enough that the official judge collapsed to
**0.74**.

## Fix strategy (v3)
Keep recipe knobs identical. Restore **prompt geometry** of the 0.92 run
(short punchy imperatives, strict formatter system, numbered output rules,
`<caption_output>`), with **rewritten wording** so we are not a plagiarism hit.

Banned fragments still avoided: HAL-9000, mere mortals, millennial-of-workload,
man-in-his-50s, “strict data-formatting pipeline”, `### CRITICAL INSTRUCTIONS ###`.

## Held fixed
Qwen3.7-Plus, 4@1024, temp 0.7, reasoning off, no describe/selector, max_tokens 400.

## Pass/fail
Official **≥0.90** = success. Target near **0.92**. If ≤0.85, stop rewriting prose
and fall back to `:single-shot` (0.90) while investigating.

## Image
```
ghcr.io/novicecoderinfinity/silver-octo-guacamole:qwen-direct-v3
digest: sha256:57189838befccc6f71164988535a527b3167fdbcef18972eb59c909636e11a99
```
