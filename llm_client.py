"""LLM clients for the captioning pipeline (vision description + styled-caption JSON)."""
import json
import random
import sys
import time

import anthropic
from openai import OpenAI


def _content_of(response) -> str:
    content = response.choices[0].message.content
    if content is None:
        return ""
    return content.strip()


def _fireworks_with_retries(call, *, label: str, attempts: int = 6):
    delay = 1.5
    last = None
    for i in range(attempts):
        try:
            return call()
        except Exception as e:
            last = e
            msg = str(e).lower()
            retryable = any(
                x in msg for x in ("429", "rate", "timeout", "503", "502", "500", "overloaded")
            )
            if not retryable or i == attempts - 1:
                break
            sleep_for = delay + random.uniform(0, 0.5)
            print(
                f"[llm] {label} retry {i + 1}/{attempts - 1} after {sleep_for:.1f}s "
                f"({type(e).__name__})",
                file=sys.stderr,
            )
            time.sleep(sleep_for)
            delay = min(delay * 1.7, 20.0)
    raise last


class FireworksClient:
    def __init__(self, api_key: str, model_id: str, base_url: str, timeout: float = 120.0):
        self.model_id = model_id
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def describe_frames(self, frames_b64: list[str], prompt: str, max_tokens: int = 1024,
                        temperature: float | None = None) -> str:
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

        response = _fireworks_with_retries(_call, label="fireworks.generate_text")
        return _content_of(response)

    def generate_json(self, prompt: str, schema: dict, frames_b64: list[str] | None = None,
                      max_tokens: int = 1024, temperature: float | None = None) -> dict:
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

        response = _fireworks_with_retries(_call, label="fireworks.generate_json")
        return json.loads(_content_of(response))


def _text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text").strip()


class ClaudeClient:
    def __init__(self, api_key: str, model_id: str, timeout: float = 120.0):
        self.model_id = model_id
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=2)

    def describe_frames(self, frames_b64: list[str], prompt: str, max_tokens: int = 1024,
                        temperature: float | None = None) -> str:
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
