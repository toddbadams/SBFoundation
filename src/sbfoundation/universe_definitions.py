"""
Backward-compatibility shim for sbfoundation.universe_definitions.

All universe types and constants are now canonical in sbuniverse.
This module re-exports them so existing callers are unaffected.
"""

from sbuniverse.universe_definition import UniverseDefinition
from sbuniverse.universe_definitions import (
    UNIVERSE_REGISTRY,
    US_ALL_CAP,
    US_LARGE_CAP,
    US_LARGE_MID_CAP,
    US_MID_CAP,
    US_SMALL_CAP,
    US_SMALL_MID_CAP,
)

__all__ = [
    "UniverseDefinition",
    "UNIVERSE_REGISTRY",
    "US_LARGE_MID_CAP",
    "US_LARGE_CAP",
    "US_MID_CAP",
    "US_SMALL_MID_CAP",
    "US_SMALL_CAP",
    "US_ALL_CAP",
]
