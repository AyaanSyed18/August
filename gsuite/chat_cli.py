import os
from typing import Optional, List
import typer
from google.apps import chat_v1 as google_chat
from gsuite.auth import get_creds

app = typer.Typer(help="Google Chat CLI.")

_chat_client = None

def get_chat_client():
    global _chat_client
    if _chat_client is None:
        _chat_client = google_chat.ChatServiceClient(credentials=get_creds())
    return _chat_client

def list_chat_spaces() -> List[google_chat.Space]:
    client = get_chat_client()
    req = google_chat.ListSpacesRequest(filter='space_type = "SPACE"')
    return list(client.list_spaces(request=req))

def send_chat_message(space_name: str, text: str) -> google_chat.Message:
    client = get_chat_client()
    msg = google_chat.Message(text=text)
    return client.create_message(parent=space_name, message=msg)

@app.command("spaces")
def spaces_cmd():
    try:
        spaces = list_chat_spaces()
        for space in spaces:
            typer.echo(f"{space.name} | {space.display_name}")
    except Exception as e:
        typer.echo(f"Chat error: {e}", err=True)
        raise typer.Exit(1)

@app.command("send")
def send_cmd(space_name: str, text: str):
    try:
        created = send_chat_message(space_name, text)
        typer.echo(f"Sent: {created.name}")
    except Exception as e:
        typer.echo(f"Chat error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

