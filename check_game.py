import re
import os, json, requests
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

# --- Configuration (set via GitHub Actions secrets/variables) ---
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
NTFY_TOPIC      = os.environ['NTFY_TOPIC']

# MLB_TEAM can be a single team ("Red Sox") or comma-separated ("Red Sox, Cubs")
TEAMS          = [t.strip() for t in os.environ.get('MLB_TEAM', 'Red Sox').split(',')]

SEEN_FILE      = 'seen_videos.json'          # tracks already-notified videos to prevent duplicates
MLB_CHANNEL_ID = 'UCoLrcjPV5PbUrUyXq5mjc_A' # official MLB YouTube channel

# Script only runs during baseball season — exits early otherwise
SEASON_START = (3, 1)    # March 1  (covers spring training)
SEASON_END   = (11, 15)  # November 15 (covers full postseason)

def in_season():
    """Returns True if today falls within the configured season window."""
    today = date.today()
    start = date(today.year, *SEASON_START)
    end   = date(today.year, *SEASON_END)
    return start <= today <= end

def load_seen():
    """Loads the set of already-notified video IDs from disk."""
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE) as f: return set(json.load(f))
    return set()

def save_seen(seen):
    """Persists the set of seen video IDs so it survives across runs."""
    with open(SEEN_FILE, 'w') as f: json.dump(list(seen), f)

def get_recent_condensed_games(team):
    """
    Searches MLB's YouTube channel for a condensed/highlights game video
    for the given team, posted in the last 24 hours.
    Returns a list of (video_id, title, url) tuples.
    """
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

        # Must mention the team
        team_match = team.lower() in title_lower

        # Must say "game highlights" (or "condensed") — plain "highlights" alone
        # matches too many unrelated recap/moment videos
        highlight_match = 'game highlights' in title_lower or 'condensed' in title_lower

        # Real condensed games always LEAD with the matchup, e.g.
        # "Red Sox vs Rockies Full Game Highlights". Recap videos bury the
        # matchup in parentheses near the end instead, e.g.
        # "...homer! | MLB Highlights (Red Sox vs Mets)" — so we check that
        # "vs" appears near the start of the title, not just anywhere in it.
        vs_near_start = bool(re.search(r'^.{0,30}\bvs\.?\b', title_lower))

        print(f'  Checking: "{title}" | team={team_match} highlight={highlight_match} vs_start={vs_near_start}')

        if team_match and highlight_match and vs_near_start:
            results.append((vid, title, f'https://www.youtube.com/watch?v={vid}'))

    return results

def send_notification(team, title, url):
    """Sends a push notification via ntfy.sh to a team-specific topic."""
    topic_suffix = team.lower().replace(' ', '-')  # "Red Sox" -> "red-sox", "Detroit Tigers" -> "detroit-tigers"
    topic = f'{NTFY_TOPIC}-{topic_suffix}'          # e.g. "seth-mlb-notifier-red-sox"
    requests.post(
        f'https://ntfy.sh/{topic}',
        headers={
            'Title': f'{team} condensed game is available',
            'Priority': 'default',
            'Tags': 'baseball',
            'Click': url,
        },
        data=title,
    )
    print(f'Notification sent to {topic}: {title}')

if __name__ == '__main__':
    if not in_season():
        print(f'Off-season ({date.today()}). Exiting.')
        exit(0)

    seen = load_seen()
    new_count = 0

    for team in TEAMS:
        print(f'Checking for {team} condensed game...')
        videos = get_recent_condensed_games(team)
        for vid, title, url in videos:
            if vid not in seen:
                send_notification(team, title, url)
                seen.add(vid)
                new_count += 1
            else:
                print(f'  Already notified: "{title}" — skipping.')

    save_seen(seen)

    if new_count:
        print(f'Sent {new_count} notification(s).')
    else:
        print(f'No new condensed games found for {", ".join(TEAMS)}.')
