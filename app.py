"""
Facebook Messenger (and Instagram DM) bot for testing on your own page.

Flow: customer message -> Meta webhook -> this server -> AI -> reply via Send API
      -> lead details saved to a Google Sheet (through an Apps Script web app).

Run:  python app.py        (then expose it with ngrok, see SETUP.md)
"""
import csv
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque

import requests
from dotenv import load_dotenv
from flask import Flask, abort, request

load_dotenv()

import brain  # noqa: E402  (after load_dotenv so env vars are available)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
APP_SECRET = os.getenv("APP_SECRET", "")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v23.0")
SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL", "")
SHEETS_SECRET = os.getenv("SHEETS_SECRET", "")

FALLBACK_REPLY = "Merci pour votre message ! Un conseiller va vous répondre très bientôt."
ATTACHMENT_REPLY = "Merci ! Pour le moment je comprends seulement les messages texte. Pouvez-vous écrire votre demande ?"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("bot")
app = Flask(__name__)

HISTORY = defaultdict(lambda: deque(maxlen=12))   # sender -> last messages
LEADS = {}                                        # sender -> lead details
SAVED = {}                                        # sender -> last saved signature
SEEN = deque(maxlen=1000)                         # message ids already handled
LOCK = threading.Lock()


# ------------------------------------------------------------------ Meta helpers
def graph_post(payload):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/me/messages"
    r = requests.post(url, params={"access_token": PAGE_ACCESS_TOKEN}, json=payload, timeout=20)
    if r.status_code != 200:
        log.error("Send API error %s: %s", r.status_code, r.text[:300])
    return r


def send_text(psid, text):
    graph_post({"recipient": {"id": psid}, "messaging_type": "RESPONSE",
                "message": {"text": text[:1900]}})


def typing_on(psid):
    try:
        graph_post({"recipient": {"id": psid}, "sender_action": "typing_on"})
    except Exception:
        pass


def valid_signature(raw_body, header):
    if not APP_SECRET:
        return True   # signature check is optional while testing
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


# ------------------------------------------------------------------ saving leads
def save_lead(channel, sender, lead, language, handoff, last_message):
    row = {
        "channel": channel, "sender_id": sender,
        "name": lead.get("name") or "", "phone": lead.get("phone") or "",
        "need": lead.get("need") or "", "details": lead.get("details") or "",
        "ready_to_buy": lead.get("ready_to_buy") or "unknown",
        "language": language or "", "needs_human": bool(handoff),
        "last_message": last_message[:300],
    }
    if SHEETS_WEBHOOK_URL:
        try:
            r = requests.post(SHEETS_WEBHOOK_URL, json={**row, "secret": SHEETS_SECRET}, timeout=25)
            log.info("Sheet response: %s %s", r.status_code, r.text[:120])
            if r.ok and '"ok":true' in r.text.replace(" ", ""):
                return
            log.error("Sheet did not accept the row, saving locally instead.")
        except Exception as e:
            log.error("Sheet error: %s. Saving locally instead.", e)
    new_file = not os.path.exists("leads_local.csv")
    with open("leads_local.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new_file:
            w.writeheader()
        w.writerow(row)


def should_save(lead, handoff):
    return bool(lead.get("phone")) or str(lead.get("ready_to_buy", "")).lower() in ("yes", "maybe") or handoff


# ------------------------------------------------------------------ message handling
def handle_event(event, channel):
    msg = event.get("message")
    postback = event.get("postback")

    # Echo = a message sent BY the page. If it was typed by a human in the inbox, stay silent for a while.
    if msg and msg.get("is_echo"):
        if not msg.get("app_id"):
            user = (event.get("recipient") or {}).get("id")
            if user:
                PAUSED[user] = time.time() + HUMAN_TAKEOVER_HOURS * 3600
                log.info("Human replied to %s: bot paused for %sh", user, HUMAN_TAKEOVER_HOURS)
        return

    sender = (event.get("sender") or {}).get("id")
    if not sender:
        return

    text, mid = None, None
    if msg:
        mid, text = msg.get("mid"), msg.get("text")
        if not text and msg.get("attachments"):
            if PAUSED.get(sender, 0) < time.time():
                send_text(sender, ATTACHMENT_REPLY)
            return
    elif postback:
        text = postback.get("title") or postback.get("payload")
        mid = postback.get("mid")
    if not text:
        return

    with LOCK:
        if mid and mid in SEEN:
            return
        if mid:
            SEEN.append(mid)

    if PAUSED.get(sender, 0) > time.time():
        log.info("Bot paused for %s, ignoring message.", sender)
        return

    log.info("[%s] %s: %s", channel, sender, text)
    typing_on(sender)
    try:
        result = brain.ask_ai(list(HISTORY[sender]), text, LEADS.get(sender))
        reply = result["reply"] or FALLBACK_REPLY
    except Exception as e:
        log.error("AI error: %s", e)
        send_text(sender, FALLBACK_REPLY)
        PAUSED[sender] = time.time() + 3600
        return

    send_text(sender, reply)
    log.info("[%s] bot -> %s: %s", channel, sender, reply)

    HISTORY[sender].append({"role": "user", "content": text})
    HISTORY[sender].append({"role": "assistant", "content": reply})
    LEADS[sender] = brain.merge_lead(LEADS.get(sender), result["lead"])

    if result["handoff"]:
        PAUSED[sender] = time.time() + HUMAN_TAKEOVER_HOURS * 3600

    lead = LEADS[sender]
    if should_save(lead, result["handoff"]):
        signature = json.dumps([lead, result["handoff"]], sort_keys=True, ensure_ascii=False)
        if SAVED.get(sender) != signature:
            SAVED[sender] = signature
            save_lead(channel, sender, lead, result["language"], result["handoff"], text)


# ------------------------------------------------------------------ web routes
@app.route("/", methods=["GET"])
def home():
    mode = request.args.get("hub.mode") or request.args.get("hub_mode")
    token = request.args.get("hub.verify_token") or request.args.get("hub_verify_token")
    challenge = request.args.get("hub.challenge") or request.args.get("hub_challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge or "", 200

    return "Bot is running.", 200

@app.route("/", methods=["POST"])
def root_post():
    return webhook()

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    abort(403)


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data()
    if not valid_signature(raw, request.headers.get("X-Hub-Signature-256")):
        abort(403)
    data = request.get_json(silent=True) or {}
    channel = "instagram" if data.get("object") == "instagram" else "facebook"
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            threading.Thread(target=safe_handle, args=(event, channel), daemon=True).start()
    return "EVENT_RECEIVED", 200   # answer Meta quickly; the work continues in a thread


def safe_handle(event, channel):
    try:
        handle_event(event, channel)
    except Exception:
        log.exception("Error while handling an event")


if __name__ == "__main__":
    if not PAGE_ACCESS_TOKEN or not VERIFY_TOKEN:
        print("WARNING: PAGE_ACCESS_TOKEN or VERIFY_TOKEN is empty. Check your .env file.")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
