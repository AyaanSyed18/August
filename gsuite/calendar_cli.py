import datetime
import os
from typing import Optional, List
import typer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gsuite.auth import get_creds

app = typer.Typer(help="Google Calendar CLI.")

TZ = "Asia/Kolkata"

import uuid

_cal_service = None

def get_cal_service():
    global _cal_service
    if _cal_service is None:
        _cal_service = build("calendar", "v3", credentials=get_creds())
    return _cal_service

def list_calendar_events(max_results: int = 10) -> List[dict]:
    svc = get_cal_service()
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    res = svc.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return res.get("items", [])

def create_calendar_event(title: str, date: str, start_time: str, end_time: str, meet: bool = True) -> dict:
    svc = get_cal_service()
    d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    st = datetime.datetime.strptime(start_time, "%H:%M").time()
    et = datetime.datetime.strptime(end_time, "%H:%M").time()
    start_dt = datetime.datetime.combine(d, st)
    end_dt = datetime.datetime.combine(d, et)

    body: dict = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TZ},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TZ},
    }

    if meet:
        body["conferenceData"] = {
            "createRequest": {"requestId": str(uuid.uuid4())}
        }

    return svc.events().insert(
        calendarId="primary",
        body=body,
        conferenceDataVersion=1 if meet else 0,
        sendUpdates="all",
    ).execute()

def delete_calendar_event(event_id: str):
    get_cal_service().events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()

@app.command("list")
def list_cmd(max_results: int = 10):
    try:
        events = list_calendar_events(max_results)
        if not events:
            typer.echo("No events.")
            return
        for idx, e in enumerate(events, start=1):
            start = e["start"].get("dateTime", e["start"].get("date"))
            meet = e.get("hangoutLink", "")
            typer.echo(f"{idx}. {start} | {e.get('summary', '(no title)')} | {e['id']} | {meet}")
    except HttpError as e:
        typer.echo(f"Calendar error: {e}", err=True)
        raise typer.Exit(1)

@app.command("create")
def create_cmd(title: str, date: str, start_time: str, end_time: str, meet: bool = True):
    try:
        event = create_calendar_event(title, date, start_time, end_time, meet)
        typer.echo(f"Created: {event.get('summary')}")
        typer.echo(f"ID: {event.get('id')}")
        typer.echo(f"Meet: {event.get('hangoutLink', '')}")
    except (HttpError, ValueError) as e:
        typer.echo(f"Calendar error: {e}", err=True)
        raise typer.Exit(1)

@app.command("delete")
def delete_cmd(event_id: str):
    if not typer.confirm(f"Delete event {event_id}?"):
        typer.echo("Cancelled.")
        raise typer.Exit()
    try:
        delete_calendar_event(event_id)
        typer.echo("Deleted.")
    except HttpError as e:
        typer.echo(f"Calendar error: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

