"""
Fetches condensed game video links directly from MLB's own Stats API
(statsapi.mlb.com) instead of YouTube. Used for teams in MLB_LINK_TEAMS
(see check_game.py) to avoid youtube.com links entirely — MLB hosts these
videos on mlb.com, a completely separate domain.

No API key required — this is a public, unauthenticated API.
"""

import requests
from datetime import date, timedelta

# MLB Stats API team IDs — add more here if you ever add more teams to MLB_LINK_TEAMS
TEAM_IDS = {
    'angels': 108, 
    'diamondbacks': 109, 
    'orioles': 110, 
    'red sox': 111,
    'cubs': 112, 
    'reds': 113,
    'guardians': 114,
    'rockies': 115,
    'tigers': 116, 
    'astros': 117, 
    'royals': 118, 
    'dodgers': 119,
    'nationals': 120,
    'mets': 121,
    'athletics': 133,
    'pirates': 134,
    'padres': 135, 
    'mariners': 136,
    'giants': 137,
    'cardinals': 138,
    'rays': 139,
    'rangers': 140,
    'blue jays': 141,
    'twins': 142,
    'phillies': 143,
    'braves': 144,
    'white sox': 145,
    'marlins': 146,
    'yankees': 147,
    'brewers': 158,
}

SCHEDULE_URL = 'https://statsapi.mlb.com/api/v1/schedule'
CONTENT_URL  = 'https://statsapi.mlb.com/api/v1/game/{game_pk}/content'


def get_recent_game_pks(team, days_back=2):
    """Returns gamePk values for the team's games over the last `days_back` days."""
    team_id = TEAM_IDS.get(team.lower())
    if team_id is None:
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

    items = r.json().get('highlights', {}).get('highlights', {}).get('items', [])
    for item in items:
        headline = (item.get('headline') or '').strip()
        slug = item.get('slug')
        # MLB's own condensed game videos are headlined exactly "Condensed Game: ..."
        if 'condensed game' in headline.lower() and slug:
            return headline, f'https://www.mlb.com/video/{slug}'
    return None


def get_recent_condensed_game_mlb(team, days_back=2):
    """Checks the team's most recent games (newest first) for a condensed game video."""
    game_pks = get_recent_game_pks(team, days_back=days_back)
    for game_pk in reversed(game_pks):  # most recent game first
        result = get_condensed_game_link(game_pk)
        if result:
            return result
    return None
