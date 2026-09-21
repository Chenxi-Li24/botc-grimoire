"""Game conclusion, fabled roles, and review timeline."""

from __future__ import annotations

from ..roles import DEMON
from ..scripts.fabled import ROLE_BY_ID as FABLED_BY_ID


class ReviewMixin:
    def mark_reply_wrong(self, seat: int, night: int, wrong: bool) -> None:
        """说书人复盘标注:该夜该座位的回复信息是错的(中毒/醉酒/酒鬼之外的主动标注)。"""
        entry = self.night_choices.get(str(night), {}).get(str(seat))
        if entry is None or not entry.get("reply"):
            raise ValueError("该夜该座位没有回复")
        entry["wrong"] = bool(wrong)
        self.save()


    def build_review(self) -> dict:
        """复盘时间线:按夜/天分组的事件条目;错误信息自动判定(当时中毒/醉酒、本人是酒鬼)+ 说书人标注。"""
        def name_of(s):
            p = self.seats.get(s)
            if p is not None:
                return p.name
            rid = self.seat_roles.get(s)
            return self.roles[rid]["name"] if rid else "空座"

        def role_of(rid):
            return self.roles[rid]["name"] if rid in self.roles else rid

        order: list[tuple[str, int]] = []
        for e in self.events:
            key = (e["phase"], e["n"])
            if e["phase"] and key not in order:
                order.append(key)
        buckets: dict[tuple, list[dict]] = {k: [] for k in order}
        pending_choice: dict[tuple, dict] = {}  # (key, seat) → 该夜的选人条目(等回复合并)
        active_marker: dict[int, dict[str, bool]] = {}  # seat → {poisoned: bool, drunk: bool}
        for e in self.events:
            key = (e["phase"], e["n"])
            d = e["data"]
            s = e["seat"]
            item = None
            if e["type"] == "kill":
                item = {"text": f"😈 恶魔「{role_of(d['role'])}」({s}号 {name_of(s)})选择刀杀 {d['target']}号 {name_of(d['target'])}"}
            elif e["type"] == "lunatic_kill":
                item = {"text": f"🩻 疯子({s}号 {name_of(s)})选择刀杀 {d['target']}号(演戏,不执行)"}
            elif e["type"] == "death":
                item = {"text": f"☠ 说书人标记 {s}号 {name_of(s)} 死亡"}
            elif e["type"] == "choice":
                t = "、".join(f"{x}号" for x in d.get("targets", []))
                item = {"text": f"🔮 {role_of(d['role'])}({s}号 {name_of(s)})选择 {t}"
                                + (f" → 变身「{role_of(d['char'])}」" if d.get("char") else "")}
                pending_choice[(key, s)] = item
            elif e["type"] == "reply":
                item = {"text": f"📩 说书人回复 {s}号 {name_of(s)}:「{d['text']}」",
                        "mark": {"seat": s, "night": e["n"]}}
                # 与同夜同座的选人条目合并
                prev = pending_choice.pop((key, s), None)
                if prev is not None:
                    prev["text"] += f" · 回复:「{d['text']}」"
                    prev["mark"] = item["mark"]
                    item = prev
                wrong_why = []
                if self._seat_real_role(s) == "drunk":
                    wrong_why.append("此人是酒鬼,信息必假")
                if active_marker.get(s, {}).get("poisoned"):
                    wrong_why.append("当时中毒")
                if active_marker.get(s, {}).get("drunk"):
                    wrong_why.append("当时醉酒")
                if wrong_why:
                    item["wrong"] = True
                    item["why"] = "、".join(wrong_why)
                entry = self.night_choices.get(str(e["n"]), {}).get(str(s))
                if entry and entry.get("wrong"):
                    item["wrong"] = True
                    item["why"] = (item.get("why") + "、" if item.get("why") else "") + "说书人标注"
            elif e["type"] == "transform":
                extra = " · 创造恶魔:本夜死亡由说书人决定" if self.roles[d["char"]]["team"] == DEMON else ""
                item = {"text": f"🎭 麻脸巫婆把 {d['target']}号 {name_of(d['target'])} 变成「{role_of(d['char'])}」(原「{role_of(d.get('from', ''))}」){extra}"}
            elif e["type"] == "transform_invalid":
                item = {"text": f"❌ 麻脸巫婆想把 {d['target']}号 变成「{role_of(d['char'])}」:角色在场,未生效(麻脸巫婆不知情)"}
            elif e["type"] == "mad":
                item = {"text": f"🎭 洗脑师让 {d['target']}号 {name_of(d['target'])} 疯狂宣称自己是「{role_of(d['char'])}」"}
            elif e["type"] == "role_change":
                tag = "🩸 传刀:" if d.get("pass_demon") else "🔄 角色转变:"
                item = {"text": f"{tag}{s}号 {name_of(s)}「{role_of(d.get('from', ''))}」→「{role_of(d['to'])}」"}
            elif e["type"] == "team_change":
                item = {"text": f"⚖ 阵营转变:{s}号 {name_of(s)} → {'邪恶' if d['team'] == 'evil' else '善良'}"}
            elif e["type"] == "execution":
                item = {"text": f"⚔ 处决:{s}号 {name_of(s)}({d.get('votes', 0)} 票)"}
            elif e["type"] == "marker":
                if d.get("on"):
                    active_marker.setdefault(s, {})[d["marker"]] = True
                else:
                    active_marker.setdefault(s, {})[d["marker"]] = False
                item = {"text": f"🧪 说书人标记 {s}号 {name_of(s)} {'中毒' if d['marker'] == 'poisoned' else '醉酒'}{'' if d.get('on') else '(解除)'}"}
            elif e["type"] == "traveler_join":
                item = {"text": f"🎒 旅行者「{d['name']}」加入"}
            elif e["type"] == "traveler_assign":
                item = {"text": f"🎒 旅行者「{d['name']}」指派为「{role_of(d['role'])}」({d['align'] == 'evil' and '邪恶' or '善良'})"}
            elif e["type"] == "traveler_exile":
                item = {"text": f"🏴 旅行者「{d['name']}」被流放"}
            elif e["type"] == "end":
                item = {"text": f"🏁 游戏结束:{'善良' if d['winner'] == 'good' else '邪恶'}阵营获胜"}
            if item is not None:
                item["type"] = e["type"]
                buckets[key].append(item)
        # 恶魔伪装(开局定好,不在场好角色)与疯子伪装:补进第 1 夜组开头
        if self.bluffs:
            if ("night", 1) not in buckets:
                order.insert(0, ("night", 1))
                buckets[("night", 1)] = []
            buckets[("night", 1)].insert(0, {
                "type": "bluffs",
                "text": f"🧪 恶魔伪装(不在场好角色):{'、'.join(role_of(r) for r in self.bluffs)}"})
        for seat, bl in self.lunatic_bluffs.items():
            if not bl:
                continue
            if ("night", 1) not in buckets:
                order.insert(0, ("night", 1))
                buckets[("night", 1)] = []
            buckets[("night", 1)].insert(0, {
                "type": "bluffs",
                "text": f"🩻 给疯子({seat}号)的伪装:{'、'.join(role_of(r) for r in bl)}"})
        groups = [{"label": f"第{pn}夜" if ph == "night" else f"第{pn}天",
                   "phase": ph, "items": buckets[(ph, pn)]}
                  for (ph, pn) in order]
        return {"groups": groups, "has_data": bool(self.events)}


    def end_game(self, winner: str | None) -> None:
        """说书人宣布游戏结束并判定获胜方(good/evil);None 撤销结算。"""
        if winner is not None and winner not in ("good", "evil"):
            raise ValueError("获胜方只能是 good/evil")
        if winner is not None and self.status != "playing":
            raise ValueError("本局还没开始")
        self.winner = winner
        if winner:
            self._log(None, "end", {"winner": winner})
        self.save()


    def toggle_fabled(self, fid: str, on: bool) -> None:
        """传奇角色(Fabled,公开信息):说书人勾选在场。换板子不丢,重置才清。"""
        if fid not in FABLED_BY_ID:
            raise ValueError("未知传奇角色")
        if on and fid not in self.fabled:
            self.fabled.append(fid)
        elif not on and fid in self.fabled:
            self.fabled.remove(fid)
        self.save()
