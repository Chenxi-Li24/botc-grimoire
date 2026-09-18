"""暗流涌动(Trouble Brewing)——官方基础剧本。

文案为初版速写,正式校对时只改这个文件。
"""

from .common import DEMON, MINION, OUTSIDER, TOWNSFOLK

SCRIPT_ID = "trouble-brewing"
NAME = "暗流涌动"
EN = "Trouble Brewing"
MIN_PLAYERS = 5

# 本板会触发配比调整的角色(抽中后生效)
ADJUST_ROLES = ("baron",)  # 男爵

ROLES = [
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
