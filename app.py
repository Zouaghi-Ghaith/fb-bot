
"""
Facebook Messenger and Instagram DM bot.
Flow: customer message -> Meta webhook -> AI -> reply
      -> lead details saved to Google Sheets through Apps Script.
"""
import csv
import hashlib
import hmac
import json
import logging
import os
import threading
from collections import defaultdict, deque

import requests
from dotenv import load_dotenv
from flask import Flask, abort, request

load_dotenv()

import brain  # noqa: E402

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
APP_SECRET = os.getenv("APP_SECRET", "")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v23.0")
SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL", "")
SHEETS_SECRET = os.getenv("SHEETS_SECRET", "")

FALLBACK_REPLY = (
    "Merci 3al message ! Wa7ed men l'équipe bech yjawbek f a9reb wa9t 🙏"
)
ATTACHMENT_REPLY = (
    "Merci ! Taw na9ra el messages el maktoubin bark. "
    "Ektebli talabek bil ktiba min fadhlek 🙏 (Je lis seulement les messages écrits.)"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)
log = logging.getLogger("bot")
app = Flask(__name__)

HISTORY = defaultdict(lambda: deque(maxlen=12))
LEADS = {}
SAVED = {}
SEEN = deque(maxlen=1000)
LOCK = threading.Lock()


# ------------------------------------------------------------------
# Meta helpers
# ------------------------------------------------------------------

def graph_post(payload):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/me/messages"
    try:
        response = requests.post(
            url,
            params={"access_token": PAGE_ACCESS_TOKEN},
            json=payload,
            timeout=20
        )
        if response.status_code != 200:
            log.error(
                "Send API error %s: %s",
                response.status_code,
                response.text[:300]
            )
        return response
    except requests.RequestException:
        log.exception("Facebook Send API request failed")
        return None


def send_text(psid, text):
    return graph_post({
        "recipient": {"id": psid},
        "messaging_type": "RESPONSE",
        "message": {"text": text[:1900]}
    })


def typing_on(psid):
    graph_post({
        "recipient": {"id": psid},
        "sender_action": "typing_on"
    })


def valid_signature(raw_body, header):
    if not APP_SECRET:
        return True  # Optional during testing

    if not header or not header.startswith("sha256="):
        return False

    expected = hmac.new(
        APP_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, header.split("=", 1)[1])


# ------------------------------------------------------------------
# Save leads to Google Sheets
# ------------------------------------------------------------------

def save_lead(channel, sender, lead, language, handoff, last_message):
    row = {
        "channel": channel,
        "sender_id": sender,
        "name": lead.get("name") or "",
        "phone": lead.get("phone") or "",
        "address": lead.get("address") or "",
        "need": lead.get("need") or "",
        "details": lead.get("details") or "",
        "ready_to_buy": lead.get("ready_to_buy") or "unknown",
        "language": language or "",
        "needs_human": bool(handoff),
        "last_message": last_message[:300],
    }

    if SHEETS_WEBHOOK_URL:
        try:
            response = requests.post(
                SHEETS_WEBHOOK_URL,
                json={**row, "secret": SHEETS_SECRET},
                timeout=25
            )
            log.info(
                "Sheet response: %s %s",
                response.status_code,
                response.text[:120]
            )

            if (
                response.ok
                and '"ok":true' in response.text.replace(" ", "")
            ):
                return

            log.error("Google Sheets did not accept the row.")

        except Exception:
            log.exception("Google Sheets request failed.")

    new_file = not os.path.exists("leads_local.csv")
    with open(
        "leads_local.csv",
        "a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def should_save(lead, handoff):
    return (
        bool(lead.get("phone"))
        or bool(lead.get("address"))
        or str(lead.get("ready_to_buy", "")).lower() in ("yes", "maybe")
        or handoff
    )


# ------------------------------------------------------------------
# Handle incoming messages — NO PAUSE SYSTEM
# ------------------------------------------------------------------

def describe_location(msg):
    """If the customer shared a map location (pin or maps link), return text the AI reads as a valid address."""
    for att in msg.get("attachments") or []:
        payload = att.get("payload") or {}
        url = att.get("url") or payload.get("url") or ""
        title = att.get("title") or ""
        coords = payload.get("coordinates") or {}

        if att.get("type") == "location" and coords:
            parts = [f"{coords.get('lat')},{coords.get('long')}"]
        elif att.get("type") == "fallback" and (
            "maps" in url.lower() or "location" in title.lower()
        ):
            parts = []
        else:
            continue

        if title:
            parts.append(title)
        if url:
            parts.append(url)
        return "[Customer shared a map location: " + " | ".join(parts) + "]"

    return None


def handle_event(event, channel):
    msg = event.get("message")
    postback = event.get("postback")

    # Ignore messages sent by the page itself.
    # This prevents the bot from replying to its own messages.
    if msg and msg.get("is_echo"):
        return

    sender = (event.get("sender") or {}).get("id")
    if not sender:
        return

    text, mid = None, None

    if msg:
        mid = msg.get("mid")
        text = msg.get("text")

        # A shared map location counts as a valid address.
        location_text = describe_location(msg)
        if location_text:
            text = f"{text}\n{location_text}" if text else location_text

        elif not text and msg.get("attachments"):
            send_text(sender, ATTACHMENT_REPLY)
            return

    elif postback:
        text = postback.get("title") or postback.get("payload")
        mid = postback.get("mid")

    if not text:
        return

    # Avoid processing the same Meta message more than once.
    with LOCK:
        if mid and mid in SEEN:
            return
        if mid:
            SEEN.append(mid)

    log.info("[%s] %s: %s", channel, sender, text)

    typing_on(sender)

    try:
        result = brain.ask_ai(
            list(HISTORY[sender]),
            text,
            LEADS.get(sender)
        )
        reply_text = result.get("reply") or FALLBACK_REPLY

    except Exception:
        log.exception("AI error")
        send_text(sender, FALLBACK_REPLY)
        return

    send_text(sender, reply_text)
    log.info("[%s] bot -> %s: %s", channel, sender, reply_text)

    HISTORY[sender].append({
        "role": "user",
        "content": text
    })
    HISTORY[sender].append({
        "role": "assistant",
        "content": reply_text
    })

    LEADS[sender] = brain.merge_lead(
        LEADS.get(sender),
        result["lead"]
    )

    # Handoff is still recorded, but never pauses the bot.
    lead = LEADS[sender]
    handoff = result.get("handoff", False)

    if should_save(lead, handoff):
        signature = json.dumps(
            [lead, handoff],
            sort_keys=True,
            ensure_ascii=False
        )

        if SAVED.get(sender) != signature:
            SAVED[sender] = signature
            save_lead(
                channel,
                sender,
                lead,
                result.get("language", ""),
                handoff,
                text
            )


# ------------------------------------------------------------------
# Webhook routes
# ------------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    mode = request.args.get("hub.mode") or request.args.get("hub_mode")
    token = (
        request.args.get("hub.verify_token")
        or request.args.get("hub_verify_token")
    )
    challenge = (
        request.args.get("hub.challenge")
        or request.args.get("hub_challenge")
    )

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge or "", 200

    return "Bot is running.", 200


@app.route("/", methods=["POST"])
def root_post():
    return webhook()


@app.route("/webhook", methods=["GET"])
def verify():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge", ""), 200

    abort(403)


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data()

    if not valid_signature(
        raw,
        request.headers.get("X-Hub-Signature-256")
    ):
        abort(403)

    data = request.get_json(silent=True) or {}
    channel = (
        "instagram"
        if data.get("object") == "instagram"
        else "facebook"
    )

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            threading.Thread(
                target=safe_handle,
                args=(event, channel),
                daemon=True
            ).start()

    return "EVENT_RECEIVED", 200


def safe_handle(event, channel):
    try:
        handle_event(event, channel)
    except Exception:
        log.exception("Error while handling an event")


if __name__ == "__main__":
    if not PAGE_ACCESS_TOKEN or not VERIFY_TOKEN:
        print(
            "WARNING: PAGE_ACCESS_TOKEN or VERIFY_TOKEN is empty. "
            "Check your environment variables."
        )

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000"))
    )
