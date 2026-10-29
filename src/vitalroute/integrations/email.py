"""Transactional notification outbox. Gmail credentials belong to this app, not Codex."""

import base64
import os
from email.message import EmailMessage

import httpx

def notify(store, run, kind, summary):
    failure = run.get("failure", {})
    subject = f"[VitalRoute] {kind.replace('_', ' ').title()} · {run['id']} · {run['date']}"
    text = "\n".join(
        [
            "VitalRoute · local cold-chain pipeline demonstration",
            "",
            f"Run: {run['id']}",
            f"Partition: {run['date']}",
            f"Status: {run['status']}",
            f"Failure: {failure.get('code', 'none')} / {failure.get('stage', 'none')}",
            f"Details: {summary}",
            f"Repair: {run.get('proposal', {}).get('label', 'not yet proposed')}",
            f"Local release commit: {run.get('deployment', {}).get('commit', 'not deployed')}",
            "Data: fictional hospital logistics; no patient data.",
            "Deployment: local sandbox and per-incident Git release. No Databricks workspace was changed.",
            "Inspect: http://127.0.0.1:8180",
            "",
            "Recovery is declared only after downstream data-quality gates pass.",
        ]
    )
    store.queue_email(
        run["id"],
        kind,
        {
            "to": os.getenv("NOTIFY_TO", "joshuadominic747@gmail.com"),
            "subject": subject,
            "body": text,
            "mode": os.getenv("EMAIL_MODE", "outbox"),
        },
    )
    store.event(
        run["id"],
        "notification",
        f"Email queued · {kind.replace('_', ' ')}",
        delivery="outbox",
        recipient=os.getenv("NOTIFY_TO", "joshuadominic747@gmail.com"),
    )

def flush(store):
    if os.getenv("EMAIL_MODE", "outbox") != "gmail":
        return
    client_id, secret, refresh = [
        os.getenv(k) for k in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")
    ]
    if not all([client_id, secret, refresh]):
        return
    for mail in store.emails():
        if mail["status"] != "queued":
            continue
        attempted = False
        try:
            with httpx.Client(timeout=20) as client:
                response = client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": client_id,
                        "client_secret": secret,
                        "refresh_token": refresh,
                        "grant_type": "refresh_token",
                    },
                )
                response.raise_for_status()
                message = EmailMessage()
                message["To"] = mail["document"]["to"]
                message["Subject"] = mail["document"]["subject"]
                message["Message-ID"] = f"<{mail['id']}@vitalroute.local>"
                message.set_content(mail["document"]["body"])
                # Mark before network send: a crash after Gmail accepts must not cause an automatic duplicate.
                if not store.claim_email(mail["id"]):
                    continue
                attempted = True
                sent = client.post(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                    headers={"Authorization": "Bearer " + response.json()["access_token"]},
                    json={"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()},
                )
                sent.raise_for_status()
                store.email_status(mail["id"], "sent", provider_id=sent.json()["id"])
                store.event(
                    mail["run_id"],
                    "notification",
                    "Gmail accepted notification",
                    provider_id=sent.json()["id"],
                )
        except Exception as exc:
            store.email_status(
                mail["id"],
                "delivery_unknown" if attempted else "failed",
                error=type(exc).__name__,
            )
