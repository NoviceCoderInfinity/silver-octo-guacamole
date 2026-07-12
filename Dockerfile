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
# Serial by default: low-tier Anthropic orgs are often ~5 RPM; parallel empties captions.
ENV MAX_WORKERS="1"
# Experiment IV vs SVG 0.88: single multimodal caption per style, no selector.
ARG CAPTION_ASSEMBLY="single_shot"
ENV CAPTION_ASSEMBLY=${CAPTION_ASSEMBLY}

CMD ["python", "main.py"]
