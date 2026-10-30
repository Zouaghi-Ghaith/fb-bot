"""
AI brain for a Facebook/Instagram business bot.
Supports Gemini, Mistral, and Groq.
Returns: reply, language, lead, handoff.

v2: Tunisian Darija + French only (non-Tunisian words are blocked and retried),
    big vocabulary (vocab.py), accepts any address / map location, cleans phone numbers.
"""

import json
import logging
import os
import re
import time

import requests

from business import BUSINESS_INFO
from vocab import (
    ADDRESS_RULES, CLARITY_RULES, LANGUAGE_RULES, PHONE_RULES,
    EXAMPLES_COMPACT, STYLE_EXAMPLES, TUNISIAN_VOCAB, VOCAB_COMPACT, find_forbidden, normalize_phone,
)

SYSTEM_PROMPT = """You are the assistant of a small Tunisian business replying to its customers on Facebook and Instagram.

BUSINESS INFORMATION (your ONLY source of facts):
{business}

{language_rules}
{clarity_rules}
YOUR GOAL
- Understand the customer's request and answer it clearly.
- Collect naturally, step by step: name, phone, address, product/service, details (size, color, quantity, date, budget), and purchase readiness.
- When enough order details are collected, summarize the order and say the team will confirm.
{address_rules}
{phone_rules}
HARD RULES
- Never invent prices, stock, addresses, delivery times, discounts, or promises.
- If the business information does not answer the question, say the team will confirm and set handoff to true.
- Never request card numbers, passwords, or verification codes.
- Set handoff=true if the customer is angry, complains, requests a human, or asks something you cannot answer.
- Stay focused on the business. Politely bring off-topic chats back to the business.
- ready_to_buy is "yes" only if they clearly want to order/book now; "maybe" if interested; "no" if they decline; otherwise "unknown".
- In lead, include only information the customer stated. Use null for unknown fields and keep known information unless the customer corrects it.

{vocab}
{examples}

KNOWN CUSTOMER INFO: {known}

Return ONLY a valid JSON object with exactly these keys:
{{
  "reply": "message to customer",
  "language": "fr" | "darija_ar" | "darija_latin",
  "lead": {{
    "name": null,
    "phone": null,
    "address": null,
    "need": null,
    "details": null,
    "ready_to_buy": "unknown"
  }},
  "handoff": false
}}
"""

LEAD_KEYS = ("name", "phone", "address", "need", "details", "ready_to_buy")


def build_prompt(known_lead, compact=False):
    return SYSTEM_PROMPT.format(
        business=BUSINESS_INFO.strip(),
        language_rules=LANGUAGE_RULES,
        clarity_rules=CLARITY_RULES,
        address_rules=ADDRESS_RULES,
        phone_rules=PHONE_RULES,
        vocab=VOCAB_COMPACT if compact else TUNISIAN_VOCAB,
        examples=EXAMPLES_COMPACT if compact else STYLE_EXAMPLES,
        known=json.dumps(known_lead or {}, ensure_ascii=False),
    )


def _extract_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise RuntimeError("AI returned invalid JSON.")


def save_lead(lead):
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    secret = os.getenv("SHEETS_SECRET", "").strip()

    if not url:
        print("ERROR: SHEETS_WEBHOOK_URL is missing")
        return

    payload = {
        "secret": secret,
        "channel": "terminal_test",
        "sender_id": "TEST_CHAT",
        "name": lead.get("name"),
        "phone": lead.get("phone"),
        "address": lead.get("address"),
        "need": lead.get("need"),
        "details": lead.get("details"),
        "ready_to_buy": lead.get("ready_to_buy", "unknown"),
        "language": "unknown",
        "needs_human": False,
        "last_message": "Terminal chat test",
    }

    try:
        response = requests.post(url, json=payload, timeout=40)
        print("SHEETS:", response.status_code, response.text[:200])
        response.raise_for_status()
    except requests.RequestException as e:
        print("ERROR saving lead:", e)


def _post_json(url, headers, body, provider, timeout=60):
    try:
        response = requests.post(
            url, headers=headers, json=body, timeout=(10, timeout)
        )
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(f"{provider} request timed out.") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"{provider} connection failed: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"{provider} HTTP {response.status_code}: {response.text[:1000]}"
        )
    return response.json()


def _call_gemini(system_prompt, history, user_text):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    contents = [
        {
            "role": "user" if item["role"] == "user" else "model",
            "parts": [{"text": item["content"]}],
        }
        for item in history
    ]
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    result = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        },
        body,
        "Gemini",
    )

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            "Gemini returned no usable text. Check its response and quota."
        )


def _call_openai_compatible(provider, base_url, key, model,
                            system_prompt, history, user_text):
    if not key:
        raise RuntimeError(f"{provider.upper()}_API_KEY is missing")

    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        role = "assistant" if item.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": item["content"]})
    messages.append({"role": "user", "content": user_text})

    result = _post_json(
        base_url,
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        },
        provider.capitalize(),
    )

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"{provider.capitalize()} returned no usable text.")


def _call_mistral(system_prompt, history, user_text):
    return _call_openai_compatible(
        "mistral",
        "https://api.mistral.ai/v1/chat/completions",
        os.getenv("MISTRAL_API_KEY"),
        os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
        system_prompt, history, user_text,
    )


def _call_groq(system_prompt, history, user_text):
    return _call_openai_compatible(
        "groq",
        "https://api.groq.com/openai/v1/chat/completions",
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        system_prompt, history, user_text,
    )


PROVIDERS = ("gemini", "mistral", "groq")
_COOLDOWN = {}          # provider -> time until it is skipped (after a rate-limit error)
log = logging.getLogger("bot")


def _has_key(provider):
    return bool(os.getenv(f"{provider.upper()}_API_KEY"))


def _provider_order():
    """AI_PROVIDER first, then backups. AI_FALLBACKS=auto (default) = every other provider that has a key;
    AI_FALLBACKS=none = no backup; AI_FALLBACKS=gemini,mistral = your own list."""
    first = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    setting = os.getenv("AI_FALLBACKS", "auto").strip().lower()
    if setting in ("none", "off", "no", ""):
        return [first]
    if setting == "auto":
        others = [p for p in PROVIDERS if p != first and _has_key(p)]
    else:
        others = [p.strip() for p in setting.split(",") if p.strip() and p.strip() != first]
    return [first] + others


def _use_compact(provider):
    """BRAIN_SIZE=full|compact forces a size. Default (auto): Groq gets the compact prompt because its
    free tier allows only about 8000 tokens per minute."""
    size = os.getenv("BRAIN_SIZE", "auto").strip().lower()
    if size in ("full", "compact"):
        return size == "compact"
    return provider == "groq"


def _generate(provider, prompt, history, user_text):
    if provider == "groq":
        return _call_groq(prompt, history, user_text)
    if provider == "mistral":
        return _call_mistral(prompt, history, user_text)
    if provider == "gemini":
        return _call_gemini(prompt, history, user_text)
    raise RuntimeError(
        f"Unsupported AI_PROVIDER '{provider}'. Use gemini, groq, or mistral."
    )


def _run(history, user_text, known_lead, correction=""):
    """Try the providers in order; a provider that is rate-limited is skipped for 60 seconds."""
    order = _provider_order()
    now = time.time()
    candidates = [p for p in order if _COOLDOWN.get(p, 0) <= now] or order
    errors = []
    for provider in candidates:
        prompt = build_prompt(known_lead, compact=_use_compact(provider)) + correction
        try:
            data = _extract_json(_generate(provider, prompt, history, user_text))
            return data, provider
        except Exception as e:
            msg = str(e)
            errors.append(f"{provider}: {msg[:300]}")
            log.warning("AI provider %s failed: %s", provider, msg[:300])
            if "HTTP 429" in msg or "HTTP 413" in msg:
                _COOLDOWN[provider] = time.time() + 60
    raise RuntimeError("All AI providers failed -> " + " | ".join(errors))


def ask_ai(history, user_text, known_lead=None):
    """Return reply, language, lead, handoff (and which provider answered)."""
    data, provider = _run(history, user_text, known_lead)

    # Safety net: if the reply contains Moroccan/Algerian/other words, ask once for a Tunisian rewrite.
    bad = find_forbidden(str(data.get("reply") or ""))
    if bad:
        fix = ("\n\nIMPORTANT CORRECTION: your previous answer used non-Tunisian words ("
               + ", ".join(bad) + "). Write the answer again using ONLY Tunisian Darija or French words, "
               "with the same meaning and the same JSON format.")
        try:
            retry, retry_provider = _run(history, user_text, known_lead, correction=fix)
            if not find_forbidden(str(retry.get("reply") or "")):
                data, provider = retry, retry_provider
        except Exception:
            pass   # keep the first answer if the retry fails

    lead = data.get("lead") or {}
    clean = {key: lead.get(key) for key in LEAD_KEYS}
    if clean.get("phone"):
        clean["phone"] = normalize_phone(clean["phone"])
    for key in ("name", "address", "need", "details"):
        if clean.get(key) is not None and not isinstance(clean[key], str):
            clean[key] = json.dumps(clean[key], ensure_ascii=False)   # never lose an address given as a list/dict

    return {
        "reply": str(data.get("reply") or "").strip(),
        "language": data.get("language") or "",
        "lead": clean,
        "handoff": bool(data.get("handoff")),
        "provider": provider,
    }


def merge_lead(known, new):
    """Keep existing lead data unless new non-empty information is provided."""
    result = dict(known or {})
    for key, value in (new or {}).items():
        if value in (None, "", "null"):
            continue
        if key == "ready_to_buy" and str(value).lower() == "unknown":
            continue
        result[key] = value
    return result