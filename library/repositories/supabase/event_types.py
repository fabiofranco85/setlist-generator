"""Supabase event type repository (org-scoped)."""

from __future__ import annotations

from typing import Any

from ...event_type import EventType, DEFAULT_EVENT_TYPE_SLUG


class SupabaseEventTypeRepository:
    """Event type repository backed by Supabase.

    Event types are org-scoped — each org has its own set of event types.
    """

    def __init__(self, client: Any, org_id: str):
        self._client = client
        self._org_id = org_id
        self._cache: dict[str, EventType] | None = None

    def _invalidate_cache(self) -> None:
        self._cache = None

    def get_all(self) -> dict[str, EventType]:
        if self._cache is not None:
            return dict(self._cache)

        response = (
            self._client.table("event_types")
            .select("slug, name, description, moments")
            .eq("org_id", self._org_id)
            .execute()
        )

        result: dict[str, EventType] = {}
        for row in response.data:
            et = EventType(
                slug=row["slug"],
                name=row["name"],
                description=row.get("description") or "",
                moments=row["moments"],
            )
            result[row["slug"]] = et

        self._cache = result
        return dict(result)

    def get(self, slug: str) -> EventType | None:
        all_types = self.get_all()
        return all_types.get(slug)

    def get_default_slug(self) -> str:
        return DEFAULT_EVENT_TYPE_SLUG

    def add(self, event_type: EventType) -> None:
        existing = self.get(event_type.slug)
        if existing:
            raise ValueError(f"Event type '{event_type.slug}' already exists")

        self._client.table("event_types").insert({
            "org_id": self._org_id,
            "slug": event_type.slug,
            "name": event_type.name,
            "description": event_type.description,
            "moments": event_type.moments,
        }).execute()

        self._invalidate_cache()

    def update(self, slug: str, **kwargs: Any) -> None:
        existing = self.get(slug)
        if not existing:
            raise KeyError(f"Event type '{slug}' not found")

        update_data = {}
        if "name" in kwargs:
            update_data["name"] = kwargs["name"]
        if "description" in kwargs:
            update_data["description"] = kwargs["description"]
        if "moments" in kwargs:
            update_data["moments"] = kwargs["moments"]

        if update_data:
            (
                self._client.table("event_types")
                .update(update_data)
                .eq("org_id", self._org_id)
                .eq("slug", slug)
                .execute()
            )

        self._invalidate_cache()

    def remove(self, slug: str) -> None:
        if slug == DEFAULT_EVENT_TYPE_SLUG:
            raise ValueError("Cannot remove the default event type")

        existing = self.get(slug)
        if not existing:
            raise KeyError(f"Event type '{slug}' not found")

        (
            self._client.table("event_types")
            .delete()
            .eq("org_id", self._org_id)
            .eq("slug", slug)
            .execute()
        )

        self._invalidate_cache()
