import os
from typing import Optional, List
import typer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gsuite.auth import get_creds

app = typer.Typer(help="Google Docs full CLI.")

_docs_service = None
_drive_service = None

def get_docs_service():
    global _docs_service
    if _docs_service is None:
        _docs_service = build("docs", "v1", credentials=get_creds())
    return _docs_service

def get_drive_service():
    global _drive_service
    if _drive_service is None:
        _drive_service = build("drive", "v3", credentials=get_creds())
    return _drive_service

def create_doc(title: str) -> dict:
    service = get_docs_service()
    doc = service.documents().create(body={"title": title}).execute()
    return doc

def get_doc(document_id: str) -> dict:
    return get_docs_service().documents().get(documentId=document_id).execute()

def append_text(document_id: str, text: str):
    service = get_docs_service()
    doc = service.documents().get(documentId=document_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"]

    requests = [
        {
            "insertText": {
                "location": {"index": end_index - 1},
                "text": text,
            }
        }
    ]
    service.documents().batchUpdate(
        documentId=document_id, body={"requests": requests}
    ).execute()

def delete_doc(document_id: str):
    get_drive_service().files().delete(fileId=document_id).execute()

@app.command("create")
def create_cmd(title: str):
    try:
        doc = create_doc(title)
        typer.echo(f"Created: '{doc.get('title')}' (ID: {doc.get('documentId')})")
    except HttpError as e:
        typer.echo(f"Docs error: {e}", err=True)
        raise typer.Exit(1)

@app.command("get")
def get_cmd(document_id: str):
    try:
        doc = get_doc(document_id)
        typer.echo(f"Title: {doc.get('title')}")
        typer.echo(f"ID: {doc.get('documentId')}")
    except HttpError as e:
        typer.echo(f"Docs error: {e}", err=True)
        raise typer.Exit(1)

@app.command("append")
def append_cmd(document_id: str, text: str):
    try:
        append_text(document_id, text)
        typer.echo("Appended.")
    except HttpError as e:
        typer.echo(f"Docs error: {e}", err=True)
        raise typer.Exit(1)

@app.command("delete")
def delete_cmd(document_id: str):
    if not typer.confirm(f"Delete document {document_id}?"):
        typer.echo("Cancelled.")
        raise typer.Exit()
    try:
        delete_doc(document_id)
        typer.echo("Deleted.")
    except HttpError as e:
        typer.echo(f"Drive error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

