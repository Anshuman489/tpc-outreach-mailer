# TPC Outreach Mailer

## Overview

As Training & Placement Coordinator at NIT Patna, I had to email HR contacts at more than 300 companies every placement season. Doing it by hand was slow and error-prone, and it was hard to keep track of who had been contacted. This project replaces that process with a mailer driven by an Excel sheet. It sends a personalized email with the institute's Job Notification Form to each company from the placement cell's own account, then writes the result (sent, failed or bounced) back into the same sheet.

## How it works

1. Each coordinator keeps a sheet with columns `to`, `cc`, `company`, `email body`, `subject` and `status`.
2. `python -m scripts.send_campaign` sends to every row whose status is not already `Sent` or `Failed`, then writes the new status back to the sheet after every row.
3. Later, `python -m scripts.bounce_tracker` reads bounce notices from the mailbox and marks the affected rows `Failed`, highlighting them in red.

## Features

- **Personalized HTML email.** The body comes from the sheet. `{{Company}}` and its variants are replaced with the company name for each row.
- **Multiple recipients per row.** Addresses separated by `/`, `;`, `,` or spaces are split out. CC is supported.
- **File attachment.** A single attachment (for example the JNF form) is added to every email.
- **Status tracking in the sheet.** Rows are marked `Sent` or `Failed`, and the sheet is saved after every row, so a crash or interruption loses nothing and a re-run resumes where it stopped.
- **Bounce detection.** Gmail is searched for delivery-failure notices from mailer-daemon, postmaster and other common bounce formats. The bounced addresses are extracted and matched back to sheet rows.
- **Bounce cleanup.** Bounce notices for addresses in the sheet can be moved to Trash, after you confirm.
- **Throttling.** There is a random 1–2 s delay between emails and a 10–15 s cooldown every 50 emails, to stay under Gmail sending limits. There is no automatic retry. Any send error, including a 429 rate-limit response, marks the row `Failed` so it can be reviewed and queued again by clearing its status.
- **Deliverability measures.** Every email gets a multipart plain-text and HTML body, proper `Date` and `Message-ID` headers, and an invisible per-message token. The token stops identical bodies from being fingerprinted as bulk mail.
- **Gmail labels.** Every sent email is labelled automatically, so a campaign can be audited from the mailbox.

## Folder structure

```
tpc-outreach-mailer/
├── mailer/
│   ├── config.py        Loads .env; paths, scopes, throttling constants
│   ├── gmail_client.py  OAuth login and token caching, labels, send, search, trash
│   ├── templates.py     Placeholder personalization and MIME message building
│   ├── sheets.py        Excel reading/saving, recipient splitting, red highlighting
│   ├── tracker.py       Bounce detection, Failed marking, sent-row extraction
│   └── campaign.py      The send loop with throttling and per-row status saving
├── scripts/
│   ├── send_campaign.py    Send the campaign for SHEET_PATH
│   ├── bounce_tracker.py   Mark today's bounced recipients Failed and red
│   ├── cleanup_bounces.py  Trash bounce notices for addresses in the sheet
│   ├── mark_red.py         Highlight every Failed row in red
│   └── extract_sent.py     Merge Sent rows from several sheets into one
├── templates/           Example HTML email body
├── sample_data/         Sample sheet with the expected columns and fake rows
├── data/                Real sheets and attachments (local only, gitignored)
├── auth/                OAuth client secret and login tokens (local only, gitignored)
├── .env.example
└── requirements.txt
```

## Setup

1. In the Google Cloud Console, create a project, enable the **Gmail API**, configure the OAuth consent screen and create an OAuth client ID of type **Desktop app**.
2. Download the client secret and save it as `auth/credentials.json`.
3. Copy `.env.example` to `.env` and set your sheet path, attachment path, sender and label.
4. Install the dependencies (tested on Python 3.11):
   ```
   pip install -r requirements.txt
   ```
5. Put your sheet in `data/`, using `sample_data/contacts_template.xlsx` as the format. Then run from the project root:
   ```
   python -m scripts.send_campaign
   python -m scripts.bounce_tracker
   python -m scripts.cleanup_bounces
   python -m scripts.mark_red
   python -m scripts.extract_sent
   ```

The first run of each script opens a browser for Google sign-in and saves a login token in `auth/`: `token.json` for sending, `token_bounce.json` (read-only) and `token_cleanup.json`. Each script asks only for the scopes it needs. Later runs reuse and refresh the token. Tokens, credentials, `.env` and all sheets are gitignored and are never committed.

## Design decisions

**Why Python and the Gmail API instead of Google Apps Script.** The first version was an Apps Script mail merge. Its emails often landed in spam: attachments sent through Apps Script triggered filters, and the sending account had a weak reputation. Moving to the Gmail API means each email is built as a proper MIME message, with a plain-text alternative, standard headers and a correctly encoded attachment. The emails are sent from the institutional placement account, tpc.tnp@nitp.ac.in, which recipients recognise and which has a better sender reputation than a personal account. The OAuth client lives in a separate Google Cloud project. Only the token of the account that logs in decides which mailbox the email is sent from.

**Why throttled sending instead of blasting.** Sending hundreds of near-identical emails in a burst is exactly the pattern spam filters and Gmail rate limits look for. Random delays, periodic cooldowns and a unique token per message make the traffic look like normal sending and keep the account clear of rate limits. Saving the status after every row means a run that is stopped, or hits a limit, can simply be restarted without emailing anyone twice.
