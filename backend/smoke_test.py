"""冒烟测试:验证 REST + WebSocket 全链路(配置→加入→选座→分配→推送)。

用法:先 `python run.py` 启动服务器,再另开终端 `python smoke_test.py`
"""

import asyncio
import json
import urllib.error
import urllib.request
from collections import Counter

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

    print("ALL PASS")


if __name__ == "__main__":
    asyncio.run(main())
