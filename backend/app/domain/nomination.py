"""Day stages, nominations, votes, and execution resolution."""

from __future__ import annotations

class NominationMixin:
    def set_day_stage(self, stage: str) -> None:
        """说书人切换白天子阶段:talk 公聊私聊 / nom 提名阶段(控节奏)。提名进行中不能退回公聊。"""
        if self.phase != "day":
            raise ValueError("现在是夜晚,不能切换白天阶段")
        if stage not in ("talk", "nom"):
            raise ValueError("白天阶段只能是 talk/nom")
        if stage == "talk" and self.current:
            raise ValueError("有进行中的提名,先结票才能回到公聊私聊")
        self.day_stage = stage
        self.save()


    def start_nomination(self, nominator: int | str, nominee: int | str) -> None:
        if self.winner:
            raise ValueError("本局已结束,先撤销结算")
        if self.phase != "day":
            raise ValueError("白天才能发起提名")
        if self.day_stage != "nom":
            raise ValueError("还没到提名阶段,等说书人宣布")
        if self.current:
            raise ValueError("已有进行中的提名,先宣布结果")
        np_, nt_ = self._target(nominator)
        if np_ is None and nt_ is None:
            if isinstance(nominator, int) and self._seat_real_role(nominator) is not None:
                if not self._seat_alive(nominator):
                    raise ValueError("死亡玩家不能发起提名")
            else:
                raise ValueError("提名者需已入座、是旅行者,或是有预发角色的空座")
        if nt_ is not None and not nt_["alive"]:
            raise ValueError("死亡旅行者不能发起提名")
        if np_ is not None and not np_.alive:
            raise ValueError("死亡玩家不能发起提名")
        np2, nt2 = self._target(nominee)
        if np2 is None and nt2 is None:
            if not (isinstance(nominee, int) and self._seat_real_role(nominee) is not None):
                raise ValueError("被提名者需已入座、是旅行者,或是有预发角色的空座")
        if nt2 is not None and nt2["exiled"]:
            raise ValueError("已流放的旅行者已离开小镇,不能再被提名")
        # 提名规则:每人每天只能发起一次提名、只能被提名一次;死者不能发起但可以被提名;可以提名自己
        todays = [n for n in self.nominations if n["day"] == self.day_no]
        if any(n["nominator"] == nominator for n in todays):
            raise ValueError("今天已发起过提名,每天只能发起一次")
        if any(n["nominee"] == nominee for n in todays):
            raise ValueError("今天已被提名过,每天只能被提名一次")
        self.current = {"nominator": nominator, "nominee": nominee, "votes": []}
        self.save()


    def toggle_vote(self, target: int | str) -> None:
        if self.winner:
            raise ValueError("本局已结束,先撤销结算")
        if not self.current:
            raise ValueError("没有进行中的提名")
        player, traveler = self._target(target)
        # 空座角色同样可投票(以说书人标记的生死为准,而不是是否在座)
        if player is None and traveler is None:
            if not (isinstance(target, int) and self._seat_real_role(target) is not None):
                raise ValueError("投票者需已入座、是旅行者,或是有预发角色的空座")
        votes = self.current["votes"]
        if target in votes:
            votes.remove(target)
            if target in self.current_dead_votes:  # 死票是本次提名交出的(尚未结算):取消举手归还死票
                self.current_dead_votes.discard(target)
                if player is not None:
                    player.dead_vote_used = False
                elif traveler is not None:
                    traveler["dead_vote_used"] = False
                else:
                    self.seat_dead_vote.pop(target, None)
        else:
            alive = (player.alive if player is not None
                     else traveler["alive"] if traveler is not None
                     else self._seat_alive(target))
            if not alive:
                used = (player.dead_vote_used if player is not None
                        else traveler["dead_vote_used"] if traveler is not None
                        else self.seat_dead_vote.get(target, False))
                if used:
                    raise ValueError("该玩家已交出过死亡票,每名死者整局只能投一票")
                if player is not None:
                    player.dead_vote_used = True
                elif traveler is not None:
                    traveler["dead_vote_used"] = True
                else:
                    self.seat_dead_vote[target] = True
                self.current_dead_votes.add(target)
            votes.append(target)
            votes.sort(key=lambda v: (isinstance(v, str), v))  # 座位号在前,旅行者 id 在后
        self.save()


    def player_nominate(self, player_id: str, nominee: int | str) -> None:
        """玩家手机发起提名:提名者必须是本人(座位或旅行者),其余校验复用 start_nomination。"""
        me = self.players[player_id]
        t = self.traveler_of(player_id)
        if t is not None:
            nominator: int | str = t["id"]
        else:
            if me.seat is None:
                raise ValueError("你还没有入座")
            nominator = me.seat
        self.start_nomination(nominator, nominee)


    def player_vote(self, player_id: str) -> None:
        """玩家手机举手/放下:只能投自己(座位或旅行者),死票规则与说书人代记一致。"""
        me = self.players[player_id]
        t = self.traveler_of(player_id)
        if t is not None:
            target: int | str = t["id"]
        else:
            if me.seat is None:
                raise ValueError("你还没有入座")
            target = me.seat
        self.toggle_vote(target)


    def resolve_nomination(self, passed: bool) -> None:
        """结票:通过则被提名者上处决台(待处决);旅行者通过则当场流放(官方:流放不等到天黑)。
        处决要等天黑时统一结算:当天待处决者中票数最多者被处决。"""
        if not self.current:
            raise ValueError("没有进行中的提名")
        rec = {**self.current, "day": self.day_no, "passed": passed, "executed": False}
        self.nominations.append(rec)
        self.current_dead_votes.clear()  # 结算后死票不可再收回
        if passed:
            player, traveler = self._target(self.current["nominee"])
            if traveler is not None:
                traveler["alive"] = False
                traveler["exiled"] = True  # 旅行者被投票通过 = 流放,当场生效
                traveler["died_day"] = self.day_no
                rec["executed"] = True
                self._log(None, "traveler_exile", {"name": traveler["name"]})
        self.current = None
        self.save()


    def _end_day_execution(self) -> None:
        """天黑时结算处决:今天通过(待处决)的座位提名中票数最多者被处决;平票则无人被处决。"""
        todays = [n for n in self.nominations
                  if n["day"] == self.day_no and n["passed"] and isinstance(n["nominee"], int)]
        if not todays:
            return
        max_votes = max(len(n["votes"]) for n in todays)
        winners = [n for n in todays if len(n["votes"]) == max_votes]
        if len(winners) != 1:
            return  # 平票:无人被处决
        nominee = winners[0]["nominee"]
        state = self.seat_state(nominee)
        if state.character_id and state.alive:
            state.alive = False
            state.public_alive = False
            state.died_day = self.day_no  # 白天结束时的处决:当天当场公开
            state.died_at = f"day:{self.day_no}:execution"
        winners[0]["executed"] = True
        self._log(nominee, "execution", {"votes": max_votes})
