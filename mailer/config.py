"""Central configuration. Values come from .env; relative paths resolve against the project root."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _path(value):
    p = Path(value)
    return str(p if p.is_absolute() else ROOT_DIR / p)


def _bool(value):
    return str(value).strip().lower() in ("1", "true", "yes")


# ── Auth: client secret + one login token per scope set, all inside AUTH_DIR ──
AUTH_DIR          = _path(os.getenv("AUTH_DIR", "auth"))
CREDENTIALS_FILE  = os.path.join(AUTH_DIR, os.getenv("CREDENTIALS_FILE", "credentials.json"))
TOKEN_SEND_FILE   = os.path.join(AUTH_DIR, os.getenv("TOKEN_SEND_FILE", "token.json"))
TOKEN_BOUNCE_FILE = os.path.join(AUTH_DIR, os.getenv("TOKEN_BOUNCE_FILE", "token_bounce.json"))
TOKEN_CLEANUP_FILE = os.path.join(AUTH_DIR, os.getenv("TOKEN_CLEANUP_FILE", "token_cleanup.json"))

SEND_SCOPES    = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']
BOUNCE_SCOPES  = ['https://www.googleapis.com/auth/gmail.readonly']
CLEANUP_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# ── Campaign ──
SHEET_PATH      = _path(os.getenv("SHEET_PATH", "data/contacts.xlsx"))
ATTACHMENT_PATH = _path(os.getenv("ATTACHMENT_PATH", "data/attachment.pdf"))
GMAIL_LABEL     = os.getenv("GMAIL_LABEL", "Outreach/Invitation")
SENDER_NAME     = os.getenv("SENDER_NAME", "Placement Cell, NIT Patna")
SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "tpc.tnp@nitp.ac.in")

# ── Throttling ──
DELAY_RANGE      = (1, 2)     # random delay (s) after every email
COOLDOWN_EVERY   = 50         # pause after this many sent emails
COOLDOWN_RANGE   = (10, 15)   # random cooldown (s)

# ── Tracking ──
STATUS_COL_INDEX = int(os.getenv("STATUS_COL_INDEX", "6"))  # 1-based; column F
ONLY_TODAY       = _bool(os.getenv("ONLY_TODAY", "true"))   # cleanup: False checks ALL bounce emails ever

# ── Sent extraction ──
INPUT_SHEETS = [_path(p.strip()) for p in os.getenv("INPUT_SHEETS", "").split(",") if p.strip()]
OUTPUT_SHEET = _path(os.getenv("OUTPUT_SHEET", "data/Sent_Combined.xlsx"))
