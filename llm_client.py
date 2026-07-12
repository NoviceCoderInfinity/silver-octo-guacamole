"""LLM clients for the captioning pipeline (vision description + styled-caption JSON).

Fireworks exposes an OpenAI-compatible Chat Completions endpoint, so this wraps the
official `openai` SDK pointed at Fireworks' base URL. The vision models available on
Fireworks (Kimi K2) are reasoning models by default: left alone they burn hundreds to
thousands of completion tokens drafting/second-guessing an answer before writing it,
which both slows down every call and risks truncating the response (mid-thought) before
`max_tokens` is reached. Passing `reasoning_effort="none"` turns that off, so `content` is
the direct answer with no chain-of-thought preamble to strip.
"""
import json
import random
import sys
import time

import anthropic
from openai import APIStatusError, OpenAI, RateLimitError


def _content_of(response) -> str:
    return response.choices[0].message.content.strip()


def _with_retries(call, *, label: str, attempts: int = 6):
    """Retry Fireworks calls on 429/5xx. Credits left ≠ rate-limit headroom."""
    delay = 1.5
    last_exc = None
    for i in range(attempts):
        try:
            return call()
        except RateLimitError as e:
            last_exc = e
        except APIStatusError as e:
            if e.status_code not in (429, 500, 502, 503, 504):
                raise
            last_exc = e
        if i == attempts - 1:
            break
        sleep_for = delay + random.uniform(0, 0.5)
        print(
            f"[llm] {label} retry {i + 1}/{attempts - 1} after {sleep_for:.1f}s "
            f"({type(last_exc).__name__})",
            file=sys.stderr,
        )
        time.sleep(sleep_for)
        delay = min(delay * 2, 20.0)
    raise last_exc


class FireworksClient:
    def __init__(self, api_key: str, model_id: str, base_url: str, timeout: float = 120.0):
        self.model_id = model_id
        # SDK retries are shallow; we add explicit 429 backoff above.
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)

    def describe_frames(self, frames_b64: list[str], prompt: str, max_tokens: int = 1024,
                        temperature: float | None = None) -> str:
        """Send JPEG frames (raw base64, chronological order) plus a prompt; return text."""
        return self.generate_text(
            frames_b64, prompt, max_tokens=max_tokens, temperature=temperature,
        )

    def generate_text(
        self,
        frames_b64: list[str],
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
    ) -> str:
        """Multimodal chat completion; optional system prompt (Qwen-direct path)."""
        content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            for b64 in frames_b64
        ]
        content.append({"type": "text", "text": prompt})
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        kwargs = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "reasoning_effort": "none",
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        def _call():
            return self.client.chat.completions.create(**kwargs)

        response = _with_retries(_call, label="fireworks.generate_text")
        return _content_of(response)

    def generate_json(self, prompt: str, schema: dict, frames_b64: list[str] | None = None,
                      max_tokens: int = 1024, temperature: float | None = None) -> dict:
        """Generate a JSON object guaranteed to match `schema` (structured outputs).

        If `frames_b64` is given, the frames are attached as image content alongside the
        prompt (used by judge.py to score captions directly against the source video)."""
        if frames_b64:
            content = [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                for b64 in frames_b64
            ]
            content.append({"type": "text", "text": prompt})
        else:
            content = prompt
        kwargs = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "reasoning_effort": "none",
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "Response", "schema": schema},
            },
            "messages": [{"role": "user", "content": content}],
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        def _call():
            return self.client.chat.completions.create(**kwargs)

        response = _with_retries(_call, label="fireworks.generate_json")
        return json.loads(_content_of(response))


def _text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text").strip()


class ClaudeClient:
    """Claude/Sonnet backend for the captioning pipeline (non-qwen assemblies)."""

    def __init__(self, api_key: str, model_id: str, timeout: float = 120.0):
        self.model_id = model_id
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=3)

    def describe_frames(self, frames_b64: list[str], prompt: str, max_tokens: int = 1024,
                        temperature: float | None = None) -> str:
        """Send JPEG frames (raw base64, chronological order) plus a prompt; return text."""
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}
            for b64 in frames_b64
        ]
        content.append({"type": "text", "text": prompt})
        kwargs = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = self.client.messages.create(**kwargs)
        return _text_of(response)

    def generate_json(self, prompt: str, schema: dict, frames_b64: list[str] | None = None,
                      max_tokens: int = 1024, temperature: float | None = None) -> dict:
        """Generate a JSON object matching `schema`."""
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}
            for b64 in (frames_b64 or [])
        ]
        content.append({"type": "text", "text": prompt})
        kwargs = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
            "messages": [{"role": "user", "content": content}],
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = self.client.messages.create(**kwargs)
        return json.loads(_text_of(response))


class ClaudeJudgeClient(ClaudeClient):
    """Claude backend for judge.py."""
