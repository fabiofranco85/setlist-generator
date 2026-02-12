"""YouTube playlist integration for setlist generation.

Pure functions for URL parsing and playlist name formatting,
plus API functions for OAuth and playlist management.
"""

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import (
    MOMENTS_CONFIG,
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_PLAYLIST_NAME_PATTERN,
    YOUTUBE_PLAYLIST_PRIVACY,
    YOUTUBE_TOKEN_FILE,
)


# --- Pure functions (no external deps) ---


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from a URL.

    Handles:
      - https://www.youtube.com/watch?v=XXXXXXXXXXX
      - https://youtu.be/XXXXXXXXXXX
      - https://www.youtube.com/embed/XXXXXXXXXXX

    Returns None for invalid or unrecognized URLs.
    """
    if not url or not url.strip():
        return None

    url = url.strip()

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    # youtube.com/watch?v=ID
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            video_ids = qs.get("v")
            if video_ids:
                return video_ids[0]
        # youtube.com/embed/ID
        if parsed.path.startswith("/embed/"):
            video_id = parsed.path.split("/embed/")[1].split("/")[0]
            if video_id:
                return video_id

    # youtu.be/ID
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
        if video_id:
            return video_id

    return None


def format_playlist_name(date_str: str, pattern: str = YOUTUBE_PLAYLIST_NAME_PATTERN) -> str:
    """Format playlist title from date string and pattern.

    Pattern placeholders:
      {DD.MM.YY}  -> 15.02.26
      {DD.MM.YYYY} -> 15.02.2026
      {YYYY-MM-DD} -> 2026-02-15

    Args:
        date_str: Date in YYYY-MM-DD format
        pattern: Name pattern with placeholders

    Returns:
        Formatted playlist name
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    result = pattern
    result = result.replace("{DD.MM.YY}", dt.strftime("%d.%m.%y"))
    result = result.replace("{DD.MM.YYYY}", dt.strftime("%d.%m.%Y"))
    result = result.replace("{YYYY-MM-DD}", date_str)

    return result


def resolve_setlist_videos(
    setlist_dict: dict,
    songs: dict,
) -> list[tuple[str, str | None]]:
    """Map setlist songs to (title, video_id_or_none) in MOMENTS_CONFIG order.

    Args:
        setlist_dict: Setlist dict with "moments" key
        songs: Dict of {title: Song} with youtube_url field

    Returns:
        List of (song_title, video_id_or_none) in moment order
    """
    result = []

    for moment in MOMENTS_CONFIG:
        song_titles = setlist_dict.get("moments", {}).get(moment, [])
        for title in song_titles:
            song = songs.get(title)
            video_id = None
            if song and song.youtube_url:
                video_id = extract_video_id(song.youtube_url)
            result.append((title, video_id))

    return result


# --- API functions (require google-api-python-client) ---


def get_credentials(
    client_secrets_path: str = YOUTUBE_CLIENT_SECRETS_FILE,
    token_path: str = YOUTUBE_TOKEN_FILE,
):
    """Get OAuth 2.0 credentials for YouTube API.

    Loads cached token from token_path if available and valid.
    Otherwise, launches browser-based OAuth consent flow.

    Args:
        client_secrets_path: Path to OAuth client secrets JSON
        token_path: Path to cached token file

    Returns:
        google.oauth2.credentials.Credentials object

    Raises:
        FileNotFoundError: If client_secrets_path doesn't exist
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/youtube"]

    secrets_file = Path(client_secrets_path)
    if not secrets_file.exists():
        raise FileNotFoundError(
            f"OAuth client secrets file not found: {client_secrets_path}\n"
            "See YOUTUBE.md for setup instructions."
        )

    token_file = Path(token_path)
    creds = None

    # Load cached token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets_file), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Cache token with restricted permissions (owner read/write only)
        token_file.write_text(creds.to_json())
        token_file.chmod(0o600)

    return creds


def create_playlist(credentials, title: str, description: str = "", privacy: str = YOUTUBE_PLAYLIST_PRIVACY) -> str:
    """Create a YouTube playlist.

    Args:
        credentials: OAuth 2.0 credentials
        title: Playlist title
        description: Playlist description
        privacy: Privacy status (public, unlisted, private)

    Returns:
        Playlist ID string
    """
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", credentials=credentials)

    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": privacy,
            },
        },
    )
    response = request.execute()
    return response["id"]


def add_video_to_playlist(credentials, playlist_id: str, video_id: str, position: int) -> None:
    """Add a video to a YouTube playlist at a specific position.

    Args:
        credentials: OAuth 2.0 credentials
        playlist_id: Target playlist ID
        video_id: YouTube video ID to add
        position: 0-indexed position in playlist
    """
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", credentials=credentials)

    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
                "position": position,
            },
        },
    )
    request.execute()


def create_setlist_playlist(
    setlist_dict: dict,
    songs: dict,
    credentials,
    playlist_name_pattern: str = YOUTUBE_PLAYLIST_NAME_PATTERN,
    privacy: str = YOUTUBE_PLAYLIST_PRIVACY,
) -> tuple[str, list[str], list[str]]:
    """Create a YouTube playlist from a setlist.

    Orchestrator function: creates playlist, adds all videos in order,
    skips songs without YouTube links.

    Args:
        setlist_dict: Setlist dict with "date" and "moments" keys
        songs: Dict of {title: Song} with youtube_url field
        credentials: OAuth 2.0 credentials
        playlist_name_pattern: Pattern for playlist title
        privacy: Privacy status for the playlist

    Returns:
        Tuple of (playlist_url, added_songs, skipped_songs)

    Raises:
        ValueError: If no songs in the setlist have YouTube links
    """
    date_str = setlist_dict["date"]
    label = setlist_dict.get("label", "")
    playlist_title = format_playlist_name(date_str, playlist_name_pattern)
    if label:
        playlist_title += f" ({label})"

    # Resolve videos
    video_entries = resolve_setlist_videos(setlist_dict, songs)

    added_songs = []
    skipped_songs = []

    for title, video_id in video_entries:
        if video_id:
            added_songs.append(title)
        else:
            skipped_songs.append(title)

    if not added_songs:
        raise ValueError(
            "No songs in this setlist have YouTube links. "
            "Add YouTube URLs to the 'youtube' column in database.csv."
        )

    # Create playlist
    description = f"Setlist for {date_str}"
    if label:
        description += f" ({label})"
    playlist_id = create_playlist(
        credentials,
        title=playlist_title,
        description=description,
        privacy=privacy,
    )

    # Add videos in order
    position = 0
    for title, video_id in video_entries:
        if video_id:
            add_video_to_playlist(credentials, playlist_id, video_id, position)
            position += 1

    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    return playlist_url, added_songs, skipped_songs
