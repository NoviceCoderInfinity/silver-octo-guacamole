"""Configuration for the video captioning pipeline."""
import os

from dotenv import load_dotenv

# Do not override: Docker ENV / graded runtime must win over any leftover .env.
load_dotenv(override=False)

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_MODEL_ID = os.environ.get("FIREWORKS_MODEL_ID", "accounts/fireworks/models/qwen3p7-plus")
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL_ID = (
    os.environ.get("CLAUDE_MODEL_ID")
    or os.environ.get("ANTHROPIC_MODEL_ID")
    or "claude-sonnet-5"
)

GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY", "") or "").strip().strip("'\"")
# Working on this key: gemini-3.5-flash / gemini-flash-latest / gemini-3.1-flash-lite
# (gemini-2.5-flash blocked for new users). Prefer 3.5-flash for quality.
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-3.5-flash")

JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "fireworks")
JUDGE_MODEL_ID = os.environ.get(
    "JUDGE_MODEL_ID",
    "claude-sonnet-5" if JUDGE_PROVIDER == "anthropic" else FIREWORKS_MODEL_ID,
)

SECONDS_PER_FRAME = float(os.environ.get("SECONDS_PER_FRAME", "5.0"))
MIN_FRAMES = int(os.environ.get("MIN_FRAMES", "4"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "4"))
FRAME_MAX_WIDTH = int(os.environ.get("FRAME_MAX_WIDTH", "1024"))

# gemini_direct = native video → all 4 styles in one Gemini JSON call
CAPTION_ASSEMBLY = os.environ.get("CAPTION_ASSEMBLY", "gemini_direct").strip().lower()
QWEN_DIRECT_TEMPERATURE = float(os.environ.get("QWEN_DIRECT_TEMPERATURE", "0.7"))
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0.55"))
