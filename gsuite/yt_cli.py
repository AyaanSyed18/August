import os
import webbrowser

import typer
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dotenv import load_dotenv

load_dotenv()


app = typer.Typer(help="YouTube CLI: search and play via youtube.com or music.youtube.com.")


def get_youtube():
    api_key = os.environ.get("YT_API_KEY")
    if not api_key:
        raise typer.Exit("Set YT_API_KEY environment variable first.")
    return build("youtube", "v3", developerKey=api_key)


def build_url(video_id: str, kind: str) -> str:
    """Return a URL for the given video_id and kind: 'music' or 'video'."""
    if kind == "music":
        # YouTube Music; still uses watch?v= but on music.youtube.com
        return f"https://music.youtube.com/watch?v={video_id}"
    else:
        # Default YouTube video
        return f"https://www.youtube.com/watch?v={video_id}"


def ask_music_or_video() -> str:
    """Ask user: music or video; return 'music' or 'video'."""
    choice = typer.prompt("Open in (m)usic.youtube.com or (v)ideo youtube.com? [m/v]", default="m").strip().lower()
    if choice.startswith("v"):
        return "video"
    return "music"


@app.command("search")
def search(query: str = typer.Argument(..., help="Search query")):
    """Search YouTube and print top results (title + videoId)."""
    yt = get_youtube()
    try:
        res = (
            yt.search()
            .list(
                part="snippet",
                q=query,
                maxResults=5,
                type="video",
            )
            .execute()
        )
        items = res.get("items", [])
        if not items:
            typer.echo("No results.")
            raise typer.Exit()
        for i, item in enumerate(items, start=1):
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            typer.echo(f"{i}. {title} | {vid}")
    except HttpError as e:
        typer.echo(f"YouTube API error: {e}", err=True)
        raise typer.Exit(1)


@app.command("play")
def play(query: str = typer.Argument(..., help="Search and play first result")):
    """Search for a query, pick a result, and open it in music.youtube.com or youtube.com."""
    yt = get_youtube()
    try:
        res = (
            yt.search()
            .list(
                part="snippet",
                q=query,
                maxResults=5,
                type="video",
            )
            .execute()
        )
        items = res.get("items", [])
        if not items:
            typer.echo("No results.")
            raise typer.Exit()

        typer.echo("Results:")
        for i, item in enumerate(items, start=1):
            title = item["snippet"]["title"]
            typer.echo(f"{i}. {title}")

        choice = typer.prompt("Pick number", default="1").strip()
        try:
            idx = int(choice) - 1
            item = items[idx]
        except (ValueError, IndexError):
            typer.echo("Invalid choice.")
            raise typer.Exit(1)

        vid = item["id"]["videoId"]
        kind = ask_music_or_video()
        url = build_url(vid, kind)
        webbrowser.open(url)
        typer.echo(f"Opened: {url}")
    except HttpError as e:
        typer.echo(f"YouTube API error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
