"""Supabase song repository with multi-tenant visibility."""

from __future__ import annotations

from typing import Any

from ...models import Song
from ...loader import parse_tags


class SupabaseSongRepository:
    """Song repository backed by Supabase with layered visibility.

    Songs are visible based on RLS policies:
    - global: visible to all
    - org: visible to org members
    - user: visible only to the owner

    The effective library merges all visible songs with priority:
    user > org > global.
    """

    def __init__(self, client: Any, org_id: str):
        self._client = client
        self._org_id = org_id
        self._cache: dict[str, Song] | None = None
        self._uuid_map: dict[str, str] = {}  # title -> UUID

    def _invalidate_cache(self) -> None:
        self._cache = None
        self._uuid_map.clear()

    def get_all(self) -> dict[str, Song]:
        """Get all visible songs (delegates to get_effective_library)."""
        return self.get_effective_library()

    def get_effective_library(self) -> dict[str, Song]:
        """Get the merged song library visible to the current user.

        RLS policies automatically filter songs by visibility.
        Songs are ordered by visibility priority (global first, then org, then user)
        so that dict.update() gives user songs highest priority.
        """
        if self._cache is not None:
            return dict(self._cache)

        response = (
            self._client.table("songs")
            .select("id, title, energy, youtube_url, visibility, content_s3_key, "
                    "song_tags(moment, weight), song_event_types(event_type_slug)")
            .eq("status", "active")
            .order("visibility")  # global < org < user
            .execute()
        )

        songs: dict[str, Song] = {}
        for row in response.data:
            tags = {t["moment"]: t["weight"] for t in (row.get("song_tags") or [])}
            event_types = [e["event_type_slug"] for e in (row.get("song_event_types") or [])]

            song = Song(
                title=row["title"],
                tags=tags,
                energy=row["energy"],
                content="",  # Loaded on demand from S3
                youtube_url=row.get("youtube_url") or "",
                event_types=event_types,
            )
            songs[row["title"]] = song
            self._uuid_map[row["title"]] = row["id"]

        self._cache = songs
        return dict(songs)

    def get_by_title(self, title: str) -> Song | None:
        """Get a single song by title."""
        library = self.get_all()
        return library.get(title)

    def search(self, query: str) -> list[Song]:
        """Search songs by title (case-insensitive)."""
        response = (
            self._client.table("songs")
            .select("id, title, energy, youtube_url, visibility, "
                    "song_tags(moment, weight), song_event_types(event_type_slug)")
            .eq("status", "active")
            .ilike("title", f"%{query}%")
            .execute()
        )

        results = []
        for row in response.data:
            tags = {t["moment"]: t["weight"] for t in (row.get("song_tags") or [])}
            event_types = [e["event_type_slug"] for e in (row.get("song_event_types") or [])]
            results.append(Song(
                title=row["title"],
                tags=tags,
                energy=row["energy"],
                content="",
                youtube_url=row.get("youtube_url") or "",
                event_types=event_types,
            ))
        return results

    def update_content(self, title: str, content: str) -> None:
        """Update song content (stores S3 key, actual content in S3)."""
        uuid = self._uuid_map.get(title)
        if not uuid:
            self.get_all()
            uuid = self._uuid_map.get(title)
        if not uuid:
            raise KeyError(f"Song '{title}' not found")

        self._client.table("songs").update(
            {"content_s3_key": content}
        ).eq("id", uuid).execute()
        self._invalidate_cache()

    def exists(self, title: str) -> bool:
        """Check if a song exists."""
        library = self.get_all()
        return title in library

    def create(self, song: Song, visibility: str = "user") -> str:
        """Create a new song.

        Args:
            song: Song to create
            visibility: 'user', 'org', or 'global'

        Returns:
            Title of the created song
        """
        data: dict[str, Any] = {
            "title": song.title,
            "energy": song.energy,
            "youtube_url": song.youtube_url,
            "visibility": visibility,
            "org_id": self._org_id,
        }

        response = self._client.table("songs").insert(data).execute()
        song_id = response.data[0]["id"]

        # Insert tags
        if song.tags:
            tag_rows = [
                {"song_id": song_id, "moment": moment, "weight": weight}
                for moment, weight in song.tags.items()
            ]
            self._client.table("song_tags").insert(tag_rows).execute()

        # Insert event type bindings
        if song.event_types:
            et_rows = [
                {"song_id": song_id, "event_type_slug": slug}
                for slug in song.event_types
            ]
            self._client.table("song_event_types").insert(et_rows).execute()

        self._invalidate_cache()
        return song.title

    def delete(self, title: str) -> None:
        """Delete a song (cascades to tags and event types)."""
        uuid = self._uuid_map.get(title)
        if not uuid:
            self.get_all()
            uuid = self._uuid_map.get(title)
        if not uuid:
            raise KeyError(f"Song '{title}' not found")

        self._client.table("songs").delete().eq("id", uuid).execute()
        self._invalidate_cache()

    def fork(self, title: str, overrides: dict) -> str:
        """Fork a song with modifications."""
        source = self.get_by_title(title)
        if not source:
            raise KeyError(f"Song '{title}' not found")

        parent_uuid = self._uuid_map.get(title)
        new_title = overrides.get("title", f"{title} (fork)")

        data: dict[str, Any] = {
            "title": new_title,
            "energy": overrides.get("energy", source.energy),
            "youtube_url": overrides.get("youtube_url", source.youtube_url),
            "visibility": "user",
            "org_id": self._org_id,
            "parent_id": parent_uuid,
        }

        response = self._client.table("songs").insert(data).execute()
        song_id = response.data[0]["id"]

        # Copy tags (potentially overridden)
        tags = overrides.get("tags", source.tags)
        if tags:
            tag_rows = [
                {"song_id": song_id, "moment": m, "weight": w}
                for m, w in tags.items()
            ]
            self._client.table("song_tags").insert(tag_rows).execute()

        self._invalidate_cache()
        return new_title

    def share_to_org(self, title: str) -> None:
        """Promote a user-level song to org visibility."""
        uuid = self._uuid_map.get(title)
        if not uuid:
            self.get_all()
            uuid = self._uuid_map.get(title)
        if not uuid:
            raise KeyError(f"Song '{title}' not found")

        self._client.table("songs").update(
            {"visibility": "org"}
        ).eq("id", uuid).execute()
        self._invalidate_cache()

    def request_global_share(self, title: str) -> str:
        """Submit a request to promote a song to global visibility."""
        uuid = self._uuid_map.get(title)
        if not uuid:
            self.get_all()
            uuid = self._uuid_map.get(title)
        if not uuid:
            raise KeyError(f"Song '{title}' not found")

        # Update song status to pending_review
        self._client.table("songs").update(
            {"status": "pending_review"}
        ).eq("id", uuid).execute()

        # Create share request
        response = self._client.table("share_requests").insert({
            "song_id": uuid,
            "org_id": self._org_id,
        }).execute()

        self._invalidate_cache()
        return response.data[0]["id"]
