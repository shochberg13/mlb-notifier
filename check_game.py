import os
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
TEAM = os.environ.get("MLB_TEAM", "Red Sox").strip()
SEEN_FILE = "seen_videos.json"
MLB_CHANNEL_ID = "UCoLrcjPV5PbUrUyXq5mjc_A"

def load_seen():
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def get_recent_condensed_game():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
    published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": MLB_CHANNEL_ID,
        "part": "snippet",
        "order": "date",
        "type": "video",
        "q": f"{TEAM} condensed game",
        "publishedAfter": published_after,
        "maxResults": 5,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    items = response.json().get("items", [])

    results = []
    for item in items:
        title = item["snippet"]["title"]
        video_id = item["id"]["videoId"]
        if "condensed" in title.lower() and TEAM.lower() in title.lower():
            results.append((video_id, title, f"https://www.youtube.com/watch?v={video_id}"))

    return results

def send_notification(title, url):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        headers={
            "Title": f"⚾ {TEAM} condensed game is ready",
            "Priority": "default",
            "Tags": "baseball",
            "Click": url,
        },
        data=title,
    )
    print(f"Notification sent: {title}")

if __name__ == "__main__":
    seen = load_seen()
    videos = get_recent_condensed_game()

    new_count = 0
    for video_id, title, url in videos:
        if video_id not in seen:
            send_notification(title, url)
            seen.add(video_id)
            new_count += 1

    if new_count:
        save_seen(seen)
        print(f"Sent {new_count} notification(s).")
    else:
        print(f"No new condensed games found for {TEAM}.")
