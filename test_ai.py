
import json
import sys
import os
import requests
from dotenv import load_dotenv

load_dotenv()

import brain


def save_lead(lead):
    """Send the collected customer lead to Google Sheets."""
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    secret = os.getenv("SHEETS_SECRET", "").strip()

    if not url:
        print("ERROR: SHEETS_WEBHOOK_URL is missing from .env")
        return

    if not secret:
        print("ERROR: SHEETS_SECRET is missing from .env")
        return

    payload = {
        "secret": secret,
        "channel": "terminal_test",
        "sender_id": "TEST_CHAT",
        "name": lead.get("name"),
        "phone": lead.get("phone"),
        "need": lead.get("need"),
        "details": lead.get("details", {}),
        "ready_to_buy": lead.get("ready_to_buy", "unknown"),
        "language": "unknown",
        "needs_human": False,
        "last_message": "Terminal chat test",
    }

    print("\nDEBUG: Sending lead to Google Sheets...")
    print("DEBUG: Customer:", lead.get("name"))
    print("DEBUG: Product:", lead.get("need"))

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=40
        )

        print("SHEETS HTTP STATUS:", response.status_code)
        print("SHEETS RESPONSE:", response.text[:1000])

        response.raise_for_status()

        try:
            result = response.json()
            if result.get("ok") is True:
                print("SUCCESS: Lead sent to Google Sheets!")
            else:
                print("WARNING: The server did not confirm saving.")
        except ValueError:
            print("WARNING: Response was not valid JSON.")

    except requests.RequestException as e:
        print("ERROR saving lead:", e)


def run_file():
    """Run the messages from test_messages.txt."""
    try:
        with open("test_messages.txt", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                print("\nCLIENT :", line)

                try:
                    r = brain.ask_ai([], line, None)
                    print("BOT    :", r["reply"])
                    print("LANG   :", r["language"], "| handoff:", r["handoff"])
                    print("LEAD   :", json.dumps(
                        r["lead"], ensure_ascii=False
                    ))
                except Exception as e:
                    print("ERROR:", e)

    except FileNotFoundError:
        print("ERROR: test_messages.txt was not found.")


def chat():
    """Chat with the AI and save the collected lead when finished."""
    history = []
    lead = {}

    print("Chat test. Type a message (empty line to stop).")

    while True:
        try:
            text = input("\nCLIENT : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nChat interrupted.")
            break

        if not text:
            break

        try:
            r = brain.ask_ai(history, text, lead)
        except Exception as e:
            print("AI ERROR:", e)
            continue

        history += [
            {"role": "user", "content": text},
            {"role": "assistant", "content": r["reply"]}
        ]

        lead = brain.merge_lead(lead, r["lead"])

        print("BOT    :", r["reply"])
        print(
            "LEAD   :",
            json.dumps(lead, ensure_ascii=False),
            "| handoff:",
            r["handoff"]
        )

    # Save the lead after the conversation ends.
    if lead and any(lead.get(k) for k in ("name", "phone", "need")):
        print("\nDEBUG: Final lead before saving:")
        print(json.dumps(lead, ensure_ascii=False, indent=2))
        save_lead(lead)
    else:
        print("\nNo customer lead details collected; nothing saved.")


if __name__ == "__main__":
    if "--chat" in sys.argv:
        chat()
    else:
        run_file()
