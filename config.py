"""Configuration for the video captioning pipeline.

Values are read from the environment first (via .env locally, Streamlit Secrets on
Streamlit Cloud, or -e at `docker run` time). Never commit a real API key: .env is
gitignored, and the Docker image is pushed to a PUBLIC registry.
"""
import os

from dotenv import load_dotenv

# A stale shell value must not shadow the explicitly configured local .env key.
# Submitted images do not contain .env, so their baked environment is unaffected.
load_dotenv(override=True)

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
# Fireworks is kept for judge/dev comparisons; the submitted generator uses Claude.
FIREWORKS_MODEL_ID = os.environ.get("FIREWORKS_MODEL_ID", "accounts/fireworks/models/qwen3p7-plus")
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Primary submission model. CLAUDE_MODEL_ID is the explicit generator setting; the
# default is Sonnet: the Opus trial scored 0.80 on the hidden leaderboard vs
# Sonnet's 0.83, so Sonnet is the reverted-to champion.
CLAUDE_MODEL_ID = (
    os.environ.get("CLAUDE_MODEL_ID")
    or os.environ.get("ANTHROPIC_MODEL_ID")
    or "claude-sonnet-5"
)

# judge.py is a standalone dev tool (not part of the graded pipeline) that scores
# generated captions. JUDGE_PROVIDER picks its backend: "fireworks" (default, reuses
# FIREWORKS_API_KEY) or "anthropic" (uses ANTHROPIC_API_KEY). JUDGE_MODEL_ID is that
# backend's model.
JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "fireworks")
JUDGE_MODEL_ID = os.environ.get(
    "JUDGE_MODEL_ID",
    "claude-sonnet-5" if JUDGE_PROVIDER == "anthropic" else FIREWORKS_MODEL_ID,
)

# Frame sampling (original 0.90 quality): ~1 frame / SECONDS_PER_FRAME, clamped.
SECONDS_PER_FRAME = float(os.environ.get("SECONDS_PER_FRAME", "5.0"))
MIN_FRAMES = int(os.environ.get("MIN_FRAMES", "8"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "20"))
FRAME_MAX_WIDTH = int(os.environ.get("FRAME_MAX_WIDTH", "768"))

# Caption assembly (single independent variable for the SVG→next experiment):
#   portfolio_select — SVG 0.88: best-of-2 specialists + frame-grounded selector
#   single_shot      — one multimodal specialist caption per style; no selector
CAPTION_ASSEMBLY = os.environ.get("CAPTION_ASSEMBLY", "single_shot").strip().lower()
