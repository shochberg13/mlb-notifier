import re
import os, json, requests
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

from mlb_stats_api import get_recent_condensed_game_mlb

# --- Configuration (set via GitHub Actions secrets/variables) ---
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
NTFY_TOPIC      = os.environ['NTFY_TOPIC']

TEAMS          = [t.strip() for t in os.environ.get('MLB_TEAM', 'Red Sox').split(',')]

SEEN_FILE      = 'seen_videos.json'
MLB_CHANNEL_ID = 'UCoLrcjPV5PbUrUyXq5mjc_A'

# Teams that should link to mlb.com (via the Stats API) instead of YouTube.
# Currently just Red Sox, since a NextDNS rule on this account blocks
# youtube.com but leaves mlb.com untouched.
MLB_LINK_TEAMS = {'red sox'}

SEASON_START = (3, 1)
SEASON_END   = (11, 15)


def in_season():
    today = date.today()
    start = date(today.year, *SEASON_START)
    end   = date(today.year, *SEASON_END)
    return start <= today <= end


def load_seen():
    """
    Loads already-notified video IDs, keyed per team, e.g.:
      {"Red Sox": ["abc123"], "Tigers": ["xyz789"]}
    Nesting by team means you can clear one team's history (to force a
    re-notification, or after a filter change) without touching any
    other team's data — just edit that team's list in the JSON file.
    """
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(seen, f, indent=2)


def get_recent_condensed_games_youtube(team):
    """Searches MLB's YouTube channel for a condensed/highlights video for the team."""
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

        team_match = team.lower() in title_lower
        game_match = 'game' in title_lower
        highlights_word_match = 'highlights' in title_lower
        highlight_match = (game_match and highlights_word_match) or 'condensed' in title_lower
        vs_near_start = bool(re.search(r'^.{0,30}\bvs\.?\b', title_lower))

        print(f'  Checking: "{title}" | team={team_match} highlight={highlight_match} vs_start={vs_near_start}')

        if team_match and highlight_match and vs_near_start:
            results.append((vid, title, f'https://www.youtube.com/watch?v={vid}'))

    return results


def get_recent_condensed_games(team):
    """
    Returns a list of (id, title, url) tuples for the team's recent
    condensed game video(s). Teams in MLB_LINK_TEAMS use MLB's own Stats
    API (mlb.com links); everyone else uses YouTube search.
    """
    if team.lower() in MLB_LINK_TEAMS:
        result = get_recent_condensed_game_mlb(team)
        if result is None:
            print(f'  No condensed game found on mlb.com for {team} yet.')
            return []
        headline, url = result
        # Use the mlb.com slug (last URL segment) as the unique dedupe ID —
        # plays the same role the YouTube video ID plays for other teams.
        video_id = url.rstrip('/').split('/')[-1]
        print(f'  Found via MLB Stats API: "{headline}"')
        return [(video_id, headline, url)]
    else:
        return get_recent_condensed_games_youtube(team)


def send_notification(team, title, url):
    """Sends a push notification via ntfy.sh to a team-specific topic."""
    topic_suffix = team.lower().replace(' ', '-')
    topic = f'{NTFY_TOPIC}-{topic_suffix}'
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
    print(f'Notification sent to {topic}: {title} -> {url}')


if __name__ == '__main__':
    if not in_season():
        print(f'Off-season ({date.today()}). Exiting.')
        exit(0)

    seen =
