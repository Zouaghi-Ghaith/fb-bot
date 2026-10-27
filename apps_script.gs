// Google Sheets receiver. Paste this in: your Google Sheet > Extensions > Apps Script.
// Then: Deploy > New deployment > type "Web app" > Execute as: Me > Who has access: Anyone > Deploy.
// Copy the web app URL into SHEETS_WEBHOOK_URL in your .env file.

const SECRET = "change-me-secret";   // must be identical to SHEETS_SECRET in .env

const HEADERS = ["Updated", "Channel", "SenderID", "Name", "Phone", "Need",
                 "Details", "ReadyToBuy", "Language", "NeedsHuman", "LastMessage"];

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.secret !== SECRET) return reply({ ok: false, error: "unauthorized" });

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.getRange("C:C").setNumberFormat("@");   // SenderID as text
      sheet.getRange("E:E").setNumberFormat("@");   // Phone as text (keeps the + and zeros)
    }

    const row = [new Date(), d.channel || "", String(d.sender_id || ""), d.name || "",
                 String(d.phone || ""), d.need || "", d.details || "", d.ready_to_buy || "",
                 d.language || "", d.needs_human ? "YES" : "", d.last_message || ""];

    // Update the customer's row if it already exists, otherwise add a new one.
    let target = 0;
    const last = sheet.getLastRow();
    if (last > 1) {
      const ids = sheet.getRange(2, 2, last - 1, 2).getValues();   // columns B (channel) and C (sender id)
      for (let i = 0; i < ids.length; i++) {
        if (String(ids[i][0]) === row[1] && String(ids[i][1]) === row[2]) { target = i + 2; break; }
      }
    }
    if (target) sheet.getRange(target, 1, 1, row.length).setValues([row]);
    else sheet.appendRow(row);

    return reply({ ok: true });
  } catch (err) {
    return reply({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
