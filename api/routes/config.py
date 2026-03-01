"""Organization config endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from library.config import GenerationConfig
from library.repositories import RepositoryContainer

from ..deps import get_repos, get_generation_config, require_role
from ..schemas.config import ConfigResponse, OrgConfigUpdate

router = APIRouter()


@router.get("", response_model=ConfigResponse)
async def get_config(config: GenerationConfig = Depends(get_generation_config)):
    """Get the effective config (system defaults + org overrides)."""
    return ConfigResponse(
        moments_config=config.moments_config,
        recency_decay_days=config.recency_decay_days,
        default_weight=config.default_weight,
        energy_ordering_enabled=config.energy_ordering_enabled,
        energy_ordering_rules=config.energy_ordering_rules,
        default_energy=config.default_energy,
    )


@router.patch("", response_model=ConfigResponse, dependencies=[Depends(require_role("org_admin"))])
async def update_config(
    data: OrgConfigUpdate,
    repos: RepositoryContainer = Depends(get_repos),
):
    """Update org-specific config overrides (org_admin only)."""
    # Write individual keys to org_config table
    client = None
    org_id = None

    # Access supabase client through the config repo if available
    if hasattr(repos.config, "_client"):
        client = repos.config._client
        org_id = repos.config._org_id

    if not client:
        raise ValueError("Config updates require Supabase backend")

    updates = {}
    if data.moments_config is not None:
        updates["moments_config"] = data.moments_config
    if data.recency_decay_days is not None:
        updates["recency_decay_days"] = data.recency_decay_days
    if data.default_weight is not None:
        updates["default_weight"] = data.default_weight
    if data.energy_ordering_enabled is not None:
        updates["energy_ordering_enabled"] = data.energy_ordering_enabled
    if data.energy_ordering_rules is not None:
        updates["energy_ordering_rules"] = data.energy_ordering_rules
    if data.default_energy is not None:
        updates["default_energy"] = data.default_energy

    for key, value in updates.items():
        client.table("org_config").upsert({
            "org_id": org_id,
            "key": key,
            "value": value,
        }, on_conflict="org_id,key").execute()

    # Invalidate cache and return new effective config
    if hasattr(repos.config, "_cache"):
        repos.config._cache = None

    new_config = GenerationConfig.from_config_repo(repos.config)
    return ConfigResponse(
        moments_config=new_config.moments_config,
        recency_decay_days=new_config.recency_decay_days,
        default_weight=new_config.default_weight,
        energy_ordering_enabled=new_config.energy_ordering_enabled,
        energy_ordering_rules=new_config.energy_ordering_rules,
        default_energy=new_config.default_energy,
    )
