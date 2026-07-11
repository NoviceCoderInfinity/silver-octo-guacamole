"""Deterministic caption cleanup for graded output (no model calls)."""
from __future__ import annotations
import re

META_PATTERNS = [
    re.compile(r"(?i)\b(in this (frame|image|video|clip)|as (seen|shown) in the (frames|images)|based on the (description|frames))\b[^.?!]*[.?!]?"),
    re.compile(r"(?i)\b(the (video|clip) (shows|depicts)|looking at the frames)\b[^.?!]*[.?!]?"),
]
TECH_IN_NONTECH = re.compile(
    r"(?i)\b(cpu|gpu|ram|api|json|http|wifi|wi-fi|server|deploy|docker|kubernetes|git|commit|bug|debug|compile|latency|bandwidth|algorithm|neural|llm|ai model|machine learning|codebase|pull request|merge conflict)\b"
)

def clean_caption(style: str, text: str) -> str:
    if not text:
        return text
    out = text.strip()
    for pat in META_PATTERNS:
        out = pat.sub("", out).strip()
    if style == "humorous_non_tech" and TECH_IN_NONTECH.search(out):
        parts = re.split(r"(?<=[.!?])\s+", out)
        kept = [p for p in parts if p and not TECH_IN_NONTECH.search(p)]
        out = " ".join(kept).strip() if kept else out
    out = re.sub(r"\s+", " ", out).strip()
    return out or text.strip()

def clean_captions(captions: dict) -> dict:
    return {s: clean_caption(s, c) for s, c in captions.items()}
