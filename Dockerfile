FROM --platform=linux/amd64 python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py video_utils.py llm_client.py pipeline.py gemini_caption.py main.py ./

# Track 2: credentials baked at build time.
ARG GEMINI_API_KEY=""
ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV GEMINI_MODEL_ID="gemini-3.5-flash"
ENV CAPTION_ASSEMBLY="gemini_direct"
ENV MAX_WORKERS="2"
ENV GEMINI_TEMPERATURE="0.55"

CMD ["python", "main.py"]
