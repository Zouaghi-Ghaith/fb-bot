"""
Compact AI brain for a Tunisian Facebook/Instagram sales bot.
Supports Groq, Mistral and Gemini.
Returns: reply, language, lead, handoff.
"""
import json
import os
import re
import requests

from business import BUSINESS_INFO

SYSTEM_PROMPT = """You are the sales assistant for a Tunisian business on Facebook/Instagram.

BUSINESS FACTS (your ONLY source; never invent products, prices, stock, delivery, or policies):
{business}

LANGUAGE — STRICT:
- Reply ONLY in French or natural Tunisian Darija.
- French customer -> French.
- Tunisian Darija Arabic script -> Tunisian Darija Arabic script.
- Tunisian Darija Arabizi -> simple Tunisian Arabizi.
- English, MSA Arabic, or another language -> French.
- Never use Moroccan/Algerian Darija or formal MSA Arabic.
- Friendly, natural and concise: usually 1–2 sentences. Ask ONE question maximum.

SALES BEHAVIOUR:
- Answer the customer's question first, then guide them naturally toward choosing or ordering.
- If they ask what is available, mention only products/services listed in BUSINESS FACTS and ask which interests them.
- If they ask for something not listed, politely explain what the business DOES offer, using only BUSINESS FACTS, and ask whether one of those options interests them. Never pretend the requested item is available.
- If BUSINESS FACTS do not confirm availability or price, say the team will confirm. Set handoff=true when human confirmation is needed.
- Do not ask again for information already provided.
- Collect naturally, one step at a time: product/service (need), preferences (size, colour, quantity, etc.), name, phone and delivery address.
- ACCEPT addresses in any language/script: Tunisian Darija, Arabizi, Arabic, French, abbreviations, landmarks or colloquial descriptions. Save the address exactly as provided; do not reject or translate it.
- If an address is genuinely unclear, ask one short clarification question.
- When enough order details are collected, briefly recap and say the team will confirm.
- ready_to_buy="yes" only if they clearly want to order now; "maybe" if interested but undecided; "no" if they decline; otherwise "unknown".
- handoff=true if the customer complains, is angry, requests a human, or asks something not covered by BUSINESS FACTS.
- Never request card details, passwords or verification codes.
- Include only information the customer stated. Keep known information unless corrected. Use null for unknown values.

KNOWN CUSTOMER INFO:
{known}

Return ONLY valid JSON with exactly these keys:
{{
  "reply": "short customer-facing reply",
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


def build_prompt(known_lead):
    return SYSTEM_PROMPT.format(
        business=BUSINESS_INFO.strip(),
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
        "secret": secret, "channel": "terminal_test", "sender_id": "TEST_CHAT",
        "name": lead.get("name"), "phone": lead.get("phone"),
        "address": lead.get("address"), "need": lead.get("need"),
        "details": lead.get("details"),
        "ready_to_buy": lead.get("ready_to_buy", "unknown"),
        "language": "unknown", "needs_human": False,
        "last_message": "Terminal chat test",
    }
    try:
        response = requests.post(url, json=payload, timeout=40)
        print("SHEETS:", response.status_code, response.text[:200])
        response.raise_for_status()
    except requests.RequestException as exc:
        print("ERROR saving lead:", exc)


def _post_json(url, headers, body, provider, timeout=60):
    try:
        response = requests.post(url, headers=headers, json=body, timeout=(10, timeout))
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(f"{provider} request timed out.") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"{provider} connection failed: {exc}") from exc
    if not response.ok:
        raise RuntimeError(f"{provider} HTTP {response.status_code}: {response.text[:1000]}")
    return response.json()


def _call_gemini(system_prompt, history, user_text):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    contents = [
        {"role": "model" if item.get("role") == "assistant" else "user",
         "parts": [{"text": str(item.get("content", ""))}]}
        for item in history
    ]
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2, "maxOutputTokens": 450,
            "responseMimeType": "application/json",
        },
    }
    result = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": key, "Content-Type": "application/json"},
        body, "Gemini",
    )
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Gemini returned no usable text. Check model, quota, and response.")


def _call_openai_compatible(provider, base_url, key, model, system_prompt, history, user_text):
    if not key:
        raise RuntimeError(f"{provider.upper()}_API_KEY is missing")
    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        role = "assistant" if item.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(item.get("content", ""))})
    messages.append({"role": "user", "content": user_text})
    result = _post_json(
        base_url,
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": model, "messages": messages, "temperature": 0.2,
         "response_format": {"type": "json_object"}},
        provider.capitalize(),
    )
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"{provider.capitalize()} returned no usable text.")


def _call_mistral(system_prompt, history, user_text):
    return _call_openai_compatible(
        "mistral", "https://api.mistral.ai/v1/chat/completions",
        os.getenv("MISTRAL_API_KEY"), os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
        system_prompt, history, user_text,
    )


def _call_groq(system_prompt, history, user_text):
    return _call_openai_compatible(
        "groq", "https://api.groq.com/openai/v1/chat/completions",
        os.getenv("GROQ_API_KEY"), os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        system_prompt, history, user_text,
    )


def ask_ai(history, user_text, known_lead=None):
    """Return reply, language, lead, handoff and provider."""
    history = (history or [])[-4:]  # Last two exchanges only; keeps token use low.
    prompt = build_prompt(known_lead)
    provider = os.getenv("AI_PROVIDER", "groq").strip().lower()
    if provider == "groq":
        raw = _call_groq(prompt, history, user_text)
    elif provider == "mistral":
        raw = _call_mistral(prompt, history, user_text)
    elif provider == "gemini":
        raw = _call_gemini(prompt, history, user_text)
    else:
        raise RuntimeError(f"Unsupported AI_PROVIDER '{provider}'. Use gemini, groq, or mistral.")

    data = _extract_json(raw)
    lead = data.get("lead") or {}
    clean_lead = {key: lead.get(key) for key in LEAD_KEYS}
    # Preserve previously collected values if the model omits them.
    for key in LEAD_KEYS:
        if clean_lead[key] in (None, "", "null") and (known_lead or {}).get(key) not in (None, "", "null"):
            clean_lead[key] = known_lead[key]
    return {
        "reply": str(data.get("reply") or "").strip(),
        "language": data.get("language") or "fr",
        "lead": clean_lead,
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
