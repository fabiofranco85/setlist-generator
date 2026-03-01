"""Supabase history repository for setlist tracking."""

from __future__ import annotations

from typing import Any

from ...models import Setlist


class SupabaseHistoryRepository:
    """Setlist history backed by Supabase with org-scoped access.

    History is NOT cached (unlike songs) because it changes frequently.
    RLS policies ensure only the current org's setlists are visible.
    """

    def __init__(self, client: Any, org_id: str):
        self._client = client
        self._org_id = org_id

    def get_all(self) -> list[dict]:
        """Get all setlists for the current org, most recent first."""
        response = (
            self._client.table("setlists")
            .select("date, label, event_type, moments")
            .eq("org_id", self._org_id)
            .order("date", desc=True)
            .order("label")
            .execute()
        )

        results = []
        for row in response.data:
            entry: dict[str, Any] = {
                "date": str(row["date"]),
                "moments": row["moments"],
            }
            if row.get("label"):
                entry["label"] = row["label"]
            if row.get("event_type"):
                entry["event_type"] = row["event_type"]
            results.append(entry)

        return results

    def get_by_date(self, date: str, label: str = "", event_type: str = "") -> dict | None:
        """Get a setlist by date, label, and event type."""
        query = (
            self._client.table("setlists")
            .select("date, label, event_type, moments")
            .eq("org_id", self._org_id)
            .eq("date", date)
            .eq("label", label)
            .eq("event_type", event_type)
        )

        response = query.execute()
        if not response.data:
            return None

        row = response.data[0]
        entry: dict[str, Any] = {
            "date": str(row["date"]),
            "moments": row["moments"],
        }
        if row.get("label"):
            entry["label"] = row["label"]
        if row.get("event_type"):
            entry["event_type"] = row["event_type"]
        return entry

    def get_latest(self) -> dict | None:
        """Get the most recent setlist."""
        response = (
            self._client.table("setlists")
            .select("date, label, event_type, moments")
            .eq("org_id", self._org_id)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        row = response.data[0]
        entry: dict[str, Any] = {
            "date": str(row["date"]),
            "moments": row["moments"],
        }
        if row.get("label"):
            entry["label"] = row["label"]
        if row.get("event_type"):
            entry["event_type"] = row["event_type"]
        return entry

    def save(self, setlist: Setlist) -> None:
        """Save a setlist (upsert on org_id + date + label + event_type)."""
        data = {
            "org_id": self._org_id,
            "date": setlist.date,
            "label": setlist.label,
            "event_type": setlist.event_type,
            "moments": setlist.moments,
        }

        self._client.table("setlists").upsert(
            data,
            on_conflict="org_id,date,label,event_type",
        ).execute()

    def update(self, date: str, setlist_dict: dict, label: str = "", event_type: str = "") -> None:
        """Update an existing setlist."""
        response = (
            self._client.table("setlists")
            .update({"moments": setlist_dict["moments"]})
            .eq("org_id", self._org_id)
            .eq("date", date)
            .eq("label", label)
            .eq("event_type", event_type)
            .execute()
        )

        if not response.data:
            label_s = f" (label: {label})" if label else ""
            type_s = f" (type: {event_type})" if event_type else ""
            raise KeyError(f"Setlist for {date}{label_s}{type_s} not found")

    def exists(self, date: str, label: str = "", event_type: str = "") -> bool:
        """Check if a setlist exists."""
        response = (
            self._client.table("setlists")
            .select("id", count="exact")
            .eq("org_id", self._org_id)
            .eq("date", date)
            .eq("label", label)
            .eq("event_type", event_type)
            .execute()
        )
        return (response.count or 0) > 0

    def delete(self, date: str, label: str = "", event_type: str = "") -> None:
        """Delete a setlist."""
        response = (
            self._client.table("setlists")
            .delete()
            .eq("org_id", self._org_id)
            .eq("date", date)
            .eq("label", label)
            .eq("event_type", event_type)
            .execute()
        )

        if not response.data:
            label_s = f" (label: {label})" if label else ""
            type_s = f" (type: {event_type})" if event_type else ""
            raise KeyError(f"Setlist for {date}{label_s}{type_s} not found")

    def get_by_date_all(self, date: str, event_type: str = "") -> list[dict]:
        """Get all setlists for a date (all labels)."""
        query = (
            self._client.table("setlists")
            .select("date, label, event_type, moments")
            .eq("org_id", self._org_id)
            .eq("date", date)
        )
        if event_type:
            query = query.eq("event_type", event_type)

        response = query.order("label").execute()

        results = []
        for row in response.data:
            entry: dict[str, Any] = {
                "date": str(row["date"]),
                "moments": row["moments"],
            }
            if row.get("label"):
                entry["label"] = row["label"]
            if row.get("event_type"):
                entry["event_type"] = row["event_type"]
            results.append(entry)

        return results
