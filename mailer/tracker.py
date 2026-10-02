"""Status tracking: bounce detection, Failed/red marking, and sent-row extraction."""
import base64
import os
import re
from datetime import date

import pandas as pd

from mailer import gmail_client, sheets

EMAIL_RE = r'[\w\.\-\+]+@[\w\.\-]+\.[a-z]{2,}'

# System/sender addresses found inside bounce notices that are not the bounced recipient
BOUNCE_SKIP = [
    "googlemail.com", "google.com", "mailer-daemon",
    "postmaster", "nitp.ac.in", "gmail.com",
    "googlegroups", "bounce", "noreply", "pphosted.com",
    "synopsys.com",
]
CLEANUP_SKIP = BOUNCE_SKIP + ["trendmicro.com", "tmes-in"]


def bounce_queries(only_today=True):
    today = date.today().strftime("%Y/%m/%d")
    date_filter = f" after:{today}" if only_today else ""
    return [
        f'from:mailer-daemon@googlemail.com subject:"Delivery Status Notification"{date_filter}',
        f'subject:"Undeliverable" has:attachment{date_filter}',
        f'from:postmaster subject:("undeliverable" OR "delivery failure" OR "returned"){date_filter}',
        f'subject:("Message blocked" OR "Mail delivery failed" OR "Delivery Status Notification"){date_filter}',
        f'subject:"Undelivered Mail Returned to Sender"{date_filter}',
        f'from:no-reply@tmes-in.trendmicro.com{date_filter}',
        # These two are always limited to today, regardless of only_today
        f'subject:"Returned mail: see transcript for details" after:{today}',
        f'from:mailer-daemon subject:("returned mail" OR "permanent fatal") after:{today}',
    ]


def find_bounce_messages(service, only_today=True):
    message_ids = gmail_client.search_message_ids(service, bounce_queries(only_today))
    print(f"Found {len(message_ids)} bounce emails to scan...")
    return message_ids


def extract_body(payload):
    """Recursively extract text from email payload."""
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    if "parts" in payload:
        for part in payload["parts"]:
            result = extract_body(part)
            if result:
                return result
    return ""


def addresses_in_message(service, msg_id, skip):
    """Lowercase addresses found in a message's body + snippet, minus skipped system addresses."""
    full = gmail_client.get_full_message(service, msg_id)
    body = extract_body(full.get("payload", {}))
    snippet = full.get("snippet", "")
    full_text = (body + " " + snippet).lower()
    found = []
    for email in re.findall(EMAIL_RE, full_text):
        email = email.strip()
        if any(s in email for s in skip):
            continue
        found.append(email)
    return found


def get_bounced_emails(service):
    """Bounced recipient addresses from today's bounce notices."""
    bounced = set()
    for msg_id in find_bounce_messages(service, only_today=True):
        try:
            for email in addresses_in_message(service, msg_id, BOUNCE_SKIP):
                bounced.add(email)
                print(f"  Bounced: {email}")
        except Exception as e:
            print(f"Error reading message {msg_id}: {e}")
    return bounced


def find_matching_bounces(service, message_ids, sheet_emails):
    """Return only message IDs where a bounced address is in the sheet."""
    matched_ids = set()
    for msg_id in message_ids:
        try:
            for email in addresses_in_message(service, msg_id, CLEANUP_SKIP):
                if email in sheet_emails:
                    print(f"  Match found: {email} → will trash bounce email")
                    matched_ids.add(msg_id)
                    break
        except Exception as e:
            print(f"Error reading message {msg_id}: {e}")
    return matched_ids


def mark_bounced_rows(sheet_path, bounced_emails, status_col):
    """Set status = Failed for rows containing a bounced address and fill them red (except status col)."""
    df = sheets.read_sheet(sheet_path)
    bounced_rows = []  # excel row numbers (1-indexed, accounting for header)

    for i, row in df.iterrows():
        to_val = str(row.get("to", "")).lower().strip()
        for bounced in bounced_emails:
            if bounced in to_val:
                df.at[i, "status"] = "Failed"
                bounced_rows.append(i + 2)  # +2: header row + 0-index
                print(f"  Marked row {i+2} as Failed: {to_val}")
                break

    sheets.save_sheet(df, sheet_path)

    wb, ws = sheets.open_workbook(sheet_path)
    for row_num in bounced_rows:
        sheets.fill_row_red(ws, row_num, skip_col=status_col)
    wb.save(sheet_path)
    print(f"\nDone. {len(bounced_rows)} rows marked red + Failed.")


def mark_failed_rows_red(sheet_path, status_col):
    """Fill columns A–E red for every row whose status is Failed."""
    wb, ws = sheets.open_workbook(sheet_path)
    marked = 0
    for row in ws.iter_rows(min_row=2):  # skip header
        status_cell = row[status_col - 1]  # 0-indexed
        if str(status_cell.value).strip().lower() == "failed":
            sheets.fill_row_red(ws, status_cell.row)
            marked += 1
    wb.save(sheet_path)
    print(f"Done. {marked} rows marked red.")


def extract_sent(input_sheets, output_sheet):
    """Combine Sent rows from several sheets into output_sheet, de-duplicated on the To address."""
    all_sent = []

    for sheet_path in input_sheets:
        if not os.path.exists(sheet_path):
            print(f"Skipping (not found): {sheet_path}")
            continue

        df = sheets.read_sheet(sheet_path)

        if "status" not in df.columns:
            print(f"Skipping (no status column): {sheet_path}")
            continue

        sent = df[df["status"].str.strip().str.lower() == "sent"].copy()
        sent["source_sheet"] = os.path.basename(sheet_path)  # track which sheet it came from
        all_sent.append(sent)
        print(f"{sheet_path} → {len(sent)} sent rows extracted")

    if not all_sent:
        print("No sent emails found across any sheet.")
        return

    combined = pd.concat(all_sent, ignore_index=True)

    # If output already exists, append without duplicating
    if os.path.exists(output_sheet):
        existing = sheets.read_sheet(output_sheet)
        combined = pd.concat([existing, combined], ignore_index=True)
        combined = combined.drop_duplicates(subset=["to"], keep="first")
        print(f"Appended to existing {output_sheet} (duplicates removed)")
    else:
        print(f"Created new {output_sheet}")

    sheets.save_sheet(combined, output_sheet)
    print(f"\nDone. {len(combined)} total sent rows saved to {output_sheet}")
