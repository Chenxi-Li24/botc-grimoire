"""生成 backend/app/night_order.py:五板子夜晚唤醒顺序。

数据源:
- TB/BMR/SV:官方全局 nightsheet.json(botc-release/resources/data)∩ 本板角色
- 瓦釜雷鸣/满堂红:钟楼剧本博物馆 JSON(本目录 data/museum/)的每角色位置与官方提醒文案
数据文件:
- sources/nightsheet.json          官方全局夜晚顺序(从 ThePandemoniumInstitute/botc-release 下载)
- sources/museum/735177364786380809.json   瓦釜雷鸣
- sources/museum/892280963319463958.json   满堂红
运行:python tools/build_night_order.py(输出到 backend/app/night_order.py)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.roles import SCRIPTS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / "sources"
NIGHTSHEET = DATA / "nightsheet.json"
MUSEUM = {  # 博物馆 JSON 按板子存一份,保证重跑可复现;更新剧本时替换对应文件
    "wafu-leiming": DATA / "museum" / "735177364786380809.json",
    "mantanghong": DATA / "museum" / "892280963319463958.json",
}

# 特殊步骤(非角色),插在首/末
DUSK = {"key": "dusk", "name": "天黑", "hint": "所有玩家闭眼"}
DAWN = {"key": "dawn", "name": "天亮", "hint": "所有玩家睁眼;宣告昨夜死者,进入白天"}
MINIONINFO = {"key": "minioninfo", "name": "爪牙会面", "hint": "唤醒所有爪牙,让他们互认,指向恶魔"}
DEMONINFO = {"key": "demoninfo", "name": "恶魔会面",
             "hint": "唤醒恶魔,指出爪牙,展示三个不在场镇民角色作为伪装"}

# TB/BMR/SV 各角色说书人提示(按官方规则书速写;未列出的角色用能力文案兜底)
HINTS = {
    # ---- 暗流涌动 ----
    "poisoner": "选一名玩家:他中毒(能力失效、信息可能出错)",
    "washerwoman": "展示一个镇民角色标记与两名玩家:其中一人是该角色(也可能是酒鬼)",
    "librarian": "展示一个外来者角色标记与两名玩家:其中一人是该角色(也可能是酒鬼);无外来者在场则展示 0",
    "investigator": "展示一个爪牙角色标记与两名玩家:其中一人是该角色;无爪牙在场则摇头",
    "chef": "展示数字:相邻的邪恶玩家对数",
    "empath": "展示数字:与你相邻的两名存活玩家中的邪恶人数",
    "fortuneteller": "选两名玩家:点头=其中有恶魔(一名善良玩家会被始终当作恶魔)",
    "butler": "选一名主人(不能是自己)",
    "spy": "可查看魔典;可能被判定为任意镇民或外来者角色",
    "monk": "选一名玩家(不能是自己):当夜免疫恶魔能力",
    "scarletwoman": "若恶魔死亡且你存活:你成为新恶魔",
    "imp": "选一名玩家:他死亡;若选自己,一名爪牙变成小恶魔",
    "ravenkeeper": "若你死于今夜:唤醒你,选一名玩家,得知其角色",
    "undertaker": "若今日有人被处决:得知其角色",
    # ---- 黯月传奇 ----
    "lunatic": "7 人及以上:展示『这些是爪牙』与三个不在场善良角色;恶魔得知你是疯子",
    "sailor": "选一名玩家:你与他当夜免疫死亡(其中一人可能醉酒)",
    "courtier": "每局一次:选一个角色,持有者三昼三夜无法行动",
    "godfather": "首夜:展示在场的外来者角色标记;之后:若今日有外来者死于白天,选一名玩家死亡",
    "devilsadvocate": "选一名玩家:他次日若被处决不会死亡",
    "pukka": "首夜:选一名玩家,他中毒;之后:上一名被你选的玩家死亡,再选一名玩家中毒",
    "grandmother": "首夜:指向孙子玩家并展示其角色标记;之后:若孙子被恶魔杀死,唤醒祖母,她死亡",
    "chambermaid": "选两名玩家:点头/摇头=他们昨晚是否被唤醒过",
    "innkeeper": "选两名玩家:其中一人当夜免疫死亡,另一人可能醉酒",
    "gambler": "选一名玩家并猜其角色:猜错则你死亡",
    "exorcist": "选一名玩家:若他是恶魔,当夜不醒、无法杀人",
    "zombuul": "若今日白天无人死亡:选一名玩家,他死亡",
    "shabaloth": "选两名玩家:他们死亡;每局一次可复活一名已死玩家",
    "po": "第 N 夜杀死 N 名玩家",
    "assassin": "每局一次:公开杀死一名玩家",
    "gossip": "若长舌今日公开陈述为真:一名玩家死亡(长舌本人不醒)",
    "professor": "每局一次:选一名已死亡的镇民,他复活",
    "tinker": "说书人可随时安排修补匠死亡",
    "moonchild": "若月之子被处决:今晚一名善良玩家死亡",
    # ---- 教派紫月 ----
    "philosopher": "每局一次:选一个善良角色获得其能力;该角色在场则其醉酒,此后按新能力唤醒",
    "snakecharmer": "选一名玩家:若选中恶魔,交换角色与阵营,新的舞蛇人中毒",
    "eviltwin": "得知恶魔是谁",
    "witch": "选一名玩家:若他明日白天提名,当晚死亡",
    "cerenovus": "选一名玩家和一个善良角色:他需『疯狂』证明该角色,否则可能被处决",
    "clockmaker": "展示数字:恶魔与最近的爪牙之间隔几步",
    "dreamer": "选一名玩家:展示一个善良角色与一个邪恶角色,其一为真",
    "seamstress": "每局一次:选两名玩家(不能是自己):点头=同阵营",
    "mathematician": "展示数字:因醉酒/中毒失效的能力数",
    "pithag": "选一名玩家和一个角色:该角色不在场则其变为该角色(造出恶魔时当晚死者由说书人定)",
    "fanggu": "选一名玩家:他死亡;杀死外来者则其变为方古、你死(每局一次)",
    "nodashii": "选一名玩家:他死亡;与你相邻的镇民醉酒",
    "vortox": "选一名玩家:他死亡;镇民获得的信息全部为假",
    "vigormortis": "选一名玩家:他死亡;被你杀死的爪牙保留能力",
    "barber": "若理发师已死亡:恶魔可交换两名玩家的角色(由说书人执行)",
    "sweetheart": "若心上人已死亡:一名玩家醉酒(尚未发生则现在执行)",
    "sage": "若恶魔杀死了你:得知两名玩家之一为恶魔",
    "flowergirl": "点头/摇头=恶魔今日是否投过票",
    "towncrier": "点头/摇头=今日是否有爪牙发起提名",
    "oracle": "展示数字:已死亡玩家中的邪恶人数",
    "juggler": "首日白天公开猜测角色;今晚告知猜对数量",
}

SLUG_FIX = {"fang-gu": "fanggu"}  # 官方 nightsheet 用 fanggu,roles.py 用 fang-gu
SLUG_UNFIX = {"fanggu": "fang-gu"}


def official_orders():
    """官方全局顺序 ∩ 本板角色 → {script: {first: [key], other: [key]}}。"""
    ns = json.loads(NIGHTSHEET.read_text(encoding="utf-8"))
    out = {}
    for sid, s in SCRIPTS.items():
        ids = {SLUG_FIX.get(r["id"], r["id"]) for r in s["roles"]}
        steps = {}
        for kind in ("first", "other"):
            keys = [k for k in ns[f"{kind}Night"]
                    if k in ids or k in ("dusk", "dawn", "minioninfo", "demoninfo")]
            steps[kind] = keys
        out[sid] = steps
    return out


def museum_orders(sid):
    """博物馆 JSON 每角色位置 → 该板顺序(不含旅行者)。按中文名匹配角色,返回 (id, hint) 列表。"""
    d = json.loads(MUSEUM[sid].read_text(encoding="utf-8"))
    roles = SCRIPTS[sid]["roles"]
    by_name = {r["name"]: r for r in roles}
    out = {"first": [], "other": []}
    for e in d:
        if e["id"] == "_meta":
            continue
        r = by_name.get(e["name"])
        if r is None:  # 旅行者(如叫花子/学徒/咖啡师)刻意不收录
            continue
        for kind, field in (("first", "firstNight"), ("other", "otherNight")):
            if e.get(field):  # 0 = 该夜不行动
                out[kind].append((e[field], r["id"],
                                  e.get(f"{kind}NightReminder", "") or r["ability"]))
    for kind in out:
        out[kind].sort()
        out[kind] = [x[1:] for x in out[kind]]  # (id, hint)
    return out


def build():
    orders = official_orders()
    wafu = museum_orders("wafu-leiming")
    mth = museum_orders("mantanghong")

    lines = [
        '"""夜晚唤醒顺序(五板子)。',
        "",
        "数据源:",
        "- 暗流涌动/黯月传奇/教派紫月:官方全局夜晚顺序表(ThePandemoniumInstitute/botc-release",
        "  resources/data/nightsheet.json)与各板角色表求交集,提示文案按官方规则书速写",
        "- 瓦釜雷鸣:钟楼剧本博物馆 735177364786380809.json 的每角色位置与官方提醒文案",
        "- 满堂红:钟楼剧本博物馆 892280963319463958.json 的每角色位置与官方提醒文案",
        "  每步 key 为角色 id 或特殊步骤 dusk/dawn/minioninfo/demoninfo",
        "生成器:backend/tools/build_night_order.py(改数据后重跑)",
        '"""',
        "",
        "DUSK = {'key': 'dusk', 'name': '天黑', 'hint': '所有玩家闭眼'}",
        "DAWN = {'key': 'dawn', 'name': '天亮', 'hint': '所有玩家睁眼;宣告昨夜死者,进入白天'}",
        "MINIONINFO = {'key': 'minioninfo', 'name': '爪牙会面', 'hint': '唤醒所有爪牙,让他们互认,指向恶魔'}",
        "DEMONINFO = {'key': 'demoninfo', 'name': '恶魔会面',",
        "             'hint': '唤醒恶魔,指出爪牙,展示三个不在场镇民角色作为伪装'}",
        "",
        "NIGHT_ORDER = {",
    ]

    def step(key, hint, role_by_id):
        if key in ("dusk", "dawn", "minioninfo", "demoninfo"):
            return {"key": key, "name": {"dusk": "天黑", "dawn": "天亮",
                                         "minioninfo": "爪牙会面", "demoninfo": "恶魔会面"}[key],
                    "hint": hint}
        r = role_by_id[key]
        return {"key": key, "name": r["name"], "hint": hint}

    for sid, s in SCRIPTS.items():
        # 步骤名按本板角色表取(板间同名不同译的角色不会串味)
        role_by_id = {r["id"]: r for r in s["roles"]}
        lines.append(f'    "{sid}": {{')
        if sid == "wafu-leiming":
            first = [("dusk", DUSK["hint"])] + wafu["first"]
            # 爪牙会面插在疯子前、恶魔会面插在疯子后(官方惯例 minioninfo→lunatic→demoninfo)
            li = next(i for i, (k, _) in enumerate(first) if k == "lunatic")
            first.insert(li, ("minioninfo", MINIONINFO["hint"]))
            first.insert(li + 2, ("demoninfo", DEMONINFO["hint"]))
            other = [("dusk", DUSK["hint"])] + wafu["other"]
        elif sid == "mantanghong":
            # 会面插在首夜开头(小怪宝在场时官方规则跳过,由说书人掌握),天亮收尾
            first = [("dusk", DUSK["hint"]), ("minioninfo", MINIONINFO["hint"]),
                     ("demoninfo", DEMONINFO["hint"])] + mth["first"] + [("dawn", DAWN["hint"])]
            other = [("dusk", DUSK["hint"])] + mth["other"] + [("dawn", DAWN["hint"])]
        else:
            keys = orders[sid]
            special = {"dusk": DUSK["hint"], "dawn": DAWN["hint"],
                       "minioninfo": MINIONINFO["hint"], "demoninfo": DEMONINFO["hint"]}
            to_ours = lambda k: SLUG_UNFIX.get(k, k)  # noqa: E731
            first = [(to_ours(k), special.get(k) or HINTS.get(k, role_by_id[to_ours(k)]["ability"]))
                     for k in keys["first"]]
            other = [(to_ours(k), special.get(k) or HINTS.get(k, role_by_id[to_ours(k)]["ability"]))
                     for k in keys["other"]]
        for kind, steps in (("first", first), ("other", other)):
            lines.append(f'        "{kind}": [')
            for key, hint in steps:
                d = step(key, hint, role_by_id)
                lines.append(f"            {d!r},")
            lines.append("        ],")
        lines.append("    },")
    lines.append("}")
    out = ROOT / "app" / "night_order.py"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written {out}")


if __name__ == "__main__":
    build()
