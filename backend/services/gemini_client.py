"""Shared Gemini client — real model calls, config-driven model names."""

import asyncio
import json
import logging
import re
from typing import Any, Optional, Type

from backend.config.settings import settings
from backend.services.llm_context import effective_gemini_key, effective_grok_key

logger = logging.getLogger(__name__)


class GeminiQuotaExceeded(RuntimeError):
    """Raised when the configured Gemini key hits RESOURCE_EXHAUSTED / 429."""


def is_quota_error(exc: BaseException) -> bool:
    """True when Gemini cannot be used (quota, invalid key, or unauthenticated)."""
    msg = str(exc)
    lowered = msg.lower()
    return any(
        s in msg
        for s in (
            "RESOURCE_EXHAUSTED",
            "UNAUTHENTICATED",
            "API_KEY_INVALID",
            "PERMISSION_DENIED",
            "quota exhausted",
        )
    ) or "429" in msg or "quota" in lowered


def is_retryable_model_error(exc: BaseException) -> bool:
    """Quota, missing model, or transient Gemini failures — try the next model."""
    if is_quota_error(exc) or isinstance(exc, GeminiQuotaExceeded):
        return True
    msg = str(exc)
    lowered = msg.lower()
    return any(
        s in msg
        for s in ("NOT_FOUND", "UNAVAILABLE", "overloaded")
    ) or any(
        s in lowered
        for s in ("not found", "not supported", "unknown model", "invalid model")
    )


def _is_gemini_35_or_newer(model: str) -> bool:
    """Keep Gemini 3.5+ only. Do not invent model IDs."""
    name = (model or "").strip().lower()
    if not name.startswith("gemini-"):
        return True
    rest = name[len("gemini-"):]
    if rest.startswith("1.") or rest.startswith("2."):
        return False
    return True


def _candidate_models(preferred: Optional[str] = None) -> list:
    primary = preferred or settings.GEMINI_MODEL
    extras = (
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    )
    out = []
    for model in (primary, *extras):
        if model and model not in out and _is_gemini_35_or_newer(model):
            out.append(model)
    if not out and primary:
        out.append(primary)
    return out


def _client():
    from google import genai

    key = effective_gemini_key()
    if key:
        return genai.Client(api_key=key)
    return genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_REGION,
    )


async def _generate_content_async(client, **kwargs):
    """Run the sync Gemini SDK off the event loop so workflows can still be polled."""
    return await asyncio.to_thread(client.models.generate_content, **kwargs)


async def _grok_complete(prompt: str, *, json_mode: bool = False) -> str:
    """xAI OpenAI-compatible chat. Used only after Gemini is unavailable."""
    key = effective_grok_key()
    if not key:
        raise GeminiQuotaExceeded(
            "Gemini quota exhausted and no Grok key is configured. Add a Gemini or xAI key in Settings."
        )
    import httpx

    payload: dict = {
        "model": settings.GROK_MODEL or "grok-4-fast",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1 if json_mode else 0.2,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Grok HTTP {response.status_code}: {response.text[:400]}")
        data = response.json()
    text = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    ).strip()
    if not text:
        raise ValueError("Grok returned an empty response")
    logger.info("LLM used Grok fallback model %s", payload["model"])
    return text


def _coerce_json(text: str) -> Any:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if starts:
        start = min(starts)
        end = max(text.rfind("}"), text.rfind("]"))
        if end > start:
            text = text[start : end + 1]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


async def generate_text(prompt: str, model: Optional[str] = None) -> str:
    from google.genai import types

    last: Optional[Exception] = None
    quota_hits = 0
    for candidate in _candidate_models(model):
        try:
            client = _client()
            response = await _generate_content_async(
                client,
                model=candidate,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            text = (response.text or "").strip()
            if text:
                if candidate != (model or settings.GEMINI_MODEL):
                    logger.info("Gemini text used fallback model %s", candidate)
                return text
            last = ValueError(f"empty response from {candidate}")
        except Exception as e:
            last = e
            if is_retryable_model_error(e):
                logger.warning("Gemini model %s unavailable (%s); trying another", candidate, e)
                if is_quota_error(e) or isinstance(e, GeminiQuotaExceeded):
                    quota_hits += 1
                    if quota_hits >= 3:
                        break
                continue
            raise
    if last and is_quota_error(last):
        try:
            return await _grok_complete(prompt, json_mode=False)
        except Exception as grok_err:
            logger.warning("Grok text fallback failed: %s", grok_err)
        raise GeminiQuotaExceeded(
            "Gemini quota exhausted. Add your own key in Settings, or an xAI Grok key as fallback."
        ) from last
    try:
        return await _grok_complete(prompt, json_mode=False)
    except Exception:
        raise last or GeminiQuotaExceeded("Gemini quota exhausted. Add your own key in Settings.")


async def generate_json(prompt: str, schema: Optional[Type] = None, model: Optional[str] = None) -> Any:
    from google.genai import types

    last: Optional[Exception] = None
    quota_hits = 0
    for candidate in _candidate_models(model):
        try:
            client = _client()
            config_kwargs = {
                "response_mime_type": "application/json",
                "temperature": 0.1,
                "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
            }
            if schema is not None:
                config_kwargs["response_schema"] = schema
            response = await _generate_content_async(
                client,
                model=candidate,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = (response.text or "").strip()
            if not text:
                raise ValueError("Model returned empty JSON")
            try:
                parsed = _coerce_json(text)
            except json.JSONDecodeError:
                logger.warning("Model JSON was invalid; requesting a repaired payload")
                fixed = await generate_text(
                    "Fix this into valid JSON only. Escape quotes and newlines inside strings. "
                    "No markdown fences.\n\n" + text[:24000],
                    model=candidate,
                )
                parsed = _coerce_json(fixed)
            if candidate != (model or settings.GEMINI_MODEL):
                logger.info("Gemini JSON used fallback model %s", candidate)
            return parsed
        except Exception as e:
            last = e
            if is_retryable_model_error(e):
                logger.warning("Gemini model %s unavailable (%s); trying another", candidate, e)
                if is_quota_error(e) or isinstance(e, GeminiQuotaExceeded):
                    quota_hits += 1
                    if quota_hits >= 3:
                        break
                continue
            logger.warning("Gemini JSON failed on %s (%s); trying another", candidate, e)
            continue
    if last and (is_quota_error(last) or isinstance(last, GeminiQuotaExceeded)):
        try:
            return _coerce_json(await _grok_complete(prompt, json_mode=True))
        except Exception as grok_err:
            logger.warning("Grok JSON fallback failed: %s", grok_err)
        raise GeminiQuotaExceeded(
            "Gemini quota exhausted. Add your own key in Settings, or an xAI Grok key as fallback."
        ) from last
    try:
        return _coerce_json(await _grok_complete(prompt, json_mode=True))
    except Exception:
        raise last or ValueError("Model returned empty JSON")


async def describe_image(image_bytes: bytes, mime: str = "image/jpeg", name: str = "photo") -> str:
    """Describe an attached photo so the planner can use it."""
    from google.genai import types

    try:
        client = _client()
        part = None
        if hasattr(types.Part, "from_bytes"):
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime or "image/jpeg")
        else:
            part = types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime or "image/jpeg"))
        response = await _generate_content_async(
            client,
            model=settings.GEMINI_MODEL,
            contents=[
                part,
                (
                    f"Describe this attached photo ({name}) for an automation agent. "
                    "Extract visible text, UI labels, URLs, tables, and what the user likely wants done."
                ),
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
    except Exception as e:
        if is_quota_error(e):
            try:
                return await _grok_complete(
                    f"Describe this attached photo ({name}) for an automation agent from the filename and mime type {mime}. "
                    "The image bytes could not be sent to Gemini. Say that a photo was attached and what the user likely wants.",
                    json_mode=False,
                )
            except Exception:
                raise GeminiQuotaExceeded(
                    "Gemini quota exhausted. Add your own key in Settings."
                ) from e
        logger.warning("Image describe failed: %s", e)
        return f"A photo named {name} was attached."
    return (response.text or f"A photo named {name} was attached.").strip()
