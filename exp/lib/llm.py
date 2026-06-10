"""Thin OpenAI client with a disk-backed response cache.

The cache key is a sha256 over (model, system, user, temperature, max_tokens),
so re-running the same prompt is free. The same idiom is used by
``exp/anti_unify.py`` — kept independent here so ``expB`` is self-contained.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    cached: bool


def _cache_key(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    h = hashlib.sha256()
    for part in (model, system, user, f"t={temperature}", f"n={max_tokens}"):
        h.update(part.encode())
        h.update(b"\0")
    return h.hexdigest()


class LLM:
    """OpenAI chat client with disk cache + simple retry/backoff."""

    def __init__(
        self,
        *,
        model: str = "gpt-5.2",
        cache_dir: Path,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        max_retries: int = 5,
    ) -> None:
        from openai import OpenAI  # local import: avoid hard dep at module import
        self._client = OpenAI()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> str | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        return payload.get("response")

    def _write_cache(self, key: str, system: str, user: str, response: str) -> None:
        self._cache_path(key).write_text(json.dumps(
            {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "system": system,
                "user": user,
                "response": response,
            },
            ensure_ascii=False,
            indent=2,
        ))

    def _call_with_retry(self, system: str, user: str) -> str:
        from openai import APIConnectionError, BadRequestError, RateLimitError
        delay = 1.0
        last_err: Exception | None = None
        # Newer models (gpt-5+) require max_completion_tokens; older ones use max_tokens.
        # Try max_completion_tokens first, fall back on an explicit unsupported-parameter error.
        tokens_kwarg: dict = {"max_completion_tokens": self.max_tokens}
        for _ in range(self.max_retries):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self.temperature,
                    **tokens_kwarg,
                )
                return resp.choices[0].message.content or ""
            except BadRequestError as e:
                if (e.code == "unsupported_parameter"
                        and "max_completion_tokens" in str(e)):
                    tokens_kwarg = {"max_tokens": self.max_tokens}
                    continue
                raise
            except (RateLimitError, APIConnectionError) as e:
                last_err = e
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
        raise RuntimeError(f"LLM call failed after {self.max_retries} retries: {last_err}")

    def chat(self, system: str, user: str) -> LLMResponse:
        key = _cache_key(self.model, system, user, self.temperature, self.max_tokens)
        cached = self._read_cache(key)
        if cached is not None:
            return LLMResponse(text=cached, cached=True)
        text = self._call_with_retry(system, user)
        self._write_cache(key, system, user, text)
        return LLMResponse(text=text, cached=False)
