"""角色数据注册表:每个板子一个模块(scripts/<板子>.py),这里汇总成全局表。

- common.py:跨板子共用(阵营常量/官方配比表/配比调整表)
- 新板子 = 新增一个 .py + 在 _MODULES 里加一行(脚本选择器/配比/夜晚生成器自动收录)
"""

from . import (bad_moon_rising, mantanghong, sects_and_violets,
               trouble_brewing, wafu_leiming)
from ..catalog import compile_builtin_packs, pack_to_view
from ..night_order import NIGHT_ORDER
from .common import (COMPOSITION, DEMON, MINION, OUTSIDER,
                     ROLE_ADJUSTMENTS, TEAM_LABELS, TOWNSFOLK)

_MODULES = (trouble_brewing, bad_moon_rising, sects_and_violets,
            wafu_leiming, mantanghong)

SCRIPT_PACKS = compile_builtin_packs(_MODULES, NIGHT_ORDER)
SCRIPTS = {script_id: pack_to_view(pack)
           for script_id, pack in SCRIPT_PACKS.items()}

# 各脚本会触发配比调整的角色(抽中后生效)
SCRIPT_ADJUST_ROLES = {m.SCRIPT_ID: m.ADJUST_ROLES for m in _MODULES}

__all__ = ["COMPOSITION", "DEMON", "MINION", "OUTSIDER", "ROLE_ADJUSTMENTS",
           "SCRIPTS", "SCRIPT_PACKS", "SCRIPT_ADJUST_ROLES", "TEAM_LABELS", "TOWNSFOLK"]
