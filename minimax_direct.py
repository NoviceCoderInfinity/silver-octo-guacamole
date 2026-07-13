"""MiniMax-direct: one Fireworks vision call → all 4 style captions as JSON.

Board pattern (VeloCap 0.91 / PADAYON-class): dense frames + MiniMax M3 + single
multimodal JSON, no describe/selector chain. Himawari-original style briefs.
Falls back to Qwen-direct then Claude for any empty/invalid styles.
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
from concurrent.futures import ThreadPoolExecutor

import requests

import config
from video_utils import (
    choose_num_frames,
    download_video,
    extract_frames,
    frame_to_b64,
    get_duration_seconds,
)

# Short imperative voices (Himawari-original; same geometry as our 0.93 Qwen-v3).
STYLE_BRIEFS = {
    "formal": (
        "Clinical instrument-log voice: cold, factual, emotionless. "
        "State only what is visibly present across the frames."
    ),
    "sarcastic": (
        "Deadpan sarcasm with eye-rolling superiority. Lightly mock something "
        "actually on screen; keep the wit sharp and grounded."
    ),
    "humorous_tech": (
        "Burned-out engineer humor: map the scene onto bugs, deploys, latency, "
        "and flaky jobs. The joke is the scene, not your résumé."
    ),
    "humorous_non_tech": (
        "Warm, slightly exhausted everyday humor. No tech words and no niche "
        "references — keep it broadly relatable."
    ),
}

API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"


def _clean_json(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text)


def _overlap(a: str, b: str) -> float:
    wa, wb = set(a.split()), set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def _valid(parsed: dict, styles: list[str]) -> bool:
    if not isinstance(parsed, dict):
        return False
    for s in styles:
        val = parsed.get(s)
        if not isinstance(val, str) or len(val.split()) < 6:
            return False
    norms = {s: _normalize(parsed[s]) for s in styles}
    if len(set(norms.values())) < len(styles):
        return False
    for i, a in enumerate(styles):
        for b in styles[i + 1 :]:
            if _overlap(norms[a], norms[b]) > 0.78:
                return False
    return True


def _extract_frames_b64(video_url: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/clip.mp4"
        download_video(video_url, path)
        duration = get_duration_seconds(path)
        n = choose_num_frames(
            duration, config.SECONDS_PER_FRAME, config.MIN_FRAMES, config.MAX_FRAMES,
        )
        frames_dir = f"{tmp}/frames"
        os.makedirs(frames_dir, exist_ok=True)
        paths = extract_frames(
            path, frames_dir, num_frames=n, max_width=config.FRAME_MAX_WIDTH,
        )
        return [frame_to_b64(p) for p in paths]


def _message_content(data: dict) -> str:
    """Handle normal content and MiniMax-style reasoning payloads."""
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text" and p.get("text"):
                parts.append(p["text"])
            elif isinstance(p, str):
                parts.append(p)
        if parts:
            return "\n".join(parts).strip()
    # Some reasoning models stash the final answer elsewhere
    for key in ("reasoning_content", "reasoning"):
        val = msg.get(key)
        if isinstance(val, str) and "{" in val:
            return val.strip()
    return ""


def _call_minimax(frames_b64: list[str], styles: list[str], *, attempt: int) -> dict:
    style_block = "\n".join(f'- "{s}": {STYLE_BRIEFS[s]}' for s in styles if s in STYLE_BRIEFS)
    prompt = (
        f"You are shown {len(frames_b64)} frames sampled evenly across one video clip, "
        "in chronological order — treat them as one continuous scene.\n\n"
        "Write ONE English caption per style below. Every caption must:\n"
        "- Accurately reflect what is actually visible (subjects, setting, actions, changes)\n"
        "- Sound unmistakably like its assigned style (a reader should tell styles apart)\n"
        "- Be 1-3 sentences with at least one concrete visual detail\n"
        "- Be genuinely distinct from the other styles (no shared jokes or paraphrases)\n"
        "- Avoid invented brands, places, or sign text unless large and unmistakable\n\n"
        f"Styles:\n{style_block}\n\n"
        f"Return ONLY a JSON object with exact keys {json.dumps(styles)}."
    )
    content = [{"type": "text", "text": prompt}]
    for b64 in frames_b64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

    # Slight temperature bump on retries to escape near-duplicate collapses.
    temp = float(getattr(config, "MINIMAX_TEMPERATURE", 0.5)) + 0.08 * attempt
    payload = {
        "model": config.FIREWORKS_MODEL_ID,
        "max_tokens": int(getattr(config, "MINIMAX_MAX_TOKENS", 1200)),
        "temperature": min(temp, 0.85),
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": content}],
    }
    # MiniMax often ignores reasoning_effort; omit rather than fight the model.
    headers = {
        "Authorization": f"Bearer {config.FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    timeout = float(getattr(config, "MINIMAX_TIMEOUT", 60))
    r = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
    if r.status_code in (429, 500, 502, 503, 504):
        raise RuntimeError(f"Fireworks HTTP {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    raw = _message_content(r.json())
    if not raw:
        raise RuntimeError("MiniMax returned empty content")
    return json.loads(_clean_json(raw))


def _qwen_fill(video_url: str, styles: list[str], frames_b64: list[str]) -> dict[str, str]:
    """Per-style Qwen-direct fill for missing keys (our 0.93 geometry)."""
    from llm_client import FireworksClient
    from pipeline import (
        QWEN_DIRECT_GUARD,
        QWEN_DIRECT_PERSONAS,
        QWEN_DIRECT_SYSTEM,
        _extract_caption_output,
    )

    client = FireworksClient(
        config.FIREWORKS_API_KEY, "accounts/fireworks/models/qwen3p7-plus", config.FIREWORKS_BASE_URL,
    )
    out: dict[str, str] = {}

    def one(s: str):
        persona = QWEN_DIRECT_PERSONAS.get(s, "")
        prompt = persona + QWEN_DIRECT_GUARD
        raw = client.generate_text(
            frames_b64, prompt, system=QWEN_DIRECT_SYSTEM,
            max_tokens=400, temperature=0.7,
        )
        return s, _extract_caption_output(raw) or raw.strip()

    with ThreadPoolExecutor(max_workers=len(styles)) as pool:
        for s, cap in pool.map(one, styles):
            out[s] = cap
    return out


def _claude_fill(video_url: str, styles: list[str], frames_b64: list[str]) -> dict[str, str]:
    if not config.ANTHROPIC_API_KEY:
        return {s: "" for s in styles}
    from llm_client import ClaudeClient

    client = ClaudeClient(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL_ID)
    schema = {
        "type": "object",
        "properties": {s: {"type": "string"} for s in styles},
        "required": list(styles),
        "additionalProperties": False,
    }
    style_block = "\n".join(f'- "{s}": {STYLE_BRIEFS[s]}' for s in styles if s in STYLE_BRIEFS)
    prompt = (
        "Write one English caption per style for this video (frames attached).\n"
        f"{style_block}\n"
        "1-2 sentences each, grounded in the frames, mutually distinct. JSON only."
    )
    try:
        return {
            s: str(v).strip()
            for s, v in client.generate_json(prompt, schema, frames_b64=frames_b64, max_tokens=900).items()
        }
    except Exception:
        print(f"[minimax] claude fill failed: {traceback.format_exc()}", file=sys.stderr)
        return {s: "" for s in styles}


def caption_video_minimax(video_url: str, styles: list[str]) -> dict[str, str]:
    wanted = [s for s in styles if s in STYLE_BRIEFS] or list(styles)
    frames_b64 = _extract_frames_b64(video_url)
    if not frames_b64:
        raise RuntimeError("no frames extracted")

    parsed: dict = {}
    for attempt in range(3):
        try:
            candidate = _call_minimax(frames_b64, wanted, attempt=attempt)
            if _valid(candidate, wanted):
                parsed = candidate
                break
            # Keep partial if better than nothing
            if not parsed:
                parsed = candidate if isinstance(candidate, dict) else {}
            print(f"[minimax] attempt {attempt+1} invalid/too-similar; retrying", file=sys.stderr)
        except Exception as e:
            print(f"[minimax] attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(0.5 * (attempt + 1) + random.random() * 0.3)

    result = {s: str((parsed or {}).get(s, "")).strip() for s in wanted}
    missing = [s for s in wanted if len(result.get(s, "").split()) < 6]
    if missing and config.FIREWORKS_API_KEY:
        try:
            print(f"[minimax] qwen fill for {missing}", file=sys.stderr)
            filled = _qwen_fill(video_url, missing, frames_b64)
            for s in missing:
                if len(str(filled.get(s, "")).split()) >= 4:
                    result[s] = str(filled[s]).strip()
        except Exception:
            print(f"[minimax] qwen fill failed: {traceback.format_exc()}", file=sys.stderr)

    missing = [s for s in wanted if len(result.get(s, "").split()) < 6]
    if missing:
        print(f"[minimax] claude fill for {missing}", file=sys.stderr)
        filled = _claude_fill(video_url, missing, frames_b64)
        for s in missing:
            if filled.get(s):
                result[s] = filled[s]

    return {s: result.get(s, "") for s in styles}
