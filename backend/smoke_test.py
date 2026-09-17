"""冒烟测试:验证 REST + WebSocket 全链路。

用法:先 `python run.py` 启动服务器,再另开终端 `python smoke_test.py`
"""

import asyncio
import json
import urllib.request

import websockets

BASE = "http://localhost:8000"
PASSWORD = "grimoire"


def req(path: str, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


async def main() -> None:
    info = req("/api/info")
    print(f"INFO  status={info['status']} lan_ip={info['lan_ip']}")

    ids = [req("/api/join", "POST", {"name": f"测试{i}"})["player_id"] for i in range(1, 7)]
    print("JOIN  6 名玩家加入")

    state = req("/api/assign", "POST", headers={"X-Storyteller-Password": PASSWORD})
    assert state["status"] == "playing", "分配后应进入 playing"
    print("ASSIGN " + ", ".join(f"{p['seat']}:{p['role']['name']}" for p in state["players"]))

    async with websockets.connect(f"ws://localhost:8000/ws?who=player:{ids[0]}") as ws:
        view = json.loads(await ws.recv())
        assert view["me"]["role"], "玩家应收到自己的角色"
        print(f"WS    玩家收到角色: {view['me']['role']['name']}")

        req("/api/player/" + ids[0] + "/alive", "POST", headers={"X-Storyteller-Password": PASSWORD})
        view = json.loads(await ws.recv())
        assert view["me"]["alive"] is False, "存活状态应实时推送"
        print("WS    存活标记实时推送 OK")

    print("ALL PASS")


if __name__ == "__main__":
    asyncio.run(main())
