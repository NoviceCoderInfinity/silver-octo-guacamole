FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py video_utils.py llm_client.py pipeline.py main.py ./

# Track 2: bake both keys — Qwen primary, Claude never-empty fill.
ARG FIREWORKS_API_KEY=""
ARG ANTHROPIC_API_KEY=""
ENV FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

ENV FIREWORKS_MODEL_ID="accounts/fireworks/models/qwen3p7-plus"
ENV CAPTION_ASSEMBLY="qwen_direct"
# Lower concurrency than the 0.43 collapse; styles still parallel within a clip.
ENV MAX_WORKERS="2"
ENV MIN_FRAMES="4"
ENV MAX_FRAMES="4"
ENV FRAME_MAX_WIDTH="1024"
ENV QWEN_DIRECT_TEMPERATURE="0.7"

CMD ["python", "main.py"]
