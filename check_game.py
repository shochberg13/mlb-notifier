import os, json, requests
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
NTFY_TOPIC      = os.environ['NTFY_TOPIC']
TEAM            = os.environ.get('MLB_TEAM', 'Red Sox').strip()
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

def get_recent_condensed_game():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    params = {
        'key': YOUTUBE_API_KEY,
        'channelId': MLB_CHANNEL_ID,
        'part': 'snippet',
        'order': 'date',
        'type': 'video',
        'q': f'{TEAM} condensed game',
        'publishedAfter': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'maxResults': 5,
    }
    r = requests.get('https://www.googleapis.com/youtube/v3/search', params=params)
    r.raise_for_status()
    results = []
    for item in r.json().get('items', []):
        title = item['snippet']['title']
        vid   = item['id']['videoId']
        if 'condensed' in title.lower() and TEAM.lower() in title.lower():
            results.append((vid, title, f'https://www.youtube.com/watch?v={vid}'))
    return results

def send_notification(title, url):
    requests.post(
        f'https://ntfy.sh/{NTFY_TOPIC}',
        headers={
            'Title': f'⚾ {TEAM} condensed game is ready',
            'Priority': 'default',
            'Tags': 'baseball',
            'Click': url,
        },
        data=title,
    )
    print(f'Notification sent: {title}')

if __name__ == '__main__':
    if not in_season():
        today = date.today()
        print(f'Off-season ({today}). Exiting.')
        exit(0)

    seen   = load_seen()
    videos = get_recent_condensed_game()
    new_count = 0
    for vid, title, url in videos:
        if vid not in seen:
            send_notification(title, url)
            seen.add(vid)
            new_count += 1
    save_seen(seen)
    if new_count:
        print(f'Sent {new_count} notification(s).')
    else:
        print(f'No new condensed games found for {TEAM}.')
