"""黯月传奇(Bad Moon Rising)——官方基础剧本。

文案为初版速写,正式校对时只改这个文件。
"""

from .common import DEMON, MINION, OUTSIDER, TOWNSFOLK

SCRIPT_ID = "bad-moon-rising"
NAME = "黯月传奇"
EN = "Bad Moon Rising"
MIN_PLAYERS = 5

# 本板会触发配比调整的角色(抽中后生效)
ADJUST_ROLES = ("godfather",)  # 教父 −1/+1(默认 +1)

ROLES = [
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
