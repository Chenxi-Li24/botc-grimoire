"""Player-safe and storyteller-complete views of a single game state."""

from ..domain.constants import FAKE_POOLS
from ..roles import (COMPOSITION, DEMON, MINION, OUTSIDER, SCRIPTS,
                     SCRIPT_ADJUST_ROLES, ROLE_ADJUSTMENTS, TOWNSFOLK)
from ..scripts.travelers import (RECOMMENDED as TRAVELER_RECOMMENDED,
                                ROLE_BY_ID as TRAVELER_BY_ID,
                                ROLES as TRAVELERS)
from ..scripts.wafu_leiming import NIGHT_ACTIONS
from ..scripts.fabled import ROLES as FABLED, ROLE_BY_ID as FABLED_BY_ID


class ProjectionMixin:
    """Compatibility mixin: public GameManager view methods live here."""


    def _team_seats(self, team: str) -> list[dict]:
        """某阵营的座位名单(在座或空座预发都列出):会面步骤指向恶魔/爪牙用。"""
        out = []
        for i in range(1, self.player_count + 1):
            p = self.seats.get(i)
            rid = self.seat_state(i).character_id
            if rid and self.roles[rid]["team"] == team:
                out.append({"seat": i, "name": p.name if p is not None else None,
                            "role": self.roles[rid]})
        return out

    def _role_seats(self, rid: str) -> list[dict]:
        """某角色的座位名单(在座或空座预发都列出):疯子等特定角色指向用。"""
        out = []
        for i in range(1, self.player_count + 1):
            p = self.seats.get(i)
            r = self.seat_state(i).character_id
            if r == rid:
                out.append({"seat": i, "name": p.name if p is not None else None})
        return out

    def _seat_real_role(self, seat: int) -> str | None:
        """座位的真实角色 id;账号是否认领不影响角色存在。"""
        return self.seat_state(seat).character_id

    def _seat_alive(self, seat: int) -> bool:
        """座位生死只读取 canonical SeatState,与账号是否在线无关。"""
        return self.seat_state(seat).alive

    def _seat_slots(self, st_view: bool, my_id: str | None = None) -> list[dict]:
        seat_of = self.seats
        slots = []
        for i in range(1, self.player_count + 1):
            p = seat_of.get(i)
            if p is None:
                slot = {"seat": i, "player": None}
                seat_state = self.seat_state(i)
                if st_view and i in self.seat_roles:  # 空座上的预发身份,说书人可见
                    slot["assigned_role"] = self.roles[self.seat_roles[i]]
                if st_view and i in self.seat_roles:  # 空座生死:以说书人标记为准
                    slot["alive"] = self.seat_alive.get(i, True)
                    slot["secret_dead"] = (not seat_state.alive
                                           and seat_state.public_alive)
                    slot["death_record"] = seat_state.death_record
                if st_view and i in self.seat_fakes:  # 空座也能先标记认知覆盖
                    slot["fake_role"] = self.roles[self.seat_fakes[i]]
                if st_view and i in self.seat_markers:  # 空座同样挂状态标记(测试/控制)
                    slot["markers"] = self.seat_markers[i]
                if st_view and i in self.mad_about:  # 空座的疯狂内容
                    slot["mad_about"] = self.roles[self.mad_about[i]]
                if st_view and i in self.seat_role_changes:  # 空座也能标记角色转变
                    slot["role_change"] = self.roles[self.seat_role_changes[i]]
                if st_view and i in self.seat_team_changes:  # 空座也能标记阵营转变
                    slot["team_change"] = self.seat_team_changes[i]
                if st_view:
                    effect_view = self.effects.projection(i)
                    slot["effects"] = effect_view["badges"]
                    slot["effect_history"] = effect_view["history"]
                slots.append(slot)
                continue
            entry = p.storyteller(self.roles) if st_view else p.public()
            slot = {"seat": i, "player": entry}
            if st_view:
                seat_state = self.seat_state(i)
                slot["secret_dead"] = (not seat_state.alive and seat_state.public_alive)
                slot["death_record"] = seat_state.death_record
            if (not p.alive and not p.dead_vote_used
                    and (st_view or not self.seat_state(i).public_alive)):
                # 秘密死亡公开前不能用死票图标侧漏。
                slot["dead_vote_left"] = True
            if st_view and i in self.seat_fakes:  # 认知覆盖标记,说书人可见
                slot["fake_role"] = self.roles[self.seat_fakes[i]]
            if st_view and i in self.seat_markers:  # 状态标记,仅说书人可见
                slot["markers"] = self.seat_markers[i]
            if st_view and i in self.mad_about:  # 疯狂内容:疯狂宣称的角色,仅说书人可见
                slot["mad_about"] = self.roles[self.mad_about[i]]
            if st_view and i in self.seat_role_changes:  # 角色转变:变成哪个角色,说书人可见
                slot["role_change"] = self.roles[self.seat_role_changes[i]]
            if st_view and i in self.seat_team_changes:  # 阵营转变:新阵营,说书人可见
                slot["team_change"] = self.seat_team_changes[i]
            if st_view:
                effect_view = self.effects.projection(i)
                slot["effects"] = effect_view["badges"]
                slot["effect_history"] = effect_view["history"]
            if my_id is not None:  # is_me 属于座位槽位层,不属于 player
                slot["is_me"] = p.id == my_id
            slots.append(slot)
        return slots

    def _public_progress(self) -> dict:
        """白天/夜晚进度(玩家与说书人都可见):含白天子阶段(公聊私聊/提名)。"""
        return {"phase": self.phase, "night_no": self.night_no, "day_no": self.day_no,
                "day_stage": self.day_stage}

    def _step_reached(self, key: str) -> bool:
        """夜晚是否已推进到 key 步骤(信息一旦给出不可收回,之后一直可见)。"""
        if self.status != "playing":
            return False
        if self.night_no > 1 or self.phase == "day":
            return True  # 第 2 夜起 / 白天:首夜会面早已发生
        return any(s["key"] == key for s in self.night_steps[:self.night_idx + 1])

    def _player_night_workflow(self, seat: int) -> dict:
        """Project only this seat's prompt and delivered message, never adjudication facts."""
        current = self.night.queue.current
        prompt = None
        lunatic_choices = []
        if current is not None and current.actor_seat == seat:
            ability_id = current.source.get(
                "ability_character", current.perceived_as or current.character_id,
            )
            ability = self.night.pack.character_by_id.get(ability_id)
            selection = ability.selection if ability else None
            needs_targets = "targets" in current.required_fields
            needs_character = "character" in current.required_fields
            target_seats = []
            if needs_targets:
                for candidate in sorted(self.seat_states.values(), key=lambda item: item.seat):
                    if candidate.character_id is None:
                        continue
                    if selection and not selection.allow_self and candidate.seat == seat:
                        continue
                    if selection and selection.alive_only and not candidate.alive:
                        continue
                    target_seats.append(candidate.seat)
            character_candidates = []
            if needs_character:
                allowed = selection.character_teams if selection else ()
                for character in self.night.pack.characters:
                    if allowed and character.team not in allowed:
                        continue
                    character_candidates.append({
                        "id": character.id,
                        "name": self.night.pack.locale[character.name_key],
                        "team": character.team,
                    })
            prompt = {
                "id": current.id,
                "character_id": ability_id,
                "trigger": current.trigger,
                "status": ("current" if current.status == "upcoming"
                           else current.status),
                "required_fields": list(current.required_fields),
                "values": {key: value for key, value in current.values.items()
                           if key in {"targets", "character", "acknowledged"}},
                "name": current.name,
                "reminder": current.reminder,
                "target_seats": target_seats,
                "player_count": selection.players if selection and needs_targets else 0,
                "character_candidates": character_candidates,
                "allow_self": selection.allow_self if selection else True,
                "alive_only": selection.alive_only if selection else False,
            }
            if ability and ability.team == DEMON:
                lunatic_choices = self.night._lunatic_context()
        event_states = {event.id: event.state for event in self.journal_events}
        deliveries = []
        for delivery in self.information_deliveries.values():
            if delivery.actor_seat != seat:
                continue
            item = delivery.to_dict()
            for hidden in (
                "real_character", "true_result", "claims", "registrations",
                "effect_snapshot", "reason", "corrections",
            ):
                item.pop(hidden, None)
            item["retracted"] = event_states.get(delivery.source_event) == "undone"
            deliveries.append(item)
        return {"night_no": self.night_no, "prompt": prompt,
                "deliveries": deliveries, "lunatic_choices": lunatic_choices}

    def player_view(self, player_id: str) -> dict:
        me = self.players[player_id]
        fake_id = self.seat_fakes.get(me.seat) if me.seat is not None else None
        started = self.status == "playing"
        me_traveler = self.traveler_of(player_id)  # 旅行者:角色/阵营存在旅行者槽位,不在 me.role_id
        view = {
            "status": self.status,
            "script": SCRIPTS[self.script_id]["name"],
            "player_count": self.player_count,
            # 官方配比(公开信息)。实际调整(男爵 +2 外来者等)绝不告知玩家
            "composition": list(COMPOSITION[self.player_count]),
            # 哨兵在场(公开,方向保密):玩家只知外来者可能 +1 或 −1
            "sentinel": self.sentinel != 0,
            "fabled": [FABLED_BY_ID[f] for f in self.fabled],  # 传奇角色公开:所有玩家可见
            **self._public_progress(),
            # 提名/投票是公开信息,实时推给玩家(举手、票型、处决)
            "nominations": self.nominations,
            "current": self.current,
            # 开局前不揭示身份:说书人开始游戏玩家才拿到角色(旅行者的角色等说书人指派)
            "me": me.public(),
            "me_wish": me.wish,  # 自己的许愿(仅本人与说书人可见)
            # 旅行者公开信息:谁加入了、什么角色(官方要求宣告),但阵营保密
            "travelers_public": [{"id": t["id"], "name": t["name"], "alive": t["alive"],
                                  "exiled": t["exiled"],
                                  "role": TRAVELER_BY_ID[t["role_id"]] if t["role_id"] else None}
                                 for t in self.travelers],
            "room_code": self.room_code,  # 玩家卡显示当前房间号
            "seats": self._seat_slots(st_view=False, my_id=player_id),
        }
        if me_traveler is not None:
            # 旅行者条目(不含 player_id)+ 已指派角色 + 阵营(官方:旅行者本人知道自己的阵营)
            view["traveler"] = {k: v for k, v in me_traveler.items() if k != "player_id"}
            if me_traveler["role_id"]:
                view["traveler"]["role"] = TRAVELER_BY_ID[me_traveler["role_id"]]
                view["me"]["role"] = TRAVELER_BY_ID[me_traveler["role_id"]]
        elif started:
            view["me"] = me.private(self.roles, fake_id)
            view["me"]["dead_vote_used"] = me.dead_vote_used
            if me.seat is not None:
                view["night_workflow"] = self._player_night_workflow(me.seat)
        # 结算:说书人宣布游戏结束 → 全场揭晓真实角色与获胜方
        if self.winner is not None:
            view["result"] = {
                "winner": self.winner,
                "seats": [{"seat": s, "name": self.seats[s].name if s in self.seats else None,
                           "alive": self._seat_alive(s),
                           "role": self.roles[rid] if (rid := self._seat_real_role(s)) else None}
                          for s in range(1, self.player_count + 1)],
                "travelers": [{"id": t["id"], "name": t["name"], "alive": t["alive"],
                               "align": t["align"],
                               "role": TRAVELER_BY_ID[t["role_id"]] if t["role_id"] else None}
                              for t in self.travelers],
            }
            view["review"] = self.build_review()  # 复盘时间线(结算页可切到独立复盘页)
        if not started:
            return view
        # 座位玩家是否公开死亡统一由 SeatState.public_alive 决定。
        if (me_traveler is not None and self.phase == "night" and not me_traveler["alive"]
                and me_traveler["died_day"] == self.night_no):
            view["traveler"]["alive"] = True  # 旅行者夜里死:本人卡同样天亮前不显示
        # 公开的死亡名单(按天排序):夜里死的人天亮才进名单;前端按天分组换行显示
        deaths = []
        for p in self.players.values():
            if p.seat is None or p.alive or p.died_day is None:
                continue
            if self.seat_state(p.seat).public_alive:
                continue  # 秘密死亡尚未由天亮事件公开
            deaths.append({"seat": p.seat, "name": p.name, "day": p.died_day})
        for t in self.travelers:
            if t["alive"] or t["died_day"] is None:
                continue
            if self.phase == "night" and t["died_day"] == self.night_no:
                continue  # 今夜刚死:天亮才公开
            deaths.append({"seat": t["id"], "name": t["name"], "day": t["died_day"],
                           "exiled": t["exiled"]})
        for i in range(1, self.player_count + 1):  # 空座死亡同样进名单(以说书人标记为准)
            if i in self.seats or i not in self.seat_roles:
                continue
            if self.seat_alive.get(i, True) or i not in self.seat_dead_day:
                continue
            if self.seat_state(i).public_alive:
                continue  # 秘密死亡尚未由天亮事件公开
            deaths.append({"seat": i, "name": self.roles[self.seat_roles[i]]["name"],
                           "day": self.seat_dead_day[i], "empty": True})
        deaths.sort(key=lambda d: (d["day"], str(d["seat"])))
        view["deaths"] = deaths
        # 邪恶旅行者:加入时由说书人告知恶魔是谁(官方规则,爪牙不告知)
        if me_traveler is not None and me_traveler["align"] == "evil":
            view["demon_seats"] = [{"seat": d["seat"], "name": d["name"]}
                                   for d in self._team_seats(DEMON)]
        # 白天私聊:本人的群/邀请/公开列表(气泡);说书人作为特殊玩家同样参与
        who = me_traveler["id"] if me_traveler is not None else me.seat
        chat_view = self.chat_view_for(who) if who is not None else None
        if chat_view is not None:
            view["chat"] = chat_view
        if me_traveler is not None:
            return view  # 旅行者没有座位,后面全是座位玩家的会面/转变逻辑
        # 夜晚唤醒(瓦釜雷鸣手机交互,先只开放这一板):ST 走到对应步骤时,该玩家手机点亮
        if (self.script_id == "wafu-leiming" and self.phase == "night"
                and me.seat is not None and self.night_steps):
            cur = self.night_steps[self.night_idx]
            real_rid = me.role_id
            real_team = self.roles[real_rid]["team"] if real_rid else None
            wake = None
            if me.alive:
                if real_team == DEMON and cur["key"] == real_rid:
                    wake = {"action": "kill"}
                elif real_rid == "lunatic" and (cur["key"] == "lunatic" or cur.get("fake_for") == me.seat):
                    wake = {"action": "kill", "lunatic": True}  # 疯子以为自己是恶魔,演戏选择
                elif (real_rid in NIGHT_ACTIONS and cur["key"] == real_rid
                      and not (NIGHT_ACTIONS[real_rid].get("info_first") and self.night_no == 1)):
                    wake = {"action": "pick", "count": NIGHT_ACTIONS[real_rid]["count"]}
                    if NIGHT_ACTIONS[real_rid].get("grimoire"):
                        wake["grimoire"] = True  # 寡妇首夜:手机查看魔典(仅此夜、仅此步)
                    if NIGHT_ACTIONS[real_rid].get("char"):
                        # 麻脸巫婆:全角色池(不知道谁在场);洗脑师:只给善良角色(疯狂宣称)
                        pool = [r for r in self.roles.values()]
                        if NIGHT_ACTIONS[real_rid].get("good_char"):
                            pool = [r for r in pool if r["team"] in (TOWNSFOLK, OUTSIDER)]
                        wake["char"] = True
                        wake["chars"] = [{"id": r["id"], "name": r["name"], "team": r["team"]}
                                         for r in pool]
                elif (real_rid in FAKE_POOLS and cur.get("fake_for") == me.seat
                      and cur["key"] in NIGHT_ACTIONS):
                    wake = {"action": "pick", "count": NIGHT_ACTIONS[cur["key"]]["count"]}  # 酒鬼假身份行动
            elif real_rid == "ravenkeeper" and me.died_day == self.night_no and cur["key"] == "ravenkeeper":
                wake = {"action": "pick", "count": 1}  # 守鸦人死于今夜:被唤醒指认
            if wake is not None:
                if wake["action"] == "kill":
                    wake["targets"] = [s for s in range(1, self.player_count + 1)
                                       if self._seat_real_role(s) and self._seat_alive(s)]
                    entry = self.night_kills.get(str(self.night_no))
                    if entry:
                        chosen = entry.get("lunatic_seat") if real_rid == "lunatic" else entry.get("seat")
                        if chosen is not None:
                            view["my_kill"] = chosen
                else:
                    wake["targets"] = [s for s in range(1, self.player_count + 1)
                                       if self._seat_real_role(s)]  # 线下/未领取座位同样可选
                view["night_wake"] = wake
                if wake.get("grimoire"):
                    # 寡妇首夜查看魔典:全部座位的真实角色与旅行者(仅此夜、仅此步,睡下后不可再看)
                    view["grimoire"] = {
                        "seats": [{"seat": s,
                                   "name": p.name if (p := self.seats.get(s)) else None,
                                   "alive": self._seat_alive(s),
                                   "role": self.roles[self.seat_roles[s]] if s in self.seat_roles else None}
                                  for s in range(1, self.player_count + 1)],
                        "travelers": [{"id": t["id"], "name": t["name"], "alive": t["alive"],
                                       "align": t["align"],
                                       "role": TRAVELER_BY_ID[t["role_id"]] if t["role_id"] else None}
                                      for t in self.travelers],
                    }
            # 自己的夜晚选择与说书人回复(夜里随时可见)
            choice = self.night_choices.get(str(self.night_no), {}).get(str(me.seat))
            if choice is not None:
                view["night_choice"] = choice
            # 恶魔得知疯子刀了谁(官方:恶魔知道疯子是谁,也知道他每夜的选择)
            entry = self.night_kills.get(str(self.night_no))
            if real_team == DEMON and entry and entry.get("lunatic_seat") is not None:
                view["lunatic_kill"] = entry["lunatic_seat"]
        team = self.roles[me.role_id]["team"] if me.role_id else None
        # 角色转变/阵营转变:必须告诉玩家本人(手机卡显示提醒),其他标记仅说书人可见
        if me.seat is not None:
            if me.seat in self.seat_role_changes:
                view["role_changed"] = self.roles[self.seat_role_changes[me.seat]]
            if me.seat in self.seat_team_changes:
                view["team_changed"] = self.seat_team_changes[me.seat]
            if me.seat in self.mad_about:
                # 疯狂通知:被疯狂者必须被告知(疯狂宣称自己是该角色,直到说书人解除,否则可能被处决)
                view["my_mad"] = {"role": self.roles[self.mad_about[me.seat]]}
        lunatic_seats = self._role_seats("lunatic")  # 真疯子:恶魔与爪牙都须知道他是谁
        # 爪牙会面:所有爪牙同时醒来——知道恶魔是谁、谁是疯子,也彼此看见对方(官方规则)
        if team == MINION and self._step_reached("minioninfo"):
            view["demon_seats"] = [{"seat": d["seat"], "name": d["name"]}
                                   for d in self._team_seats(DEMON)]
            view["minion_seats"] = [{"seat": m["seat"], "name": m["name"]}
                                    for m in self._team_seats(MINION)]
            if lunatic_seats:
                view["lunatic_seats"] = [{"seat": l["seat"], "name": l["name"]} for l in lunatic_seats]
        # 恶魔会面:爪牙是谁 + 三个伪装,推进到该步骤才揭晓(按真实身份判断,酒鬼假镇民不触发)
        if team == DEMON and self._step_reached("demoninfo"):
            view["minion_seats"] = [{"seat": m["seat"], "name": m["name"]}
                                    for m in self._team_seats(MINION)]
            if lunatic_seats:
                view["lunatic_seats"] = [{"seat": l["seat"], "name": l["name"]} for l in lunatic_seats]
            if self.bluffs:
                view["bluffs"] = [self.roles[rid] for rid in self.bluffs]
        # 疯子自己:以为自己是恶魔——爪牙与伪装都是说书人选的(不一定是真的),疯子步骤/爪牙会面推进后揭晓
        if me.role_id == "lunatic" and (self._step_reached("lunatic") or self._step_reached("minioninfo")):
            fakes = self.lunatic_minions.get(me.seat, [])
            bluffs = self.lunatic_bluffs.get(me.seat, [])
            if fakes:
                view["minion_seats"] = [{"seat": s, "name": self.seats[s].name if s in self.seats else None}
                                        for s in fakes]
            if bluffs:
                view["bluffs"] = [self.roles[rid] for rid in bluffs]
        return view

    def storyteller_view(self) -> dict:
        # 处决门槛:存活玩家(不含旅行者)的一半及以上,向上取整;空座同样按说书人标记的生死计
        alive_count = sum(1 for state in self.seat_states.values()
                          if state.character_id and state.alive)
        total_players = (sum(1 for state in self.seat_states.values() if state.character_id)
                         + len(self.travelers))
        return {
            "status": self.status,
            "script": self.script_id,
            "player_count": self.player_count,
            "scripts": [{"id": sid, "name": s["name"], "en": s["en"],
                         "min": s.get("min_players", 5)}
                        for sid, s in SCRIPTS.items()],
            # 手动发身份用:当前板子的角色表 + 基础配比 + 调整角色
            "roles": SCRIPTS[self.script_id]["roles"],
            "composition": list(COMPOSITION[self.player_count]),
            "adjust_roles": {rid: list(ROLE_ADJUSTMENTS[rid])
                             for rid in SCRIPT_ADJUST_ROLES.get(self.script_id, ())},
            "seat_roles": {str(seat): rid for seat, rid in self.seat_roles.items()},
            "seats": self._seat_slots(st_view=True),
            **self._public_progress(),
            "night": {"steps": self.night_steps, "idx": self.night_idx},
            "nominations": self.nominations,
            "current": self.current,
            "alive_count": alive_count,
            "quorum": (alive_count + 1) // 2,  # 处决所需票数:存活玩家(不含旅行者)一半及以上
            # 旅行者:流放票数 = 全体玩家(含死者)总数的一半;旅行者不算配板,加入/流放不限时刻
            "travelers": self.travelers,
            "traveler_roles": TRAVELERS,
            "traveler_recommended": TRAVELER_RECOMMENDED.get(self.script_id, None),  # None=社区板子,全部可选
            "total_players": total_players,
            "exile_quorum": (total_players + 1) // 2,
            # 人未齐开局:每个座位都有身份(在座持有或空座预发)即可强制开始
            "can_start": self.status == "lobby" and all(
                (self.seats.get(i) is not None and self.seats[i].role_id)
                or i in self.seat_roles for i in range(1, self.player_count + 1)),
            "bluffs": [self.roles[rid] for rid in self.bluffs],  # 恶魔的三个伪装(说书人可见)
            "fake_pools": FAKE_POOLS,  # 认知覆盖类角色 → 假身份可取阵营(手动面板渲染选择器用)
            "sentinel": self.sentinel,  # 哨兵:+1/−1/2(不变)/0(关),说书人可见
            # 入夜会面:告诉爪牙谁是恶魔、告诉恶魔谁是爪牙(空座预发也列出)
            "demon_seats": self._team_seats(DEMON),
            "minion_seats": self._team_seats(MINION),
            "lunatic_seats": self._role_seats("lunatic"),  # 真疯子座位:恶魔/爪牙会面时须一并指认
            "lunatic_minions": {str(s): ms for s, ms in self.lunatic_minions.items()},  # 疯子以为的爪牙
            "lunatic_bluffs": {str(s): [self.roles[rid] for rid in bs]
                               for s, bs in self.lunatic_bluffs.items()},  # 疯子的伪装(说书人选,不一定是真的)
            # 认知覆盖待定:发牌后说书人尚未选定假身份的座位(玩家卡先别给看)
            "fakes_pending": [{"seat": i, "role": self.roles[rr]}
                              for i in range(1, self.player_count + 1)
                              if (rr := self._seat_real_role(i)) in FAKE_POOLS and i not in self.seat_fakes],
            "saved_at": self.saved_at,
            "room_code": self.room_code,  # 房间号:说书人可改,玩家加入须匹配
            "winner": self.winner,
            "fabled": [FABLED_BY_ID[f] for f in self.fabled],  # 在场的传奇角色(公开)
            "chats": [self._chat_st_view(c) for c in self.chats],  # 私聊全量(数组格式,说书人查看所有内容并留档)
            "fabled_pool": FABLED,  # 全部传奇角色(魔典勾选用)
            "review": self.build_review() if self.winner else None,  # 复盘时间线(魔典复盘视图用)
            "night_kills": self.night_kills,  # 夜晚刀人:恶魔/疯子的手机选择(说书人可见)
            "night_choices": self.night_choices,  # 夜晚信息交互:各座位选择与说书人回复
            "night_actions": NIGHT_ACTIONS,  # 夜晚行动配置(前端代操作面板用)
            "night_workflow": self.night.projection(),  # Vue 夜晚工作台的权威动态队列
            "fortuneteller_red": self.fortuneteller_red,  # 占卜师宿敌(红鲱鱼):只有说书人知道
            # 已加入的玩家(含未入座):许愿仅说书人可见,配板/手动发身份时参考
            "players": [{"id": p.id, "name": p.name, "seat": p.seat, "alive": p.alive,
                         "wish": p.wish} for p in self.players.values()],
        }
