# Test the Facebook Messenger bot on your own page

What you get: a customer writes to your Facebook Page -> the AI understands (French, Darija, Arabic) and replies ->
name, phone, need and "ready to buy?" are saved in a Google Sheet.

IMPORTANT
- Until Meta approves your app (App Review), the bot only answers Facebook accounts that have a role on your app
  (Administrator, Developer or Tester). That is perfect for testing on your own page.
- On a free AI tier, use FAKE customer data only (free-tier data may be used by the provider).

Files: app.py (webhook) | brain.py (AI + prompt) | business.py (what the bot knows: EDIT IT) |
       apps_script.gs (Google Sheet receiver) | test_ai.py + test_messages.txt (test without Facebook) | .env.example

---------------------------------------------------------------------------------------------------

## 1. Install and prepare (Windows PowerShell)

    cd path\to\fb-bot
    python -m venv venv
    .\venv\Scripts\Activate.ps1          (if blocked: Set-ExecutionPolicy -Scope Process Bypass)
    pip install -r requirements.txt
    copy .env.example .env
    notepad .env

## 2. Get a free AI key and test the AI first (no Facebook needed)

- Gemini: https://aistudio.google.com -> "Get API key" -> put it in GEMINI_API_KEY (AI_PROVIDER=gemini)
- or Mistral: https://console.mistral.ai -> API keys -> MISTRAL_API_KEY (AI_PROVIDER=mistral)
- If you get "model not found", copy a current model name from the provider's page into GEMINI_MODEL / MISTRAL_MODEL.

Edit business.py with your own (fake) products, prices and delivery rules, then:

    python test_ai.py            # runs all messages in test_messages.txt
    python test_ai.py --chat     # chat yourself in French / Darija / Arabizi

Add your own difficult messages to test_messages.txt. Improve DARIJA_GLOSSARY in brain.py when the bot misunderstands a word.

## 3. Google Sheet (free)

1. Create a new Google Sheet (any name).
2. Extensions -> Apps Script -> delete the sample code -> paste apps_script.gs.
3. Change SECRET at the top to a random text. Put the SAME text in SHEETS_SECRET in .env.
4. Deploy -> New deployment -> gear icon -> "Web app" -> Execute as: Me -> Who has access: Anyone -> Deploy.
5. Authorize (Advanced -> "Go to project" if Google warns). Copy the Web app URL (ends with /exec) into SHEETS_WEBHOOK_URL.
6. If you edit the script later: Deploy -> Manage deployments -> pencil -> Version: New version -> Deploy.
If the sheet is not configured or fails, leads are saved in leads_local.csv instead.

## 4. Start the bot and a public tunnel

Terminal 1:
    python app.py                (you should see: Running on http://127.0.0.1:5000)

Terminal 2 (ngrok: https://ngrok.com -> free account -> install -> "ngrok config add-authtoken <token>"):
    ngrok http 5000
Copy the https URL it shows (https://xxxx.ngrok-free.app). On the free plan it changes every time you restart ngrok,
so you must update the Meta callback URL each time.

## 5. Create the Meta app and connect your Page

(Meta renames dashboard items often. Names below may differ slightly.)
1. Go to https://developers.facebook.com with the Facebook account that is ADMIN of your Page. Register as a developer.
2. My Apps -> Create App -> choose the use case for Messenger ("Engage with customers on Messenger from Meta"),
   or app type "Business" and add the "Messenger" product. Create it.
3. Open the Messenger settings ("Messenger API setup" / "Customize the use case").
4. Generate a Page access token: add your Page, click "Generate token", copy it into PAGE_ACCESS_TOKEN in .env.
5. Configure webhooks: Callback URL = https://xxxx.ngrok-free.app/webhook , Verify token = your VERIFY_TOKEN. Click Verify and save.
   (The bot must be running and ngrok must be on, or verification fails.)
6. Subscribe the webhook fields: messages and messaging_postbacks (optional: message_echoes). Make sure your Page is
   subscribed ("Add or remove pages" / "Add subscriptions").
7. App settings -> Basic -> App secret -> Show -> copy into APP_SECRET (or leave empty while testing).
8. Restart `python app.py` after editing .env.

## 6. Add a test account (recommended)

App roles -> Roles -> Add People -> choose "Testers" -> add a second Facebook account.
That person accepts the invitation at https://developers.facebook.com/requests .
Admins, developers and testers are the only people the bot answers until App Review.

## 7. Test

From the tester (or admin) account, open your Page and click "Send message". Try:
- "3aslema, chnowa el prix mta3 el sneakers ?"
- "Bonjour, je veux 2 t-shirts noirs en M"
- give a name and a phone number
- "je veux parler à quelqu'un"  (the bot hands over and stays silent for 12 hours for that person)
Watch the terminal logs, then open the Google Sheet: one row per customer, updated as the chat goes on.
To reset the bot's memory and silence timers, stop and restart `python app.py`.

## Troubleshooting

- Verify and save fails: bot or ngrok not running, wrong URL (must end with /webhook), VERIFY_TOKEN differs from .env.
- Nothing arrives: Page not subscribed to the app, fields not subscribed, or the sender has no role on the app.
- POST returns 403 in the logs: APP_SECRET is wrong. Empty it while testing.
- "AI error 429": free limit reached. Wait, or switch AI_PROVIDER.
- "AI error 400/404": wrong model name. Check the provider's current model list.
- Send API error in the logs: expired/wrong PAGE_ACCESS_TOKEN, a missing permission, or the 24-hour reply window.
  If it mentions the API version, update GRAPH_VERSION to a current one from Meta's docs.
- Sheet stays empty: check SHEETS_SECRET equals SECRET, access is "Anyone", and look at Apps Script -> Executions.

## Limits of this test version

Memory is kept in RAM (lost on restart), one server process, no database. For real clients you need: hosting with
a permanent https address, a database, a paid AI tier for privacy, and Meta App Review + Business Verification.
Instagram: app.py already accepts Instagram events, but it is untested. Do it after Facebook works
(Instagram professional account linked to the Page, and the Instagram messaging permissions).
