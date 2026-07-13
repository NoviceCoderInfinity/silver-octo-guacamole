"""Configuration for the video captioning pipeline."""
import os

from dotenv import load_dotenv

# Docker ENV / explicit exports must win over leftover local .env values.
load_dotenv(override=False)

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
# Primary for minimax_direct (VeloCap-class board winners).
FIREWORKS_MODEL_ID = os.environ.get(
    "FIREWORKS_MODEL_ID", "accounts/fireworks/models/minimax-m3",
)
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

# Dense temporal sampling (VeloCap uses 24@640). We use 16@640 for speed/quality balance.
SECONDS_PER_FRAME = float(os.environ.get("SECONDS_PER_FRAME", "3.0"))
MIN_FRAMES = int(os.environ.get("MIN_FRAMES", "16"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "16"))
FRAME_MAX_WIDTH = int(os.environ.get("FRAME_MAX_WIDTH", "640"))

# minimax_direct = one MiniMax call → JSON all 4 styles (+ Qwen/Claude fill)
CAPTION_ASSEMBLY = os.environ.get("CAPTION_ASSEMBLY", "minimax_direct").strip().lower()

QWEN_DIRECT_TEMPERATURE = float(os.environ.get("QWEN_DIRECT_TEMPERATURE", "0.7"))
MINIMAX_TEMPERATURE = float(os.environ.get("MINIMAX_TEMPERATURE", "0.5"))
MINIMAX_MAX_TOKENS = int(os.environ.get("MINIMAX_MAX_TOKENS", "1200"))
MINIMAX_TIMEOUT = float(os.environ.get("MINIMAX_TIMEOUT", "60"))
