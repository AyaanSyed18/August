import base64
import os
from email.mime.text import MIMEText
from typing import Optional, List
import typer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gsuite.auth import get_creds

app = typer.Typer(help="Gmail CLI.")

_gmail_service = None

def get_gmail_service():
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = build("gmail", "v1", credentials=get_creds())
    return _gmail_service

def build_message(to: str, subject: str, body: str) -> dict:
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}

def send_email(to: str, subject: str, body: str) -> dict:
    svc = get_gmail_service()
    message = build_message(to, subject, body)
    return svc.users().messages().send(userId="me", body=message).execute()

def list_gmail_messages(n: int = 10) -> List[dict]:
    svc = get_gmail_service()
    result = svc.users().messages().list(userId="me", maxResults=n, labelIds=["INBOX"]).execute()
    messages = result.get("messages", [])
    if not messages:
        return []

    detailed_messages = []
    
    def callback(request_id, response, exception):
        if exception:
            return
        headers = response.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")
        detailed_messages.append({"id": response["id"], "subject": subject})

    batch = svc.new_batch_http_request()
    for m in messages:
        batch.add(svc.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["Subject"]), callback=callback)
    batch.execute()
    
    return detailed_messages

def trash_gmail_message(message_id: str):
    svc = get_gmail_service()
    svc.users().messages().trash(userId="me", id=message_id).execute()

@app.command("send")
def send_cmd(to: str, subject: str, body: str):
    try:
        sent = send_email(to, subject, body)
        typer.echo(f"Sent. ID: {sent.get('id')}")
    except HttpError as e:
        typer.echo(f"Gmail error: {e}", err=True)
        raise typer.Exit(1)

@app.command("list")
def list_cmd(n: int = 10):
    try:
        messages = list_gmail_messages(n)
        for m in messages:
            typer.echo(f"{m['id']} | {m['subject']}")
    except HttpError as e:
        typer.echo(f"Gmail error: {e}", err=True)
        raise typer.Exit(1)

@app.command("trash")
def trash_cmd(message_id: str):
    try:
        trash_gmail_message(message_id)
        typer.echo("Trashed.")
    except HttpError as e:
        typer.echo(f"Gmail error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

