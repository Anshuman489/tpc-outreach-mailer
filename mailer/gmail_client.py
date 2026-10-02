"""Gmail API access: OAuth login, labels, sending, searching and trashing."""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mailer import config


def get_service(token_file, scopes):
    """Return a Gmail service, reusing/refreshing token_file or running the browser login."""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.CREDENTIALS_FILE, scopes)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]
    new_label = service.users().labels().create(userId="me", body={"name": label_name}).execute()
    print(f"Created label: {label_name}")
    return new_label["id"]


def send_with_label(service, message, label_id):
    sent_msg = service.users().messages().send(userId="me", body=message).execute()
    service.users().messages().modify(
        userId="me",
        id=sent_msg["id"],
        body={"addLabelIds": [label_id]}
    ).execute()
    return sent_msg


def search_message_ids(service, queries):
    """Union of message IDs matching any query (first 200 per query)."""
    all_message_ids = set()
    for query in queries:
        try:
            results = service.users().messages().list(
                userId="me", q=query, maxResults=200
            ).execute()
            for m in results.get("messages", []):
                all_message_ids.add(m["id"])
        except Exception as e:
            print(f"Query failed: {query} → {e}")
    return all_message_ids


def get_full_message(service, msg_id):
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


def trash_messages(service, message_ids):
    trashed = 0
    for msg_id in message_ids:
        try:
            service.users().messages().trash(userId="me", id=msg_id).execute()
            trashed += 1
        except Exception as e:
            print(f"Failed to trash {msg_id}: {e}")
    print(f"\nDone. {trashed}/{len(message_ids)} bounce emails moved to trash.")
