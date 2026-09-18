"""教派紫月(Sects & Violets)——官方基础剧本。

文案为初版速写,正式校对时只改这个文件。
"""

from .common import DEMON, MINION, OUTSIDER, TOWNSFOLK

SCRIPT_ID = "sects-and-violets"
NAME = "教派紫月"
EN = "Sects & Violets"
MIN_PLAYERS = 5

# 本板会触发配比调整的角色(抽中后生效)
ADJUST_ROLES = ("fang-gu",)  # 方古

ROLES = [
    # ---- 镇民 (13) ----
    {"id": "clockmaker", "name": "钟表匠", "en": "Clockmaker", "team": TOWNSFOLK,
     "ability": "首夜,你得知恶魔与最近的爪牙之间隔着多少步。"},
    {"id": "dreamer", "name": "筑梦师", "en": "Dreamer", "team": TOWNSFOLK,
     "ability": "每个夜晚,你要选择除你及旅行者以外的一名玩家:你会得知一个善良角色和一个邪恶角色,该玩家是其中一个角色。"},
    {"id": "snakecharmer", "name": "舞蛇人", "en": "Snake Charmer", "team": TOWNSFOLK,
     "ability": "每个夜晚,你要选择一名存活的玩家:如果你选中了恶魔,你和他交换角色和阵营,然后他中毒。"},
    {"id": "mathematician", "name": "数学家", "en": "Mathematician", "team": TOWNSFOLK,
     "ability": "每夜,你得知有多少名玩家的能力因醉酒或中毒而失效。"},
    {"id": "flowergirl", "name": "花童", "en": "Flowergirl", "team": TOWNSFOLK,
     "ability": "每夜,你得知恶魔是否在白天投过票。"},
    {"id": "towncrier", "name": "镇传令", "en": "Town Crier", "team": TOWNSFOLK,
     "ability": "每夜,你得知是否有爪牙在白天发起过提名。"},
    {"id": "oracle", "name": "神谕者", "en": "Oracle", "team": TOWNSFOLK,
     "ability": "每夜,你得知已死亡的玩家中有多少是邪恶的。"},
    {"id": "savant", "name": "博学者", "en": "Savant", "team": TOWNSFOLK,
     "ability": "每个白天,你可以私下询问说书人以得知两条信息:一个是正确的,一个是错误的。"},
    {"id": "seamstress", "name": "裁缝", "en": "Seamstress", "team": TOWNSFOLK,
     "ability": "每局一次,夜晚选择两名玩家(不能选自己):你得知他们是否为同一阵营。"},
    {"id": "philosopher", "name": "哲学家", "en": "Philosopher", "team": TOWNSFOLK,
     "ability": "每局游戏限一次,在夜晚时,你可以选择一个善良角色:你获得该角色的能力。如果这个角色在场,他醉酒。"},
    {"id": "artist", "name": "艺术家", "en": "Artist", "team": TOWNSFOLK,
     "ability": "每局一次,白天问说书人一个是非题,说书人必须如实回答。"},
    {"id": "juggler", "name": "杂耍师", "en": "Juggler", "team": TOWNSFOLK,
     "ability": "首日,你可以公开猜测最多 5 名玩家的角色;当晚你得知猜对的数量。"},
    {"id": "sage", "name": "贤者", "en": "Sage", "team": TOWNSFOLK,
     "ability": "若恶魔杀死你,你得知他可能是哪两名玩家之一。"},
    # ---- 外来者 (4) ----
    {"id": "sweetheart", "name": "心上人", "en": "Sweetheart", "team": OUTSIDER,
     "ability": "当你死亡时,会有一名玩家开始醉酒。"},
    {"id": "barber", "name": "理发师", "en": "Barber", "team": OUTSIDER,
     "ability": "你死亡时,恶魔可以在当晚交换两名玩家的角色(由说书人执行)。"},
    {"id": "klutz", "name": "糊涂蛋", "en": "Klutz", "team": OUTSIDER,
     "ability": "你死亡时,公开选择一名存活玩家:若他是邪恶阵营,善良阵营落败。"},
    {"id": "mutant", "name": "畸形秀演员", "en": "Mutant", "team": OUTSIDER,
     "ability": '如果你"疯狂"地证明自己是外来者,你可能被处决。'},
    # ---- 爪牙 (4) ----
    {"id": "cerenovus", "name": "洗脑师", "en": "Cerenovus", "team": MINION,
     "ability": '每个夜晚,你要选择一名玩家和一个善良角色。他明天白天和夜晚需要"疯狂"地证明自己是这个角色,不然他可能被处决。'},
    {"id": "pithag", "name": "麻脸巫婆", "en": "Pit-Hag", "team": MINION,
     "ability": "每个夜晚*,你要选择一名玩家和一个角色,如果该角色不在场,他变成该角色。如果因此创造了一个恶魔,当晚的死亡由说书人决定。"},
    {"id": "eviltwin", "name": "邪恶双子", "en": "Evil Twin", "team": MINION,
     "ability": "你与一名镇民互为双子,你得知恶魔是谁;若你的双子被处决,邪恶阵营获胜。"},
    {"id": "witch", "name": "女巫", "en": "Witch", "team": MINION,
     "ability": "每夜选择一名玩家:若他次日白天提名,当晚他死亡。"},
    # ---- 恶魔 (4) ----
    {"id": "fang-gu", "name": "方古", "en": "Fang Gu", "team": DEMON,
     "ability": "每个夜晚*,你要选择一名玩家:他死亡。被该能力杀死的外来者改为变成邪恶的方古且你代替他死亡,但每局游戏仅能成功转化一次。[+1外来者]"},
    {"id": "vigormortis", "name": "亡骨魔", "en": "Vigormortis", "team": DEMON,
     "ability": "每个夜晚*,你要选择一名玩家:他死亡。被你杀死的爪牙保留他的能力,且与他邻近的两名镇民之一中毒。"},
    {"id": "nodashii", "name": "诺达希尔", "en": "No Dashii", "team": DEMON,
     "ability": "每夜选择一名玩家:他死亡。与你相邻的镇民醉酒。"},
    {"id": "vortox", "name": "沃托克斯", "en": "Vortox", "team": DEMON,
     "ability": "每夜选择一名玩家:他死亡。镇民获得的所有信息都是假的。"},
]
