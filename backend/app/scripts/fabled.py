"""传奇角色(Fabled,官方 14 个;哨兵已做成独立配置开关,不在此列)。

传奇角色不是玩家角色,是说书人的规则修改器;公开信息,所有玩家都知道有哪些在场。
说书人在魔典里勾选,玩家手机可见列表。
"""

ROLES = [
    {"id": "angel", "name": "天使", "en": "Angel",
     "ability": "对新玩家的死亡负最大责任的人,可能会遭遇一些不好的事情。"},
    {"id": "buddhist", "name": "佛教徒", "en": "Buddhist",
     "ability": "每个白天的前两分钟老玩家不能发言。"},
    {"id": "duchess", "name": "公爵夫人", "en": "Duchess",
     "ability": "每个白天,三名玩家可以一起拜访你。当晚*,他们会得知他们之中有几个是邪恶的,但其中一人的信息是错的。"},
    {"id": "djinn", "name": "灯神", "en": "Djinn",
     "ability": "使用灯神的相克规则。所有玩家都会知道其内容。"},
    {"id": "doomsayer", "name": "末日预言者", "en": "Doomsayer",
     "ability": "如果大于等于四名玩家存活,每名当前存活的玩家可以公开要求你杀死一名与他阵营相同的玩家(每名玩家限一次)。"},
    {"id": "failed-god", "name": "失败的上帝", "en": "Failed God",
     "ability": "每局游戏至少一次,说书人将会出现失误,但会纠正并公开承认自己曾处理有误。"},
    {"id": "ferryman", "name": "摆渡人", "en": "Ferryman",
     "ability": "在游戏的最后一天,所有已死亡玩家会重新获得投票标记。"},
    {"id": "fibbin", "name": "骗人精", "en": "Fibbin",
     "ability": "每局游戏限一次,一名善良玩家可能会得知\"有问题\"的信息。"},
    {"id": "fiddler", "name": "小提琴手", "en": "Fiddler",
     "ability": "每局游戏限一次,恶魔可以秘密选择一名对立阵营的玩家,所有玩家要表决:这两名玩家中谁的阵营获胜。(平局邪恶阵营获胜)"},
    {"id": "hells-librarian", "name": "地狱藏书员", "en": "Hell's Librarian",
     "ability": "当说书人宣布安静时,仍在说话的玩家可能会遭遇一些不好的事情。"},
    {"id": "revolutionary", "name": "革命者", "en": "Revolutionary",
     "ability": "公开声明一对邻座玩家本局游戏一直保持同一阵营。每局游戏限一次,他们中的一人可能被当作其他的角色/阵营。"},
    {"id": "spirit-of-ivory", "name": "圣洁之魂", "en": "Spirit of Ivory",
     "ability": "游戏过程中邪恶玩家的总数最多能比初始设置多一名。"},
    {"id": "toymaker", "name": "玩具匠", "en": "Toymaker",
     "ability": "恶魔可以在夜晚选择放弃攻击(每局游戏至少一次)。邪恶玩家照常获取初始信息。"},
]

ROLE_BY_ID = {r["id"]: r for r in ROLES}
