"""Email personalization and MIME message building."""
import base64
import os
import re
import uuid
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from mailer import config

# All company-name placeholder variants accepted in the sheet's email body
COMPANY_PLACEHOLDERS = ["[Company_Name]", "{{Company}}", "{{company}}", "{{company_name}}", "{{companyname}}"]


def personalize(html_body, company):
    for placeholder in COMPANY_PLACEHOLDERS:
        html_body = html_body.replace(placeholder, company)
    return html_body


def build_message(to, subject, html_body, cc="", attachment_path=None):
    msg = MIMEMultipart("mixed")
    msg["From"]       = f"{config.SENDER_NAME} <{config.SENDER_EMAIL}>"
    msg["To"]         = to
    msg["Subject"]    = subject
    msg["Date"]       = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    if cc:
        msg["Cc"] = cc

    # Unique invisible token — prevents identical content fingerprinting
    unique_body = html_body + f'<span style="display:none;font-size:0">{uuid.uuid4()}</span>'

    # Plain text fallback
    plain = re.sub(r'<[^>]+>', '', unique_body).replace('&nbsp;', ' ').strip()

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(unique_body, "html", "utf-8"))
    msg.attach(alt)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(attachment_path)}"')
            msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}
