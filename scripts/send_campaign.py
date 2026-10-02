"""Send personalized emails to every pending row of SHEET_PATH.

Usage: python -m scripts.send_campaign
"""
from mailer.campaign import send_emails

if __name__ == "__main__":
    send_emails()
