"""角色数据兼容入口。

数据已按板子拆分到 scripts/ 包(每个板子一个 .py,更新/移植单板只动一个文件),
本文件保留原有导出 API,game.py / tools 无需改动:
- scripts/common.py          阵营常量、官方配比表、配比调整表(跨板子共用)
- scripts/<板子>.py          各板角色表与元信息
- scripts/__init__.py        注册表:汇总成 SCRIPTS / SCRIPT_ADJUST_ROLES
"""

from .scripts import (COMPOSITION, DEMON, MINION, OUTSIDER,  # noqa: F401
                      ROLE_ADJUSTMENTS, SCRIPTS,
                      SCRIPT_ADJUST_ROLES, SCRIPT_PACKS, TEAM_LABELS, TOWNSFOLK)
from .scripts import (bad_moon_rising, mantanghong,  # noqa: F401
                      sects_and_violets, trouble_brewing, wafu_leiming)

TB_ROLES = trouble_brewing.ROLES
BMR_ROLES = bad_moon_rising.ROLES
SV_ROLES = sects_and_violets.ROLES
VAFR_ROLES = wafu_leiming.ROLES
MTH_ROLES = mantanghong.ROLES

__all__ = ["COMPOSITION", "DEMON", "MINION", "OUTSIDER", "ROLE_ADJUSTMENTS",
           "SCRIPTS", "SCRIPT_ADJUST_ROLES", "TEAM_LABELS", "TOWNSFOLK",
           "SCRIPT_PACKS", "TB_ROLES", "BMR_ROLES", "SV_ROLES", "VAFR_ROLES", "MTH_ROLES"]
