import os
from typing import Optional, List
import typer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gsuite.auth import get_creds

app = typer.Typer(help="Google Slides CLI.")

_slides_service = None
_drive_service = None

def get_slides_service():
    global _slides_service
    if _slides_service is None:
        _slides_service = build("slides", "v1", credentials=get_creds())
    return _slides_service

def get_drive_service():
    global _drive_service
    if _drive_service is None:
        _drive_service = build("drive", "v3", credentials=get_creds())
    return _drive_service

def create_presentation(title: str) -> dict:
    return get_slides_service().presentations().create(body={"title": title}).execute()

def get_presentation(presentation_id: str) -> dict:
    return get_slides_service().presentations().get(presentationId=presentation_id).execute()

def add_slide_to_presentation(presentation_id: str, layout: str = "BLANK"):
    requests = [{"createSlide": {"slideLayoutReference": {"predefinedLayout": layout}}}]
    get_slides_service().presentations().batchUpdate(
        presentationId=presentation_id, body={"requests": requests}
    ).execute()

def delete_presentation(presentation_id: str):
    get_drive_service().files().delete(fileId=presentation_id).execute()

@app.command("create")
def create_cmd(title: str):
    try:
        pres = create_presentation(title)
        pid = pres["presentationId"]
        url = f"https://docs.google.com/presentation/d/{pid}/edit"
        typer.echo(f"Created: {title}")
        typer.echo(f"ID: {pid}")
        typer.echo(f"URL: {url}")
    except HttpError as e:
        typer.echo(f"Slides error: {e}", err=True)
        raise typer.Exit(1)

@app.command("info")
def info_cmd(presentation_id: str):
    try:
        pres = get_presentation(presentation_id)
        title = pres["title"]
        slides = pres.get("slides", [])
        typer.echo(f"Title: {title}")
        typer.echo(f"Slides: {len(slides)}")
    except HttpError as e:
        typer.echo(f"Slides error: {e}", err=True)
        raise typer.Exit(1)

@app.command("add-slide")
def add_slide_cmd(presentation_id: str, layout: str = "BLANK"):
    try:
        add_slide_to_presentation(presentation_id, layout)
        typer.echo("Slide added.")
    except HttpError as e:
        typer.echo(f"Slides error: {e}", err=True)
        raise typer.Exit(1)

@app.command("delete")
def delete_cmd(presentation_id: str):
    if not typer.confirm(f"Delete presentation {presentation_id}?"):
        typer.echo("Cancelled.")
        raise typer.Exit()
    try:
        delete_presentation(presentation_id)
        typer.echo("Deleted.")
    except HttpError as e:
        typer.echo(f"Drive error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

