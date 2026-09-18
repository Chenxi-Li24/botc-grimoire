"""满堂红(华灯与山雨赛事剧本 · 剧本社区第 176 期,作者 SUI)。

数据源:钟楼剧本博物馆 892280963319463958.json
(https://cdn.jsdelivr.net/gh/Roushelfy/botc-script-museum@main/docs/json/892280963319463958.json)
与官方/瓦釜雷鸣共用的角色直接引用同一份 dict(改名/改文案一处生效)。
7~15 人;旅行者「叫花子」按项目惯例不收录。

小怪宝官方开局:设置阶段移除恶魔角色标记、加入一个爪牙标记(小怪宝不是玩家,
由爪牙每晚秘密决定谁照看)。随机发牌按此自动开局(0 恶魔座位、爪牙 +1);
手动发身份时把「小怪宝」发到不坐人的空座位作标记即可,照看者由说书人掌握。
"""

from .common import DEMON, MINION, OUTSIDER, TOWNSFOLK
from .bad_moon_rising import ROLES as _BMR
from .sects_and_violets import ROLES as _SV
from .trouble_brewing import ROLES as _TB
from .wafu_leiming import ROLES as _WAFU

_shared = {r["id"]: r for r in _TB + _BMR + _SV + _WAFU}

# 这几个角色在满堂红官方名/文案与基础剧本不同:按本板官方名覆盖(spread 拷贝,不影响原板)
_flowergirl = {**_shared["flowergirl"], "name": "卖花女孩",
               "ability": "每个夜晚*,你会得知在今天白天时是否有恶魔投过票。"}
_towncrier = {**_shared["towncrier"], "name": "城镇公告员",
              "ability": "每个夜晚*,你会得知在今天白天时是否有爪牙发起过提名。"}
_gossip = {**_shared["gossip"], "name": "造谣者",
           "ability": "每个白天,你可以公开发表一个声明。如果该声明正确,在当晚会有一名玩家死亡。"}
_slayer = {**_shared["slayer"], "name": "猎手",
           "ability": "每局游戏限一次,你可以在白天时公开选择一名玩家:如果他是恶魔,他死亡。"}

SCRIPT_ID = "mantanghong"
NAME = "满堂红"
EN = "Man Tang Hong"
MIN_PLAYERS = 7

# 本板会触发配比调整的角色(抽中后生效):教父 ±1 外来者(默认 +1);小怪宝 +1 爪牙/−1 恶魔
ADJUST_ROLES = ("godfather", "lil-monsta")

ROLES = [
    # ---- 镇民 (13) ----
    {"id": "tixingguan", "name": "提刑官", "en": "Tixingguan", "team": TOWNSFOLK,
     "ability": "在你首次提名玩家后,你会在当晚得知他的角色。外来者会被你的能力当作爪牙或恶魔角色。"},
    {"id": "yanshi", "name": "偃师", "en": "Yanshi", "team": TOWNSFOLK,
     "ability": "如果你在夜晚死亡,你与一名存活的爪牙玩家交换角色。"},
    {"id": "chongfei", "name": "宠妃", "en": "Chongfei", "team": TOWNSFOLK,
     "ability": "每局游戏限一次,说书人会在关于你的事情上打破规则。随后,你会秘密得知说书人为此做了什么。"},
    _flowergirl, _towncrier, _shared["savant"], _shared["cannibal"], _gossip,
    {"id": "noble", "name": "贵族", "en": "Noble", "team": TOWNSFOLK,
     "ability": "在你的首个夜晚,你会得知三名玩家:其中有且只有一名玩家是邪恶的。"},
    _slayer, _shared["gambler"],
    {"id": "fisherman", "name": "渔夫", "en": "Fisherman", "team": TOWNSFOLK,
     "ability": "每局游戏限一次,在白天时,你可以让说书人给你一些能帮助你的阵营获胜的建议。"},
    _shared["chef"],
    # ---- 外来者 (4) ----
    {"id": "rulianshi", "name": "入殓师", "en": "Rulianshi", "team": OUTSIDER,
     "ability": "如果你提名并处决了恶魔,你会变成邪恶的恶魔。当剩余存活玩家小于等于四人时(旅行者除外),你失去能力。"},
    _shared["recluse"], _shared["drunk"], _shared["mutant"],
    # ---- 爪牙 (5) ----
    {"id": "niangjiushi", "name": "酿酒师", "en": "Niangjiushi", "team": MINION,
     "ability": "每个夜晚,你要选择一个镇民角色:当他下一次通过自身能力获取信息时,改为得知你给出的信息。"},
    _shared["godfather"], _shared["pithag"], _shared["assassin"],
    {"id": "panguan", "name": "判官", "en": "Panguan", "team": MINION,
     "ability": "在你的首个夜晚,你会得知一个关键词。在白天时(最后一天除外)有邪恶玩家首次说出该关键词会使得当前白天阶段立即结束。"},
    # ---- 恶魔 (3) ----
    {"id": "jianning", "name": "奸佞", "en": "Jianning", "team": DEMON,
     "ability": "每个夜晚*,你要选择一名玩家:他死亡。如果你今天白天没有投票,今晚你可以行动两次。"},
    {"id": "lil-monsta", "name": "小怪宝", "en": "Lil' Monsta", "team": DEMON,
     "ability": "每个夜晚,所有爪牙要秘密决定由哪名玩家来照看小怪宝并且「是恶魔」。每个夜晚*,会有一名玩家死亡。[+1爪牙]"},
    _shared["imp"],
]
