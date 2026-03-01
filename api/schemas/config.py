"""Config schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel


class OrgConfigUpdate(BaseModel):
    moments_config: dict[str, int] | None = None
    recency_decay_days: int | None = None
    default_weight: int | None = None
    energy_ordering_enabled: bool | None = None
    energy_ordering_rules: dict[str, str] | None = None
    default_energy: float | None = None


class ConfigResponse(BaseModel):
    moments_config: dict[str, int]
    recency_decay_days: int
    default_weight: int
    energy_ordering_enabled: bool
    energy_ordering_rules: dict[str, str]
    default_energy: float
