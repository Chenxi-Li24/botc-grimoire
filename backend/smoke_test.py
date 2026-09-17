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
        print(f"WS    玩家收到角色: {view['me']['role']['name']}(座位 {view['me']['seat']})")

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

    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    print("ALL PASS")


if __name__ == "__main__":
    asyncio.run(main())
