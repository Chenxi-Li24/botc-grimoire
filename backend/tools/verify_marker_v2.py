"""HTTP verification for role-change-with-role + team-change player notification.
Standalone temp script, no caller, no file I/O (HTTP only), no smoke_test duplicates (smoke_test intentionally out of sync per user's token-saving instruction)."""
import json
import urllib.request

BASE = "http://localhost:8000"
HDRS = {"Content-Type": "application/json", "X-Storyteller-Password": "grimoire"}


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers or HDRS)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


ok = []
def check(name, cond, detail=""):
    ok.append(cond)
    print(("PASS" if cond else "FAIL") + " " + name + ((" " + str(detail)) if detail else ""))


call("POST", "/api/reset")
code, _ = call("POST", "/api/config", {"script": "trouble-brewing", "player_count": 6})
check("config TB 6p -> 200", code == 200, code)
st = call("GET", "/api/state")[1]
room = st["room_code"]
_, join = call("POST", "/api/join", {"name": "P1", "room_code": room})
pid = join["player_id"]
call("POST", f"/api/player/{pid}/sit", {"seat": 1})
call("POST", "/api/assign")

# 1. role-change without role -> 400
code, _ = call("POST", "/api/marker", {"seat": 1, "marker": "role-change", "on": True})
check("role-change missing role -> 400", code == 400, code)

# 2. bogus role -> 400
code, _ = call("POST", "/api/marker", {"seat": 1, "marker": "role-change", "on": True, "role": "nosuchrole"})
check("bogus role -> 400", code == 400, code)

# 3. valid role -> stored in slot.role_change
code, v = call("POST", "/api/marker", {"seat": 1, "marker": "role-change", "on": True, "role": "washerwoman"})
slot1 = {s["seat"]: s for s in v["seats"]}[1]
check("valid role-change -> slot role_change", slot1.get("role_change", {}).get("id") == "washerwoman", slot1.get("role_change"))

# 4. role-change -> role_changed pushed to player view (玩家必须被告知)
_, pv = call("GET", f"/api/me/{pid}")
check("role-change -> player role_changed", pv.get("role_changed", {}).get("id") == "washerwoman")

# 5. team-change without team -> 400
code, _ = call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": True})
check("team-change missing team -> 400", code == 400, code)

# 6. bogus team -> 400
code, _ = call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": True, "team": "sideways"})
check("bogus team -> 400", code == 400, code)

# 7. valid team-change -> slot.team_change + player team_changed
code, v = call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": True, "team": "evil"})
slot1 = {s["seat"]: s for s in v["seats"]}[1]
check("valid team-change -> slot team_change", slot1.get("team_change") == "evil", slot1.get("team_change"))
_, pv = call("GET", f"/api/me/{pid}")
check("team-change -> player team_changed evil", pv.get("team_changed") == "evil")

# 8. markers NOT leaked to player view
check("player view has no slot leak", "role_change" not in pv and "team_change" not in pv and "markers" not in pv)

# 9. role-change off clears (slot + player flag)
code, v = call("POST", "/api/marker", {"seat": 1, "marker": "role-change", "on": False})
slot1 = {s["seat"]: s for s in v["seats"]}[1]
check("role-change off -> cleared", "role_change" not in slot1)
_, pv = call("GET", f"/api/me/{pid}")
check("role-change off -> player flag gone", pv.get("role_changed") is None)

# 10. team-change off clears player flag
call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": False})
_, pv = call("GET", f"/api/me/{pid}")
check("team-change off -> player flag gone", pv.get("team_changed") is None)

# 留一个演示状态给浏览器检查:座1 角色转变→厨师 + 阵营转变→邪恶
call("POST", "/api/marker", {"seat": 1, "marker": "role-change", "on": True, "role": "chef"})
call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": True, "team": "evil"})
print(pid)
print("ALL_PASS" if all(ok) else "SOME_FAILED")
