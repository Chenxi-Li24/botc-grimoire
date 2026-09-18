"""瓦釜雷鸣 v11.1.1(Catfishing,作者 Emily)——社区"官混"缝合板子。

角色文案取自钟楼剧本博物馆官方整理版 JSON
(https://cdn.jsdelivr.net/gh/Roushelfy/botc-script-museum@main/docs/json/735177364786380809.json)
与官方脚本共用的角色直接引用同一份 dict(改名/改文案一处生效)
"""

from .common import DEMON, MINION, OUTSIDER, TOWNSFOLK
from .bad_moon_rising import ROLES as _BMR
from .sects_and_violets import ROLES as _SV
from .trouble_brewing import ROLES as _TB

_shared = {r["id"]: r for r in _TB + _BMR + _SV}

SCRIPT_ID = "wafu-leiming"
NAME = "瓦釜雷鸣"
EN = "Catfishing"
MIN_PLAYERS = 7

# 本板会触发配比调整的角色(抽中后生效)
ADJUST_ROLES = ("fang-gu", "vigormortis", "balloonist", "godfather")

ROLES = [
    # ---- 镇民 (13) ----
    _shared["investigator"], _shared["chef"], _shared["grandmother"],
    {"id": "balloonist", "name": "气球驾驶员", "en": "Balloonist", "team": TOWNSFOLK,
     "ability": "每个夜晚,你会得知一名与上个夜晚得知的玩家角色类型不同的玩家。[+0~1外来者]"},
    _shared["dreamer"], _shared["snakecharmer"], _shared["fortuneteller"],
    _shared["gambler"], _shared["savant"],
    {"id": "amnesiac", "name": "失忆者", "en": "Amnesiac", "team": TOWNSFOLK,
     "ability": "你不知道你的能力是什么。每个白天你可以找说书人猜测一次,你会得知你的猜测有多准确。"},
    _shared["philosopher"], _shared["ravenkeeper"],
    {"id": "cannibal", "name": "食人族", "en": "Cannibal", "team": TOWNSFOLK,
     "ability": "你拥有上个死于处决的玩家的能力。如果该玩家属于邪恶阵营,你中毒直到下个善良玩家死于处决。"},
    # ---- 外来者 (5) ----
    _shared["drunk"], _shared["recluse"], _shared["mutant"], _shared["sweetheart"], _shared["lunatic"],
    # ---- 爪牙 (4) ----
    _shared["godfather"], _shared["cerenovus"], _shared["pithag"],
    {"id": "widow", "name": "寡妇", "en": "Widow", "team": MINION,
     "ability": "在你的首个夜晚,你能查看魔典并选择一名玩家:他中毒。随后,始终会有一名善良玩家知道寡妇在场。"},
    # ---- 恶魔 (3) ----
    _shared["fang-gu"],
    # 亡骨魔在瓦釜雷鸣中是社区改版(多 −1 外来者),单独覆盖文案,不影响教派紫月
    {**_shared["vigormortis"],
     "ability": "每个夜晚*,你要选择一名玩家:他死亡。被你杀死的爪牙保留他的能力,且与他邻近的两名镇民之一中毒。[-1外来者]"},
    _shared["imp"],
]
