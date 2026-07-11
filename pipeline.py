"""Core video -> multi-style caption pipeline.

CAPTION_ASSEMBLY:
  - portfolio_select: describe → best-of-2 → selector (SVG 0.88)
  - single_shot: describe → one caption/style
  - direct: one Claude multimodal call/style
  - qwen_direct: one Fireworks Qwen vision call/style (Quiptionary-class)
"""
import json
import os
import re
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import config
from video_utils import (
    choose_num_frames,
    download_video,
    extract_frames,
    frame_to_b64,
    get_duration_seconds,
)


class CaptionClient(Protocol):
    def describe_frames(self, frames_b64: list[str], prompt: str, max_tokens: int = 1024,
                        temperature: float | None = None) -> str:
        ...

    def generate_json(self, prompt: str, schema: dict, frames_b64: list[str] | None = None,
                      max_tokens: int = 1024, temperature: float | None = None) -> dict:
        ...


STYLE_GUIDE = {
    "formal": (
        "Professional, objective, factual tone, like a news-agency or stock-footage caption. "
        "One clear declarative sentence stating what the video shows. "
        "No slang, no humour, no exclamation marks, no opinions."
    ),
    "sarcastic": (
        "Dry, deadpan, ironic, lightly mocking. Use understatement, mock admiration, or "
        "faint praise aimed at something actually visible in the clip. "
        "One sentence. Subtle wit, not mean-spirited or absurd."
    ),
    "humorous_tech": (
        "Genuinely funny, built on a technology or programming joke (e.g. bugs, deploys, "
        "merge conflicts, CPUs, Wi-Fi, AI, loading screens) mapped onto what is literally "
        "happening in the clip. One to two sentences. The scene must still be recognisable "
        "from the caption."
    ),
    "humorous_non_tech": (
        "Genuinely funny, warm, relatable everyday humour that anyone would get. "
        "Absolutely NO technology, programming, internet, or science references. "
        "One to two sentences about everyday life, feelings, food, weather, work, etc., "
        "grounded in what the clip shows."
    ),
}

# Persona line prepended to each style's specialist call. Writing one style per call
# (instead of all four in one) measurably sharpened tone in pairwise judging.
PERSONAS = {
    "formal": (
        "You are a senior news-agency caption writer. Your captions are precise, "
        "objective, single-sentence, publishable as-is."
    ),
    "sarcastic": (
        "You are a dry, deadpan comedy writer known for ironic, mock-admiring "
        "one-liners. Your sarcasm is unmistakable but never mean."
    ),
    "humorous_tech": (
        "You are a comedy writer for a developer audience. Your jokes map bugs, "
        "deploys, CPUs, Wi-Fi and AI onto everyday scenes, and they actually land."
    ),
    "humorous_non_tech": (
        "You are a warm observational comedian. Your jokes are about everyday life - "
        "food, moods, weather, work - and never mention technology or science."
    ),
}

# Hard personas for qwen_direct (Quiptionary-class: voice-first, XML-tagged output).
QWEN_DIRECT_PERSONAS = {
    "formal": (
        "Analyse the visual, with the cold attitude of HAL-9000 with purely factual, "
        "emotionless tone."
    ),
    "sarcastic": (
        "Analyze the visual with a very deadpan and sarcastic tone and eye-rolling, as if "
        "you were forced to deal with mere mortals with a sigh incomparable to your power, "
        "describe with incredible wit and condescending tone."
    ),
    "humorous_tech": (
        "Describe the visual like a tired millennial of workload in his AI job. But focus "
        "on the visual, do not divert from the visual heavily towards your 'job'. Use "
        "clever technical jargon but make it effective in being absolutely funny and "
        "understandably humorous."
    ),
    "humorous_non_tech": (
        "Give a very funny and relatable attitude when describing the visual sequence as "
        "if you were a man who is in his 50s who finds it hard to keep up with the fast "
        "growing world. Do not use technical jargon and do not give very niche references."
    ),
}

QWEN_DIRECT_SYSTEM = (
    "You are a strict data-formatting pipeline. You will receive a persona and an image. "
    "You MUST wrap your final caption inside exact <caption_output> and </caption_output> tags. "
    "Do NOT output any thinking process. Do NOT output any conversational text. "
    "Do NOT use Markdown formatting (no asterisks, no headers). Plain text only. "
    "Respond ONLY IN ENGLISH."
)

QWEN_DIRECT_GUARD = (
    "\n\n### CRITICAL INSTRUCTIONS ###\n"
    "1. You MUST wrap your final caption inside exact <caption_output> and </caption_output> tags.\n"
    "2. Do NOT put anything else inside the tags.\n"
    "3. Do NOT explain your thinking or write a checklist."
)

# Tone exemplars from OTHER scenes (a balloon festival, a blacksmith), used only for
# tone calibration. Formal deliberately gets none: A/B testing showed exemplars help
# sarcasm/humour but add noise to formal.
CAPTION_EXEMPLARS = {
    "sarcastic": [
        "Ah yes, dozens of giant balloons expensively drifting wherever the wind feels like taking them, truly humanity's boldest answer to a question nobody asked.",
        "Wow, a man hitting hot metal with a hammer over and over until it becomes slightly flatter hot metal, riveting stuff from the cutting edge of the year 1400.",
    ],
    "humorous_tech": [
        "Sunrise rollout: fifty hot-air balloons spinning up over the valley like autoscaled pods, and impressively not a single one crashed on launch.",
        "This blacksmith is just debugging hardware with a hammer: heat the metal, whack it, inspect the output, repeat until the sword finally compiles.",
    ],
    "humorous_non_tech": [
        "Fifty balloons drifting over the river at sunrise, all pretending they know where they're going, just like the rest of us before breakfast.",
        "A man with the arm strength of three gym memberships keeps whacking that glowing metal like it owes him money, and the sparks clearly agree.",
    ],
}

DESCRIBE_PROMPT = (
    "You are shown {n} frames sampled evenly, in chronological order, from a single video clip "
    "(roughly 30 seconds to 2 minutes long). Write a factual, neutral description of the clip: "
    "the setting and time of day, the main subject(s), what they are doing, how the action "
    "progresses across the frames, and any distinctive visual details (colours, weather, "
    "objects, visible text, camera angle or motion). 4-6 sentences. Describe only what is "
    "clearly visible in the frames; do not speculate or invent details. Do not identify a "
    "city, country, company, building, or sign text unless it is large, legible, and "
    "unambiguous in the sampled frames."
)

CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}

SINGLE_CAPTION_SCHEMA = {
    "type": "object",
    "properties": {"caption": {"type": "string"}},
    "required": ["caption"],
    "additionalProperties": False,
}


def _qwen_direct_prompt(style: str) -> str:
    persona = QWEN_DIRECT_PERSONAS.get(style, f"Caption this in a {style} tone.")
    return persona + QWEN_DIRECT_GUARD


def _extract_caption_output(raw: str) -> str:
    match = re.search(r"<caption_output>(.*?)</caption_output>", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _exemplar_block(style: str) -> str:
    exemplars = CAPTION_EXEMPLARS.get(style, [])
    if not exemplars:
        return ""
    ex_lines = "\n".join(f'- "{e}"' for e in exemplars)
    return (
        "\nExamples of the tone sharpness expected, from OTHER videos (a balloon "
        "festival, a blacksmith) - match their quality, never reuse their "
        f"subjects or jokes:\n{ex_lines}\n"
    )


def _specialist_prompt(style: str, description: str) -> str:
    ex_block = _exemplar_block(style)
    return (
        f"{PERSONAS[style]}\n\n"
        "Here is a factual description of a video clip:\n\n"
        f"{description}\n\n"
        f'Write TWO different candidate captions for this video in the "{style}" '
        f"style: {STYLE_GUIDE[style]}\n"
        f"{ex_block}\n"
        "The two candidates must take clearly different angles (different detail "
        "focused on, or a different joke/framing). Each caption will be scored by a "
        "judge who watches the video: 1-5 for accuracy (every claim visibly true) and "
        "1-5 for tone fit (the style must be unmistakable, not mild). Write to earn "
        "5/5 on both. Each candidate must include at least one concrete, specific "
        "visual detail from the description, be 1-2 sentences, in English. Never "
        "mention frames, images, descriptions, or video analysis. Avoid named places, "
        "brands, or sign text unless the description says they are unmistakably "
        "legible. Respond with only a JSON object with keys \"a\" and \"b\"."
    )


def _single_shot_prompt(style: str, description: str) -> str:
    """One caption per style — same personas/exemplars/rubric as SVG specialists."""
    ex_block = _exemplar_block(style)
    return (
        f"{PERSONAS[style]}\n\n"
        "Here is a factual description of a video clip:\n\n"
        f"{description}\n\n"
        f'Write ONE caption for this video in the "{style}" style: '
        f"{STYLE_GUIDE[style]}\n"
        f"{ex_block}\n"
        "The caption will be scored by a judge who watches the video: 1-5 for "
        "accuracy (every claim visibly true) and 1-5 for tone fit (the style must "
        "be unmistakable, not mild). Write to earn 5/5 on both. Include at least "
        "one concrete, specific visual detail from the description, be 1-2 "
        "sentences, in English. Never mention frames, images, descriptions, or "
        "video analysis. Avoid named places, brands, or sign text unless the "
        "description says they are unmistakably legible. Respond with only a JSON "
        "object with key \"caption\"."
    )


def _direct_style_prompt(style: str) -> str:
    """Voice-first: frames are the only scene evidence (no prose description)."""
    ex_block = _exemplar_block(style)
    return (
        f"{PERSONAS[style]}\n\n"
        "Above are frames sampled evenly, in chronological order, from one video "
        "clip. The frames are ground truth.\n\n"
        f'Write ONE caption for this video in the "{style}" style: '
        f"{STYLE_GUIDE[style]}\n"
        f"{ex_block}\n"
        "The caption will be scored for accuracy (every claim visibly true in the "
        "frames) and tone fit (style must be unmistakable, not mild). Write to "
        "earn top marks on both. Include at least one concrete visual detail from "
        "the frames, be 1-2 sentences, in English. Never mention frames, images, "
        "or video analysis. Avoid named places, brands, or sign text unless large "
        "and unmistakably legible in the frames. Respond with only a JSON object "
        "with key \"caption\"."
    )


def _selection_prompt(description: str, candidates: dict) -> str:
    cand_block = json.dumps(candidates, indent=2)
    return (
        "Above are frames sampled evenly, in chronological order, from a video clip. "
        "Here is a factual description of the clip:\n\n"
        f"{description}\n\n"
        "For each caption style below there are two candidate captions, \"a\" and "
        f"\"b\":\n\n{cand_block}\n\n"
        "The frames are ground truth. For EACH style, choose the candidate that (1) is "
        "more accurate - every claim visibly true in the frames - and (2) has the more "
        "unmistakable, sharper execution of its style. Return the chosen caption TEXT "
        "exactly as written, one per style, in a JSON object keyed by style name. Do "
        "not rewrite, merge, or edit the captions; copy the winner verbatim."
    )


def _style_prompt(description: str, styles: list[str]) -> str:
    """Single-call multi-style prompt. Kept as the FALLBACK path (and for the demo
    app); the primary path is the per-style specialist flow in caption_video()."""
    style_lines = "\n".join(f'- "{s}": {STYLE_GUIDE[s]}' for s in styles)
    return (
        "Here is a factual description of a video clip:\n\n"
        f"{description}\n\n"
        "Write one caption for this video in EACH of the following styles:\n"
        f"{style_lines}\n\n"
        "Every caption is judged separately on two things: (1) how accurately it reflects the "
        "actual video content, and (2) how well it matches its requested tone. So each caption "
        "- including the funny ones - must name at least one concrete, specific visual detail "
        "from the description (a colour, an object, a distinguishing feature, a setting "
        "detail) rather than a generic paraphrase, and must stand alone. "
        "Avoid named places, brands, building names, or exact sign text unless the "
        "description says the text is unmistakably legible. "
        "Write in English. Do not mention frames, images, descriptions, or that "
        "this is a video analysis. Respond with only a single JSON object matching the "
        "requested schema, no other text."
    )


def _caption_schema(styles: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {s: {"type": "string"} for s in styles},
        "required": list(styles),
        "additionalProperties": False,
    }


def _extract_frames_b64(video_url: str) -> list[str]:
    """Download the clip and return base64 JPEG frames, evenly sampled, in order."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        video_path = os.path.join(tmp_dir, "clip.mp4")
        download_video(video_url, video_path)

        duration = get_duration_seconds(video_path)
        num_frames = choose_num_frames(
            duration, config.SECONDS_PER_FRAME, config.MIN_FRAMES, config.MAX_FRAMES,
        )

        frames_dir = os.path.join(tmp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        frame_paths = extract_frames(
            video_path, frames_dir,
            num_frames=num_frames, max_width=config.FRAME_MAX_WIDTH,
        )
        return [frame_to_b64(p) for p in frame_paths]


def _describe_video(video_url: str, client: CaptionClient) -> str:
    frames_b64 = _extract_frames_b64(video_url)
    return client.describe_frames(frames_b64, DESCRIBE_PROMPT.format(n=len(frames_b64)))


def describe_video(video_url: str, client: CaptionClient) -> str:
    """Return just the factual scene description (no style rewriting)."""
    return _describe_video(video_url, client)


def captions_from_description(description: str, styles: list[str],
                              client: CaptionClient) -> dict:
    """Single-call fallback: rewrite a description into one caption per style.

    Uses structured outputs, so the response is guaranteed to be valid JSON with
    exactly the requested style keys."""
    captions = client.generate_json(_style_prompt(description, styles), _caption_schema(styles))
    result = {s: str(captions.get(s, "")).strip() for s in styles}

    # An empty caption scores zero for that style — retry just the empty ones once.
    missing = [s for s in styles if not result[s]]
    if missing:
        retry = client.generate_json(_style_prompt(description, missing), _caption_schema(missing))
        for s in missing:
            result[s] = str(retry.get(s, "")).strip()

    return result


def caption_video(video_url: str, styles: list[str], client: CaptionClient) -> dict:
    """Assembly mode from config.CAPTION_ASSEMBLY."""
    frames_b64 = _extract_frames_b64(video_url)
    valid_styles = [s for s in styles if s in STYLE_GUIDE]
    assembly = (getattr(config, "CAPTION_ASSEMBLY", "qwen_direct") or "qwen_direct").strip().lower()
    print(f"[pipeline] caption_assembly={assembly} frames={len(frames_b64)}", file=sys.stderr)

    result: dict[str, str] = {}
    description = ""

    if assembly == "qwen_direct":
        generate_text = getattr(client, "generate_text", None)
        if generate_text is None:
            raise TypeError("qwen_direct requires a client with generate_text()")
        temp = float(getattr(config, "QWEN_DIRECT_TEMPERATURE", 0.7))

        def _run_qwen(s: str):
            raw = generate_text(
                frames_b64,
                _qwen_direct_prompt(s),
                system=QWEN_DIRECT_SYSTEM,
                max_tokens=400,
                temperature=temp,
            )
            caption = _extract_caption_output(raw)
            if not caption:
                print(f"[pipeline] qwen_direct missing tags for {s}: {raw[:200]!r}",
                      file=sys.stderr)
            return s, caption

        if valid_styles:
            with ThreadPoolExecutor(max_workers=len(valid_styles)) as executor:
                futures = [executor.submit(_run_qwen, s) for s in valid_styles]
                for future in futures:
                    try:
                        style, caption = future.result()
                        result[style] = caption
                    except Exception:
                        print(f"[pipeline] qwen_direct style call failed: "
                              f"{traceback.format_exc()}", file=sys.stderr)
    elif assembly == "direct":
        def _run_direct(s: str):
            payload = client.generate_json(
                _direct_style_prompt(s), SINGLE_CAPTION_SCHEMA,
                frames_b64=frames_b64, max_tokens=500,
            )
            return s, str(payload.get("caption", "")).strip()

        if valid_styles:
            with ThreadPoolExecutor(max_workers=len(valid_styles)) as executor:
                futures = [executor.submit(_run_direct, s) for s in valid_styles]
                for future in futures:
                    try:
                        style, caption = future.result()
                        result[style] = caption
                    except Exception:
                        print(f"[pipeline] direct style call failed: "
                              f"{traceback.format_exc()}", file=sys.stderr)
    else:
        description = client.describe_frames(
            frames_b64, DESCRIBE_PROMPT.format(n=len(frames_b64)),
        )
        if assembly == "single_shot":
            def _run_single(s: str):
                payload = client.generate_json(
                    _single_shot_prompt(s, description), SINGLE_CAPTION_SCHEMA,
                    frames_b64=frames_b64, max_tokens=500,
                )
                return s, str(payload.get("caption", "")).strip()

            if valid_styles:
                with ThreadPoolExecutor(max_workers=len(valid_styles)) as executor:
                    futures = [executor.submit(_run_single, s) for s in valid_styles]
                    for future in futures:
                        try:
                            style, caption = future.result()
                            result[style] = caption
                        except Exception:
                            print(f"[pipeline] single-shot specialist failed: "
                                  f"{traceback.format_exc()}", file=sys.stderr)
        else:
            # SVG 0.88: best-of-2 + selector
            def _run_specialist(s: str):
                return s, client.generate_json(
                    _specialist_prompt(s, description), CANDIDATE_SCHEMA,
                    frames_b64=frames_b64, max_tokens=800,
                )

            candidates: dict[str, dict] = {}
            if valid_styles:
                with ThreadPoolExecutor(max_workers=len(valid_styles)) as executor:
                    futures = [executor.submit(_run_specialist, s) for s in valid_styles]
                    for future in futures:
                        try:
                            style, candidate = future.result()
                            candidates[style] = candidate
                        except Exception:
                            print(f"[pipeline] specialist call failed: "
                                  f"{traceback.format_exc()}", file=sys.stderr)

            if candidates:
                sel_schema = {
                    "type": "object",
                    "properties": {s: {"type": "string"} for s in candidates},
                    "required": list(candidates),
                    "additionalProperties": False,
                }
                for attempt in (1, 2):
                    try:
                        chosen = client.generate_json(
                            _selection_prompt(description, candidates), sel_schema,
                            frames_b64=frames_b64, max_tokens=2000,
                        )
                        for s in candidates:
                            result[s] = str(chosen.get(s, "")).strip()
                        break
                    except Exception:
                        print(f"[pipeline] selection attempt {attempt} failed: "
                              f"{traceback.format_exc()}", file=sys.stderr)
                for s in candidates:
                    if not result.get(s, "").strip():
                        result[s] = str(candidates[s].get("a", "")).strip()

    missing = [s for s in styles if not result.get(s, "").strip()]
    if missing:
        if not description:
            description = client.describe_frames(
                frames_b64, DESCRIBE_PROMPT.format(n=len(frames_b64)),
            )
        fallback = captions_from_description(description, missing, client)
        for s in missing:
            result[s] = fallback.get(s, "")

    return {s: result.get(s, "") for s in styles}
