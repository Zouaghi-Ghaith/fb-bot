"""
Test ONLY the Google Sheet connection (no Facebook, no AI).

  python test_sheet.py

It sends one fake lead to your Apps Script web app. If it works, a row appears in your Google Sheet.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
secret = os.getenv("SHEETS_SECRET", "").strip()

if not url:
    raise SystemExit("SHEETS_WEBHOOK_URL is empty in .env. Paste the Web app URL (ends with /exec).")
if not url.endswith("/exec"):
    print("WARNING: the URL should end with /exec (not /dev). Check your deployment URL.")

payload = {
    "secret": secret, "channel": "facebook", "sender_id": "TEST123", "name": "Test Client",
    "phone": "+21622123456", "need": "sneakers", "details": "size 42, black",
    "ready_to_buy": "yes", "language": "fr", "needs_human": False, "last_message": "test from test_sheet.py",
}
r = requests.post(url, json=payload, timeout=40)
print("HTTP status:", r.status_code)
print("Answer     :", r.text[:400].replace("\n", " "))

text = r.text.lower()
if '"ok":true' in text.replace(" ", ""):
    print("\nSUCCESS. Open the Google Sheet that you used for Extensions > Apps Script: a 'Test Client' row should be there.")
elif "unauthorized" in text:
    print("\nSECRET mismatch: SECRET in the Apps Script must be identical to SHEETS_SECRET in .env. "
          "After editing the script, deploy a NEW VERSION (Deploy > Manage deployments > pencil > New version).")
elif "<html" in text or "sign in" in text:
    print("\nGoogle returned a web page, not the script answer. Redeploy as Web app with 'Who has access: Anyone', "
          "and use the URL ending in /exec.")
elif "null" in text or "getsheets" in text:
    print("\nThe script is not attached to a Google Sheet. Open YOUR sheet, then Extensions > Apps Script, and paste the "
          "code THERE (do not create it from script.google.com).")
else:
    print("\nUnexpected answer. Open the script > Executions to see the error.")
