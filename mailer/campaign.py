"""The send loop: sheet rows → personalized emails → status written back after every row."""
import os
import random
import time

from mailer import config, gmail_client, sheets, templates


def send_emails():
    sheet_path = config.SHEET_PATH
    attachment_path = config.ATTACHMENT_PATH

    if not os.path.exists(attachment_path):
        raise FileNotFoundError(f"Attachment not found: {attachment_path}")

    service = gmail_client.get_service(config.TOKEN_SEND_FILE, config.SEND_SCOPES)
    label_id = gmail_client.get_or_create_label(service, config.GMAIL_LABEL)
    df = sheets.read_sheet(sheet_path)

    sent_count = 0

    for i, row in df.iterrows():
        status = str(row.get("status", "")).strip().lower()
        if status in ("sent", "failed"):
            continue

        raw_to = str(row.get("to", "")).strip()
        to_email = ",".join(sheets.split_recipients(raw_to))
        if not to_email or to_email.lower() == "nan":
            continue

        company   = str(row.get("company", "")).strip()
        subject   = str(row.get("subject", "")).strip()
        cc        = str(row.get("cc", "")).strip()
        html_body = templates.personalize(str(row.get("email body", "")), company)

        try:
            message = templates.build_message(to_email, subject, html_body, cc, attachment_path)
            gmail_client.send_with_label(service, message, label_id)
            df.at[i, "status"] = "Sent"
            sent_count += 1
            print(f"[{sent_count}] Sent → {to_email} ({company})")

            # Random delay between every email
            delay = random.uniform(*config.DELAY_RANGE)
            print(f"    Waiting {delay:.1f}s...")
            time.sleep(delay)

            # Longer cooldown every COOLDOWN_EVERY emails
            if sent_count % config.COOLDOWN_EVERY == 0:
                pause = random.uniform(*config.COOLDOWN_RANGE)
                print(f"\n--- {sent_count} sent. Cooling down {pause:.1f}s ---\n")
                time.sleep(pause)

        except Exception as e:
            df.at[i, "status"] = "Failed"
            print(f"[!] Failed → {to_email} ({company}): {e}")

        # Save after every row (crash-safe)
        sheets.save_sheet(df, sheet_path)

    print(f"\nDone. {sent_count} emails sent.")
