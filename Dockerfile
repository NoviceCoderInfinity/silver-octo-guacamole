FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py video_utils.py llm_client.py pipeline.py minimax_direct.py main.py ./

# Track 2: credentials baked at build (harness injects no env).
ARG FIREWORKS_API_KEY=""
ARG ANTHROPIC_API_KEY=""
ENV FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

ENV FIREWORKS_MODEL_ID="accounts/fireworks/models/minimax-m3"
ENV CAPTION_ASSEMBLY="minimax_direct"
ENV MAX_WORKERS="5"
ENV MIN_FRAMES="16"
ENV MAX_FRAMES="16"
ENV FRAME_MAX_WIDTH="640"
ENV SECONDS_PER_FRAME="3.0"
ENV MINIMAX_TEMPERATURE="0.5"

CMD ["python", "main.py"]
