"""
YouTube command - create YouTube playlist from existing setlist.
"""

from library import (
    get_repositories,
    resolve_setlist_videos,
)


def run(date, output_dir, history_dir, label="", event_type=""):
    """
    Create a YouTube playlist from an existing setlist.

    Args:
        date: Target date (YYYY-MM-DD) or None for latest
        output_dir: Custom output directory
        history_dir: Custom history directory
        label: Optional label for multiple setlists per date
        event_type: Optional event type slug
    """
    from cli.cli_utils import resolve_paths, handle_error, validate_label, find_setlist_or_fail, resolve_event_type

    label = validate_label(label)

    # Paths
    paths = resolve_paths(output_dir, history_dir)
    history_dir_path = paths.history_dir

    # Load data via repositories
    repos = get_repositories(history_dir=history_dir_path)

    # Resolve event type
    et = resolve_event_type(repos, event_type)
    et_slug = event_type
    et_name = et.name if et and not (et_slug == "" or et_slug == "main") else ""

    print("Loading songs...")
    songs = repos.songs.get_all()
    print(f"Loaded {len(songs)} songs")

    # Find target setlist
    target_setlist = find_setlist_or_fail(repos, date, label, event_type=et_slug)

    target_date = target_setlist["date"]
    target_label = target_setlist.get("label", "")

    # Display setlist
    header = f"\nCreating YouTube playlist for {target_date}"
    if et_name:
        header += f" | {et_name}"
    if target_label:
        header += f" ({target_label})"
    print(header + "...")
    print("Moments:")
    for moment, song_list in target_setlist["moments"].items():
        display_moment = moment.capitalize()
        print(f"  {display_moment}: {', '.join(song_list)}")

    # Resolve videos and show status
    video_entries = resolve_setlist_videos(target_setlist, songs)

    added = [(title, vid) for title, vid in video_entries if vid]
    skipped = [title for title, vid in video_entries if not vid]

    if skipped:
        print(f"\nWarning: {len(skipped)} song(s) without YouTube links (will be skipped):")
        for title in skipped:
            print(f"  - {title}")

    if not added:
        handle_error(
            "No songs in this setlist have YouTube links.\n"
            "Add YouTube URLs to the 'youtube' column in database.csv."
        )

    print(f"\n{len(added)} song(s) will be added to the playlist.")

    # Import YouTube API dependencies
    try:
        from library.youtube import (
            create_setlist_playlist,
            get_credentials,
        )
        from library.config import (
            YOUTUBE_CLIENT_SECRETS_FILE,
            YOUTUBE_TOKEN_FILE,
        )
    except ImportError:
        print("\nError: Google API libraries not installed.")
        print("Install with: uv sync            (installs all dependencies)")
        print("         or: uv add google-api-python-client google-auth-oauthlib google-auth-httplib2")
        raise SystemExit(1)

    # Authenticate
    print("\nAuthenticating with YouTube...")
    try:
        credentials = get_credentials(
            client_secrets_path=YOUTUBE_CLIENT_SECRETS_FILE,
            token_path=YOUTUBE_TOKEN_FILE,
        )
    except FileNotFoundError as e:
        handle_error(str(e))
    except Exception as e:
        handle_error(f"Authentication failed: {e}")

    # Create playlist
    try:
        playlist_url, added_songs, skipped_songs = create_setlist_playlist(
            setlist_dict=target_setlist,
            songs=songs,
            credentials=credentials,
            event_type_name=et_name,
        )
    except Exception as e:
        handle_error(f"Creating playlist: {e}")

    # Display summary
    print(f"\n{'=' * 60}")
    print(f"YOUTUBE PLAYLIST CREATED")
    print(f"{'=' * 60}")
    print(f"\nPlaylist URL: {playlist_url}")
    print(f"\nAdded ({len(added_songs)} songs):")
    for i, title in enumerate(added_songs, 1):
        print(f"  {i}. {title}")

    if skipped_songs:
        print(f"\nSkipped ({len(skipped_songs)} songs, no YouTube link):")
        for title in skipped_songs:
            print(f"  - {title}")
