FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py video_utils.py llm_client.py pipeline.py main.py ./

# Track 2 rules: no env vars are injected by the harness — credentials ship inside
# the image. The key is supplied at build time (--build-arg), never committed to git.
ARG ANTHROPIC_API_KEY=""
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ENV MAX_WORKERS="6"
# Opus high-upside amended primary: direct frame-grounded call per style.
# No description stage, no best-of-2, no selector. Personas held fixed.
ARG CAPTION_ASSEMBLY="direct"
ENV CAPTION_ASSEMBLY=${CAPTION_ASSEMBLY}

CMD ["python", "main.py"]
