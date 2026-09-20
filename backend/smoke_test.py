"""冒烟测试:验证 REST + WebSocket 全链路(配置→加入→选座→分配→推送)。

用法:先 `python tools/run_test_server.py` 启动 8001 测试服(固定临时存档,不碰线上局),
再另开终端 `SMOKE_BASE=http://localhost:8001 python smoke_test.py`(不设则默认 8000 线上)
"""

import asyncio
import json
import os
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import websockets

BASE = os.environ.get("SMOKE_BASE", "http://localhost:8000")
PASSWORD = "grimoire"
ST = {"X-Storyteller-Password": PASSWORD}


def room() -> str:
    """当前房间号:重置会换号,加入前现取。"""
    return req("/api/state", headers=ST)["room_code"]

def req(path: str, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


def finish_night() -> dict:
    """按动态夜序推进到天亮，不再假设旧步骤表与运行队列等长。"""
    for _ in range(100):
        state = req("/api/state", headers=ST)
        if state["phase"] == "day":
            return state
        req("/api/night/next", "POST", headers=ST)
    raise AssertionError("夜晚在 100 次推进后仍未结束")


async def main() -> None:
    # 幂等:先重置,清掉上一局可能残留的状态
    req("/api/reset", "POST", headers=ST)

    # 说书人配置板子 + 人数
    cfg = req("/api/config", "POST", {"script": "sects-and-violets", "player_count": 6}, ST)
    assert cfg["player_count"] == 6 and len(cfg["seats"]) == 6
    print("CONFIG 教派紫月 6 人 OK")

    ids = [req("/api/join", "POST", {"name": f"测试{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
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

    async with websockets.connect(f"ws://{BASE.split('//', 1)[1]}/ws?who={ids[0]}") as ws:
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
        # 夜里刚死:本人卡天亮前不显示死亡(手机扣桌上防旁人偷看),说书人侧已置死
        assert view["me"]["alive"] is True, "夜里本人卡应隐藏死亡直到天亮"
        assert req("/api/state", "GET", headers=ST)["seats"][0]["player"]["alive"] is False
        print("WS    存活标记实时推送(夜里本人不显示,说书人可见) OK")

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

    ids = [req("/api/join", "POST", {"name": f"瓦{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
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
    ids = [req("/api/join", "POST", {"name": f"手{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
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
    state = req("/api/assign/manual", "POST", {"assignments": good, "fakes": [{"seat": 6, "role": "washerwoman"}]}, ST)
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
    state = req("/api/assign/manual", "POST", {"assignments": pre, "fakes": [{"seat": 6, "role": "washerwoman"}]}, ST)
    assert state["status"] == "lobby", "无人入座时应保持 lobby"
    assigned = {s["seat"]: (s.get("assigned_role") or {}).get("id") for s in state["seats"]}
    assert assigned == want, f"空座预发身份不符 {assigned}"
    print("MANUAL 无人入座预发身份成功,状态保持 lobby OK")

    ids = [req("/api/join", "POST", {"name": f"预{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids, 1):
        view = req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
        if seat < 6:
            # 开局前不揭示身份:入座虽继承预发,但说书人开局才发身份
            assert "role" not in view["me"], f"开局前座位 {seat} 不应看到角色"
            assert req("/api/state", "GET", headers=ST)["status"] == "lobby", "未满员不应开局"
        else:
            # 酒鬼(座 6)发牌时已带认知覆盖 → 本人看到假身份洗衣妇,说书人侧仍是 drunk
            want_see = "washerwoman" if seat == 6 else want[seat]
            assert view["me"]["role"]["id"] == want_see, f"满员自动开局后座位 {seat} 应继承 {want_see}"
    assert req(f"/api/me/{ids[0]}")["me"]["role"]["id"] == "imp", "开局后其他玩家也拿到角色"
    state = req("/api/state", "GET", headers=ST)
    assert state["status"] == "playing", "最后一人入座后应自动开局"
    by_seat = {s["seat"]: s["player"]["role"]["id"] for s in state["seats"] if s["player"]}
    assert by_seat == want, f"预发继承结果不符 {by_seat}"
    print("MANUAL 玩家随后入座继承预发身份,开局前不见角色,满员自动开局 OK")

    # 重置后回到 lobby,座位清空
    state = req("/api/reset", "POST", headers=ST)
    assert state["status"] == "lobby" and all(s["player"] is None for s in state["seats"])
    print("RESET 回到 lobby、座位清空 OK")

    # ---- v1 完整:夜晚流程 + 状态标记 + 提名处决 + 存档 ----
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids = [req("/api/join", "POST", {"name": f"夜{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    state = req("/api/assign", "POST", headers=ST)
    assert state["phase"] == "night" and state["night_no"] == 1
    assert state["night"]["steps"][0]["key"] == "dusk"
    assert state["night"]["steps"][-1]["key"] == "dawn"
    assert len(state["bluffs"]) == 3, "随机发牌时应同时抽好伪装"
    print("NIGHT 开局进入第 1 夜,dusk 起 dawn 止 OK")

    # 走到天亮
    state = finish_night()
    assert state["phase"] == "day" and state["day_no"] == 1
    print("NIGHT 走完第 1 夜 → 第 1 天 OK")

    # 标记:说书人可见,玩家不可见(疯狂需附内容:善良角色)
    req("/api/marker", "POST", {"seat": 1, "marker": "poisoned", "on": True}, ST)
    req("/api/marker", "POST", {"seat": 1, "marker": "mad", "on": True, "about": "chef"}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["seats"][0]["markers"] == ["mad", "poisoned"], state["seats"][0].get("markers")
    pview = req(f"/api/me/{ids[0]}")
    assert "markers" not in pview["seats"][0], "标记不应泄露给玩家"
    req("/api/marker", "POST", {"seat": 1, "marker": "poisoned", "on": False}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["seats"][0]["markers"] == ["mad"]
    print("MARKER 标记说书人可见、玩家不可见,可增删 OK")

    # 提名 → 投票 → 结票(待处决)→ 天黑结算最多票者
    # 天亮默认「公聊私聊」子阶段:此时提名应被拒绝,说书人切换后才开放
    state = req("/api/state", "GET", headers=ST)
    assert state["day_stage"] == "talk", "天亮应先进入公聊私聊阶段"
    try:
        req("/api/nomination", "POST", {"nominator": 2, "nominee": 3}, ST)
        raise AssertionError("公聊阶段提名未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("DAY   天亮默认公聊阶段,提名被拒绝 OK")
    state = req("/api/day/stage", "POST", {"stage": "nom"}, ST)
    assert state["day_stage"] == "nom"
    # 提名进行中不能退回公聊
    req("/api/nomination", "POST", {"nominator": 2, "nominee": 3}, ST)
    try:
        req("/api/day/stage", "POST", {"stage": "talk"}, ST)
        raise AssertionError("提名进行中退回公聊未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    for s in (1, 2, 5, 6):
        req("/api/nomination/vote", "POST", {"seat": s}, ST)
    state = req("/api/state", "GET", headers=ST)
    # 处决门槛 = 存活玩家(不含旅行者)一半及以上:6 人全活 → 3 票
    assert state["current"]["votes"] == [1, 2, 5, 6] and state["quorum"] == 3
    # 投票中不能另起提名
    try:
        req("/api/nomination", "POST", {"nominator": 4, "nominee": 5}, ST)
        raise AssertionError("投票中另起提名未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/nomination/resolve", "POST", {"passed": True}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["current"] is None
    assert state["nominations"][-1]["passed"] and not state["nominations"][-1]["executed"], "结票后应待处决"
    assert state["nominations"][-1]["votes"] == [1, 2, 5, 6]
    assert state["seats"][2]["player"]["alive"] is True, "天黑前不处决,只标记待处决"
    print("NOM   提名→4 票→结票通过(待处决),座位 3 未死 OK")

    # 无效提名不通过
    req("/api/nomination", "POST", {"nominator": 4, "nominee": 5}, ST)
    req("/api/nomination/resolve", "POST", {"passed": False}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["nominations"][-1]["passed"] is False
    assert state["seats"][4]["player"]["alive"] is True
    print("NOM   无效提名不通过 OK")

    # 天黑 → 结算处决:唯一最多票者(3 号 4 票)被处决,再进第 2 夜
    state = req("/api/day/end", "POST", headers=ST)
    assert state["phase"] == "night" and state["night_no"] == 2
    assert state["seats"][2]["player"]["alive"] is False, "天黑时应处决票数最多的 3 号"
    noms = state["nominations"]
    assert noms[0]["executed"] is True and noms[1]["executed"] is False, "只有最多票者被处决"
    keys = [s["key"] for s in state["night"]["steps"]]
    assert "washerwoman" not in keys and "imp" in keys, keys
    print("NIGHT 天黑 → 结算处决 3 号(4 票)→ 第 2 夜,首夜角色不再出现 OK")

    # 存档:每次变更写盘;读档可撤销重置(测试服 SAVE_PATH 在临时目录,与 run_test_server.py 同规则)
    save_file = Path(os.environ.get("TEST_SAVE_PATH",
                   str(Path(tempfile.gettempdir()) / "botc-e2e" / "game.json"))) \
        if os.environ.get("SMOKE_BASE") else Path(__file__).parent / "data" / "game.json"
    assert save_file.exists(), "存档文件未生成"
    assert json.loads(save_file.read_text(encoding="utf-8"))["night_no"] == 2
    req("/api/reset", "POST", headers=ST)
    state = req("/api/load", "POST", headers=ST)
    assert state["status"] == "playing" and state["night_no"] == 2
    assert state["seats"][2]["player"]["alive"] is False
    print("SAVE  读档撤销重置,恢复第 2 夜与死者 OK")

    # 平票:两人同样最高票并列 → 天黑无人被处决(读档恢复的是第 2 夜,走到白天再试)
    finish_night()
    assert req("/api/state", "GET", headers=ST)["day_stage"] == "talk", "读档后天亮也应回到公聊阶段"
    req("/api/day/stage", "POST", {"stage": "nom"}, ST)
    req("/api/nomination", "POST", {"nominator": 1, "nominee": 2}, ST)
    for s in (1, 2, 6):
        req("/api/nomination/vote", "POST", {"seat": s}, ST)
    req("/api/nomination/resolve", "POST", {"passed": True}, ST)
    req("/api/nomination", "POST", {"nominator": 4, "nominee": 5}, ST)
    for s in (4, 5, 1):
        req("/api/nomination/vote", "POST", {"seat": s}, ST)
    req("/api/nomination/resolve", "POST", {"passed": True}, ST)
    state = req("/api/day/end", "POST", headers=ST)
    assert state["phase"] == "night" and state["night_no"] == 3
    assert state["seats"][1]["player"]["alive"] and state["seats"][4]["player"]["alive"], "平票无人被处决"
    assert not any(n["executed"] for n in state["nominations"] if n["day"] == 2), "平票当天无人处决"
    print("NOM   平票(3 票并列)天黑无人处决 OK")

    # 酒鬼认知覆盖 → 夜晚步骤含假角色步骤(改认知覆盖会重算步骤表)
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids2 = [req("/api/join", "POST", {"name": f"醉{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids2, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    pre = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "poisoner"},
           {"seat": 3, "role": "empath"}, {"seat": 4, "role": "chef"},
           {"seat": 5, "role": "investigator"}, {"seat": 6, "role": "drunk"}]
    req("/api/assign/manual", "POST", {"assignments": pre, "fakes": [{"seat": 6, "role": "washerwoman"}]}, ST)
    req("/api/fake", "POST", {"seat": 6, "role": "washerwoman"}, ST)
    pview = req(f"/api/me/{ids2[5]}")
    assert pview["me"]["role"]["id"] == "washerwoman", "酒鬼应看到假角色"
    state = req("/api/state", "GET", headers=ST)
    fake_steps = [s for s in state["night"]["steps"] if s.get("fake_for") == 6]
    assert fake_steps and fake_steps[0]["key"] == "washerwoman", "夜晚步骤应含假角色步"
    print("FAKE  酒鬼看到洗衣妇,夜晚步骤含假角色步(座 6) OK")

    # ---- 伪装:配版时选好;开局才发身份,会面推进到相应阶段才揭晓 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
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
    # 说书人指定伪装:配版时即生效;无人入座 → 保持 lobby
    want_bluffs = ["washerwoman", "soldier", "virgin"]
    state = req("/api/assign/manual", "POST", {"assignments": pre, "bluffs": want_bluffs, "fakes": [{"seat": 6, "role": "washerwoman"}]}, ST)
    b = state["bluffs"]
    assert [r["id"] for r in b] == want_bluffs, "伪装应与说书人指定一致"
    in_play = {"imp", "poisoner", "empath", "chef", "investigator", "drunk"}
    assert not ({r["id"] for r in b} & in_play), "伪装必须不在场"
    assert state["status"] == "lobby", "无人入座时应保持 lobby"
    # 酒鬼认知覆盖(真实身份外来者,即使看到假镇民也不得伪装)
    req("/api/fake", "POST", {"seat": 6, "role": "washerwoman"}, ST)
    # 开局前:玩家入座继承预发但不揭示身份与伪装
    b_ids = [req("/api/join", "POST", {"name": f"伪{i}", "room_code": room()})["player_id"] for i in range(1, 6)]
    for seat, pid in enumerate(b_ids, 1):
        view = req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
        assert "role" not in view["me"], f"开局前座位 {seat} 不应看到角色"
    dview = req(f"/api/me/{b_ids[0]}")
    assert "role" not in dview["me"] and "bluffs" not in dview, "开局前恶魔不应看到角色与伪装"
    last = req("/api/join", "POST", {"name": "伪6","room_code": room()})["player_id"]
    view = req(f"/api/player/{last}/sit", "POST", {"seat": 6})  # 满员自动开局
    assert view["me"]["role"]["id"] == "washerwoman", "满员自动开局后酒鬼应看到假角色"
    dview = req(f"/api/me/{b_ids[0]}")
    assert dview["me"]["role"]["id"] == "imp", "开局后恶魔拿到角色"
    assert "bluffs" not in dview and "minion_seats" not in dview, \
        "恶魔会面前不应看到伪装与爪牙名单"
    mview = req(f"/api/me/{b_ids[1]}")
    assert "demon_seats" not in mview, "爪牙会面前不应看到恶魔名单"
    pview = req(f"/api/me/{b_ids[2]}")
    assert "bluffs" not in pview, "非恶魔不应看到伪装"
    # 推进到恶魔会面:伪装 + 爪牙名单揭晓;爪牙会面更早,爪牙同步拿到恶魔名单
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    demon_idx = next(i for i, s in enumerate(steps) if s["key"] == "demoninfo")
    req("/api/night/goto", "POST", {"idx": demon_idx}, ST)
    dview = req(f"/api/me/{b_ids[0]}")
    assert [r["id"] for r in dview["bluffs"]] == [r["id"] for r in b], "恶魔会面后应看到伪装"
    assert [m["seat"] for m in dview["minion_seats"]] == [2], "恶魔会面后应看到爪牙是谁"
    mview = req(f"/api/me/{b_ids[1]}")
    assert [d["seat"] for d in mview["demon_seats"]] == [1], "爪牙会面后应看到恶魔是谁"
    dview6 = req(f"/api/me/{last}")
    assert dview6["me"]["role"]["id"] == "washerwoman", "酒鬼应看到假角色"
    assert "bluffs" not in dview6, "酒鬼(假镇民)不应看到伪装"
    print("BLUFF 开局才发身份+会面阶段揭晓伪装/爪牙/恶魔,仅当事人可见 OK")

    # ---- 人未齐也可开局:随机发牌覆盖空座;迟到玩家入座继承 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    late_ids = [req("/api/join", "POST", {"name": f"迟{i}", "room_code": room()})["player_id"] for i in range(1, 5)]
    for seat, pid in enumerate(late_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    state = req("/api/assign", "POST", headers=ST)  # 只 4 人入座也应能发牌并开局
    assert state["status"] == "playing" and state["phase"] == "night" and state["night_no"] == 1
    assigned_roles = {str(seat): rid for seat, rid in state["seat_roles"].items()}
    assert set(assigned_roles) == {"1", "2", "3", "4", "5", "6"}, assigned_roles
    empty_roles = {str(slot["seat"]): assigned_roles[str(slot["seat"])]
                   for slot in state["seats"] if slot["player"] is None}
    assert set(empty_roles) == {"5", "6"}, empty_roles
    rids = {r["id"] for r in state["roles"]}
    assert set(empty_roles.values()) <= rids, "空座预发角色应在板子角色表中"
    late5 = req("/api/join", "POST", {"name": "迟到者5","room_code": room()})["player_id"]
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
    ids3 = [req("/api/join", "POST", {"name": f"强{i}", "room_code": room()})["player_id"] for i in range(1, 5)]
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
    state = req("/api/assign/manual", "POST", {"assignments": pre, "fakes": [{"seat": 6, "role": "washerwoman"}]}, ST)
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
    pid = req("/api/join", "POST", {"name": "senti1","room_code": room()})["player_id"]
    req(f"/api/player/{pid}/sit", "POST", {"seat": 1})
    pview = req(f"/api/me/{pid}")
    assert pview["sentinel"] is True and pview["composition"] == [3, 1, 1, 1], \
        "玩家应知哨兵在场但不知方向、不见实际配比"
    state = req("/api/assign", "POST", headers=ST)  # 随机发牌:+1 应作用于实际配比
    teams = Counter(next(r["team"] for r in state["roles"] if r["id"] == rid)
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
    pid = req("/api/join", "POST", {"name": "senti2","room_code": room()})["player_id"]
    req(f"/api/player/{pid}/sit", "POST", {"seat": 1})
    pview = req(f"/api/me/{pid}")
    assert pview["sentinel"] is True and pview["composition"] == [3, 1, 1, 1], \
        "哨兵不变:玩家应知在场但不知方向、配比仍是官方基础"
    state = req("/api/assign", "POST", headers=ST)  # 不变:实际配比不因哨兵改变
    teams = Counter(next(r["team"] for r in state["roles"] if r["id"] == rid)
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

    # ---- 许愿(仅大厅):善良/邪恶预设与自定义;说书人可见;开局后拒绝 ----
    w_ids = [req("/api/join", "POST", {"name": f"愿{i}", "room_code": room()})["player_id"] for i in range(1, 3)]
    view = req(f"/api/player/{w_ids[0]}/wish", "POST", {"wish": "善良"})
    assert view["me_wish"] == "善良", "许愿后本人应看到自己的愿望"
    view = req(f"/api/player/{w_ids[1]}/wish", "POST", {"wish": "想玩信息角色"})
    assert view["me_wish"] == "想玩信息角色"
    state = req("/api/state", "GET", headers=ST)
    by_id = {p["id"]: p for p in state["players"]}
    assert by_id[w_ids[0]]["wish"] == "善良" and by_id[w_ids[1]]["wish"] == "想玩信息角色", \
        "说书人应看到许愿清单(未入座玩家同样可见)"
    view = req(f"/api/player/{w_ids[0]}/wish", "POST", {"wish": None})  # 清除
    assert view["me_wish"] is None
    state = req("/api/state", "GET", headers=ST)
    assert next(p for p in state["players"] if p["id"] == w_ids[0])["wish"] is None
    # 满员开局后不能再许愿
    for seat, pid in enumerate(w_ids + [req("/api/join", "POST", {"name": f"愿{i}", "room_code": room()})["player_id"] for i in range(3, 7)], 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    req("/api/assign", "POST", headers=ST)
    try:
        req(f"/api/player/{w_ids[1]}/wish", "POST", {"wish": "邪恶"})
        raise AssertionError("开局后许愿未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("WISH  大厅许愿(预设/自定义/清除,说书人可见)+开局后拒绝 OK")

    # ---- 旅行者:中途加入 / 指派阵营 / 夜晚步骤 / 提名流放 / 说书人随时流放 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ids = [req("/api/join", "POST", {"name": f"座{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    req("/api/assign", "POST", headers=ST)

    # 开局后中途加入:不坐座位,作为旅行者,先等说书人指派角色
    tp = req("/api/join", "POST", {"name": "旅行甲", "room_code": room()})["player_id"]
    view = req(f"/api/player/{tp}/traveler", "POST")
    assert view["traveler"]["id"] == "t1" and view["traveler"]["role_id"] is None
    assert view["me"]["seat"] is None and "role" not in view["me"], "未指派前不应看到角色"
    print("TRAV  开局后玩家以旅行者加入(t1),未指派角色 OK")

    # 指派旅行者角色与阵营:说书人操作,任意时刻;邪恶旅行者得知恶魔
    state = req("/api/traveler/assign", "POST", {"id": "t1", "role": "bureaucrat", "align": "evil"}, ST)
    assert state["travelers"][0]["role_id"] == "bureaucrat" and state["travelers"][0]["align"] == "evil"
    view = req(f"/api/me/{tp}")
    assert view["traveler"]["role"]["id"] == "bureaucrat", "旅行者本人应看到角色"
    assert view["traveler"]["align"] == "evil", "旅行者本人应知道自己的阵营"
    assert "demon_seats" in view, "邪恶旅行者应得知恶魔是谁"
    gview = req(f"/api/me/{ids[0]}")
    assert gview["travelers_public"][0]["role"]["id"] == "bureaucrat", "旅行者角色应公开"
    assert "align" not in gview["travelers_public"][0], "其他玩家不应知道旅行者阵营"
    print("TRAV  指派官员/邪恶:本人知阵营+恶魔,他人只知角色 OK")

    # 夜晚步骤注入:官员在黄昏阶段行动(第 2 夜,紧跟黄昏步)
    finish_night()
    state = req("/api/day/end", "POST", headers=ST)
    steps = state["night"]["steps"]
    assert steps[0]["key"] == "dusk" and steps[1]["key"] == "bureaucrat", \
        f"旅行者步应紧跟黄昏之后 {[s['key'] for s in steps[:3]]}"
    print("TRAV  第 2 夜步骤表含官员步,紧跟黄昏 OK")

    # 白天:旅行者参与提名与投票;流放门槛 = 全体(6+1)一半 = 4 票,通过即当场流放(不等天黑)
    state = finish_night()
    assert state["phase"] == "day"
    assert state["day_stage"] == "talk", "天亮应先进入公聊私聊阶段"
    req("/api/day/stage", "POST", {"stage": "nom"}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["exile_quorum"] == 4, f"流放门槛应为 4,实际 {state['exile_quorum']}"
    assert state["quorum"] == 3, f"处决门槛应为 3(存活玩家 6 人一半,不含旅行者),实际 {state['quorum']}"
    req("/api/nomination", "POST", {"nominator": 1, "nominee": "t1"}, ST)
    req("/api/nomination/vote", "POST", {"seat": "t1"}, ST)  # 旅行者本人投票
    for s in (2, 3, 4):
        req("/api/nomination/vote", "POST", {"seat": s}, ST)
    state = req("/api/state", "GET", headers=ST)
    assert state["current"]["votes"] == [2, 3, 4, "t1"], f"票型应含旅行者 {state['current']['votes']}"
    req("/api/nomination/resolve", "POST", {"passed": True}, ST)
    state = req("/api/state", "GET", headers=ST)
    t1 = state["travelers"][0]
    assert not t1["alive"] and t1["exiled"], "投票处决旅行者应转为流放"
    assert state["nominations"][-1]["executed"], "流放当场结算,记录标记已执行"
    view = req(f"/api/me/{ids[0]}")
    deaths = {d["seat"]: d for d in view["deaths"]}
    assert "t1" in deaths and deaths["t1"]["exiled"], "死亡名单应公开流放"
    try:  # 流放后离开小镇,不能再投票
        req("/api/nomination/vote", "POST", {"seat": "t1"}, ST)
        raise AssertionError("流放旅行者不应能投票")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("TRAV  提名旅行者→投票(含其本人)→流放,名单公开,流放后不能投票 OK")

    # 说书人随时直接流放/撤销(早退玩家)
    tp2 = req("/api/join", "POST", {"name": "旅行乙", "room_code": room()})["player_id"]
    req(f"/api/player/{tp2}/traveler", "POST")
    req("/api/traveler/assign", "POST", {"id": "t2", "role": "gunslinger"}, ST)
    state = req("/api/traveler/exile", "POST", {"id": "t2", "exiled": True}, ST)
    assert not state["travelers"][1]["alive"] and state["travelers"][1]["exiled"]
    state = req("/api/traveler/exile", "POST", {"id": "t2", "exiled": False}, ST)
    assert state["travelers"][1]["alive"] and not state["travelers"][1]["exiled"], "撤销流放应复活"
    print("TRAV  说书人随时流放/撤销流放(早退玩家) OK")

    # 说书人直接添加旅行者(无手机关联):名字必填,添加后照常指派/流放,对玩家公开
    state = req("/api/traveler/add", "POST", {"name": "旅行丙"}, ST)
    t3 = state["travelers"][2]
    assert t3["name"] == "旅行丙" and t3["player_id"] is None, "说书人添加的旅行者应无手机关联"
    state = req("/api/traveler/assign", "POST", {"id": t3["id"], "role": "judge", "align": "good"}, ST)
    assert state["travelers"][2]["role_id"] == "judge"
    view = req(f"/api/me/{ids[0]}")
    assert len(view["travelers_public"]) == 3, "说书人添加的旅行者对玩家公开可见"
    try:  # 空名应被拒绝
        req("/api/traveler/add", "POST", {"name": "  "}, ST)
        raise AssertionError("空名旅行者应被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("TRAV  说书人直接添加旅行者并指派(玩家端公开,空名拒绝) OK")

    # ---- 玩家手机主动发起提名 + 举手投票(说书人端实时可见,死票整局一次) ----
    state = req(f"/api/player/{ids[1]}/nominate", "POST", {"nominee": 3})
    assert state["current"]["nominator"] == 2, "手机发起的提名应为本人(座 2)"
    req(f"/api/player/{ids[0]}/vote", "POST")  # 座 1 手机举手
    req(f"/api/player/{tp2}/vote", "POST")     # 旅行者本人手机举手
    state = req("/api/state", "GET", headers=ST)
    assert state["current"]["votes"] == [1, "t2"], f"手机投票应实时同步 {state['current']['votes']}"
    req("/api/nomination/resolve", "POST", {"passed": False}, ST)
    # 死者死票:整局唯一,结算前可收回
    req(f"/api/player/{ids[2]}/alive", "POST", headers=ST)  # 座 3 标记死亡(说书人)
    state = req(f"/api/player/{ids[3]}/nominate", "POST", {"nominee": 1})
    assert state["current"]["nominator"] == 4
    req(f"/api/player/{ids[2]}/vote", "POST")
    state = req("/api/state", "GET", headers=ST)
    assert 3 in state["current"]["votes"], "死者手机举手应算死票"
    req(f"/api/player/{ids[2]}/vote", "POST")  # 取消举手 → 归还死票
    state = req("/api/state", "GET", headers=ST)
    assert 3 not in state["current"]["votes"], "未结算取消应归还死票"
    req(f"/api/player/{ids[2]}/vote", "POST")  # 再举手仍可(死票未结算)
    state = req("/api/state", "GET", headers=ST)
    assert 3 in state["current"]["votes"]
    req("/api/nomination/resolve", "POST", {"passed": False}, ST)  # 结算 → 死票不可再收回
    state = req(f"/api/player/{ids[4]}/nominate", "POST", {"nominee": 2})
    try:  # 死票已交:不能再投
        req(f"/api/player/{ids[2]}/vote", "POST")
        raise AssertionError("结算后死票不可再用")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/nomination/resolve", "POST", {"passed": False}, ST)
    print("PLAYER 手机发起提名+举手+旅行者投票+死者死票(可收回/结算后不可用) OK")

    # 已入座玩家不能作为旅行者加入
    try:
        req(f"/api/player/{ids[0]}/traveler", "POST")
        raise AssertionError("已入座玩家不应能作为旅行者加入")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("TRAV  已入座玩家不能作为旅行者加入 OK")

    # ---- 占卜师宿敌(红鲱鱼):说书人私下标记善良玩家,只有说书人知道 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    f_ids = [req("/api/join", "POST", {"name": f"占{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(f_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    pre2 = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "poisoner"},
            {"seat": 3, "role": "fortuneteller"}, {"seat": 4, "role": "chef"},
            {"seat": 5, "role": "investigator"}, {"seat": 6, "role": "drunk"}]
    req("/api/assign/manual", "POST", {"assignments": pre2, "fakes": [{"seat": 6, "role": "washerwoman"}]}, ST)
    st = req("/api/state", "GET", headers=ST)
    assert st["fortuneteller_red"] is None
    try:  # 恶魔不能当宿敌
        req("/api/fortuneteller/red", "POST", {"seat": 1}, ST)
        raise AssertionError("恶魔当宿敌未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    try:  # 本人不能当宿敌
        req("/api/fortuneteller/red", "POST", {"seat": 3}, ST)
        raise AssertionError("占卜师本人当宿敌未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    st = req("/api/fortuneteller/red", "POST", {"seat": 4}, ST)
    assert st["fortuneteller_red"] == 4
    pview = req(f"/api/me/{f_ids[0]}")
    assert "fortuneteller_red" not in pview, "宿敌标记不能泄露给玩家"
    st = req("/api/fortuneteller/red", "POST", {"seat": None}, ST)  # 清除
    assert st["fortuneteller_red"] is None
    st = req("/api/fortuneteller/red", "POST", {"seat": 5}, ST)
    assert st["fortuneteller_red"] == 5
    # 没有占卜师的局不能标记
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    try:
        req("/api/fortuneteller/red", "POST", {"seat": 1}, ST)
        raise AssertionError("无占卜师标记宿敌未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("RED   占卜师宿敌标记(限善良/非本人/可清除/不泄露/无占卜师拒绝) OK")

    # ---- 瓦釜雷鸣手机刀人:恶魔选择自动执行,疯子演戏不生效,说书人可见,其他板子拒绝 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "godfather"},
           {"seat": 3, "role": "dreamer"}, {"seat": 4, "role": "gambler"},
           {"seat": 5, "role": "savant"}, {"seat": 6, "role": "lunatic"},
           {"seat": 7, "role": "chef"}]
    req("/api/assign/manual", "POST", {"assignments": pre,
        "fakes": [{"seat": 6, "role": "fang-gu", "minions": [2],
                   "bluffs": ["chef", "dreamer", "gambler"]}]}, ST)
    k_ids = [req("/api/join", "POST", {"name": f"刀{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(k_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    # 第一夜:疯子步骤点亮手机刀人界面;疯子选择只演戏,天亮不执行
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    lun_idx = next(i for i, s in enumerate(steps) if s["key"] == "lunatic")
    req("/api/night/goto", "POST", {"idx": lun_idx}, ST)
    lview = req(f"/api/me/{k_ids[5]}")  # 座 6 疯子
    assert lview["night_wake"]["action"] == "kill" and lview["night_wake"]["lunatic"], "疯子步骤应点亮刀人界面"
    req(f"/api/player/{k_ids[5]}/kill", "POST", {"seat": 3})
    st = req("/api/state", "GET", headers=ST)
    assert st["night_kills"]["1"]["lunatic_seat"] == 3, "疯子的选择应记录为演戏"
    dview1 = req(f"/api/me/{k_ids[0]}")
    assert dview1["lunatic_kill"] == 3, "恶魔应得知疯子刀了谁(官方规则)"
    tview = req(f"/api/me/{k_ids[2]}")
    assert "lunatic_kill" not in tview, "其他玩家不应看到疯子的选择"
    finish_night()
    st = req("/api/state", "GET", headers=ST)
    assert st["phase"] == "day" and st["seats"][2]["player"]["alive"], "疯子的刀不执行"
    try:  # 镇民没有刀人能力
        req(f"/api/player/{k_ids[2]}/kill", "POST", {"seat": 1})
        raise AssertionError("镇民刀人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("KILL  第一夜疯子演戏刀不执行,镇民刀人被拒 OK")
    # 天黑 → 第 2 夜:恶魔步骤点亮,选择 → 天亮自动执行,说书人可见选择
    req("/api/day/end", "POST", headers=ST)
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    imp_idx = next(i for i, s in enumerate(steps) if s["key"] == "imp")
    req("/api/night/goto", "POST", {"idx": imp_idx}, ST)
    dview = req(f"/api/me/{k_ids[0]}")  # 座 1 小恶魔
    assert dview["night_wake"]["action"] == "kill" and dview["night_wake"]["targets"] == list(range(1, 8)), \
        "恶魔步骤应点亮刀人界面与存活目标"
    req(f"/api/player/{k_ids[0]}/kill", "POST", {"seat": 5})
    st = req("/api/state", "GET", headers=ST)
    assert st["night_kills"]["2"]["seat"] == 5 and st["night_kills"]["2"]["by"] == 1, "说书人应看到恶魔的选择"
    assert st["seats"][4]["player"]["alive"], "天亮前被刀者仍存活"
    finish_night()
    st = req("/api/state", "GET", headers=ST)
    assert st["phase"] == "day" and not st["seats"][4]["player"]["alive"], "天亮应自动执行恶魔刀人"
    pview = req(f"/api/me/{k_ids[2]}")
    deaths = {d["seat"]: d for d in pview["deaths"]}
    assert deaths[5]["day"] == 2, "刀杀名单应公开为第 2 天"
    print("KILL  第 2 夜恶魔手机刀人 → 天亮自动执行,说书人可见 OK")
    # 其他板子暂不开放手机刀人
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    tb_ids = [req("/api/join", "POST", {"name": f"暗{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(tb_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    st = req("/api/assign", "POST", headers=ST)
    demon_pid = next(p["id"] for s in st["seats"] if s["player"]
                     for p in [s["player"]] if p["role"]["team"] == "demon")
    try:
        req(f"/api/player/{demon_pid}/kill", "POST", {"seat": 2})
        raise AssertionError("暗流涌动手机刀人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("KILL  其他板子(暗流涌动)手机刀人被拒 OK")

    # ---- 瓦釜雷鸣夜晚信息交互:占卜师选两人 → 说书人电子回复(仅本人可见) ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre3 = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "godfather"},
            {"seat": 3, "role": "fortuneteller"}, {"seat": 4, "role": "dreamer"},
            {"seat": 5, "role": "gambler"}, {"seat": 6, "role": "savant"},
            {"seat": 7, "role": "recluse"}]
    req("/api/assign/manual", "POST", {"assignments": pre3}, ST)
    n_ids = [req("/api/join", "POST", {"name": f"夜{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(n_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    ft_idx = next(i for i, s in enumerate(steps) if s["key"] == "fortuneteller")
    req("/api/night/goto", "POST", {"idx": ft_idx}, ST)
    ft_view = req(f"/api/me/{n_ids[2]}")  # 座 3 占卜师
    assert ft_view["night_wake"]["action"] == "pick" and ft_view["night_wake"]["count"] == 2, \
        "占卜师步骤应点亮选两人界面"
    try:  # 选错数量被拒
        req(f"/api/player/{n_ids[2]}/choice", "POST", {"targets": [4]})
        raise AssertionError("占卜师只选一人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req(f"/api/player/{n_ids[2]}/choice", "POST", {"targets": [4, 6]})
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["1"]["3"]["targets"] == [4, 6], "说书人应看到占卜师的选择"
    req("/api/night/reply", "POST", {"seat": 3, "text": "✅ 有恶魔"}, ST)
    ft_view = req(f"/api/me/{n_ids[2]}")
    assert ft_view["night_choice"]["reply"] == "✅ 有恶魔", "占卜师手机应收到说书人回复"
    other = req(f"/api/me/{n_ids[0]}")
    assert "night_choice" not in other, "其他玩家不应看到占卜师的选择与回复"
    # 教父首夜:只有信息(在场外来者),不开放选人;说书人一键发送
    gf_idx = next(i for i, s in enumerate(steps) if s["key"] == "godfather")
    req("/api/night/goto", "POST", {"idx": gf_idx}, ST)
    gf_view = req(f"/api/me/{n_ids[1]}")  # 座 2 教父
    assert "night_wake" not in gf_view or gf_view["night_wake"]["action"] != "pick", "教父首夜不应有选人界面"
    try:
        req(f"/api/player/{n_ids[1]}/choice", "POST", {"targets": [4]})
        raise AssertionError("教父首夜选人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/night/reply", "POST", {"seat": 2, "text": "外来者:陌客", "role": "godfather"}, ST)
    gf_view = req(f"/api/me/{n_ids[1]}")
    assert gf_view["night_choice"]["reply"] == "外来者:陌客", "教父手机应收到首夜外来者信息"
    # 第二夜起教父可正常选人
    finish_night()
    req("/api/day/end", "POST", headers=ST)
    steps2 = req("/api/state", "GET", headers=ST)["night"]["steps"]
    gf2_idx = next(i for i, s in enumerate(steps2) if s["key"] == "godfather")
    req("/api/night/goto", "POST", {"idx": gf2_idx}, ST)
    gf_view = req(f"/api/me/{n_ids[1]}")
    assert gf_view["night_wake"]["action"] == "pick" and gf_view["night_wake"]["count"] == 1, \
        "教父第二夜起应开放选人"
    print("NINFO 教父首夜信息(一键发送,不开放选人),第二夜起可行动 OK")

    # 寡妇首夜:手机查看魔典(仅此步)+ 选人中毒 + 告知善良玩家
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre4 = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "widow"},
            {"seat": 3, "role": "fortuneteller"}, {"seat": 4, "role": "dreamer"},
            {"seat": 5, "role": "gambler"}, {"seat": 6, "role": "savant"},
            {"seat": 7, "role": "recluse"}]
    req("/api/assign/manual", "POST", {"assignments": pre4}, ST)
    w_ids = [req("/api/join", "POST", {"name": f"寡{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(w_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    wd_idx = next(i for i, s in enumerate(steps) if s["key"] == "widow")
    req("/api/night/goto", "POST", {"idx": wd_idx}, ST)
    wview = req(f"/api/me/{w_ids[1]}")  # 座 2 寡妇
    assert wview["night_wake"]["action"] == "pick" and wview["night_wake"]["grimoire"], \
        "寡妇步骤应点亮选人+魔典"
    by_seat = {g["seat"]: g["role"]["id"] for g in wview["grimoire"]["seats"] if g["role"]}
    assert by_seat[1] == "imp" and by_seat[7] == "recluse", "魔典应显示全部真实角色"
    oview = req(f"/api/me/{w_ids[2]}")
    assert "grimoire" not in oview, "其他玩家不应看到魔典"
    req(f"/api/player/{w_ids[1]}/choice", "POST", {"targets": [5]})
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["1"]["2"]["targets"] == [5], "说书人应看到寡妇的毒人选择"
    req("/api/night/reply", "POST", {"seat": 3, "text": "⚠ 寡妇在场", "role": "widow-note"}, ST)
    gview = req(f"/api/me/{w_ids[2]}")
    assert gview["night_choice"]["reply"] == "⚠ 寡妇在场", "善良玩家应收到寡妇在场的告知"
    req(f"/api/player/{w_ids[1]}/choice", "POST", {"targets": [2]})  # 寡妇改选自己(官方:不告知善良玩家)
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["1"]["2"]["targets"] == [2], "寡妇应能选择自己"
    req("/api/night/next", "POST", headers=ST)  # 过了寡妇步 → 魔典消失(睡下不可再看)
    wview = req(f"/api/me/{w_ids[1]}")
    assert "grimoire" not in wview, "过了寡妇步魔典应消失"
    print("NINFO 寡妇首夜魔典(仅此步)+毒人选择+告知善良玩家 OK")
    try:  # 无该行动的角色(贤者,座 6)被拒
        req(f"/api/player/{w_ids[5]}/choice", "POST", {"targets": [1]})
        raise AssertionError("贤者夜晚选人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400

    # 麻脸巫婆:选玩家+不在场角色变身(死亡角色也算在场),说书人确认生效;
    # 按行动轮次注入新角色步骤;创造恶魔 → 本夜死亡由说书人决定
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre5 = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "pithag"},
            {"seat": 3, "role": "fortuneteller"}, {"seat": 4, "role": "dreamer"},
            {"seat": 5, "role": "gambler"}, {"seat": 6, "role": "savant"},
            {"seat": 7, "role": "recluse"}]
    req("/api/assign/manual", "POST", {"assignments": pre5}, ST)
    p_ids = [req("/api/join", "POST", {"name": f"麻{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(p_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    # 第一夜无麻脸巫婆步骤 → 走完到第 2 夜
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    finish_night()
    req("/api/day/end", "POST", headers=ST)
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    ph_idx = next(i for i, s in enumerate(steps) if s["key"] == "pithag")
    req("/api/night/goto", "POST", {"idx": ph_idx}, ST)
    ph_view = req(f"/api/me/{p_ids[1]}")  # 座 2 麻脸巫婆
    assert ph_view["night_wake"]["action"] == "pick" and ph_view["night_wake"]["char"], \
        "麻脸巫婆步骤应点亮选人+角色"
    char_ids = {c["id"] for c in ph_view["night_wake"]["chars"]}
    assert "imp" in char_ids and "recluse" in char_ids, "麻脸巫婆不知道谁在场:角色池应是全板子角色"
    # 选在场角色 → 不报错,静默无效(麻脸巫婆自己不知道)
    req(f"/api/player/{p_ids[1]}/choice", "POST", {"targets": [6], "char": "imp"})
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["2"]["2"]["invalid"] is True, "在场角色应静默无效"
    assert st["seats"][5]["player"]["role"]["id"] == "savant", "无效选择不应改变角色"
    # 选不在场角色 → 提交即自动转变
    req(f"/api/player/{p_ids[1]}/choice", "POST", {"targets": [6], "char": "grandmother"})
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["2"]["2"]["applied"] is True, "提交应自动生效"
    assert st["seats"][5]["player"]["role"]["id"] == "grandmother", "确认后贤者应变祖母"
    pview6 = req(f"/api/me/{p_ids[5]}")
    assert pview6["role_changed"]["id"] == "grandmother", "被变身玩家应收到角色转变提示"
    keys = [s["character_id"] for s in st["night_workflow"]["steps"]]
    assert "grandmother" in keys, "祖母步应按行动轮次注入本夜步骤"
    # 说书人撤销(容错):角色恢复、注入步骤移除
    st = req("/api/night/transform", "POST", {"seat": 2}, ST)
    assert st["seats"][5]["player"]["role"]["id"] == "savant", "撤销后贤者应恢复"
    keys = [s["character_id"] for s in st["night_workflow"]["steps"]]
    assert "grandmother" not in keys, "撤销后注入步骤应移除"
    # 创造恶魔:本夜死亡由说书人决定,恶魔手机刀不生效
    req(f"/api/player/{p_ids[1]}/choice", "POST", {"targets": [6], "char": "fang-gu"})
    st = req("/api/state", "GET", headers=ST)
    demon_change = next(item for item in reversed(st["night_workflow"]["transformations"]["history"])
                        if item["new_character"] == "fang-gu")
    assert demon_change["status"] == "confirmed" and demon_change["creates_demon"], \
        "创造恶魔应记录已确认的变身事务"
    assert "all_deaths_this_night_are_storyteller_arbitrary" in demon_change["demon_consequences"], \
        "创造恶魔应标记本夜死亡由说书人决定"
    created_demon_step = next(item for item in st["night_workflow"]["steps"]
                              if item["actor_seat"] == 6 and item["character_id"] == "fang-gu")
    assert created_demon_step["status"] == "skipped" \
        and created_demon_step["skip_reason"] == "created_demon_no_kill_this_night", \
        "新造恶魔本夜不应获得正常刀人行动"
    steps2 = st["night"]["steps"]
    imp_idx = next(i for i, s in enumerate(steps2) if s["key"] == "imp")
    req("/api/night/goto", "POST", {"idx": imp_idx}, ST)
    req(f"/api/player/{p_ids[0]}/kill", "POST", {"seat": 5})  # 恶魔仍选(不知情)
    finish_night()
    st = req("/api/state", "GET", headers=ST)
    assert st["phase"] == "day" and st["seats"][4]["player"]["alive"], \
        "创造恶魔之夜恶魔刀不执行,死亡由说书人决定"
    print("PITHAG 麻脸巫婆:全角色池/在场静默无效/自动转变/撤销/造恶魔死亡由说书人决定 OK")

    # ---- 洗脑师疯狂细分:选玩家+善良角色自动生效,被疯狂者手机被告知;重提交换目标 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre6 = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "cerenovus"},
            {"seat": 3, "role": "fortuneteller"}, {"seat": 4, "role": "dreamer"},
            {"seat": 5, "role": "gambler"}, {"seat": 6, "role": "savant"},
            {"seat": 7, "role": "recluse"}]
    req("/api/assign/manual", "POST", {"assignments": pre6}, ST)
    c_ids = [req("/api/join", "POST", {"name": f"疯{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(c_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    ce_idx = next(i for i, s in enumerate(steps) if s["key"] == "cerenovus")
    req("/api/night/goto", "POST", {"idx": ce_idx}, ST)
    ce_view = req(f"/api/me/{c_ids[1]}")  # 座 2 洗脑师
    assert ce_view["night_wake"]["action"] == "pick" and ce_view["night_wake"]["char"], \
        "洗脑师步骤应点亮选人+角色"
    char_teams = {c["id"]: c["team"] for c in ce_view["night_wake"]["chars"]}
    assert "imp" not in char_teams and "chef" in char_teams, "疯狂宣称角色池应只含善良角色"
    try:  # 疯狂宣称恶魔被拒
        req(f"/api/player/{c_ids[1]}/choice", "POST", {"targets": [6], "char": "imp"})
        raise AssertionError("疯狂宣称恶魔未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req(f"/api/player/{c_ids[1]}/choice", "POST", {"targets": [6], "char": "chef"})
    st = req("/api/state", "GET", headers=ST)
    mad_effect = next(effect for effect in st["seats"][5]["effects"]
                      if effect["type"] == "mad" and effect["source_character"] == "cerenovus")
    assert mad_effect["state"] == "active" \
        and mad_effect["expected_end"] == "next_cerenovus_choice" \
        and st["seats"][5]["mad_about"]["id"] == "chef", \
        "洗脑师提交应自动标记疯狂"
    mview = req(f"/api/me/{c_ids[5]}")
    assert mview["my_mad"]["role"]["id"] == "chef", "被疯狂者手机应被告知疯狂内容"
    oview = req(f"/api/me/{c_ids[2]}")
    assert "my_mad" not in oview, "其他玩家不应看到疯狂"
    # 重新提交 → 旧目标解除,新目标生效
    req(f"/api/player/{c_ids[1]}/choice", "POST", {"targets": [5], "char": "dreamer"})
    st = req("/api/state", "GET", headers=ST)
    old_effect = next(effect for effect in st["seats"][5]["effect_history"]
                      if effect["id"] == mad_effect["id"])
    assert old_effect["state"] == "ended" and not st["seats"][5]["effects"], \
        "旧目标疯狂应解除并保留历史"
    new_effect = next(effect for effect in st["seats"][4]["effect_history"]
                      if effect["type"] == "mad" and effect["source_character"] == "cerenovus"
                      and effect["state"] == "active")
    assert new_effect["payload"]["claimed_character"] == "dreamer" \
        and st["seats"][4]["mad_about"]["id"] == "dreamer", "新目标应被疯狂"
    # 说书人手动标记:须带善良角色内容;解除后通知消失
    try:
        req("/api/marker", "POST", {"seat": 4, "marker": "mad", "on": True}, ST)
        raise AssertionError("无内容疯狂未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    try:
        req("/api/marker", "POST", {"seat": 4, "marker": "mad", "on": True, "about": "imp"}, ST)
        raise AssertionError("邪恶角色疯狂未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    st = req("/api/marker", "POST", {"seat": 4, "marker": "mad", "on": True, "about": "chef"}, ST)
    assert st["seats"][3]["mad_about"]["id"] == "chef"
    mview4 = req(f"/api/me/{c_ids[3]}")
    assert mview4["my_mad"]["role"]["id"] == "chef", "手动标记同样通知玩家"
    st = req("/api/marker", "POST", {"seat": 4, "marker": "mad", "on": False}, ST)
    mview4 = req(f"/api/me/{c_ids[3]}")
    assert "my_mad" not in mview4, "解除后通知消失"
    print("MAD   洗脑师疯狂:善良角色池/自动生效/被疯狂者被告知/重提交换目标/手动标记带内容 OK")

    # ---- 空座代操作(便于测试人未齐开局):说书人按座位刀人/选人/收回复 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre7 = [{"seat": 1, "role": "dreamer"}, {"seat": 2, "role": "godfather"},
            {"seat": 3, "role": "gambler"}, {"seat": 4, "role": "savant"},
            {"seat": 5, "role": "recluse"}, {"seat": 6, "role": "fortuneteller"},
            {"seat": 7, "role": "imp"}]
    req("/api/assign/manual", "POST", {"assignments": pre7}, ST)
    e_ids = [req("/api/join", "POST", {"name": f"空{i}", "room_code": room()})["player_id"] for i in range(1, 6)]
    for seat, pid in enumerate(e_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    req("/api/start", "POST", headers=ST)  # 人未齐强制开局:座 6 占卜师、座 7 小恶魔为空座
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    ft_idx = next(i for i, s in enumerate(steps) if s["key"] == "fortuneteller")
    req("/api/night/goto", "POST", {"idx": ft_idx}, ST)
    req("/api/seat/6/choice", "POST", {"targets": [1, 2]}, ST)  # 空座占卜师代操作
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["1"]["6"]["targets"] == [1, 2], "空座占卜师应能代操作选人"
    req("/api/night/reply", "POST", {"seat": 6, "text": "✅ 有恶魔"}, ST)
    st = req("/api/state", "GET", headers=ST)
    assert st["night_choices"]["1"]["6"]["reply"] == "✅ 有恶魔", "空座应能收到回复"
    # 空座状态栏:标记/疯狂/角色转变对空座同样生效并可见
    st = req("/api/marker", "POST", {"seat": 6, "marker": "mad", "on": True, "about": "chef"}, ST)
    assert "mad" in st["seats"][5].get("markers", []) and st["seats"][5]["mad_about"]["id"] == "chef", \
        "空座疯狂标记应可见"
    st = req("/api/marker", "POST", {"seat": 6, "marker": "role-change", "on": True, "role": "grandmother"}, ST)
    assert st["seats"][5]["role_change"]["id"] == "grandmother", "空座角色转变应可见"
    # 空座生死以说书人标记为准:白天标记空座死亡 → 进死亡名单、计入侵活数
    finish_night()
    st = req("/api/seat/6/alive", "POST", headers=ST)  # 白天标死空座占卜师
    assert st["seats"][5]["alive"] is False, "空座应能被标死"
    st = req("/api/state", "GET", headers=ST)
    assert st["alive_count"] == 6 and st["quorum"] == 3, \
        f"存活数应按座位生死计(5 入座存活 + 空座 7 活),实际 {st['alive_count']}"
    pview = req(f"/api/me/{e_ids[0]}")
    deaths = {d["seat"]: d for d in pview["deaths"]}
    assert 6 in deaths and deaths[6]["empty"], "空座死亡应进死亡名单"
    try:  # 无行动角色空座被拒(贤者座 4)
        req("/api/seat/4/choice", "POST", {"targets": [1]}, ST)
        raise AssertionError("贤者空座代操作未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    # 第 2 夜:空座恶魔代操作刀人 → 天亮自动执行
    req("/api/day/end", "POST", headers=ST)
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    imp_idx = next(i for i, s in enumerate(steps) if s["key"] == "imp")
    req("/api/night/goto", "POST", {"idx": imp_idx}, ST)
    req("/api/seat/7/kill", "POST", {"target": 3}, ST)
    st = req("/api/state", "GET", headers=ST)
    assert st["night_kills"]["2"]["seat"] == 3 and st["night_kills"]["2"]["by"] == 7, \
        "空座恶魔应能代操作刀人"
    finish_night()
    st = req("/api/state", "GET", headers=ST)
    assert st["phase"] == "day" and not st["seats"][2]["player"]["alive"], "空座恶魔刀人天亮应执行"
    # 空座投票:死亡空座(座 6)交出唯一死票,可收回、结算后不可再用
    req("/api/day/stage", "POST", {"stage": "nom"}, ST)
    req("/api/nomination", "POST", {"nominator": 1, "nominee": 2}, ST)
    req("/api/nomination/vote", "POST", {"seat": 6}, ST)
    st = req("/api/state", "GET", headers=ST)
    assert 6 in st["current"]["votes"], "死亡空座应能举手交死票"
    req("/api/nomination/vote", "POST", {"seat": 6}, ST)  # 取消 → 归还死票
    st = req("/api/state", "GET", headers=ST)
    assert 6 not in st["current"]["votes"], "未结算取消应归还空座死票"
    req("/api/nomination/vote", "POST", {"seat": 6}, ST)
    req("/api/nomination/resolve", "POST", {"passed": False}, ST)
    req("/api/nomination", "POST", {"nominator": 2, "nominee": 3}, ST)
    try:  # 死票已结算,不能再投
        req("/api/nomination/vote", "POST", {"seat": 6}, ST)
        raise AssertionError("结算后空座死票未拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/nomination/resolve", "POST", {"passed": False}, ST)
    print("SEAT  空座代操作:占卜师选人/收回复/空座生死/死票投票/恶魔刀人自动执行 OK")
    # 其他板子暂不开放
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    t_ids = [req("/api/join", "POST", {"name": f"信{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(t_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    st = req("/api/assign", "POST", headers=ST)
    t_pid = next(s["player"]["id"] for s in st["seats"] if s["player"]["role"]["team"] == "townsfolk")
    try:
        req(f"/api/player/{t_pid}/choice", "POST", {"targets": [1]})
        raise AssertionError("暗流涌动夜晚选人未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("NINFO 夜晚信息交互:占卜师选两人→说书人回复→不泄露→无行动/其他板子拒绝 OK")

    # ---- 结算:说书人宣布游戏结束+判定获胜方,全场揭晓,封冻操作,可撤销 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    g_ids = [req("/api/join", "POST", {"name": f"结{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(g_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    req("/api/assign", "POST", headers=ST)
    st = req("/api/end", "POST", {"winner": "good"}, ST)
    assert st["winner"] == "good", "说书人应能宣布善良获胜"
    pview = req(f"/api/me/{g_ids[0]}")
    r = pview["result"]
    assert r["winner"] == "good" and len(r["seats"]) == 6, "结算页应含全部座位"
    assert any(g["role"]["team"] == "demon" for g in r["seats"]), "结算页应揭晓恶魔真实身份"
    try:  # 结束后封冻夜晚推进
        req("/api/night/next", "POST", headers=ST)
        raise AssertionError("结束后夜晚推进未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    try:  # 非法获胜方
        req("/api/end", "POST", {"winner": "平局"}, ST)
        raise AssertionError("非法获胜方未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    st = req("/api/end", "POST", {"winner": None}, ST)  # 撤销结算
    assert st["winner"] is None
    pview = req(f"/api/me/{g_ids[0]}")
    assert "result" not in pview, "撤销后结算页消失"
    req("/api/night/next", "POST", headers=ST)  # 恢复可推进
    print("END   结算:宣布获胜方/全场揭晓/封冻/撤销恢复 OK")

    # ---- 复盘:事件时间线/错误信息自动判定(酒鬼/中毒)/传刀识别/说书人标错 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    pre8 = [{"seat": 1, "role": "imp"}, {"seat": 2, "role": "godfather"},
            {"seat": 3, "role": "drunk"}, {"seat": 4, "role": "dreamer"},
            {"seat": 5, "role": "gambler"}, {"seat": 6, "role": "savant"},
            {"seat": 7, "role": "chef"}]
    req("/api/assign/manual", "POST", {"assignments": pre8,
        "fakes": [{"seat": 3, "role": "fortuneteller"}]}, ST)
    r_ids = [req("/api/join", "POST", {"name": f"复{i}", "room_code": room()})["player_id"] for i in range(1, 8)]
    for seat, pid in enumerate(r_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    steps = req("/api/state", "GET", headers=ST)["night"]["steps"]
    ft_idx = next(i for i, s in enumerate(steps) if s["key"] == "fortuneteller")
    req("/api/night/goto", "POST", {"idx": ft_idx}, ST)
    req(f"/api/player/{r_ids[2]}/choice", "POST", {"targets": [1, 2]})  # 酒鬼(假占卜师)选人
    req("/api/night/reply", "POST", {"seat": 3, "text": "有恶魔"}, ST)
    dr_idx = next(i for i, s in enumerate(steps) if s["key"] == "dreamer")
    req("/api/night/goto", "POST", {"idx": dr_idx}, ST)
    req("/api/marker", "POST", {"seat": 4, "marker": "poisoned", "on": True}, ST)  # 筑梦师中毒
    req(f"/api/player/{r_ids[3]}/choice", "POST", {"targets": [1]})
    req("/api/night/reply", "POST", {"seat": 4, "text": "1号是恶魔"}, ST)
    req("/api/marker", "POST", {"seat": 2, "marker": "role-change", "on": True, "role": "imp"}, ST)  # 传刀
    req("/api/end", "POST", {"winner": "evil"}, ST)
    pview = req(f"/api/me/{r_ids[0]}")
    review = pview["review"]
    assert review["has_data"], "应有复盘数据"
    texts = [(it.get("text", ""), it.get("wrong"), it.get("why", ""))
             for g in review["groups"] for it in g["items"]]
    drunk_line = next((w, why) for it, w, why in texts if "回复:" in it and "(3号" in it)
    assert drunk_line[0] and "酒鬼" in drunk_line[1], "酒鬼回复应自动标注错误"
    po_line = next((w, why) for it, w, why in texts if "回复:" in it and "(4号" in it)
    assert po_line[0] and "中毒" in po_line[1], "中毒回复应自动标注错误"
    assert any("🩸 传刀" in it for it, _, _ in texts), "爪牙变恶魔应识别为传刀"
    assert any("🧪 恶魔伪装" in it for it, _, _ in texts), "复盘应含恶魔伪装"
    # 说书人标错 → why 含「说书人标注」;撤销后消失
    req("/api/review/mark", "POST", {"seat": 4, "night": 1, "wrong": True}, ST)
    pview = req(f"/api/me/{r_ids[0]}")
    texts2 = [(it.get("text", ""), it.get("wrong"), it.get("why", ""))
              for g in pview["review"]["groups"] for it in g["items"]]
    po2 = next((w, why) for it, w, why in texts2 if "回复:" in it and "(4号" in it)
    assert "说书人标注" in po2[1], "说书人标错应出现在 why"
    req("/api/review/mark", "POST", {"seat": 4, "night": 1, "wrong": False}, ST)
    pview = req(f"/api/me/{r_ids[0]}")
    texts3 = [(it.get("text", ""), it.get("wrong"), it.get("why", ""))
              for g in pview["review"]["groups"] for it in g["items"]]
    po3 = next((w, why) for it, w, why in texts3 if "回复:" in it and "(4号" in it)
    assert "说书人标注" not in po3[1], "撤销标错后标注应消失"
    print("REVIEW 复盘:酒鬼/中毒自动标注,传刀识别,说书人标错/撤销 OK")

    # ---- 传奇角色:说书人勾选,玩家公开可见,取消/换板子保留 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    st = req("/api/fabled", "POST", {"id": "angel", "on": True}, ST)
    assert any(f["id"] == "angel" for f in st["fabled"]), "说书人应能勾选传奇角色"
    st = req("/api/fabled", "POST", {"id": "buddhist", "on": True}, ST)
    assert len(st["fabled"]) == 2
    f_ids = [req("/api/join", "POST", {"name": f"传{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    pview = req(f"/api/me/{f_ids[0]}")
    assert [f["id"] for f in pview["fabled"]] == ["angel", "buddhist"], "传奇角色应公开给玩家"
    try:  # 未知传奇角色
        req("/api/fabled", "POST", {"id": "nope", "on": True}, ST)
        raise AssertionError("未知传奇角色未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/fabled", "POST", {"id": "angel", "on": False}, ST)
    st = req("/api/state", "GET", headers=ST)
    assert [f["id"] for f in st["fabled"]] == ["buddhist"], "取消勾选应移除"
    req("/api/config", "POST", {"script": "wafu-leiming", "player_count": 7}, ST)
    st = req("/api/state", "GET", headers=ST)
    assert [f["id"] for f in st["fabled"]] == ["buddhist"], "换板子应保留传奇角色"
    print("FABLED 传奇角色:勾选/公开/取消/换板子保留 OK")

    # ---- 白天私聊:邀请/接受拒绝/申请审批/历史隔离/说书人全知+发言/召回/天黑即焚 ----
    req("/api/reset", "POST", headers=ST)
    req("/api/config", "POST", {"script": "trouble-brewing", "player_count": 6}, ST)
    ch_ids = [req("/api/join", "POST", {"name": f"聊{i}", "room_code": room()})["player_id"] for i in range(1, 7)]
    for seat, pid in enumerate(ch_ids, 1):
        req(f"/api/player/{pid}/sit", "POST", {"seat": seat})
    req("/api/assign", "POST", headers=ST)
    try:  # 夜晚不能私聊
        req(f"/api/chat/create?player_id={ch_ids[0]}", "POST", {"invitees": [2]})
        raise AssertionError("夜晚私聊未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    finish_night()
    req(f"/api/chat/create?player_id={ch_ids[0]}", "POST", {"invitees": [2, 3, "st"]})
    v2 = req(f"/api/me/{ch_ids[1]}")
    assert len(v2["chat"]["invites"]) == 1, "被邀请者应看到邀请"
    req(f"/api/chat/1/invite?player_id={ch_ids[1]}", "POST", {"accept": True})
    req(f"/api/chat/1/invite?player_id={ch_ids[2]}", "POST", {"accept": False})
    req("/api/chat-st/1/invite", "POST", {"accept": True}, ST)
    req(f"/api/chat/1/send?player_id={ch_ids[0]}", "POST", {"text": "秘密消息"})
    v4 = req(f"/api/me/{ch_ids[3]}")
    assert any(c["id"] == 1 for c in v4["chat"]["chats_public"]), "公开列表应显示私聊"
    req(f"/api/chat/1/request?player_id={ch_ids[3]}", "POST")
    v1 = req(f"/api/me/{ch_ids[0]}")
    assert v1["chat"]["my_chat"]["requests"], "发起者应看到申请"
    req(f"/api/chat/1/approve?player_id={ch_ids[0]}", "POST", {"who": 4, "approve": True})
    v4 = req(f"/api/me/{ch_ids[3]}")
    assert v4["chat"]["my_chat"]["messages"] == [], "后加入者不应看到历史消息"
    req(f"/api/chat/1/send?player_id={ch_ids[0]}", "POST", {"text": "新消息"})
    v4 = req(f"/api/me/{ch_ids[3]}")
    assert len(v4["chat"]["my_chat"]["messages"]) == 1, "后加入者应看到加入后的消息"
    st = req("/api/state", "GET", headers=ST)
    chat1 = next(c for c in st["chats"] if c["id"] == 1)
    assert any("秘密消息" in m["text"] for m in chat1["messages"]), "说书人应能查看所有私聊内容"
    req("/api/chat-st/1/send", "POST", {"text": "说书人插话"}, ST)
    v2 = req(f"/api/me/{ch_ids[1]}")
    assert any("说书人插话" in m["text"] for m in v2["chat"]["my_chat"]["messages"]), "成员应看到说书人发言"
    # 私聊进行中:发起者邀请更多玩家(新成员看不到历史)
    req(f"/api/chat/1/invite-more?player_id={ch_ids[0]}", "POST", {"invitees": [5]})
    v5 = req(f"/api/me/{ch_ids[4]}")
    assert len(v5["chat"]["invites"]) == 1, "中途被邀请者应看到邀请"
    req(f"/api/chat/1/invite?player_id={ch_ids[4]}", "POST", {"accept": True})
    req(f"/api/chat/1/send?player_id={ch_ids[0]}", "POST", {"text": "给新成员的话"})
    v5 = req(f"/api/me/{ch_ids[4]}")
    assert [m["text"] for m in v5["chat"]["my_chat"]["messages"]] == ["给新成员的话"], \
        "中途加入者只应看到加入后的消息"
    try:  # 非发起者不能邀请
        req(f"/api/chat/1/invite-more?player_id={ch_ids[1]}", "POST", {"invitees": [6]})
        raise AssertionError("非发起者邀请未被拒绝")
    except urllib.error.HTTPError as e:
        assert e.code == 400
    req("/api/chat-st/recall", "POST", headers=ST)
    v1 = req(f"/api/me/{ch_ids[0]}")
    assert v1["chat"]["my_chat"] is None, "召回后私聊应关闭"
    st = req("/api/state", "GET", headers=ST)
    chat1 = next(c for c in st["chats"] if c["id"] == 1)
    assert chat1["closed"] and any("秘密消息" in m["text"] for m in chat1["messages"]), \
        "说书人应保留已关闭私聊的留档"
    req(f"/api/chat/create?player_id={ch_ids[0]}", "POST", {"invitees": [2]})
    req("/api/day/end", "POST", headers=ST)
    v1 = req(f"/api/me/{ch_ids[0]}")
    assert "chat" not in v1, "天黑后玩家不应再有私聊数据"
    st = req("/api/state", "GET", headers=ST)
    assert any(c["id"] == 2 and c["closed"] for c in st["chats"]), "说书人档案应保留天黑关闭的群"
    print("CHAT  私聊:邀请/接受拒绝/申请审批/历史隔离/说书人全知+发言/召回留档/天黑玩家销毁 OK")

    req("/api/reset", "POST", headers=ST)
    print("ALL PASS")


if __name__ == "__main__":
    asyncio.run(main())
