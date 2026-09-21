"""Role-team policy shared by rule methods and view projections."""

from ..roles import DEMON, TOWNSFOLK

FAKE_POOLS = {"drunk": (TOWNSFOLK,), "lunatic": (DEMON,)}
MARKERS = ("poisoned", "drunk", "mad", "role-change", "team-change")
MARKER_LABELS = {"poisoned": "中毒", "drunk": "醉酒", "mad": "疯狂"}
