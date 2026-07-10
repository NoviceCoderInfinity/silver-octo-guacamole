"""Arush 0.87 lean pipeline core, with hooks for novel arms.

Byte-compatible with friend main's specialist+selection flow when hooks are unused.
Kept inside this repo so experiments never mutate Arush's tree.
"""
from __future__ import annotations

import json
import sys
import traceback
from typing import Callable

import config
from llm_client import ClaudeClient

# Re-export style constants matching Arush's pipeline.
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

VERIFIABILITY_RULES = (
    "HARD VERIFIABILITY RULES (accuracy outranks wit): "
    "Every claim must be checkable from the main subject and its central action. "
    "Do NOT mention background colours, object counts, fleeting single-frame details, "
    "weather labels like 'early evening' unless unmistakable, dew/moisture, or anything "
    "a strict judge could mark unverifiable. Prefer a plainer true joke over a flashier "
    "shaky one."
)


def specialist_prompt(style: str, description: str, *, verifiability: bool = False) -> str:
    exemplars = CAPTION_EXEMPLARS.get(style, [])
    ex_block = ""
    if exemplars:
        ex_lines = "\n".join(f'- "{e}"' for e in exemplars)
        ex_block = (
            "\nExamples of the tone sharpness expected, from OTHER videos (a balloon "
            "festival, a blacksmith) - match their quality, never reuse their "
            f"subjects or jokes:\n{ex_lines}\n"
        )
    extra = f"\n{VERIFIABILITY_RULES}\n" if verifiability else ""
    return (
        f"{PERSONAS[style]}\n\n"
        "Here is a factual description of a video clip:\n\n"
        f"{description}\n\n"
        f'Write TWO different candidate captions for this video in the "{style}" '
        f"style: {STYLE_GUIDE[style]}\n"
        f"{ex_block}{extra}\n"
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


def selection_prompt(description: str, candidates: dict, *, verifiability: bool = False) -> str:
    cand_block = json.dumps(candidates, indent=2)
    extra = (
        " Accuracy outranks flash: reject any candidate with an unverifiable flourish "
        "(background colour, count, fleeting detail) even if funnier.\n"
        if verifiability else ""
    )
    return (
        "Above are frames sampled evenly, in chronological order, from a video clip. "
        "Here is a factual description of the clip:\n\n"
        f"{description}\n\n"
        "For each caption style below there are two candidate captions, \"a\" and "
        f"\"b\":\n\n{cand_block}\n\n"
        "The frames are ground truth. For EACH style, choose the candidate that (1) is "
        "more accurate - every claim visibly true in the frames - and (2) has the more "
        "unmistakable, sharper execution of its style."
        f"{extra}"
        "Return the chosen caption TEXT exactly as written, one per style, in a JSON "
        "object keyed by style name. Do not rewrite, merge, or edit the captions; copy "
        "the winner verbatim."
    )


def style_prompt(description: str, styles: list[str]) -> str:
    style_lines = "\n".join(f'- "{s}": {STYLE_GUIDE[s]}' for s in styles)
    return (
        "Here is a factual description of a video clip:\n\n"
        f"{description}\n\n"
        "Write one caption for this video in EACH of the following styles:\n"
        f"{style_lines}\n\n"
        "Every caption is judged separately on two things: (1) how accurately it reflects the "
        "actual video content, and (2) how well it matches its requested tone. So each caption "
        "- including the funny ones - must name at least one concrete, specific visual detail "
        "from the description rather than a generic paraphrase, and must stand alone. "
        "Avoid named places, brands, building names, or exact sign text unless the "
        "description says the text is unmistakably legible. "
        "Write in English. Do not mention frames, images, descriptions, or that "
        "this is a video analysis. Respond with only a single JSON object matching the "
        "requested schema, no other text."
    )


def caption_schema(styles: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {s: {"type": "string"} for s in styles},
        "required": list(styles),
        "additionalProperties": False,
    }


def captions_from_description(description: str, styles: list[str], client: ClaudeClient) -> dict:
    captions = client.generate_json(style_prompt(description, styles), caption_schema(styles))
    result = {s: str(captions.get(s, "")).strip() for s in styles}
    missing = [s for s in styles if not result[s]]
    if missing:
        retry = client.generate_json(style_prompt(description, missing), caption_schema(missing))
        for s in missing:
            result[s] = str(retry.get(s, "")).strip()
    return result


def run_specialists_and_select(
    description: str,
    styles: list[str],
    frames_b64: list[str],
    client: ClaudeClient,
    *,
    verifiability: bool = False,
    select_fn: Callable | None = None,
) -> dict[str, str]:
    """Arush specialist+selection core. select_fn overrides Claude selection if provided."""
    candidates: dict[str, dict] = {}
    for s in styles:
        if s not in STYLE_GUIDE:
            continue
        try:
            candidates[s] = client.generate_json(
                specialist_prompt(s, description, verifiability=verifiability),
                CANDIDATE_SCHEMA,
                max_tokens=800,
            )
        except Exception:
            print(f"[exp] specialist failed {s}: {traceback.format_exc()}", file=sys.stderr)

    result: dict[str, str] = {}
    if candidates:
        sel_schema = {
            "type": "object",
            "properties": {s: {"type": "string"} for s in candidates},
            "required": list(candidates),
            "additionalProperties": False,
        }
        if select_fn is not None:
            try:
                chosen = select_fn(description, candidates, frames_b64, sel_schema)
                for s in candidates:
                    result[s] = str(chosen.get(s, "")).strip()
            except Exception:
                print(f"[exp] custom select failed: {traceback.format_exc()}", file=sys.stderr)
        else:
            for attempt in (1, 2):
                try:
                    chosen = client.generate_json(
                        selection_prompt(description, candidates, verifiability=verifiability),
                        sel_schema,
                        frames_b64=frames_b64,
                        max_tokens=2000,
                    )
                    for s in candidates:
                        result[s] = str(chosen.get(s, "")).strip()
                    break
                except Exception:
                    print(f"[exp] selection attempt {attempt} failed: {traceback.format_exc()}",
                          file=sys.stderr)
        for s in candidates:
            if not result.get(s, "").strip():
                result[s] = str(candidates[s].get("a", "")).strip()

    missing = [s for s in styles if not result.get(s, "").strip()]
    if missing:
        fallback = captions_from_description(description, missing, client)
        for s in missing:
            result[s] = fallback.get(s, "")
    return {s: result.get(s, "") for s in styles}


def make_claude() -> ClaudeClient:
    return ClaudeClient(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL_ID)
