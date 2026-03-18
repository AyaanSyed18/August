import os
import webbrowser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

def get_youtube():
    api_key = os.environ.get("YT_API_KEY")
    if not api_key:
        return None
    return build("youtube", "v3", developerKey=api_key)

def youtube_search(query, max_results=5):
    """Search YouTube and return top results (title + videoId)."""
    yt = get_youtube()
    if not yt:
        return "Sir, I require a 'YT_API_KEY' in your .env file to search YouTube. Could you kindly provide one?"
    
    try:
        res = (
            yt.search()
            .list(
                part="snippet",
                q=query,
                maxResults=max_results,
                type="video",
            )
            .execute()
        )
        items = res.get("items", [])
        if not items:
            return "No results found."
        
        results = []
        for item in items:
            results.append({
                "title": item["snippet"]["title"],
                "videoId": item["id"]["videoId"]
            })
        return results
    except HttpError as e:
        return f"YouTube API error: {e}"

def youtube_play(video_id=None, query=None, mode="music"):
    """Open a YouTube video in the browser. If query is provided, searches and plays the first result."""
    if not video_id and query:
        # Search for the query and get the first result
        search_results = youtube_search(query, max_results=1)
        if isinstance(search_results, list) and len(search_results) > 0:
            video_id = search_results[0]["videoId"]
        else:
            return f"Could not find any results for '{query}', Sir."
    
    if not video_id:
        return "No video ID or query provided to play, Sir."

    if mode == "music":
        url = f"https://music.youtube.com/watch?v={video_id}"
    else:
        url = f"https://www.youtube.com/watch?v={video_id}"
    
    webbrowser.open(url)
    return f"Certainly, Sir. Opening that for you now."
