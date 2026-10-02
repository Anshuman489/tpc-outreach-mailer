"""Move bounce notices for addresses in the sheet to Gmail Trash (asks for confirmation).

Usage: python -m scripts.cleanup_bounces
"""
from mailer import config, gmail_client, sheets, tracker

if __name__ == "__main__":
    service = gmail_client.get_service(config.TOKEN_CLEANUP_FILE, config.CLEANUP_SCOPES)
    sheet_emails = sheets.recipient_set(config.SHEET_PATH)
    message_ids = tracker.find_bounce_messages(service, only_today=config.ONLY_TODAY)

    if not message_ids:
        print("No bounce emails found.")
    else:
        matched = tracker.find_matching_bounces(service, message_ids, sheet_emails)
        if not matched:
            print("No bounce emails matched addresses in your sheet.")
        else:
            print(f"\n{len(matched)} bounce emails match your sheet.")
            confirm = input("Trash them? (yes/no): ").strip().lower()
            if confirm == "yes":
                gmail_client.trash_messages(service, matched)
            else:
                print("Aborted. Nothing trashed.")
