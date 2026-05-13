# MLB Condensed Game Notifier

Get a push notification on your phone when your team's condensed game is available
on YouTube — no spoilers, no browsing required.

Uses GitHub Actions (free) to poll YouTube every 30 minutes and
[ntfy](https://ntfy.sh) to deliver a push notification directly to your phone.
Tapping the notification opens the video immediately.

## How it works

1. GitHub Actions runs a Python script every 30 minutes from 5pm–5am ET
2. The script searches MLB's YouTube channel for a new condensed game for your team
3. If a new one is found, it sends a push notification via ntfy to your phone
4. Tapping the notification opens the YouTube video directly

## Setup

### 1. Install ntfy on your phone

- [Android (Play Store)](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
- [iOS (App Store)](https://apps.apple.com/us/app/ntfy/id1625396347)

Open the app and subscribe to a topic. Pick something unique to you —
for example `alice-cubs-condensed`. Anyone who knows your topic name could
send you notifications, so avoid anything too obvious.

### 2. Fork this repo

Click **Fork** in the top right corner of this page.

### 3. Get a YouTube Data API key

1. Go to the [Google Cloud Console](https://console.developers.google.com)
2. Create a new project
3. Enable the **YouTube Data API v3**
4. Go to **Credentials** → **Create Credentials** → **API key**
5. Copy the key

The free quota is extremely generous — this project uses a tiny fraction of it.

### 4. Configure your fork

In your forked repo, go to **Settings** → **Secrets and variables** → **Actions**.

Add the following **Secrets** (sensitive, hidden):

| Name | Value |
|---|---|
| `YOUTUBE_API_KEY` | Your YouTube Data API key from step 3 |
| `NTFY_TOPIC` | Your ntfy topic name from step 1 |

Add the following **Variable** (not sensitive):

| Name | Value |
|---|---|
| `MLB_TEAM` | Your team name, e.g. `Red Sox`, `Cubs`, `Dodgers` |

Use the team name as it commonly appears in YouTube video titles.
If notifications aren't coming through, check the Actions logs and
try adjusting the name to match how MLB titles their videos.

### 5. Test it

Go to the **Actions** tab in your repo, select **Check for MLB Condensed Game**,
and click **Run workflow**. Check the logs to confirm it ran without errors.

After that, the schedule takes over automatically.

## Supported teams

Any MLB team works — just set `MLB_TEAM` to the team name as it appears in
YouTube titles. Examples: `Red Sox`, `Yankees`, `Dodgers`, `Cubs`, `Mets`,
`Braves`, `Astros`.

## Troubleshooting

**No notification during a game day** — Check the Actions tab for recent runs
and look at the logs. The most common issue is the team name not matching
how MLB titles their YouTube videos.

**Notifications firing repeatedly for the same game** — Make sure the workflow
has write permissions to commit `seen_videos.json`. Go to Settings →
Actions → General → Workflow permissions and set to "Read and write permissions."

**GitHub Actions not running on schedule** — GitHub may pause scheduled workflows
in forked repos by default. Go to the Actions tab and enable them if prompted.
Also note: GitHub's scheduler can run up to ~15 minutes late during busy periods.

## Notes

- The schedule runs 5pm–5am ET, covering games that end late on the west coast
- The script looks back 12 hours to catch any games it might have missed
- `seen_videos.json` is committed back to your repo to prevent duplicate notifications
