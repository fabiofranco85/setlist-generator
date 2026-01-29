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
RECENCY_DECAY_DAYS = 45  # Days for a song to feel "fresh" again (time-based decay)

# Energy ordering configuration
ENERGY_ORDERING_ENABLED = True  # Master switch to enable/disable feature
ENERGY_ORDERING_RULES = {
    "louvor": "ascending",  # 1→4 (upbeat to worship)
    # Future: "ofertório": "descending", etc.
}
DEFAULT_ENERGY = 2.5  # Default for songs without energy metadata

# Output path configuration
DEFAULT_OUTPUT_DIR = "output"      # Markdown setlists directory
DEFAULT_HISTORY_DIR = "history"    # JSON tracking directory

# Environment variable names (for documentation)
ENV_OUTPUT_DIR = "SETLIST_OUTPUT_DIR"
ENV_HISTORY_DIR = "SETLIST_HISTORY_DIR"
