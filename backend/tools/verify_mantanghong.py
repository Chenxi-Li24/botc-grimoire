"""满堂红+板子拆分隔离验证:不连 8000 端口、SAVE_PATH 指向临时目录,绝不碰线上局。"""
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app.game as G  # noqa: E402
from app.night_order import NIGHT_ORDER  # noqa: E402
from app.roles import SCRIPTS, SCRIPT_ADJUST_ROLES, COMPOSITION, ROLE_ADJUSTMENTS  # noqa: E402

G.SAVE_PATH = Path(tempfile.mkdtemp()) / "game-test.json"

fails = []


def check(name, cond, detail=""):
    if not cond:
        fails.append(f"{name}: {detail}")
    print(("PASS " if cond else "FAIL ") + name + (f" | {detail}" if detail and not cond else ""))


# ---- 1. 注册表 ----
check("五板子都在", set(SCRIPTS) == {"trouble-brewing", "bad-moon-rising",
                                    "sects-and-violets", "wafu-leiming", "mantanghong"})
mth = SCRIPTS["mantanghong"]
ids = [r["id"] for r in mth["roles"]]
check("满堂红 25 角色(无旅行者)", len(ids) == 25, str(len(ids)))
check("满堂红角色 id 全局唯一", len(set(ids)) == len(ids))
check("满堂红 min_players=7", mth["min_players"] == 7)
teams = Counter(r["team"] for r in mth["roles"])
check("满堂红 13镇/4外/5爪/3恶", (teams["townsfolk"], teams["outsider"], teams["minion"], teams["demon"])
      == (13, 4, 5, 3), str(dict(teams)))
# 共用角色是同一份 dict(一处改全板生效)
tb = SCRIPTS["trouble-brewing"]
by = {r["id"]: r for r in tb["roles"]}
check("imp 与暗流涌动共用 dict", {r["id"]: r for r in mth["roles"] if r["id"] == "imp"}["imp"] is by["imp"])
# 满堂红覆盖名不污染原板
check("满堂红造谣者覆盖名", {r["id"]: r for r in mth["roles"] if r["id"] == "gossip"}["gossip"]["name"] == "造谣者")
check("黯月长舌原名保留", next(r for r in SCRIPTS["bad-moon-rising"]["roles"] if r["id"] == "gossip")["name"] == "长舌")
# 调整角色
check("小怪宝配比调整 +1爪/−1恶", ROLE_ADJUSTMENTS["lil-monsta"] == (0, 0, 1, -1))
check("满堂红调整角色表", set(SCRIPT_ADJUST_ROLES["mantanghong"]) == {"godfather", "lil-monsta"})
# 夜晚顺序:key 都是本板角色或特殊步
for kind in ("first", "other"):
    keys = [s["key"] for s in NIGHT_ORDER["mantanghong"][kind]]
    valid = set(ids) | {"dusk", "dawn", "minioninfo", "demoninfo"}
    check(f"满堂红夜晚{kind}步骤合法", all(k in valid for k in keys), str([k for k in keys if k not in valid]))
check("满堂红首夜含会面", all(k in [s["key"] for s in NIGHT_ORDER["mantanghong"]["first"]]
                            for k in ("minioninfo", "demoninfo")))
check("满堂红天亮收尾", NIGHT_ORDER["mantanghong"]["first"][-1]["key"] == "dawn"
      and NIGHT_ORDER["mantanghong"]["other"][-1]["key"] == "dawn")

# ---- 2. 随机发牌:满堂红 7~15 人 × 200 局 ----
for n in range(7, 16):
    for _ in range(200):
        gm = G.GameManager()
        gm.configure("mantanghong", n)
        gm.assign_roles()
        assigned = [p.role_id for p in gm.players.values() if p.role_id]
        assigned += [rid for rid in gm.seat_roles.values()]
        assert len(assigned) == n, f"{n}人局发了{len(assigned)}张牌"
        tc = Counter(gm.roles[r]["team"] for r in assigned)
        base = COMPOSITION[n]
        if tc["demon"] == 0:  # 小怪宝官方开局:爪牙+1,无恶魔(小怪宝不发给任何座位)
            if tc["minion"] != base[2] + 1:
                fails.append(f"{n}人局小怪宝爪牙数 {tc}")
                break
        elif tc["demon"] == 1:
            if tc["minion"] != base[2]:
                fails.append(f"{n}人局普通爪牙数 {tc}")
                break
        else:
            fails.append(f"{n}人局恶魔数异常 {tc}")
            break
        if tc["outsider"] < 0:
            fails.append(f"{n}人局外来者负数 {tc}")
            break
print("随机发牌 9 种人数 × 200 局完成")

# ---- 3. 夜晚流程:首夜/次夜步骤组装 ----
gm = G.GameManager()
gm.configure("mantanghong", 9)
gm.assign_roles()
check("满堂红开局进夜晚", gm.phase == "night" and gm.night_no == 1)
check("首夜步骤非空", len(gm.night_steps) > 3)
check("首夜含爪牙会面步", any(s["key"] == "minioninfo" for s in gm.night_steps))
gm.end_day() if gm.phase == "day" else None
while gm.phase == "night":
    gm.night_next()
gm.end_day()  # 天黑 → 第 2 夜
check("第 2 夜步骤非空", gm.phase == "night" and gm.night_no == 2 and len(gm.night_steps) > 3)

# ---- 4. 手动发身份:小怪宝空座标记路径 ----
gm2 = G.GameManager()
gm2.configure("mantanghong", 7)
base = COMPOSITION[7]
m_roles = {r["id"]: r for r in gm2.roles.values()}
mins = [r["id"] for r in gm2.roles.values() if r["team"] == "minion"]
good = [r["id"] for r in gm2.roles.values() if r["team"] in ("townsfolk", "outsider")]
assign = [{"seat": i + 1, "role": mins[i % len(mins)] if i < base[2] + 1
           else good[(i - base[2] - 1) % len(good)]} for i in range(6)]
assign.append({"seat": 7, "role": "lil-monsta"})
try:
    gm2.assign_manual(assign)
    check("手动发身份小怪宝(恶魔=1标记)通过", True)
except ValueError as e:
    check("手动发身份小怪宝(恶魔=1标记)通过", False, str(e))

# ---- 5. 其余板子回归:随机发牌恶魔恰 1、总数对 ----
for sid, minp in (("trouble-brewing", 5), ("bad-moon-rising", 5),
                  ("sects-and-violets", 5), ("wafu-leiming", 7)):
    for n in (minp, 15):
        for _ in range(30):
            gm3 = G.GameManager()
            gm3.configure(sid, n)
            gm3.assign_roles()
            assigned = [p.role_id for p in gm3.players.values() if p.role_id] + list(gm3.seat_roles.values())
            tc = Counter(gm3.roles[r]["team"] for r in assigned)
            check(f"{sid} {n}人局恶魔恰1", tc["demon"] == 1, str(dict(tc)))
            if tc["demon"] != 1 or len(assigned) != n:
                fails.append(f"{sid} {n}人局: {dict(tc)} / {len(assigned)}")
                break
print("回归完成")

# ---- 6. 说书人视图:脚本列表含满堂红 ----
gm4 = G.GameManager()
gm4.configure("mantanghong", 8)
sv = gm4.storyteller_view()
check("ST 视图脚本列表含满堂红", any(s["id"] == "mantanghong" for s in sv["scripts"]))
check("ST 视图调整角色含小怪宝", "lil-monsta" in sv["adjust_roles"])

print()
if fails:
    print(f"FAILED {len(fails)} 项")
    for f in fails[:30]:
        print(" -", f)
    sys.exit(1)
print("ALL PASS")
