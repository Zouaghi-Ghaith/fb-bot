
"""
AI brain for a Facebook/Instagram business bot.
Supports Gemini, Mistral, and Groq.
Returns: reply, language, lead, handoff.
"""

import json
import os
import re
import requests

from business import BUSINESS_INFO

DARIJA_GLOSSARY = """
Tunisian Darija hints (Arabizi: 3=ع, 7=ح, 9=ق, 5=خ, 2=ء):
- 3aslema / aslema / salem = hello
- chnowa / chnouwa / شنوة = what
- 9adech / 9addeh / قداش = how much
- nheb / نحب = I want
- nechri / نشري = I buy
- famma / fama / فما = is there
- mouch / mech / موش = not
- taw / tawa / توا = now
- ghodwa / غدوة = tomorrow
- barcha / برشا = a lot
- behi / باهي = good, ok
- ghali / غالي = expensive
- rkhis / رخيص = cheap
- win / وين = where
- wa9teh / وقتاش = when
- kifech / كيفاش = how
- yaatik essaha = thank you
- flous / فلوس = money
- esmi = my name is
- numrou = phone number
"""

SYSTEM_PROMPT = """You are the assistant of a small business replying to Facebook/Instagram customers.

BUSINESS INFORMATION (your ONLY source of facts):
{business}

LANGUAGE RULES
- Reply in the customer's language and script: French, MSA Arabic, Tunisian Darija Arabic, Tunisian Darija Arabizi, or English.
- For Arabizi, reply in simple Arabizi or French.
- Be friendly, polite and concise: 1-3 sentences. Ask only ONE question at a time.
{glossary}

YOUR GOAL
- Understand the customer's request.
- Collect naturally: name, phone, product/service, details (size, color, quantity, area, date, budget), and purchase readiness.
- When enough order details are collected, summarize the order and say the team will confirm.

HARD RULES
- Never invent prices, stock, addresses, delivery times, discounts, or promises.
- If business information does not answer the question, say the team will confirm and set handoff to true.
- Never request card numbers, passwords, or verification codes.
- Set handoff=true if the customer is angry, complains, requests a human, or asks something you cannot answer.
- Stay focused on the business.
- ready_to_buy is "yes" only if they clearly want to order/book now; "maybe" if interested; "no" if they decline; otherwise "unknown".
- In lead, include only information the customer stated. Use null for unknown fields and retain known information unless corrected.

KNOWN CUSTOMER INFO: {known}

Return ONLY a valid JSON object with exactly these keys:
{{
  "reply": "message to customer",
  "language": "fr" | "ar" | "darija_ar" | "darija_latin" | "en",
  "lead": {{
    "name": null,
    "phone": null,
    "need": null,
    "details": null,
    "ready_to_buy": "unknown"
  }},
  "handoff": false
}}
"""

def build_prompt(known_lead):
    return SYSTEM_PROMPT.format(
        business=BUSINESS_INFO.strip(),
        glossary=DARIJA_GLOSSARY,
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


def ask_ai(history, user_text, known_lead=None):
    """Return reply, language, lead and handoff."""
    prompt = build_prompt(known_lead)
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()

    if provider == "groq":
        raw = _call_groq(prompt, history, user_text)
    elif provider == "mistral":
        raw = _call_mistral(prompt, history, user_text)
    elif provider == "gemini":
        raw = _call_gemini(prompt, history, user_text)
    else:
        raise RuntimeError(
            f"Unsupported AI_PROVIDER '{provider}'. Use gemini, groq, or mistral."
        )

    data = _extract_json(raw)
    lead = data.get("lead") or {}

    return {
        "reply": str(data.get("reply") or "").strip(),
        "language": data.get("language") or "",
        "lead": {
            key: lead.get(key)
            for key in (
                "name", "phone", "need", "details", "ready_to_buy"
            )
        },
        "handoff": bool(data.get("handoff")),
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
