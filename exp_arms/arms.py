"""Five novel arms + Arush baseline wrappers."""
from __future__ import annotations

import json
import sys
import traceback

import config
from exp_arms import core
from exp_arms.media import cached_video_path, scene_aware_frames_b64, uniform_frames_b64
from gemini_client import GeminiVideoClient
from google import genai
from google.genai import types as gtypes


FRAME_KW = dict(
    max_width=768,  # match Arush baseline frame width for fair compare
    seconds_per_frame=config.SECONDS_PER_FRAME,
    min_frames=config.MIN_FRAMES,
    max_frames=config.MAX_FRAMES,
)


def _claude_describe(frames_b64, client, extra_suffix: str = "") -> str:
    prompt = core.DESCRIBE_PROMPT.format(n=len(frames_b64)) + extra_suffix
    return client.describe_frames(frames_b64, prompt)


# --- Arm 0: Arush baseline (exact lean path, 768px uniform frames) ---
def arm_arush_baseline(video_url: str, styles: list[str]) -> dict:
    client = core.make_claude()
    path = str(cached_video_path(video_url))
    frames = uniform_frames_b64(path, **FRAME_KW)
    description = _claude_describe(frames, client)
    return core.run_specialists_and_select(description, styles, frames, client)


# --- Arm 1: Verifiability lock (prompt-only; same perception as Arush) ---
def arm_verifiability(video_url: str, styles: list[str]) -> dict:
    client = core.make_claude()
    path = str(cached_video_path(video_url))
    frames = uniform_frames_b64(path, **FRAME_KW)
    description = _claude_describe(frames, client)
    return core.run_specialists_and_select(
        description, styles, frames, client, verifiability=True,
    )


# --- Arm 2: Gemini temporal notes + Claude frame describe ---
TEMPORAL_NOTES_PROMPT = (
    "Watch this video clip. List, in strict chronological order, only the EVENTS and "
    "CHANGES that happen over time: subject movement and direction, things that start "
    "or stop, arrivals or departures, state changes, and camera motion. 3-6 short bullet "
    "points, each under 15 words. Do NOT describe colours, appearance, clothing, species, "
    "brands, or the setting - events and motion only. Only include events that actually "
    "occur; never speculate. If essentially nothing changes, reply with: "
    "'- static scene, no notable changes'."
)

NOTES_BLOCK = (
    "\n\nAdditionally, here are temporal notes from watching the full continuous video "
    "(the frames above are only samples, so they can miss or misorder events):\n"
    "{notes}\n"
    "Use these notes ONLY to get the sequence of events right. For appearance, colours, "
    "setting and every other visual detail, trust the frames. If a note contradicts what "
    "the frames clearly show, trust the frames."
)


def _gemini_temporal_notes(video_path: str) -> str | None:
    if not config.GEMINI_API_KEY:
        return None
    try:
        gclient = genai.Client(api_key=config.GEMINI_API_KEY)
        with open(video_path, "rb") as f:
            part = gtypes.Part.from_bytes(data=f.read(), mime_type="video/mp4")
        resp = gclient.models.generate_content(
            model=config.GEMINI_MODEL_ID,
            contents=[part, TEMPORAL_NOTES_PROMPT],
            config=gtypes.GenerateContentConfig(temperature=0.2, max_output_tokens=500),
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception:
        print(f"[exp] temporal notes failed: {traceback.format_exc()}", file=sys.stderr)
        return None


def arm_gemini_temporal(video_url: str, styles: list[str]) -> dict:
    client = core.make_claude()
    path = str(cached_video_path(video_url))
    frames = uniform_frames_b64(path, **FRAME_KW)
    notes = _gemini_temporal_notes(path)
    suffix = NOTES_BLOCK.format(notes=notes) if notes else ""
    description = _claude_describe(frames, client, extra_suffix=suffix)
    return core.run_specialists_and_select(description, styles, frames, client)


# --- Arm 3: Scene-aware frame sampling ---
def arm_scene_frames(video_url: str, styles: list[str]) -> dict:
    client = core.make_claude()
    path = str(cached_video_path(video_url))
    frames = scene_aware_frames_b64(path, **FRAME_KW)
    description = _claude_describe(frames, client)
    return core.run_specialists_and_select(description, styles, frames, client)


# --- Arm 4: Cross-family selection (Claude candidates, Gemini picks) ---
def _gemini_select(description: str, candidates: dict, frames_b64: list[str],
                   sel_schema: dict) -> dict:
    """Independent selector: Gemini sees frames + candidates; Claude never picks."""
    g = GeminiVideoClient(config.GEMINI_API_KEY, config.GEMINI_MODEL_ID)
    # Gemini client is video-oriented; for frames use raw generate_content with images.
    client = g.client
    parts = []
    for b64 in frames_b64:
        import base64
        parts.append(gtypes.Part.from_bytes(data=base64.b64decode(b64), mime_type="image/jpeg"))
    prompt = core.selection_prompt(description, candidates, verifiability=True)
    prompt += (
        "\nRespond with ONLY a JSON object keyed by style name whose values are the "
        "exact winning caption strings."
    )
    parts.append(prompt)
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL_ID,
        contents=parts,
        config=gtypes.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2000,
            response_mime_type="application/json",
        ),
    )
    data = json.loads((resp.text or "").strip())
    # Ensure required keys exist
    out = {}
    for s, pair in candidates.items():
        val = str(data.get(s, "")).strip()
        if val not in (pair.get("a", ""), pair.get("b", "")):
            # If model rewrote, fall back to 'a' to keep selection honest
            val = str(pair.get("a", "")).strip()
        out[s] = val
    return out


def arm_cross_family_select(video_url: str, styles: list[str]) -> dict:
    client = core.make_claude()
    path = str(cached_video_path(video_url))
    frames = uniform_frames_b64(path, **FRAME_KW)
    description = _claude_describe(frames, client)
    return core.run_specialists_and_select(
        description, styles, frames, client, select_fn=_gemini_select,
    )


# --- Arm 5: Claim-audit repair (Gemini audits Claude captions; different family) ---
AUDIT_PROMPT = (
    "You are shown frames from a video and one caption. List every concrete factual "
    "claim in the caption. For each claim say whether it is visibly supported by the "
    "frames (supported|unverifiable|contradicted). Then, if any claim is unverifiable "
    "or contradicted, rewrite the caption in the SAME style/tone so every claim is "
    "supported — keep the joke/voice if possible, drop shaky details. If all claims are "
    "supported, return the original caption unchanged.\n\n"
    "Style: {style}\n"
    "Style definition: {style_def}\n"
    "Caption: {caption}\n\n"
    "Respond JSON: {{\"claims\":[{{\"claim\":str,\"verdict\":str}}], \"caption\": str}}"
)


def _gemini_audit_caption(frames_b64: list[str], style: str, caption: str) -> str:
    import base64
    g = GeminiVideoClient(config.GEMINI_API_KEY, config.GEMINI_MODEL_ID)
    parts = [
        gtypes.Part.from_bytes(data=base64.b64decode(b64), mime_type="image/jpeg")
        for b64 in frames_b64
    ]
    parts.append(AUDIT_PROMPT.format(
        style=style, style_def=core.STYLE_GUIDE[style], caption=caption,
    ))
    resp = g.client.models.generate_content(
        model=config.GEMINI_MODEL_ID,
        contents=parts,
        config=gtypes.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1200,
            response_mime_type="application/json",
        ),
    )
    data = json.loads((resp.text or "").strip())
    new_cap = str(data.get("caption", "")).strip()
    return new_cap or caption


def arm_claim_audit(video_url: str, styles: list[str]) -> dict:
    client = core.make_claude()
    path = str(cached_video_path(video_url))
    frames = uniform_frames_b64(path, **FRAME_KW)
    description = _claude_describe(frames, client)
    captions = core.run_specialists_and_select(description, styles, frames, client)
    # Audit non-formal styles (where unverifiable flourishes concentrate).
    for s in styles:
        if s == "formal":
            continue
        try:
            captions[s] = _gemini_audit_caption(frames, s, captions[s])
        except Exception:
            print(f"[exp] claim audit failed {s}: {traceback.format_exc()}", file=sys.stderr)
    return captions


ARMS = {
    "arush_baseline": {
        "fn": arm_arush_baseline,
        "title": "Arush 0.87 lean baseline",
        "novel": False,
    },
    "verifiability": {
        "fn": arm_verifiability,
        "title": "Verifiability-locked specialists/selection",
        "novel": True,
    },
    "gemini_temporal": {
        "fn": arm_gemini_temporal,
        "title": "Gemini temporal notes + Claude describe",
        "novel": True,
    },
    "scene_frames": {
        "fn": arm_scene_frames,
        "title": "Scene-change + uniform frame mix",
        "novel": True,
    },
    "cross_family_select": {
        "fn": arm_cross_family_select,
        "title": "Claude candidates + Gemini frame selector",
        "novel": True,
    },
    "claim_audit": {
        "fn": arm_claim_audit,
        "title": "Claude captions + Gemini claim-audit repair",
        "novel": True,
    },
}
