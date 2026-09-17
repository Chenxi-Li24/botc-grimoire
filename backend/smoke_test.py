"""冒烟测试:验证 REST + WebSocket 全链路(配置→加入→选座→分配→推送)。

用法:先 `python run.py` 启动服务器,再另开终端 `python smoke_test.py`
"""

import asyncio
import json
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import websockets

BASE = "http://localhost:8000"
PASSWORD = "grimoire"
ST = {"X-Storyteller-Password": PASSWORD}


def req(path: str, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


async def main() -> None:
    # 幂等:先重置,清掉上一局可能残留的状态
    req("/api/reset", "POST", headers=ST)

    # 说书人配置板子 + 人数
    cfg = req("/api/config", "POST", {"script": "sects-and-violets", "player_count": 6}, ST)
    assert cfg["player_count"] == 6 and len(cfg["seats"]) == 6
    print("CONFIG 教派紫月 6 人 OK")

    ids = [req("/api/join", "POST", {"name": f"测试{i}"})["player_id"] for i in range(1, 7)]
    print("JOIN  6 名玩家加入")

    # 选座:座位 1~6
    for seat, pid in enumerate(ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    print("SIT   6 名玩家入座 1~6")

    # 占座冲突应被拒绝
    try:
        req(f"/api/player/{ids[0]}/sit", "POST", {"seat": 2})
        raise AssertionError("座位冲突未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400, f"冲突应 400,实际 {e.code}"
    print("SIT   占座冲突被拒绝 OK")

    state = req("/api/assign", "POST", headers=ST)
    assert state["status"] == "playing"
    teams = Counter(p["role"]["team"] for s in state["seats"] for p in [s["player"]] if p)
    assert teams["demon"] == 1 and sum(teams.values()) == 6, f"配比异常 {dict(teams)}"
    print("ASSIGN " + ", ".join(f"{s['player']['seat']}:{s['player']['role']['name']}"
                                for s in state["seats"] if s["player"]))
    print(f"ASSIGN 配比 {dict(teams)}(方古在场则为 2镇民2外来者1爪牙1恶魔)")

    async with websockets.connect(f"ws://localhost:8000/ws?who={ids[0]}") as ws:
        view = json.loads(await ws.recv())
        assert view["me"]["role"], "玩家应收到自己的角色"
        assert view["me"]["seat"] == 1
        assert view["seats"][0]["is_me"] is True
        assert "role" not in view["seats"][1]["player"], "玩家不应看到他人角色"
        # 官方配比(公开)与说书人一致;实际配置(预发身份等)不泄露
        assert view["composition"] == state["composition"] and len(view["composition"]) == 4, \
            "玩家应看到官方基础配比"
        assert "seat_roles" not in view and "demon_seats" not in view, "实际配置不应泄露给玩家"
        print(f"WS    玩家收到角色: {view['me']['role']['name']}(座位 {view['me']['seat']}),"
              f"配比 {view['composition']} OK")

        req(f"/api/player/{ids[0]}/alive", "POST", headers=ST)
        view = json.loads(await ws.recv())
        assert view["me"]["alive"] is False, "存活状态应实时推送"
        print("WS    存活标记实时推送 OK")

    # ---- 瓦釜雷鸣:7~15 人,6 人应被拒绝 ----
    try:
        req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 6}, ST)
        raise AssertionError("瓦釜雷鸣 6 人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400, f"瓦釜雷鸣 6 人应 400,实际 {e.code}"
    print("CONFIG 瓦釜雷鸣 6 人被拒绝 OK")

    req("/api/reset", "POST", headers=ST)  # 清掉上一局的玩家
    cfg = req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    assert cfg["player_count"] == 7 and len(cfg["seats"]) == 7
    print("CONFIG 瓦釜雷鸣 7 人 OK")

    ids = [req("/api/join", "POST", {"name": f"瓦{i}"})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    state = req("/api/assign", "POST", headers=ST)
    assert state["status"] == "playing"
    teams = Counter(p["role"]["team"] for s in state["seats"] for p in [s["player"]] if p)
    assert teams["demon"] == 1 and sum(teams.values()) == 7, f"瓦釜雷鸣配比异常 {dict(teams)}"
    assert teams.get("outsider", 0) >= 0
    print("VAFU  " + ", ".join(f"{s['player']['seat']}:{s['player']['role']['name']}"
                              for s in state["seats"] if s["player"]))
    print(f"VAFU  配比 {dict(teams)}(恶魔决定 ±外来者)")

    # ---- 手动发身份 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids = [req("/api/join", "POST", {"name": f"手{i}"})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})

    # 两个恶魔应被拒绝
    bad = [{"seat": s, "role": "imp" if s <= 2 else ("chef" if s <= 4 else "drunk")} for s in range(1, 7)]
    try:
        req("/api/assign/manual", "POST", {"assignments": bad}, ST)
        raise AssertionError("两名恶魔未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("MANUAL 两名恶魔被拒绝 OK")

    # 重复角色应被拒绝(即使恶魔/爪牙数量合法)
    dup = [{"seat": s, "role": r} for s, r in zip(
        range(1, 7), ["imp", "poisoner", "chef", "chef", "investigator", "drunk"])]
    try:
        req("/api/assign/manual", "POST", {"assignments": dup}, ST)
        raise AssertionError("重复角色未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("MANUAL 重复角色被拒绝 OK")

    good = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "poisoner"},
            {"seat": 3, "role": "empath"}, {"seat": 4, "role": "chef"},
            {"seat": 5, "role": "investigator"}, {"seat": 6, "role": "drunk"}]
    state = req("/api/assign/manual", "POST", {"assignments": good}, ST)
    assert state["status"] == "playing"
    by_seat = {s["seat"]: s["player"]["role"]["id"] for s in state["seats"] if s["player"]}
    want = {1: "imp", 2: "poisoner", 3: "empath", 4: "chef", 5: "investigator", 6: "drunk"}
    assert by_seat == want, f"手动分配结果不符 {by_seat}"
    print("MANUAL 6 座手动发身份成功,角色与指定一致 OK")

    # ---- 手动发身份:无人入座也能先发,玩家入座自动继承 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    pre = [{"seat": s, "role": r} for s, r in zip(
        range(1, 7), ["imp", "poisoner", "empath", "chef", "investigator", "drunk"])]
    state = req("/api/assign/manual", "POST", {"assignments": pre}, ST)
    assert state["status"] == "lobby", "无人入座时应保持 lobby"
    assigned = {s["seat"]: (s.get("assigned_role") or {}).get("id") for s in state["seats"]}
    assert assigned == want, f"空座预发身份不符 {assigned}"
    print("MANUAL 无人入座预发身份成功,状态保持 lobby OK")

    ids = [req("/api/join", "POST", {"name": f"预{i}"})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids, 1):
        view = req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
        assert view["me"]["role"]["id"] == want[seat], f"座位 {seat} 应继承 {want[seat]}"
        if seat == 3:
            assert req("/api/state", "GET", headers=ST)["status"] == "lobby", "未满员不应开局"
    state = req("/api/state", "GET", headers=ST)
    assert state["status"] == "playing", "最后一人入座后应自动开局"
    by_seat = {s["seat"]: s["player"]["role"]["id"] for s in state["seats"] if s["player"]}
    assert by_seat == want, f"预发继承结果不符 {by_seat}"
    print("MANUAL 玩家随后入座继承预发身份,满员自动开局 OK")

    # 重置后回到 lobby,座位清空
    state = req("/api/reset", "POST", headers=ST)
    assert state["status"] == "lobby" and all(s["player"] is None for s in state["seats"])
    print("RESET 回到 lobby、座位清空 OK")

    # ---- v1 完整:夜晚流程 + 状态标记 + 提名处决 + 存档 ----
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids = [req("/api/join", "POST", {"name": f"夜{i}"})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    state = req("/api/assign", "POST", headers=ST)
    assert state["phase"] == "night" and state["night_no"] == 1
    assert state["night"]["steps"][0]["key"] == "dusk"
    assert state["night"]["steps"][-1]["key"] == "dawn"
    assert len(state["bluffs"]) == 3, "随机发牌时应同时抽好伪装"
    print("NIGHT 开局进入第 1 夜,dusk 起 dawn 止 OK")

    # 走到天亮
    for _ in range(len(state["night"]["steps"])):
        state = req("/api/night/next", "POST", headers=ST)
    assert state["phase"] == "day" and state["day_no"] == 1
    print("NIGHT 走完第 1 夜 → 第 1 天 OK")

    # 标记:说书人可见,玩家不可见
    req("/api/marker", "POST", {"seat": 1, "marker": "poisoned", "on": True}, ST)
    req("/api/marker", "POST", {"seat": 1, "marker": "mad", "on": True}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["seats"][0]["markers"] == ["mad", "poisoned"], state["seats"][0].get("markers")
    pview = req(f"/api/me/{ids[0]}")
    assert "markers" not in pview["seats"][0], "标记不应泄露给玩家"
    req("/api/marker", "POST", {"seat": 1, "marker": "poisoned", "on": False}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["seats"][0]["markers"] == ["mad"]
    print("MARKER 标记说书人可见、玩家不可见,可增删 OK")

    # 提名 → 投票 → 处决
    req("/api/nomination", "POST", {"nominator": 2, "nominee": 3}, ST)
    for s in (1, 2, 5, 6):
        req("/api/nomination/vote", "POST", {"seat": s}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["current"]["votes"] == [1, 2, 5, 6] and state["quorum"] == 4
    # 投票中不能另起提名
    try:
        req("/api/nomination", "POST", {"nominator": 4, "nominee": 5}, ST)
        raise AssertionError("投票中另起提名未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/nomination/resolve", "POST", {"executed": True}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["current"] is None
    assert state["nominations"][-1]["executed"] and state["nominations"][-1]["votes"] == [1, 2, 5, 6]
    assert state["seats"][2]["player"]["alive"] is False
    print("NOM   提名→4 票→处决,座位 3 死亡 OK")

    # 无效提名不处决
    req("/api/nomination", "POST", {"nominator": 4, "nominee": 5}, ST)
    req("/api/nomination/resolve", "POST", {"executed": False}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["seats"][4]["player"]["alive"] is True
    print("NOM   无效提名不处决 OK")

    # 天黑 → 第 2 夜,首夜专用角色不再出现
    state = req("/api/day/end", "POST", headers=ST)
    assert state["phase"] == "night" and state["night_no"] == 2
    keys = [s["key"] for s in state["night"]["steps"]]
    assert "washerwoman" not in keys and "imp" in keys, keys
    print("NIGHT 天黑 → 第 2 夜,首夜角色不再出现 OK")

    # 存档:每次变更写盘;读档可撤销重置
    save_file = Path(__file__).parent / "data" / "game.json"
    assert save_file.exists(), "存档文件未生成"
    assert json.loads(save_file.read_text(encoding="utf-8"))["night_no"] == 2
    req("/api/reset", "POST", headers=ST)
    state = req("/api/load", "POST", headers=ST)
    assert state["status"] == "playing" and state["night_no"] == 2
    assert state["seats"][2]["player"]["alive"] is False
    print("SAVE  读档撤销重置,恢复第 2 夜与死者 OK")

    # 酒鬼认知覆盖 → 夜晚步骤含假角色步骤(改认知覆盖会重算步骤表)
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids2 = [req("/api/join", "POST", {"name": f"醉{i}"})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids2, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    pre = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "poisoner"},
           {"seat": 3, "role": "empath"}, {"seat": 4, "role": "chef"},
           {"seat": 5, "role": "investigator"}, {"seat": 6, "role": "drunk"}]
    req("/api/assign/manual", "POST", {"assignments": pre}, ST)
    req("/api/fake", "POST", {"seat": 6, "role": "washerwoman"}, ST)
    pview = req(f"/api/me/{ids2[5]}")
    assert pview["me"]["role"]["id"] == "washerwoman", "酒鬼应看到假角色"
    state = req("/api/state", "GET", headers=ST)
    fake_steps = [s for s in state["night"]["steps"] if s.get("fake_for") == 6]
    assert fake_steps and fake_steps[0]["key"] == "washerwoman", "夜晚步骤应含假角色步"
    print("FAKE  酒鬼看到洗衣妇,夜晚步骤含假角色步(座 6) OK")

    # ---- 伪装:配版时选好,恶魔得知三个不在场好角色,仅恶魔可见 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    b_ids = [req("/api/join", "POST", {"name": f"伪{i}"})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(b_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    pre = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "poisoner"},
           {"seat": 3, "role": "empath"}, {"seat": 4, "role": "chef"},
           {"seat": 5, "role": "investigator"}, {"seat": 6, "role": "drunk"}]
    # 非法伪装(提交失败不改变状态,可连续重试):在场 / 非好角色 / 数量不对 / 不属于板子
    for bad in (["empath", "soldier", "virgin"],           # 共情者在场
                ["washerwoman", "drunk", "virgin"],        # 酒鬼是外来者(TB 伪装限镇民)
                ["washerwoman", "soldier"],                # 只给 2 个
                ["washerwoman", "soldier", "balloonist"]):  # 不属于本板子
        try:
            req("/api/assign/manual", "POST", {"assignments": pre, "bluffs": bad}, ST)
            raise AssertionError(f"非法伪装未被拒绝 {bad}")
        except urllib.error.HTTPError as e:
            assert e.code == 400, f"非法伪装应 400,实际 {e.code}"
    # 说书人指定伪装:配版时即生效
    want_bluffs = ["washerwoman", "soldier", "virgin"]
    state = req("/api/assign/manual", "POST", {"assignments": pre, "bluffs": want_bluffs}, ST)
    b = state["bluffs"]
    assert [r["id"] for r in b] == want_bluffs, "伪装应与说书人指定一致"
    in_play = {"imp", "poisoner", "empath", "chef", "investigator", "drunk"}
    assert not ({r["id"] for r in b} & in_play), "伪装必须不在场"
    dview = req(f"/api/me/{b_ids[0]}")
    assert [r["id"] for r in dview["bluffs"]] == [r["id"] for r in b], "恶魔应看到伪装"
    pview = req(f"/api/me/{b_ids[2]}")
    assert "bluffs" not in pview, "非恶魔不应看到伪装"
    # 酒鬼看到假镇民角色,但真实身份是外来者,不应看到伪装
    req("/api/fake", "POST", {"seat": 6, "role": "washerwoman"}, ST)
    dview6 = req(f"/api/me/{b_ids[5]}")
    assert "bluffs" not in dview6, "酒鬼(假镇民)不应看到伪装"
    print("BLUFF 配版时选伪装:指定生效、4 种非法拒绝、仅恶魔可见 OK")

    # ---- 人未齐也可开局:随机发牌覆盖空座;迟到玩家入座继承 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    late_ids = [req("/api/join", "POST", {"name": f"迟{i}"})["player_id"] for i in range(1, 5)]
    for seat, pid in enumerate(late_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    state = req("/api/assign", "POST", headers=ST)  # 只 4 人入座也应能发牌并开局
    assert state["status"] == "playing" and state["phase"] == "night" and state["night_no"] == 1
    empty_roles = {str(seat): rid for seat, rid in state["seat_roles"].items()}
    assert set(empty_roles) == {"5", "6"}, empty_roles
    rids = {r["id"] for r in state["roles"]}
    assert set(empty_roles.values()) <= rids, "空座预发角色应在板子角色表中"
    late5 = req("/api/join", "POST", {"name": "迟到者5"})["player_id"]
    view = req(f"/api/player/{late5}/sit", "POST", {"seat": 5})
    assert view["me"]["role"]["id"] == empty_roles["5"], "迟到入座应继承预发身份"
    assert view["status"] == "playing"
    print("LATE  4 人随机发牌即开局,空座 5/6 挂预发身份,迟到者入座继承 OK")

    # 会面名单对空座预发的恶魔也成立(姓名为空时前端显示「空(预发)」)
    dseat = state["demon_seats"][0]
    assert len(state["demon_seats"]) == 1 and len(state["minion_seats"]) >= 1
    occupied = {s["seat"] for s in state["seats"] if s["player"]}
    assert (dseat["name"] is None) == (dseat["seat"] not in occupied), \
        f"恶魔座姓名应与入座状态一致 {dseat}"
    print("MEET  恶魔/爪牙座名单与空座预发一致 OK")

    # 进行中换座仍被拒绝
    try:
        req(f"/api/player/{late_ids[0]}/sit", "POST", {"seat": 6})
        raise AssertionError("进行中换座未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("LATE  游戏进行中换座被拒绝 OK")

    # ---- 手动预发 + 强制开始 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids3 = [req("/api/join", "POST", {"name": f"强{i}"})["player_id"] for i in range(1, 5)]
    for seat, pid in enumerate(ids3, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    try:  # 没发身份就点开始应被拒绝
        req("/api/start", "POST", headers=ST)
        raise AssertionError("未发身份强制开局未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    pre = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "poisoner"},
           {"seat": 3, "role": "empath"}, {"seat": 4, "role": "chef"},
           {"seat": 5, "role": "investigator"}, {"seat": 6, "role": "drunk"}]
    state = req("/api/assign/manual", "POST", {"assignments": pre}, ST)
    assert state["status"] == "lobby" and state["can_start"] is True, "人未齐时手动发身份应保持 lobby 且可开始"
    assert len(state["bluffs"]) == 3, "未指定伪装时应自动抽好(配版时即定)"
    # 会面名单:告诉爪牙谁是恶魔、告诉恶魔谁是爪牙
    assert [d["seat"] for d in state["demon_seats"]] == [1], state["demon_seats"]
    assert [m["seat"] for m in state["minion_seats"]] == [2], state["minion_seats"]
    assert state["demon_seats"][0]["name"] == "强1" and state["minion_seats"][0]["name"] == "强2", \
        "会面名单应带在座玩家姓名"
    state = req("/api/start", "POST", headers=ST)
    assert state["status"] == "playing" and state["phase"] == "night" and state["night_no"] == 1
    keys = [s["key"] for s in state["night"]["steps"]]
    assert "investigator" in keys, "空座 5 的调查员步骤应在夜晚表中"
    print("START 手动预发 4/6 人强制开局成功,空座角色步骤在夜晚表中 OK")
    print("MEET  会面名单:恶魔座 1(强1)、爪牙座 2(强2) OK")

    # ---- 哨兵(神职角色):说书人调外来者数,方向保密、玩家只见「哨兵在场」 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["sentinel"] == 0
    for bad in (3, -2):
        try:
            req("/api/sentinel", "POST", {"value": bad}, ST)
            raise AssertionError(f"哨兵 {bad} 应被拒绝")
        except urllib.error.HTTPError as e:
            assert e.code == 400
    state = req("/api/sentinel", "POST", {"value": 1}, ST)
    assert state["sentinel"] == 1
    pid = req("/api/join", "POST", {"name": "senti1"})["player_id"]
    req(f"/api/player/{pid}/sit", "POST", {"seat": 1})
    pview = req(f"/api/me/{pid}")
    assert pview["sentinel"] is True and pview["composition"] == [3, 1, 1, 1], \
        "玩家应知哨兵在场但不知方向、不见实际配比"
    state = req("/api/assign", "POST", headers=ST)  # 随机发牌:+1 应作用于实际配比
    teams = Counter(p["role"]["team"] for s in state["seats"] for p in [s["player"]] if p)
    teams += Counter(next(r["team"] for r in state["roles"] if r["id"] == rid)
                     for rid in state["seat_roles"].values())
    assert teams.get("outsider", 0) in (2, 4), f"哨兵 +1 后外来者应为 2 或 4(视男爵),实际 {dict(teams)}"
    try:  # 开局后不能再改哨兵
        req("/api/sentinel", "POST", {"value": 0}, ST)
        raise AssertionError("开局后改哨兵应被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print(f"SENTI 哨兵 +1:实际配比 {dict(teams)},玩家只见官方配比与在场提示 OK")

    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    req("/api/sentinel", "POST", {"value": -1}, ST)
    state = req("/api/assign", "POST", headers=ST)
    teams = Counter(next(r["team"] for r in state["roles"] if r["id"] == rid)
                    for rid in state["seat_roles"].values())
    assert teams.get("outsider", 0) in (0, 2), f"哨兵 -1 后外来者应为 0 或 2(视男爵),实际 {dict(teams)}"
    print(f"SENTI 哨兵 -1:实际配比 {dict(teams)} OK")

    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    state = req("/api/sentinel", "POST", {"value": 2}, ST)
    assert state["sentinel"] == 2, "哨兵「不变」应可保存(在场但不调整)"
    pid = req("/api/join", "POST", {"name": "senti2"})["player_id"]
    req(f"/api/player/{pid}/sit", "POST", {"seat": 1})
    pview = req(f"/api/me/{pid}")
    assert pview["sentinel"] is True and pview["composition"] == [3, 1, 1, 1], \
        "哨兵不变:玩家应知在场但不知方向、配比仍是官方基础"
    state = req("/api/assign", "POST", headers=ST)  # 不变:实际配比不因哨兵改变
    teams = Counter(p["role"]["team"] for s in state["seats"] for p in [s["player"]] if p)
    teams += Counter(next(r["team"] for r in state["roles"] if r["id"] == rid)
                     for rid in state["seat_roles"].values())
    assert teams.get("outsider", 0) in (1, 3), \
        f"哨兵不变时外来者应为 1 或 3(仅视男爵),实际 {dict(teams)}"
    print(f"SENTI 哨兵不变:实际配比 {dict(teams)},配比未因哨兵改变 OK")

    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 5}, ST)
    try:  # 5 人局官方配比没有外来者名额 -> -1 被拒绝
        req("/api/sentinel", "POST", {"value": -1}, ST)
        raise AssertionError("5 人局哨兵 -1 应被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("SENTI 5 人局哨兵 -1 被拒绝 OK")

    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    print("ALL PASS")


if __name__ == "__main__":
    asyncio.run(main())
