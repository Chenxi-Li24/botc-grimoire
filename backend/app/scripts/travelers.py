"""旅行者角色:官方基础版 15 个 + 实验性 3 个(集石官方中文译名与能力)。

旅行者机制(官方规则要点):
- 任意时刻加入(游戏开始后即可,通常在白天;首夜前也可以),不算配板、不计入邪恶阵营获胜条件
- 说书人私下定阵营(善良/邪恶);邪恶旅行者得知恶魔是谁
- 白天参与提名与投票,死亡时获得投票标记(死票)
- 通过「流放」杀死:白天任意玩家(含死者)可提议,成功需全体玩家总数一半支持(不耗死票);
  同一白天可流放多个旅行者,每名旅行者每天只能被提议流放一次;流放不能被角色能力影响
- 旅行者的夜晚行动全部发生在黄昏阶段(检查闭眼之后)
"""

TRAVELER = "traveler"

ROLES = [
    # ---- 暗流涌动推荐 (5) ----
    {"id": "bureaucrat", "name": "官员", "en": "Bureaucrat", "team": TRAVELER,
     "ability": "每个夜晚,你要选择除你以外的一名玩家:明天白天,他的投票算作三票。"},
    {"id": "beggar", "name": "乞丐", "en": "Beggar", "team": TRAVELER,
     "ability": "你只能使用投票标记才能投票。死亡的玩家可以将他的投票标记给你,如果他这么做,你会得知他的阵营。你不会中毒和醉酒。"},
    {"id": "gunslinger", "name": "枪手", "en": "Gunslinger", "team": TRAVELER,
     "ability": "每个白天,当首次投票被统计后,你可以选择一名刚投过票的玩家:他死亡。"},
    {"id": "thief", "name": "窃贼", "en": "Thief", "team": TRAVELER,
     "ability": "每个夜晚,你要选择除你以外的一名玩家:明天白天他的投票会被算作负数。"},
    {"id": "scapegoat", "name": "替罪羊", "en": "Scapegoat", "team": TRAVELER,
     "ability": "如果你的阵营的一名玩家被处决,你可能会代替他被处决。"},
    # ---- 黯月初升推荐 (5) ----
    {"id": "judge", "name": "法官", "en": "Judge", "team": TRAVELER,
     "ability": "每局游戏限一次,如果其他玩家发起了提名,你可以选择让本次提名直接执行处决或让投票无效。"},
    {"id": "matron", "name": "女舍监", "en": "Matron", "team": TRAVELER,
     "ability": "每个白天,你可以选择至多三对玩家交换座位。玩家不能离开座位私聊。"},
    {"id": "voudon", "name": "巫毒师", "en": "Voudon", "team": TRAVELER,
     "ability": "只有你和死亡的玩家可以投票,且投票不需要使用投票标记。忽略票数需要过半的要求。"},
    {"id": "apprentice", "name": "学徒", "en": "Apprentice", "team": TRAVELER,
     "ability": "在你的首个夜晚,如果你是善良的,你会获得一个镇民角色的能力;如果你是邪恶的,你会获得一个爪牙角色的能力。"},
    {"id": "bishop", "name": "主教", "en": "Bishop", "team": TRAVELER,
     "ability": "只有说书人可以发起提名。每个白天说书人至少要提名一名你对立阵营的玩家。"},
    # ---- 梦殒春宵推荐 (5) ----
    {"id": "deviant", "name": "怪咖", "en": "Deviant", "team": TRAVELER,
     "ability": "如果你表现得很有趣,当天你不能被流放。"},
    {"id": "bone-collector", "name": "集骨者", "en": "Bone Collector", "team": TRAVELER,
     "ability": "每局游戏限一次,在夜晚时,你可以选择一名死亡的玩家:他重新获得能力直到下个黄昏。"},
    {"id": "barista", "name": "咖啡师", "en": "Barista", "team": TRAVELER,
     "ability": "每个夜晚,直至下个黄昏,由说书人二选一:1)一名玩家解除并免受醉酒和中毒影响,且会得知正确信息;2)一名玩家的能力可以生效两次。该玩家会得知是哪个效果。"},
    {"id": "harlot", "name": "流莺", "en": "Harlot", "team": TRAVELER,
     "ability": "每个夜晚,你要选择一名存活的玩家:如果他同意,你会得知他的角色,但是你们两个可能同时死亡。"},
    {"id": "butcher", "name": "屠夫", "en": "Butcher", "team": TRAVELER,
     "ability": "每个白天,首次处决后,你可以再次发起提名。"},
    # ---- 实验性 (3) ----
    {"id": "gangster", "name": "黑帮", "en": "Gangster", "team": TRAVELER,
     "ability": "每个白天限一次,你可以杀死与你邻近的两名存活的玩家中的一名,但需要另一边那个存活的玩家同意。"},
    {"id": "cacklejack", "name": "笑匠", "en": "Cacklejack", "team": TRAVELER,
     "ability": "每个白天,你要选择一名玩家:一名其他玩家会在当晚改变角色。"},
    {"id": "gnome", "name": "侏儒", "en": "Gnome", "team": TRAVELER,
     "ability": "当你加入游戏时,所有玩家会得知一名与你阵营相同的玩家。每当他被提名时,你可以杀死提名者。"},
]

ROLE_BY_ID = {r["id"]: r for r in ROLES}

# 旅行者夜晚行动顺序(官方夜晚行动顺序一览:黄昏阶段,检查闭眼之后,按此顺序)
DUSK_ORDER = ["bureaucrat", "thief", "apprentice", "barista", "harlot", "bone-collector"]

# 官方各板子推荐的旅行者;社区板子(瓦釜雷鸣/满堂红)不限定 → 全部可用
RECOMMENDED = {
    "trouble-brewing": ["bureaucrat", "beggar", "gunslinger", "thief", "scapegoat"],
    "bad-moon-rising": ["judge", "matron", "voudon", "apprentice", "bishop"],
    "sects-and-violets": ["deviant", "bone-collector", "barista", "harlot", "butcher"],
    "experimental": ["gangster", "cacklejack", "gnome"],
}
