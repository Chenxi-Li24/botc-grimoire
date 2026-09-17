"""角色数据:暗流涌动 / 黯月传奇 / 教派紫月 / 瓦釜雷鸣 四个脚本。

文案为初版速写,正式校对时只改这个文件。
官方角色与瓦釜雷鸣的命名以「钟楼剧本博物馆」社区通用名为准(守鸦人/酒鬼/陌客/洗脑师/麻脸巫婆/亡骨魔等)。
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

# 官方通用配置表:玩家数 → (镇民数, 外来者数, 爪牙数, 恶魔数)
COMPOSITION = {
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

# 会改变配比的角色 id → (镇民增量, 外来者增量, 爪牙增量, 恶魔增量)
ROLE_ADJUSTMENTS = {
    "baron": (-2, 2, 0, 0),       # 男爵:多 2 外来者、少 2 镇民
    "fang-gu": (-1, 1, 0, 0),     # 方古:多 1 外来者、少 1 镇民
    "vigormortis": (1, -1, 0, 0),  # 亡骨魔(瓦釜雷鸣社区改版):少 1 外来者、多 1 镇民
    "balloonist": (-1, 1, 0, 0),  # 气球驾驶员:+0~+1 外来者,默认 +1
    "godfather": (-1, 1, 0, 0),   # 教父:−1 或 +1 外来者,默认 +1
}

TB_ROLES = [
    # ---- 镇民 (13) ----
    {"id": "washerwoman", "name": "洗衣妇", "en": "Washerwoman", "team": TOWNSFOLK,
     "ability": "第一夜,你得知两名玩家中有一名是特定的镇民角色(也可能是醉鬼伪装的)。"},
    {"id": "librarian", "name": "图书管理员", "en": "Librarian", "team": TOWNSFOLK,
     "ability": "第一夜,你得知两名玩家中有一名是特定的外来者角色(也可能是醉鬼伪装的)。"},
    {"id": "investigator", "name": "调查员", "en": "Investigator", "team": TOWNSFOLK,
     "ability": "在你的首个夜晚,你会得知两名玩家和一个爪牙角色:这两名玩家之一是该角色(或者你会得知没有爪牙在场)。"},
    {"id": "chef", "name": "厨师", "en": "Chef", "team": TOWNSFOLK,
     "ability": "在你的首个夜晚,你会得知场上邻座的邪恶玩家有多少对。"},
    {"id": "empath", "name": "共情者", "en": "Empath", "team": TOWNSFOLK,
     "ability": "每夜,你得知与你相邻的两名存活玩家中有多少名是邪恶的。"},
    {"id": "fortuneteller", "name": "占卜师", "en": "Fortune Teller", "team": TOWNSFOLK,
     "ability": "每个夜晚,你要选择两名玩家:你会得知他们之中是否有恶魔。会有一名善良玩家始终被你的能力当作恶魔。"},
    {"id": "undertaker", "name": "送葬者", "en": "Undertaker", "team": TOWNSFOLK,
     "ability": "每夜,你得知今天白天被处决的玩家的角色。"},
    {"id": "monk", "name": "僧侣", "en": "Monk", "team": TOWNSFOLK,
     "ability": "每夜选择一名玩家(不能选自己),该玩家当夜免疫恶魔的能力。"},
    {"id": "ravenkeeper", "name": "守鸦人", "en": "Ravenkeeper", "team": TOWNSFOLK,
     "ability": "如果你在夜晚死亡,你会被唤醒,然后你要选择一名玩家:你会得知他的角色。"},
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
    {"id": "drunk", "name": "酒鬼", "en": "Drunk", "team": OUTSIDER,
     "ability": "你不知道你是酒鬼。你以为你是一个镇民角色,但其实你不是。"},
    {"id": "recluse", "name": "陌客", "en": "Recluse", "team": OUTSIDER,
     "ability": "你可能会被当作邪恶阵营、爪牙角色或恶魔角色,即使你已死亡。"},
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
     "ability": "每个夜晚*,你要选择一名玩家:他死亡。如果你以这种方式自杀,一名爪牙会变成小恶魔。"},
]

BMR_ROLES = [
    # ---- 镇民 (13) ----
    {"id": "grandmother", "name": "祖母", "en": "Grandmother", "team": TOWNSFOLK,
     "ability": "在你的首个夜晚,你会得知一名善良玩家和他的角色。如果恶魔杀死了他,你也会死亡。"},
    {"id": "sailor", "name": "水手", "en": "Sailor", "team": TOWNSFOLK,
     "ability": "每夜选择一名玩家:你与他都不会死亡,直到黄昏(你们之一可能醉酒)。"},
    {"id": "chambermaid", "name": "侍女", "en": "Chambermaid", "team": TOWNSFOLK,
     "ability": "每夜选择两名玩家:你得知他们昨晚是否被唤醒过。"},
    {"id": "exorcist", "name": "驱魔人", "en": "Exorcist", "team": TOWNSFOLK,
     "ability": "每夜选择一名玩家:若他是恶魔,他当夜不会醒来,无法攻击。"},
    {"id": "innkeeper", "name": "客栈老板", "en": "Innkeeper", "team": TOWNSFOLK,
     "ability": "每夜选择两名玩家:其中一人当夜免疫死亡,另一人可能醉酒。"},
    {"id": "gambler", "name": "赌徒", "en": "Gambler", "team": TOWNSFOLK,
     "ability": "每个夜晚*,你要选择一名玩家并猜测他的角色:如果你猜错了,你会死亡。"},
    {"id": "gossip", "name": "长舌", "en": "Gossip", "team": TOWNSFOLK,
     "ability": "白天你可以公开说一个陈述:若为真,当晚说书人会让一名玩家死亡。"},
    {"id": "courtier", "name": "弄臣", "en": "Courtier", "team": TOWNSFOLK,
     "ability": "每局一次,夜晚选择一个角色:持有该角色的玩家三昼三夜无法行动。"},
    {"id": "professor", "name": "教授", "en": "Professor", "team": TOWNSFOLK,
     "ability": "每局一次,夜晚选择一名已死亡的镇民:他复活。"},
    {"id": "minstrel", "name": "吟游诗人", "en": "Minstrel", "team": TOWNSFOLK,
     "ability": "若白天有爪牙被处决,当晚所有爪牙不会醒来。"},
    {"id": "tealady", "name": "茶艺师", "en": "Tealady", "team": TOWNSFOLK,
     "ability": "每夜,若与你相邻的两名玩家都存活,他们免疫恶魔的攻击。"},
    {"id": "pacifist", "name": "和平主义者", "en": "Pacifist", "team": TOWNSFOLK,
     "ability": "被处决的镇民可能不会死亡(由说书人决定)。"},
    {"id": "fool", "name": "愚者", "en": "Fool", "team": TOWNSFOLK,
     "ability": "你第一次「死亡」时,其实不会死。"},
    # ---- 外来者 (4) ----
    {"id": "goon", "name": "呆子", "en": "Goon", "team": OUTSIDER,
     "ability": "每夜第一个选择你的玩家:若是镇民,他醉酒至黄昏;若是恶魔,你的阵营转为邪恶。"},
    {"id": "lunatic", "name": "疯子", "en": "Lunatic", "team": OUTSIDER,
     "ability": "你以为你是一个恶魔,但其实你不是。恶魔知道你是疯子以及你在每个夜晚选择了哪些玩家。"},
    {"id": "tinker", "name": "修补匠", "en": "Tinker", "team": OUTSIDER,
     "ability": "你随时可能死亡(说书人可以安排你死)。"},
    {"id": "moonchild", "name": "月之子", "en": "Moonchild", "team": OUTSIDER,
     "ability": "当你被处决时,当晚一名善良玩家会死亡。"},
    # ---- 爪牙 (4) ----
    {"id": "assassin", "name": "刺客", "en": "Assassin", "team": MINION,
     "ability": "每局一次,夜晚你可以公开杀死一名玩家。"},
    {"id": "devilsadvocate", "name": "恶魔代言人", "en": "Devil's Advocate", "team": MINION,
     "ability": "每夜选择一名玩家:他若在次日被处决,不会死亡。"},
    {"id": "godfather", "name": "教父", "en": "Godfather", "team": MINION,
     "ability": "在你的首个夜晚,你会得知有哪些外来者角色在场。如果有外来者在白天死亡,你会在当晚被唤醒并且你要选择一名玩家:他死亡。[-1或+1外来者]"},
    {"id": "mastermind", "name": "主谋", "en": "Mastermind", "team": MINION,
     "ability": "若恶魔被处决且你存活,你变成新的恶魔。"},
    # ---- 恶魔 (4) ----
    {"id": "shabaloth", "name": "沙巴尔", "en": "Shabaloth", "team": DEMON,
     "ability": "每夜选择两名玩家:他们死亡。每局一次,你可以复活一名已死亡的玩家。"},
    {"id": "po", "name": "珀", "en": "Po", "team": DEMON,
     "ability": "每夜选择玩家:第 N 夜你杀死 N 名玩家。"},
    {"id": "zombuul", "name": "祖布尔", "en": "Zombuul", "team": DEMON,
     "ability": "若白天没有人死亡,每夜你选择一名玩家:他死亡。你第一次死亡时,其实不会死。"},
    {"id": "pukka", "name": "帕卡", "en": "Pukka", "team": DEMON,
     "ability": "每夜选择一名玩家:他中毒;上一名被你选择的玩家死亡。若你被处决,所有人痊愈。"},
]

SV_ROLES = [
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

# ---- 瓦釜雷鸣 v11.1.1(Catfishing,作者 Emily)----
# 社区"官混"缝合板子,角色文案取自钟楼剧本博物馆官方整理版 JSON
# (https://cdn.jsdelivr.net/gh/Roushelfy/botc-script-museum@main/docs/json/735177364786380809.json)
# 与官方脚本共用的角色直接引用同一份 dict(改名/改文案一处生效)
_shared = {r["id"]: r for r in TB_ROLES + BMR_ROLES + SV_ROLES}

VAFR_ROLES = [
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

SCRIPTS = {
    "trouble-brewing": {"name": "暗流涌动", "en": "Trouble Brewing", "roles": TB_ROLES},
    "bad-moon-rising": {"name": "黯月传奇", "en": "Bad Moon Rising", "roles": BMR_ROLES},
    "sects-and-violets": {"name": "教派紫月", "en": "Sects & Violets", "roles": SV_ROLES},
    "wafu-leiming": {"name": "瓦釜雷鸣", "en": "Catfishing", "min_players": 7, "roles": VAFR_ROLES},
}

# 各脚本会触发配比调整的角色(抽中后生效)
SCRIPT_ADJUST_ROLES = {
    "trouble-brewing": ("baron",),                              # 男爵
    "bad-moon-rising": ("godfather",),                          # 教父 −1/+1(默认 +1)
    "sects-and-violets": ("fang-gu",),                          # 方古
    "wafu-leiming": ("fang-gu", "vigormortis", "balloonist", "godfather"),
}
