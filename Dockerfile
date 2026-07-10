FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py video_utils.py llm_client.py gemini_client.py pipeline.py main.py ./

# Track 2 rules: no env vars are injected by the harness — credentials ship inside
# the image. The key is supplied at build time (--build-arg), never committed to git.
ARG ANTHROPIC_API_KEY=""
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

ARG GEMINI_API_KEY=""
ENV GEMINI_API_KEY=${GEMINI_API_KEY}

# claude = frame describe (Arush-compatible); gemini = full-video describe front-end.
ARG DESCRIBE_BACKEND="claude"
ENV DESCRIBE_BACKEND=${DESCRIBE_BACKEND}

ARG GEMINI_MODEL_ID="gemini-3-flash-preview"
ENV GEMINI_MODEL_ID=${GEMINI_MODEL_ID}

# Match formal_grounded experiment: uniform frames (scene_frames did not move leaderboard).
ARG FRAME_SAMPLE_MODE="uniform"
ENV FRAME_SAMPLE_MODE=${FRAME_SAMPLE_MODE}

# formal_grounded = formal first, then lock other styles to its entities (best v2 arm).
ARG CAPTION_MODE="formal_grounded"
ENV CAPTION_MODE=${CAPTION_MODE}

# Safety valve for the post-selection critique/repair pass (see config.py).
ARG ENABLE_CRITIQUE_REPAIR="false"
ENV ENABLE_CRITIQUE_REPAIR=${ENABLE_CRITIQUE_REPAIR}

CMD ["python", "main.py"]
