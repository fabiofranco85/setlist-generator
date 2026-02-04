# YouTube Playlist Integration

Create unlisted YouTube playlists from your setlists with a single command.

## Prerequisites

1. A Google account with access to YouTube
2. Google Cloud project with YouTube Data API v3 enabled
3. OAuth 2.0 client credentials (`client_secrets.json`)
4. YouTube video URLs added to songs in `database.csv`

## Google Cloud Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** (top bar) > **New Project**
3. Name it (e.g., "Songbook YouTube") and click **Create**

### 2. Enable YouTube Data API v3

1. Go to **APIs & Services** > **Library**
2. Search for **YouTube Data API v3**
3. Click **Enable**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** user type, click **Create**
3. Fill in the required fields (App name, User support email, Developer email)
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes**
6. Find and add `https://www.googleapis.com/auth/youtube`
7. Click **Save and Continue**
8. On the **Test Users** page, add your Google email address
9. Click **Save and Continue**, then **Back to Dashboard**

### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth Client ID**
3. Application type: **Desktop application**
4. Name it (e.g., "Songbook CLI")
5. Click **Create**
6. Click **Download JSON** on the confirmation dialog
7. Rename the downloaded file to `client_secrets.json`
8. Place it in the project root (same directory as `database.csv`)

The file is automatically gitignored for security.

## Adding YouTube Links to Songs

Edit `database.csv` and add YouTube URLs to the `youtube` column:

```csv
song;energy;tags;youtube
Oceanos;3;louvor(2);https://www.youtube.com/watch?v=XXXXXXXXXXX
Hosana;3;louvor;https://youtu.be/YYYYYYYYYYY
Lugar Secreto;4;louvor;
```

**Supported URL formats:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

Songs without YouTube links are still valid for setlist generation. The `youtube` command simply skips them when building the playlist.

## Usage

```bash
# Create playlist from the latest setlist
songbook youtube

# Create playlist for a specific date
songbook youtube --date 2026-02-15
```

### First Run Authentication

On the first run, a browser window will open asking you to authorize the application:

1. Sign in with your Google account
2. Click **Continue** on the consent screen
3. Grant YouTube access
4. The browser will show "The authentication flow has completed"
5. Return to the terminal — the playlist will be created

After the first authentication, a token is cached in `.youtube_token.json` (gitignored). Subsequent runs will reuse the cached token.

### Example Output

```
Loading songs...
Loaded 56 songs

Loading history...
Found 15 historical setlists

Creating YouTube playlist for 2026-02-15...
Moments:
  Prelúdio: Estamos de Pé
  Ofertório: Agradeço
  Louvor: Hosana, Oceanos, Perfeito Amor, Lugar Secreto
  Poslúdio: Autoridade e Poder

Warning: 3 song(s) without YouTube links (will be skipped):
  - Agradeço
  - Estamos de Pé
  - Autoridade e Poder

4 song(s) will be added to the playlist.

Authenticating with YouTube...

============================================================
YOUTUBE PLAYLIST CREATED
============================================================

Playlist URL: https://www.youtube.com/playlist?list=PLxxxxxxxxxx

Added (4 songs):
  1. Hosana
  2. Oceanos
  3. Perfeito Amor
  4. Lugar Secreto

Skipped (3 songs, no YouTube link):
  - Agradeço
  - Estamos de Pé
  - Autoridade e Poder
```

## Configuration

Settings in `library/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `YOUTUBE_PLAYLIST_NAME_PATTERN` | `"Culto {DD.MM.YY}"` | Playlist title pattern |
| `YOUTUBE_PLAYLIST_PRIVACY` | `"unlisted"` | Privacy: `public`, `unlisted`, or `private` |
| `YOUTUBE_CLIENT_SECRETS_FILE` | `"client_secrets.json"` | Path to OAuth client secrets |
| `YOUTUBE_TOKEN_FILE` | `".youtube_token.json"` | Path to cached auth token |

### Playlist Name Patterns

Available placeholders:
- `{DD.MM.YY}` - Day.Month.ShortYear (e.g., `15.02.26`)
- `{DD.MM.YYYY}` - Day.Month.FullYear (e.g., `15.02.2026`)
- `{YYYY-MM-DD}` - ISO format (e.g., `2026-02-15`)

Examples:
```python
YOUTUBE_PLAYLIST_NAME_PATTERN = "Culto {DD.MM.YY}"       # "Culto 15.02.26"
YOUTUBE_PLAYLIST_NAME_PATTERN = "Worship {YYYY-MM-DD}"    # "Worship 2026-02-15"
YOUTUBE_PLAYLIST_NAME_PATTERN = "Service {DD.MM.YYYY}"    # "Service 15.02.2026"
```

## Troubleshooting

### "OAuth client secrets file not found"

Place `client_secrets.json` in the project root. See [Google Cloud Setup](#google-cloud-setup) above.

### "Google API libraries not installed"

Run:
```bash
uv sync
```

### "No songs in this setlist have YouTube links"

Add YouTube URLs to the `youtube` column in `database.csv` for at least some songs in the setlist.

### Token expired or invalid

Delete `.youtube_token.json` and run the command again. A new browser authentication will be triggered.

```bash
rm .youtube_token.json
songbook youtube
```

### "Access blocked: This app's request is invalid" (Error 400)

This happens when the OAuth consent screen is not properly configured. Check:
1. The YouTube Data API v3 is enabled
2. Your email is added as a test user
3. The `youtube` scope is added to the consent screen

### API Quota

YouTube Data API v3 has a daily quota of **10,000 units**. Approximate costs:
- Create playlist: ~50 units
- Add video to playlist: ~50 units per video
- A typical 9-song setlist: ~500 units

This allows approximately **20 playlists per day** with the default quota.
