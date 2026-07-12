FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py video_utils.py llm_client.py pipeline.py main.py ./

# Track 2 rules: no env vars are injected by the harness — credentials ship inside
# the image. The key is supplied at build time (--build-arg), never committed to git.
ARG FIREWORKS_API_KEY=""
ENV FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
ENV FIREWORKS_MODEL_ID="accounts/fireworks/models/qwen3p7-plus"
# Sequential by default: avoids Fireworks RPM stampedes (credits ≠ rate limit).
# ~12 clips × 4 styles still fits the 10-minute harness budget.
ENV MAX_WORKERS="1"
# Quiptionary-parity profile: Qwen direct vision, 4 frames @ 1024, XML captions.
ARG CAPTION_ASSEMBLY="qwen_direct"
ENV CAPTION_ASSEMBLY=${CAPTION_ASSEMBLY}
ENV MIN_FRAMES="4"
ENV MAX_FRAMES="4"
ENV FRAME_MAX_WIDTH="1024"
ENV QWEN_DIRECT_TEMPERATURE="0.7"

CMD ["python", "main.py"]
