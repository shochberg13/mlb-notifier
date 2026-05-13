import os, json, requests
from datetime import datetime, timezone, timedelta, date
import re
from pathlib import Path

YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
NTFY_TOPIC      = os.environ['NTFY_TOPIC']
TEAMS           = [t.strip() for t in os.environ.get('MLB_TEAM', 'Red Sox').split(',')]
SEEN_FILE       = 'seen_videos.json'
MLB_CHANNEL_ID  = 'UCoLrcjPV5PbUrUyXq5mjc_A'

SEASON_START = (3, 1)   # March 1
SEASON_END   = (11, 15) # November 15

def in_season():
    today = date.today()
    start = date(today.year, *SEASON_START)
    end   = date(today.year, *SEASON_END)
    return start <= today <= end

def load_seen():
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE) as f: return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f: json.dump(list(seen), f)

def get_recent_condensed_games(team):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    params = {
        'key': YOUTUBE_API_KEY,
        'channelId': MLB_CHANNEL_ID,
        'part': 'snippet',
        'order': 'date',
        'type': 'video',
        'q': f'{team} game highlights',
        'publishedAfter': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'maxResults': 5,
    }
    r = requests.get('https://www.googleapis.com/youtube/v3/search', params=params)
    r.raise_for_status()
    results = []
    for item in r.json().get('items', []):
        title = item['snippet']['title']
        vid   = item['id']['videoId']
        title_lower = title.lower()
        team_match      = team.lower() in title_lower
        highlight_match = 'condensed' in title_lower or 'highlights' in title_lower
        date_match      = bool(re.search(r'\(\d{1,2}/\d{1,2}/\d{2,4}\)', title))
        if team_match and highlight_match and date_match:
            results.append((vid, title, f'https://www.youtube.com/watch?v={vid}'))
    return results

def send_notification(team, title, url):
    requests.post(
        f'https://ntfy.sh/{NTFY_TOPIC}',
        headers={
            'Title': f'{team} condensed game is available',
            'Priority': 'default',
            'Tags': 'baseball',
            'Click': url,
        },
        data=title,
    )
    print(f'Notification sent: {title}')

if __name__ == '__main__':
    if not in_season():
        print(f'Off-season ({date.today()}). Exiting.')
        exit(0)

    seen = load_seen()
    new_count = 0

    for team in TEAMS:
        videos = get_recent_condensed_games(team)
        for vid, title, url in videos:
            if vid not in seen:
                send_notification(team, title, url)
                seen.add(vid)
                new_count += 1

    save_seen(seen)
    if new_count:
        print(f'Sent {new_count} notification(s).')
    else:
        print(f'No new condensed games found for {", ".join(TEAMS)}.')
