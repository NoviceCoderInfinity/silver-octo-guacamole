"""Gemini video-native describe client.

Used only for the perception/describe stage. Style writing stays on Claude: our own
A/B history showed Opus/Gemini-as-stylist is not automatically better, and a prior
Gemini full-describe probe hallucinated appearance details — so prompts here are
conservative, and Claude frame-grounded selection remains the accuracy backstop.
"""
from __future__ import annotations

import json
import os
import time

from google import genai
from google.genai import types as gtypes

INLINE_LIMIT = 18 * 1024 * 1024

DESCRIBE_FACTS_PROMPT = (
    "Watch this entire video clip (roughly 30 seconds to 2 minutes). Respond with a "
    "single JSON object with two fields:\n\n"
    "- \"description\": a factual, neutral description — setting and time of day, main "
    "subject(s), what they are doing, how action progresses over time, and distinctive "
    "visual details that are unambiguous. 4-6 sentences.\n"
    "- \"facts\": 5-10 short, independently-checkable claims about what is literally "
    "visible or clearly audible. Order from most visually prominent/persistent (main "
    "subject and central action) to least (background or single-moment details).\n\n"
    "Hard rules:\n"
    "- Describe only what you can verify from the video; do not speculate.\n"
    "- Do not invent colours, object counts, brands, city/country names, or sign text "
    "unless they are large, legible, and unambiguous.\n"
    "- Prefer the main subject and its action over background flourishes.\n"
    "- If almost nothing changes, say so explicitly.\n"
    "Respond with ONLY the JSON object, no markdown fences."
)


class GeminiVideoClient:
    def __init__(self, api_key: str, model_id: str, timeout: float = 180.0):
        self.model_id = model_id
        self.client = genai.Client(api_key=api_key.strip().strip("'\""))
        self.timeout = timeout

    def _video_part(self, video_path: str):
        size = os.path.getsize(video_path)
        if size <= INLINE_LIMIT:
            with open(video_path, "rb") as f:
                return gtypes.Part.from_bytes(data=f.read(), mime_type="video/mp4")
        uploaded = self.client.files.upload(file=video_path)
        while uploaded.state and uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = self.client.files.get(name=uploaded.name)
        if uploaded.state and uploaded.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini file upload state: {uploaded.state.name}")
        return uploaded

    def describe_video_with_facts(self, video_path: str) -> dict:
        """Return {description: str, facts: list[str]} from the full video file."""
        video_part = self._video_part(video_path)
        resp = self.client.models.generate_content(
            model=self.model_id,
            contents=[video_part, DESCRIBE_FACTS_PROMPT],
            config=gtypes.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1536,
                response_mime_type="application/json",
            ),
        )
        text = (resp.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty describe response")
        data = json.loads(text)
        return {
            "description": str(data.get("description", "")).strip(),
            "facts": [str(f).strip() for f in data.get("facts", []) if str(f).strip()],
        }
