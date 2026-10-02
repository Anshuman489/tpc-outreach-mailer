"""Scan today's bounce notices and mark matching sheet rows Failed + red.

Usage: python -m scripts.bounce_tracker
"""
from mailer import config, gmail_client, tracker

if __name__ == "__main__":
    service = gmail_client.get_service(config.TOKEN_BOUNCE_FILE, config.BOUNCE_SCOPES)
    bounced = tracker.get_bounced_emails(service)

    if bounced:
        print(f"\nTotal unique bounced addresses: {len(bounced)}")
        tracker.mark_bounced_rows(config.SHEET_PATH, bounced, config.STATUS_COL_INDEX)
    else:
        print("No bounced addresses found.")
