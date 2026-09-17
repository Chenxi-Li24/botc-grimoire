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
call("POST", "/api/config", {"script": "tb", "player_count": 6})
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

# 4. team-change -> team_changed in player view
code, _ = call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": True})
_, pv = call("GET", f"/api/me/{pid}")
check("team-change -> player team_changed", pv.get("team_changed") is True)

# 5. other markers NOT leaked to player view
check("player view has no role_change/seat_markers leak", "role_change" not in pv and "markers" not in pv)

# 6. role-change off clears
code, v = call("POST", "/api/marker", {"seat": 1, "marker": "role-change", "on": False})
slot1 = {s["seat"]: s for s in v["seats"]}[1]
check("role-change off -> cleared", "role_change" not in slot1)

# 7. team-change off clears player flag
call("POST", "/api/marker", {"seat": 1, "marker": "team-change", "on": False})
_, pv = call("GET", f"/api/me/{pid}")
check("team-change off -> flag gone", pv.get("team_changed") is not True)

call("POST", "/api/reset")
print("ALL_PASS" if all(ok) else "SOME_FAILED")
