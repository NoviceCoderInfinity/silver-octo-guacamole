"""Gemini native-video captioning (Track-2 graded path).

Competitors' public agents mostly use Fireworks frame VLMs. Gemini's advantage is
full-clip video understanding in one shot — we use that, with Himawari-original
personas (not competitor prose).
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import tempfile
import time
import traceback

from google import genai
from google.genai import types as gtypes

from video_utils import download_video

INLINE_LIMIT = 18 * 1024 * 1024

# Short imperative voices (same geometry as our 0.93 Qwen-direct-v3; original wording).
STYLE_BRIEFS = {
    "formal": (
        "Read the clip like a clinical instrument log: cold, factual, emotionless. "
        "State only what is visibly present."
    ),
    "sarcastic": (
        "Deadpan sarcasm with eye-rolling superiority. Lightly mock something actually "
        "on screen as if it barely deserves attention, but keep the wit sharp."
    ),
    "humorous_tech": (
        "Burned-out engineer humor: map what is on screen onto bugs, deploys, latency, "
        "and flaky jobs. Stay visual — the joke is the scene, not your résumé."
    ),
    "humorous_non_tech": (
        "Warm, slightly out-of-touch everyday humor from someone who finds modern life "
        "exhausting. No tech words and no niche references — keep it broadly relatable."
    ),
}


def _with_retries(call, *, label: str, attempts: int = 5):
    delay = 2.0
    last = None
    for i in range(attempts):
        try:
            return call()
        except Exception as e:
            last = e
            msg = str(e).lower()
            retryable = any(x in msg for x in ("429", "rate", "quota", "unavailable", "503", "500", "timeout"))
            if not retryable or i == attempts - 1:
                break
            sleep_for = delay + random.uniform(0, 0.5)
            print(f"[gemini] {label} retry {i+1}/{attempts-1} after {sleep_for:.1f}s ({type(e).__name__})",
                  file=sys.stderr)
            time.sleep(sleep_for)
            delay = min(delay * 2, 20.0)
    raise last


class GeminiVideoCaptioner:
    def __init__(self, api_key: str, model_id: str, temperature: float = 0.55):
        self.model_id = model_id
        self.temperature = temperature
        self.client = genai.Client(api_key=api_key.strip().strip("'\""))

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

    def _generate(self, video_part, prompt: str, *, max_tokens: int = 4096,
                  temperature: float | None = None, json_mode: bool = False) -> str:
        config_kwargs = {
            "temperature": self.temperature if temperature is None else temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        def _call():
            return self.client.models.generate_content(
                model=self.model_id,
                contents=[video_part, prompt],
                config=gtypes.GenerateContentConfig(**config_kwargs),
            )

        resp = _with_retries(_call, label=f"generate:{self.model_id}")
        text = (resp.text or "").strip()
        if not text:
            # Thinking models sometimes leave .text empty while parts exist
            try:
                parts = []
                for c in (resp.candidates or []):
                    content = getattr(c, "content", None)
                    for p in getattr(content, "parts", None) or []:
                        t = getattr(p, "text", None)
                        if t:
                            parts.append(t)
                text = "\n".join(parts).strip()
            except Exception:
                pass
        if not text:
            raise RuntimeError("Gemini returned empty text")
        return text

    def caption_styles(self, video_url: str, styles: list[str]) -> dict[str, str]:
        """One native-video call returning all requested styles as JSON (credit-efficient)."""
        wanted = [s for s in styles if s in STYLE_BRIEFS]
        if not wanted:
            return {s: "" for s in styles}

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clip.mp4")
            download_video(video_url, path)
            video_part = self._video_part(path)

            style_lines = "\n".join(
                f'- "{s}": {STYLE_BRIEFS[s]}' for s in wanted
            )
            prompt = (
                "You are watching one short video clip. Write one English caption for EACH "
                "style below. Captions must be grounded in what is actually visible or clearly "
                "audible in the video — no invented brands, places, or sign text unless large "
                "and unmistakable. Each caption should be 1-2 sentences, distinctive in voice "
                "from the others (do not paraphrase the same sentence four ways).\n\n"
                f"Styles:\n{style_lines}\n\n"
                "Return ONLY a JSON object whose keys are exactly the style names above and "
                "whose values are the caption strings. Escape any internal double-quotes in "
                "captions properly for JSON. Prefer captions without nested quotation marks."
            )

            raw = self._generate(video_part, prompt, max_tokens=4096, temperature=0.55, json_mode=True)
            data = _parse_style_json(raw, wanted)
            if not data:
                print(f"[gemini] JSON parse failed; falling back to per-style. raw[:200]={raw[:200]!r}",
                      file=sys.stderr)

            result = {s: str(data.get(s, "")).strip() for s in wanted}

            # Retry missing / unparsed styles with a focused single-style call
            missing = [s for s in wanted if not result.get(s)]
            for s in missing:
                try:
                    one = self._generate(
                        video_part,
                        (
                            f"Watch the video. Write ONE English caption in this voice:\n"
                            f"{STYLE_BRIEFS[s]}\n\n"
                            "1-2 sentences, grounded in the video. Plain text only — no JSON, "
                            "no markdown, no preamble."
                        ),
                        max_tokens=1024,
                        temperature=0.6 if s != "formal" else 0.25,
                        json_mode=False,
                    )
                    result[s] = one.strip().strip('"')
                except Exception:
                    print(f"[gemini] single-style fallback failed for {s}: "
                          f"{traceback.format_exc()}", file=sys.stderr)

        return {s: result.get(s, "") for s in styles}


def _parse_style_json(raw: str, wanted: list[str]) -> dict:
    """Best-effort parse of Gemini JSON; tolerate fences and minor quote damage."""
    if not raw:
        return {}
    candidates = [raw.strip()]
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])

    for chunk in candidates:
        try:
            data = json.loads(chunk)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    # Last resort: pull "style": "..." fields even if the whole object is invalid JSON
    out: dict[str, str] = {}
    for s in wanted:
        m = re.search(
            rf'"{re.escape(s)}"\s*:\s*"((?:\\.|[^"\\])*)"',
            raw,
            flags=re.DOTALL,
        )
        if m:
            try:
                out[s] = json.loads(f'"{m.group(1)}"')
            except json.JSONDecodeError:
                out[s] = m.group(1)
    return out
