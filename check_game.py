import os, json, requests
from datetime import date, timedelta
from pathlib import Path

# --- Configuration (set via GitHub Actions secrets/variables) ---
NTFY_TOPIC = os.environ['NTFY_TOPIC']

# MLB_TEAM can be a single team ("Red Sox") or comma-separated ("Red Sox, Tigers")
TEAMS = [t.strip() for t in os.environ.get('MLB_TEAM', 'Red Sox').split(',')]

SEEN_FILE = 'seen_videos.json'  # tracks already-notified videos, keyed per team

# Script only runs during baseball season — exits early otherwise
SEASON_START = (3, 1)    # March 1  (covers spring training)
SEASON_END   = (11, 15)  # November 15 (covers full postseason)

# MLB Stats API team IDs — used to look up each team's recent games
TEAM_IDS = {
    'angels': 108, 'diamondbacks': 109, 'orioles': 110, 'red sox': 111,
    'cubs': 112, 'reds': 113, 'guardians': 114, 'rockies': 115,
    'tigers': 116, 'astros': 117, 'royals': 118, 'dodgers': 119,
    'nationals': 120, 'mets': 121, 'athletics': 133, 'pirates': 134,
    'padres': 135, 'mariners': 136, 'giants': 137, 'cardinals': 138,
    'rays': 139, 'rangers': 140, 'blue jays': 141, 'twins': 142,
    'phillies': 143, 'braves': 144, 'white sox': 145, 'marlins': 146,
    'yankees': 147, 'brewers': 158,
}

SCHEDULE_URL = 'https://statsapi.mlb.com/api/v1/schedule'
CONTENT_URL  = 'https://statsapi.mlb.com/api/v1/game/{game_pk}/content'


def in_season():
    """Returns True if today falls within the configured season window."""
    today = date.today()
    start = date(today.year, *SEASON_START)
    end   = date(today.year, *SEASON_END)
    return start <= today <= end


def load_seen():
    """
    Loads already-notified video IDs, keyed per team, e.g.:
      {"Red Sox": ["condensed-game-..."], "Tigers": ["condensed-game-..."]}
    Nesting by team means you can clear one team's history without
    touching any other team's data — just edit that team's list in the file.
    """
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def save_seen(seen):
    """Persists the seen-videos dict so it survives across runs."""
    with open(SEEN_FILE, 'w') as f:
        json.dump(seen, f, indent=2)


def get_recent_game_pks(team, days_back=2):
    """Returns gamePk values for the team's games over the last `days_back` days."""
    team_id = TEAM_IDS.get(team.lower())
    if team_id is None:
        print(f'  Unknown team "{team}" — check TEAM_IDS for the correct name.')
        return []

    end = date.today()
    start = end - timedelta(days=days_back)
    params = {
        'sportId': 1,
        'teamId': team_id,
        'startDate': start.strftime('%Y-%m-%d'),
        'endDate': end.strftime('%Y-%m-%d'),
    }
    r = requests.get(SCHEDULE_URL, params=params)
    r.raise_for_status()

    game_pks = []
    for day in r.json().get('dates', []):
        for game in day.get('games', []):
            game_pks.append(game['gamePk'])
    return game_pks


def get_condensed_game_link(game_pk):
    """Returns (headline, mlb.com url) for the condensed game video, or None if not posted yet."""
    r = requests.get(CONTENT_URL.format(game_pk=game_pk))
    if r.status_code != 200:
        return None

    # Use "or {}" rather than .get()'s dict-default, since the API can return
    # an explicit `null` for "highlights" on very recent/in-progress games —
    # .get('highlights', {}) would still pass that None through untouched.
    highlights = (r.json().get('highlights') or {}).get('highlights') or {}
    items = highlights.get('items', [])

    for item in items:
        headline = (item.get('headline') or '').strip()
        slug = item.get('slug')
        # MLB's own condensed game videos are headlined exactly "Condensed Game: ..."
        if 'condensed game' in headline.lower() and slug:
            return headline, f'https://www.mlb.com/video/{slug}'
    return None


def get_recent_condensed_games(team):
    """
    Returns a list of (id, title, url) tuples for the team's recent
    condensed game video, checking the most recent games first.
    A failure on any single game is logged and skipped rather than
    crashing the whole run — that way one bad response for this team
    can't prevent other teams later in TEAMS from being checked.
    """
    game_pks = get_recent_game_pks(team)
    for game_pk in reversed(game_pks):  # most recent game first
        try:
            result = get_condensed_game_link(game_pk)
        except Exception as e:
            print(f'  Error checking game {game_pk}: {e}')
            continue

        if result:
            headline, url = result
            # Use the mlb.com slug (last URL segment) as the unique dedupe ID
            video_id = url.rstrip('/').split('/')[-1]
            print(f'  Found via MLB Stats API: "{headline}"')
            return [(video_id, headline, url)]

    print(f'  No condensed game found on mlb.com for {team} yet.')
    return []


def send_notification(team, title, url):
    """Sends a push notification via ntfy.sh to a team-specific topic."""
    topic_suffix = team.lower().replace(' ', '-')  # "Red Sox" -> "red-sox"
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
    print(f'Notification sent to {topic}: {title} -> {url}')


if __name__ == '__main__':
    if not in_season():
        print(f'Off-season ({date.today()}). Exiting.')
        exit(0)

    seen = load_seen()
    new_count = 0

    for team in TEAMS:
        print(f'Checking for {team} condensed game...')
        team_seen = set(seen.get(team, []))
        videos = get_recent_condensed_games(team)

        for vid, title, url in videos:
            if vid not in team_seen:
                send_notification(team, title, url)
                team_seen.add(vid)
                new_count += 1
            else:
                print(f'  Already notified: "{title}" — skipping.')

        seen[team] = list(team_seen)

    save_seen(seen)

    if new_count:
        print(f'Sent {new_count} notification(s).')
    else:
        print(f'No new condensed games found for {", ".join(TEAMS)}.')
