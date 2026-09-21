"""Player-owned, append-only deductions; never used by the game rules engine."""

from __future__ import annotations

import time


VALID_CATEGORIES = {"role", "alignment", "status", "change"}
VALID_OPERATIONS = {"set", "clear", "end"}
VALID_STATUSES = {"poisoned", "drunk", "mad"}


class InferenceMixin:
    def _validate_inference(self, target, category, operation, data, client_id):
        if self.status != "playing":
            raise ValueError("本局未开始，暂不能记录推测")
        if self.winner is not None:
            raise ValueError("本局已结算，推测记录只读")
        if not isinstance(target, (int, str)) or isinstance(target, bool):
            raise ValueError("推测目标无效")
        if isinstance(target, int):
            if not 1 <= target <= self.player_count:
                raise ValueError("座位号超出范围")
        elif not any(t["id"] == target for t in self.travelers):
            raise ValueError("旅行者不存在")
        if category not in VALID_CATEGORIES or operation not in VALID_OPERATIONS:
            raise ValueError("推测类别或操作无效")
        if not isinstance(client_id, str) or not 4 <= len(client_id) <= 80 or not all(c.isalnum() or c in "-_" for c in client_id):
            raise ValueError("变更编号无效")
        if not isinstance(data, dict):
            raise ValueError("推测内容无效")
        if len(self.inference_events) >= 5000:
            raise ValueError("本局推测记录已达上限")
        if operation != "set":
            if category == "status" and data.get("status") not in VALID_STATUSES:
                raise ValueError("须指定要结束的异常状态")
            return
        role_ids = set(self.roles)
        if category == "role":
            if data.get("role") not in role_ids:
                raise ValueError("角色不在当前剧本中")
            alternatives = data.get("alternatives", [])
            if not isinstance(alternatives, list) or len(alternatives) > 2 or any(role not in role_ids for role in alternatives):
                raise ValueError("备选角色无效")
            if data.get("confidence", "medium") not in {"low", "medium", "high"}:
                raise ValueError("把握程度无效")
        elif category == "alignment":
            if data.get("alignment") not in {"good", "evil", "unknown"}:
                raise ValueError("阵营推测无效")
        elif category == "status":
            if data.get("status") not in VALID_STATUSES:
                raise ValueError("异常状态无效")
            if data.get("claimed_role") and data["claimed_role"] not in role_ids:
                raise ValueError("疯狂声称的角色不在剧本中")
        else:
            if data.get("kind") not in {"role", "alignment"}:
                raise ValueError("变化类型无效")
            if data["kind"] == "role" and any(data.get(key) and data[key] not in role_ids for key in ("from", "to")):
                raise ValueError("变化角色不在剧本中")
            if data["kind"] == "alignment" and any(data.get(key) and data[key] not in {"good", "evil"} for key in ("from", "to")):
                raise ValueError("变化阵营无效")
        for key, value in data.items():
            if isinstance(value, str) and len(value) > (500 if key == "reason" else 100):
                raise ValueError("推测文字过长")
        if len(str(data)) > 1600:
            raise ValueError("推测内容过长")

    def record_inference(self, player_id, target, category, operation, data, client_id):
        if player_id not in self.players:
            raise ValueError("玩家不存在")
        # Retry protection is checked before the record limit; a repeated write is safe.
        existing = next((event for event in self.inference_events
                         if event["author"] == player_id and event["client_id"] == client_id), None)
        if existing is not None:
            if (existing["target"], existing["category"], existing["operation"], existing["data"]) != (target, category, operation, data):
                raise ValueError("变更编号已被其他内容使用")
            return existing
        self._validate_inference(target, category, operation, data, client_id)
        self.inference_seq += 1
        event = {"seq": self.inference_seq, "author": player_id, "target": target,
                 "category": category, "operation": operation, "data": data,
                 "client_id": client_id, "recorded_at": time.time(),
                 "phase": self.phase, "day_no": self.day_no, "night_no": self.night_no}
        self.inference_events.append(event)
        self.save()
        return event

    def inference_view(self, player_id):
        events = [{key: value for key, value in event.items() if key != "author"}
                  for event in self.inference_events if event["author"] == player_id]
        current = {}
        for event in events:
            category = event["category"]
            status = event["data"].get("status") if category == "status" else None
            key = (str(event["target"]), category, status)
            if category == "change":
                if event["operation"] == "set":
                    current[(str(event["target"]), "change", event["seq"])] = event
            elif event["operation"] == "set":
                current[key] = event
            else:
                current.pop(key, None)
        return {"events": events, "current": list(current.values())}

    def storyteller_inferences(self):
        return [{"player_id": player.id, "name": player.name, "seat": player.seat,
                 **self.inference_view(player.id)}
                for player in self.players.values() if any(
                    event["author"] == player.id for event in self.inference_events)]

    def inference_replay(self, player_id):
        if self.winner is None:
            return None
        events = self.inference_view(player_id)["events"]
        latest = {}
        for event in events:
            if event["category"] in {"role", "alignment"}:
                latest[(event["target"], event["category"])] = event["seq"] if event["operation"] == "set" else None
        entries = []
        for event in events:
            verdict = "unverified"
            target = event["target"]
            if (isinstance(target, int) and event["operation"] == "set"
                    and latest.get((target, event["category"])) == event["seq"]):
                actual_role = self._seat_real_role(target)
                changed_role = target in self.seat_role_changes or any(
                    item.get("seat") == target and item.get("type") == "role_change"
                    for item in self.events)
                changed_alignment = changed_role or target in self.seat_team_changes or any(
                    item.get("seat") == target and item.get("type") == "team_change"
                    for item in self.events)
                if actual_role is not None and not changed_role and event["category"] == "role":
                    verdict = "correct" if event["data"]["role"] == actual_role else "incorrect"
                elif actual_role is not None and not changed_alignment and event["category"] == "alignment":
                    if event["data"]["alignment"] != "unknown":
                        verdict = "correct" if event["data"]["alignment"] == self.seat_state(target).alignment else "incorrect"
            entries.append({**event, "verdict": verdict})
        return entries
