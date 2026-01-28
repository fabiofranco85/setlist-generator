"""Configuration constants for setlist generation."""

# Service moments configuration
MOMENTS_CONFIG = {
    "prelúdio": 1,
    "ofertório": 1,
    "saudação": 1,
    "crianças": 1,
    "louvor": 4,
    "poslúdio": 1,
}

# Selection algorithm parameters
DEFAULT_WEIGHT = 3
RECENCY_PENALTY_PERFORMANCES = 3  # Number of performances until "fresh"

# Energy ordering configuration
ENERGY_ORDERING_ENABLED = True  # Master switch to enable/disable feature
ENERGY_ORDERING_RULES = {
    "louvor": "ascending",  # 1→4 (upbeat to worship)
    # Future: "ofertório": "descending", etc.
}
DEFAULT_ENERGY = 2.5  # Default for songs without energy metadata
