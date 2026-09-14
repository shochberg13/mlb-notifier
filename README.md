# MLB Condensed Game Notifier

Get a push notification on your phone when your team's condensed game is
available — no spoilers, no browsing required. Completely free!

Uses GitHub Actions (free) to poll MLB's own Stats API and
[ntfy](https://ntfy.sh) to deliver a push notification directly to your phone.
Tapping the notification opens the condensed game on mlb.com immediately.

## How it works

1. GitHub Actions runs a Python script on a schedule throughout the evening
   and once in the early morning (see schedule below).
2. The script checks MLB's own Stats API for each configured team's recent
   games, looking for a "Condensed Game" video entry.
3. If a new one is found, it sends a push notification via ntfy to your phone.
4. Tapping the notification opens the video directly on mlb.com.

No API key, no quota limits, no YouTube — this pulls directly from MLB's
public Stats API, which is free and unauthenticated.

## Two ways to use this

### Option A: Easy mode (just want notifications, no setup)

If someone you know is already running this for your team, you don't need to
fork anything or touch GitHub at all. Just:

1. Install ntfy: [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) | [iOS](https://apps.apple.com/us/app/ntfy/id1625396347)
2. Subscribe to the topic they give you for your team (e.g. `seth-mlb-notifier-tigers`)
3. Done. You'll get a push notification whenever that team's condensed game is posted.

Each team gets its own topic, so you only get notified for the team you
subscribe to, even if the person running it tracks many teams. You have zero
control over the schedule in this mode — if that's all you want, stop reading here.

### Option B: Full control (run your own copy)

If you want your own schedule, your own team list, or just don't want to rely
on someone else keeping their repo running, fork this repo and run your own
independent copy. Takes about 10 minutes.

## Setup

### 1. Install ntfy on your phone

- [Android (Play Store)](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
- [iOS (App Store)](https://apps.apple.com/us/app/ntfy/id1625396347)

You'll subscribe to specific topics once your fork is running (step 4 explains
the naming).

### 2. Fork this repo

Click **Fork** in the top right corner of this page.

### 3. Configure your fork

In your forked repo, go to **Settings** → **Secrets and variables** → **Actions**.

Add the following **Secret** (sensitive, hidden):

| Name | Value |
|---|---|
| `NTFY_TOPIC` | A base topic name unique to you, e.g. `alice-mlb-notifier` |

Add the following **Variable** (not sensitive):

| Name | Value |
|---|---|
| `MLB_TEAM` | One or more teams, comma-separated, e.g. `Red Sox, Tigers, Phillies` |

**Important:** use the short team name exactly as it appears in the `TEAM_IDS`
dictionary at the top of `check_game.py` (e.g. `Tigers`, not `Detroit Tigers`).
All 30 teams are supported — see the full list below.

For each team, a separate ntfy topic is generated automatically as
`{NTFY_TOPIC}-{team-name}` (spaces become hyphens, lowercased). For example,
with `NTFY_TOPIC = alice-mlb-notifier` and `MLB_TEAM = Red Sox, Tigers`,
subscribe to:
- `alice-mlb-notifier-red-sox`
- `alice-mlb-notifier-tigers`

This lets you share individual team topics with friends (Option A above)
without them needing to fork or configure anything.

### 4. Set write permissions

Go to **Settings** → **Actions** → **General** → **Workflow permissions**,
and select **Read and write permissions**. This lets the workflow save its
dedupe history back to the repo.

### 5. Test it

Go to the **Actions** tab, select **Check for MLB Condensed Game**, and click
**Run workflow**. Check the logs to confirm it ran without errors.

After that, the schedule takes over automatically.

## Supported teams

Use these short names in `MLB_TEAM`:

`Angels`, `Diamondbacks`, `Orioles`, `Red Sox`, `Cubs`, `Reds`, `Guardians`,
`Rockies`, `Tigers`, `Astros`, `Royals`, `Dodgers`, `Nationals`, `Mets`,
`Athletics`, `Pirates`, `Padres`, `Mariners`, `Giants`, `Cardinals`, `Rays`,
`Rangers`, `Blue Jays`, `Twins`, `Phillies`, `Braves`, `White Sox`, `Marlins`,
`Yankees`, `Brewers`

## Schedule

The workflow runs hourly from 5pm to midnight ET, plus one additional check
around 4am ET to catch late-ending west coast games before typical wake-up
time. No changes needed for daylight saving — the schedule is built to stay
close enough year-round without manual adjustment.

## Troubleshooting

**No notification during a game day** — Check the Actions tab for recent
runs and look at the logs. The most common cause is a team name in
`MLB_TEAM` that doesn't match a key in `TEAM_IDS` — check spelling against
the supported teams list above. The logs will also show "No condensed game
found" if MLB simply hasn't posted one yet.

**Notifications firing repeatedly for the same game** — Make sure write
permissions are enabled (step 4 above) so `seen_videos.json` can be
committed back to the repo. If it can't be saved, the script has no memory
between runs.

**GitHub Actions not running on schedule** — GitHub may pause scheduled
workflows in forked repos by default; check the Actions tab and enable them
if prompted. GitHub's scheduler can also run behind — sometimes by an hour
or more — during periods of high platform load.

## Notes

- `seen_videos.json` tracks notified games per team (nested by team name),
  so you can clear one team's history without affecting any other team.
- The script only runs during baseball season (March 1 – November 15);
  outside that window it exits immediately without making any API calls.
- No API key or quota to manage — MLB's Stats API is free and unauthenticated.
