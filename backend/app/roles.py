"""角色数据:暗流涌动(Trouble Brewing)全部 22 个角色。

文案为初版速写,正式校对时只改这个文件。
"""

TOWNSFOLK = "townsfolk"
OUTSIDER = "outsider"
MINION = "minion"
DEMON = "demon"

TEAM_LABELS = {
    TOWNSFOLK: "镇民",
    OUTSIDER: "外来者",
    MINION: "爪牙",
    DEMON: "恶魔",
}

# 玩家数 → (镇民数, 外来者数, 爪牙数, 恶魔数),官方配置表
TB_COMPOSITION = {
    5: (3, 0, 1, 1),
    6: (3, 1, 1, 1),
    7: (5, 0, 1, 1),
    8: (5, 1, 1, 1),
    9: (5, 2, 1, 1),
    10: (7, 0, 2, 1),
    11: (7, 1, 2, 1),
    12: (7, 2, 2, 1),
    13: (9, 0, 3, 1),
    14: (9, 1, 3, 1),
    15: (9, 2, 3, 1),
}

TB_ROLES = [
    # ---- 镇民 (13) ----
    {"id": "washerwoman", "name": "洗衣妇", "en": "Washerwoman", "team": TOWNSFOLK,
     "ability": "第一夜,你得知两名玩家中有一名是特定的镇民角色(也可能是醉鬼伪装的)。"},
    {"id": "librarian", "name": "图书管理员", "en": "Librarian", "team": TOWNSFOLK,
     "ability": "第一夜,你得知两名玩家中有一名是特定的外来者角色(也可能是醉鬼伪装的)。"},
    {"id": "investigator", "name": "调查员", "en": "Investigator", "team": TOWNSFOLK,
     "ability": "第一夜,你得知两名玩家中有一名是特定的爪牙角色。"},
    {"id": "chef", "name": "厨师", "en": "Chef", "team": TOWNSFOLK,
     "ability": "第一夜,你得知相邻的邪恶玩家共有几对。"},
    {"id": "empath", "name": "共情者", "en": "Empath", "team": TOWNSFOLK,
     "ability": "每夜,你得知与你相邻的两名存活玩家中有多少名是邪恶的。"},
    {"id": "fortuneteller", "name": "占卜师", "en": "Fortune Teller", "team": TOWNSFOLK,
     "ability": "每夜选择两名玩家,你得知他们之中是否有恶魔;若选中了已死亡玩家,你将醉酒至黄昏。"},
    {"id": "undertaker", "name": "送葬者", "en": "Undertaker", "team": TOWNSFOLK,
     "ability": "每夜,你得知今天白天被处决的玩家的角色。"},
    {"id": "monk", "name": "僧侣", "en": "Monk", "team": TOWNSFOLK,
     "ability": "每夜选择一名玩家(不能选自己),该玩家当夜免疫恶魔的能力。"},
    {"id": "ravenkeeper", "name": "渡鸦看守者", "en": "Ravenkeeper", "team": TOWNSFOLK,
     "ability": "若你在夜里死亡,当晚你会被唤醒并得知一名玩家的角色。"},
    {"id": "virgin", "name": "处女", "en": "Virgin", "team": TOWNSFOLK,
     "ability": "第一个提名你的镇民会立即被处决。"},
    {"id": "slayer", "name": "杀手", "en": "Slayer", "team": TOWNSFOLK,
     "ability": "每局限一次,白天你可以公开指认并击杀一名玩家;若对方是恶魔,善良阵营获胜;否则你死亡。"},
    {"id": "soldier", "name": "士兵", "en": "Soldier", "team": TOWNSFOLK,
     "ability": "恶魔的能力对你无效。"},
    {"id": "mayor", "name": "市长", "en": "Mayor", "team": TOWNSFOLK,
     "ability": "若只剩 3 名存活玩家且白天没有发生处决,你的阵营获胜。"},
    # ---- 外来者 (4) ----
    {"id": "butler", "name": "管家", "en": "Butler", "team": OUTSIDER,
     "ability": "每夜选择一名主人(不能选自己);白天只有你的主人投票之后你才能投票。"},
    {"id": "drunk", "name": "醉鬼", "en": "Drunk", "team": OUTSIDER,
     "ability": "你不知道自己是醉鬼:你以为自己是某个镇民角色,但你的能力无效且信息可能出错。"},
    {"id": "recluse", "name": "莽夫", "en": "Recluse", "team": OUTSIDER,
     "ability": "你可能会被判定为邪恶阵营或恶魔/爪牙身份,即使你并不是。"},
    {"id": "saint", "name": "圣徒", "en": "Saint", "team": OUTSIDER,
     "ability": "若你被处决,你的阵营落败。"},
    # ---- 爪牙 (4) ----
    {"id": "poisoner", "name": "投毒者", "en": "Poisoner", "team": MINION,
     "ability": "每夜选择一名玩家,该玩家中毒:能力失效、信息可能出错,直到黄昏。"},
    {"id": "spy", "name": "间谍", "en": "Spy", "team": MINION,
     "ability": "你登记为善良阵营;每夜你可以查看魔典,并可能被判定为任意镇民或外来者角色。"},
    {"id": "scarletwoman", "name": "猩红女郎", "en": "Scarlet Woman", "team": MINION,
     "ability": "若恶魔死亡,你立即变成新的恶魔。"},
    {"id": "baron", "name": "男爵", "en": "Baron", "team": MINION,
     "ability": "本局会多出两名外来者、少两名镇民(角色配置表已按此计算)。"},
    # ---- 恶魔 (1) ----
    {"id": "imp", "name": "小恶魔", "en": "Imp", "team": DEMON,
     "ability": "每夜选择一名玩家,该玩家死亡;若你死亡,当晚一名爪牙会变成新的小恶魔。"},
]
