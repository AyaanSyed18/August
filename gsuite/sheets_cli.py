import os
from typing import Optional, List
import typer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gsuite.auth import get_creds

app = typer.Typer(help="Google Sheets full CLI.")

_sheets_service = None
_drive_service = None

def get_sheets_service():
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = build("sheets", "v4", credentials=get_creds())
    return _sheets_service

def get_drive_service():
    global _drive_service
    if _drive_service is None:
        _drive_service = build("drive", "v3", credentials=get_creds())
    return _drive_service

def create_spreadsheet(title: str) -> dict:
    body = {"properties": {"title": title}}
    ss = get_sheets_service().spreadsheets().create(body=body, fields="spreadsheetId,properties").execute()
    return ss

def get_spreadsheet(spreadsheet_id: str) -> dict:
    return get_sheets_service().spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="spreadsheetId,properties/title"
    ).execute()

def set_cell_value(spreadsheet_id: str, range_name: str, value: str):
    body = {"values": [[value]]}
    get_sheets_service().spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()

def clear_range(spreadsheet_id: str, range_name: str):
    get_sheets_service().spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        body={},
    ).execute()

def delete_spreadsheet(spreadsheet_id: str):
    get_drive_service().files().delete(fileId=spreadsheet_id).execute()

@app.command("create")
def create_cmd(title: str):
    try:
        ss = create_spreadsheet(title)
        ss_id = ss["spreadsheetId"]
        url = f"https://docs.google.com/spreadsheets/d/{ss_id}/edit"
        typer.echo(f"Created: {title}")
        typer.echo(f"ID: {ss_id}")
        typer.echo(f"URL: {url}")
    except HttpError as e:
        typer.echo(f"Sheets error: {e}", err=True)
        raise typer.Exit(1)

@app.command("get")
def get_cmd(spreadsheet_id: str):
    try:
        ss = get_spreadsheet(spreadsheet_id)
        title = ss["properties"]["title"]
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        typer.echo(f"Title: {title}")
        typer.echo(f"ID: {spreadsheet_id}")
        typer.echo(f"URL: {url}")
    except HttpError as e:
        typer.echo(f"Sheets error: {e}", err=True)
        raise typer.Exit(1)

@app.command("set")
def set_cmd(spreadsheet_id: str, range_name: str, value: str):
    try:
        set_cell_value(spreadsheet_id, range_name, value)
        typer.echo("Updated.")
    except HttpError as e:
        typer.echo(f"Sheets error: {e}", err=True)
        raise typer.Exit(1)

@app.command("clear")
def clear_cmd(spreadsheet_id: str, range_name: str):
    try:
        clear_range(spreadsheet_id, range_name)
        typer.echo("Cleared.")
    except HttpError as e:
        typer.echo(f"Sheets error: {e}", err=True)
        raise typer.Exit(1)

@app.command("delete")
def delete_cmd(spreadsheet_id: str):
    if not typer.confirm(f"Delete spreadsheet {spreadsheet_id}?"):
        typer.echo("Cancelled.")
        raise typer.Exit()
    try:
        delete_spreadsheet(spreadsheet_id)
        typer.echo("Deleted.")
    except HttpError as e:
        typer.echo(f"Drive error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

