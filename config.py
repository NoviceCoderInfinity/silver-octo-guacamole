"""Configuration for the video captioning pipeline.

Values are read from the environment first (via .env locally, Streamlit Secrets on
Streamlit Cloud, or -e at `docker run` time). Never commit a real API key: .env is
gitignored, and the Docker image is pushed to a PUBLIC registry.
"""
import os

from dotenv import load_dotenv

# Docker ENV / explicit exports must win over leftover local .env.
load_dotenv(override=False)

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
# Primary generator for this experiment: Qwen3.7-Plus via Fireworks (Quiptionary-class).
FIREWORKS_MODEL_ID = os.environ.get("FIREWORKS_MODEL_ID", "accounts/fireworks/models/qwen3p7-plus")
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL_ID = (
    os.environ.get("CLAUDE_MODEL_ID")
    or os.environ.get("ANTHROPIC_MODEL_ID")
    or "claude-sonnet-5"
)

JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "fireworks")
JUDGE_MODEL_ID = os.environ.get(
    "JUDGE_MODEL_ID",
    "claude-sonnet-5" if JUDGE_PROVIDER == "anthropic" else FIREWORKS_MODEL_ID,
)

# Quiptionary-parity sampling: exactly 4 frames at 1024px (not 8–20 @ 768).
SECONDS_PER_FRAME = float(os.environ.get("SECONDS_PER_FRAME", "5.0"))
MIN_FRAMES = int(os.environ.get("MIN_FRAMES", "4"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "4"))
FRAME_MAX_WIDTH = int(os.environ.get("FRAME_MAX_WIDTH", "1024"))

# Caption assembly:
#   portfolio_select | single_shot | direct | qwen_direct
# qwen_direct = one Fireworks Qwen vision call per style, XML-tagged caption, no describe/selector.
CAPTION_ASSEMBLY = os.environ.get("CAPTION_ASSEMBLY", "qwen_direct").strip().lower()

# Quiptionary uses temperature 0.7 on the styled vision call.
QWEN_DIRECT_TEMPERATURE = float(os.environ.get("QWEN_DIRECT_TEMPERATURE", "0.7"))
