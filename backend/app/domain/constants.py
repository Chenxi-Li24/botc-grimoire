"""Role-team policy shared by rule methods and view projections."""

from ..roles import DEMON, TOWNSFOLK

FAKE_POOLS = {"drunk": (TOWNSFOLK,), "lunatic": (DEMON,)}
