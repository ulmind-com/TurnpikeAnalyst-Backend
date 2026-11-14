"""One way to talk to a language model, across several vendors.

The programme holds keys for Gemini, OpenAI, OpenRouter, Groq and Anthropic.
Rather than tying each feature to one vendor, every call names an ordered
*chain* of providers and the first one that answers wins. A vendor being
rate limited, out of credit or simply down then costs a retry rather than a
failed submission.

Three transports cover all five vendors:

* Gemini      — generateContent. Not the Interactions API: on this
  project that endpoint accepts a request and never answers.
* OpenAI-compatible — OpenAI, OpenRouter and Groq all speak
  `POST /chat/completions` with the same body, so they differ only by base
  URL and key.
* Anthropic   — the Messages API.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# Deliberately not generous. A chain is only resilient if a hung provider
# gives up quickly enough for the next one to be tried while the caller is
# still waiting — a 180s stall on the first provider is indistinguishable
# from an outage to the person on the other end.
TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0)
# Gemini's free tier on this project answers a trivial prompt in 150-210
# seconds, so its ceiling is its own. It is last in the review chain, where
# the work is already detached from the request, and is not in the chatbot
# chain at all.
GEMINI_TIMEOUT = httpx.Timeout(connect=10.0, read=420.0, write=30.0, pool=10.0)

# Smallest ceiling that still leaves room for a visible answer after a
# reasoning model has finished thinking.
REASONING_FLOOR = 1024


class LLMError(RuntimeError):
    """A single provider failed. The caller may still try the next one."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class AllProvidersFailed(RuntimeError):
    """Every provider in the chain failed; the message lists each reason."""


@dataclass(frozen=True)
class Provider:
    name: str
    api_key: str
    model: str


# Default model per provider. Overridable per call.
DEFAULT_MODELS = {
    "gemini": "gemini-3.8-flash",
    "openai": "gpt-4o-mini",
    # "openrouter/free" is their auto-router across whatever free models are
    # currently served. Pinning one slug means the chain breaks the day that
    # model is retired, which is exactly what happened to the last one.
    "openrouter": "openrouter/free",
    # Confirmed against GET /models on this account.
    "groq": "openai/gpt-oss-120b",
    "anthropic": "claude-opus-5-5",
}

# OpenAI, OpenRouter and Groq share a request shape; only these differ.
OPENAI_COMPATIBLE = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
}


def _key_for(name: str) -> str:
    return {
        "gemini": settings.GEMINI_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
    }.get(name, "")


def build_chain(names: List[str], *, model_override: str = "") -> List[Provider]:
    """Resolve provider names into usable providers.

    Names without a configured key are dropped silently: a chain is a list
    of preferences, and an absent key means "not available here", not an
    error worth surfacing on every call.

    `model_override` applies only to the FIRST provider. Model names are
    vendor-specific — handing Groq's model id to Gemini produces a 404, not
    a fallback — so the rest of the chain keeps its own defaults.
    """
    chain: List[Provider] = []
    for name in names:
        key = _key_for(name)
        if not key:
            continue
        is_primary = not chain
        chain.append(
            Provider(
                name=name,
                api_key=key,
                model=(model_override if (is_primary and model_override) else DEFAULT_MODELS.get(name, "")),
            )
        )
    return chain


def extract_json(text: str) -> Dict[str, Any]:
    """Pull a JSON object out of a model reply.

    Models wrap JSON in a fenced block even when told not to, so the fence
    is stripped rather than failing the caller over formatting.
    """
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("The model returned no JSON object.")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"The model returned malformed JSON: {exc}") from exc


# --------------------------------------------------------------------------
# Transports
# --------------------------------------------------------------------------

async def _complete_openai_compatible(
    provider: Provider,
    system: str,
    user: str,
    max_tokens: int,
    json_schema: Optional[Dict[str, Any]],
) -> str:
    # Reasoning models spend the budget on hidden reasoning tokens before
    # they emit a single visible character, so a small ceiling comes back as
    # finish_reason "length" with empty content. The floor is what makes a
    # short answer actually arrive.
    body: Dict[str, Any] = {
        "model": provider.model,
        "max_tokens": max(max_tokens, REASONING_FLOOR),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_schema:
        # Every one of these three accepts json_object; only some accept a
        # full schema, so the prompt also states the shape as a backstop.
        body["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    if provider.name == "openrouter":
        # OpenRouter asks callers to identify the app; these appear on the
        # account's activity page and are not used for anything else.
        headers["HTTP-Referer"] = "https://turnpikeanalyst.com"
        headers["X-Title"] = "Turnpike Analyst"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{OPENAI_COMPATIBLE[provider.name]}/chat/completions",
            json=body,
            headers=headers,
        )

    if response.status_code in (401, 403):
        raise LLMError(f"{provider.name} rejected the API key.", retryable=False)
    if response.status_code == 429:
        raise LLMError(f"{provider.name} is rate limited.")
    if response.status_code >= 400:
        raise LLMError(f"{provider.name} returned {response.status_code}: {response.text[:200]}")

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise LLMError(f"{provider.name} returned no choices.")

    choice = choices[0]
    content = (choice.get("message") or {}).get("content") or ""
    if not content.strip() and choice.get("finish_reason") == "length":
        # Distinguishable from a real outage: the budget ran out inside the
        # model's reasoning. Worth saying so rather than reporting "empty".
        raise LLMError(
            f"{provider.name} exhausted its token budget before answering "
            f"(model {provider.model} reasons before it writes)."
        )
    return content


async def _complete_anthropic(
    provider: Provider,
    system: str,
    user: str,
    max_tokens: int,
    json_schema: Optional[Dict[str, Any]],
) -> str:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": provider.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            headers={
                "x-api-key": provider.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    if response.status_code in (401, 403):
        raise LLMError("anthropic rejected the API key.", retryable=False)
    if response.status_code == 429:
        raise LLMError("anthropic is rate limited.")
    if response.status_code >= 400:
        raise LLMError(f"anthropic returned {response.status_code}: {response.text[:200]}")

    blocks = response.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


async def _complete_gemini(
    provider: Provider,
    system: str,
    user: str,
    max_tokens: int,
    json_schema: Optional[Dict[str, Any]],
) -> str:
    """Gemini over generateContent.

    Not the Interactions API and not the SDK: on this project the
    Interactions endpoint accepts the request and then never responds,
    while generateContent answers correctly. Plain HTTP also keeps every
    transport in this module the same shape.

    Measured latency on the free tier is 230-290 seconds for a trivial
    prompt, with intermittent 503s, which is why Gemini sits last in the
    review chain and is absent from the chatbot chain entirely — a chat
    widget cannot wait two minutes.
    """
    body: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"maxOutputTokens": max(max_tokens, REASONING_FLOOR)},
    }
    if json_schema:
        # Constraining the reply to a schema removes malformed JSON as a
        # failure mode entirely.
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = _to_gemini_schema(json_schema)

    try:
        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{provider.model}:generateContent",
                json=body,
                headers={"x-goog-api-key": provider.api_key, "Content-Type": "application/json"},
            )
    except httpx.TimeoutException as exc:
        raise LLMError("gemini did not answer in time.") from exc

    if response.status_code in (401, 403):
        raise LLMError("gemini rejected the API key.", retryable=False)
    if response.status_code in (429, 503):
        raise LLMError(f"gemini is overloaded or rate limited ({response.status_code}).")
    if response.status_code >= 400:
        raise LLMError(f"gemini returned {response.status_code}: {response.text[:200]}")

    candidates = response.json().get("candidates") or []
    if not candidates:
        raise LLMError("gemini returned no candidates.")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts)


def _to_gemini_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Strip the JSON Schema keywords Gemini's responseSchema rejects.

    It accepts a subset — notably not `additionalProperties`, and `enum`
    only on strings — so an unsupported keyword is dropped rather than
    failing the whole request.
    """
    allowed = {"type", "properties", "items", "required", "enum", "description", "nullable"}
    if not isinstance(schema, dict):
        return schema
    cleaned: Dict[str, Any] = {}
    for key, value in schema.items():
        if key not in allowed:
            continue
        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {k: _to_gemini_schema(v) for k, v in value.items()}
        elif key == "items":
            cleaned[key] = _to_gemini_schema(value)
        else:
            cleaned[key] = value
    return cleaned


TRANSPORTS = {
    "gemini": _complete_gemini,
    "anthropic": _complete_anthropic,
    "openai": _complete_openai_compatible,
    "openrouter": _complete_openai_compatible,
    "groq": _complete_openai_compatible,
}


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

async def complete(
    chain: List[Provider],
    *,
    system: str,
    user: str,
    max_tokens: int = 4000,
    json_schema: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Run the chain until one provider answers.

    Returns the reply text and the provider that produced it, so callers can
    record which model actually did the work. Raises AllProvidersFailed only
    when every provider has been tried.
    """
    if not chain:
        raise AllProvidersFailed(
            "No AI provider is configured. Set at least one provider API key."
        )

    failures: List[str] = []
    for provider in chain:
        transport = TRANSPORTS.get(provider.name)
        if not transport:
            failures.append(f"{provider.name}: unknown provider")
            continue
        try:
            text = await transport(provider, system, user, max_tokens, json_schema)
            if not text.strip():
                raise LLMError(f"{provider.name} returned an empty response.")
            if provider is not chain[0]:
                logger.info("LLM call fell through to %s", provider.name)
            return text, provider.name
        except LLMError as exc:
            logger.warning("Provider %s failed: %s", provider.name, exc)
            failures.append(f"{provider.name}: {exc}")
        except Exception as exc:  # noqa: BLE001 — one vendor must not end the chain
            logger.warning("Provider %s raised %s: %s", provider.name, type(exc).__name__, exc)
            failures.append(f"{provider.name}: {type(exc).__name__}: {str(exc)[:120]}")

    raise AllProvidersFailed("; ".join(failures))
