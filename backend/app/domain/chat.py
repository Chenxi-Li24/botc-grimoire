"""Private chat lifecycle and participant-specific projections."""

from __future__ import annotations

class ChatMixin:

    CHAT_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c", "#3498db",
                   "#9b59b6", "#e91e63", "#00bcd4", "#8bc34a"]


    def _chat_who_name(self, who) -> str:
        if who == "st":
            return "说书人"
        if isinstance(who, str):
            t = next((x for x in self.travelers if x["id"] == who), None)
            return t["name"] if t else who
        p = self.seats.get(who)
        return p.name if p else f"{who}号"


    def _chat_who_ok(self, who) -> bool:
        """who 可以是座位(已入座)、旅行者 id 或说书人 "st"。"""
        if who == "st":
            return True
        if isinstance(who, str):
            return any(t["id"] == who and not t["exiled"] for t in self.travelers)
        return isinstance(who, int) and who in self.seats


    def _active_chat(self, cid: int) -> dict:
        c = next((x for x in self.chats if x["id"] == cid and not x["closed"]), None)
        if c is None:
            raise ValueError("私聊不存在或已关闭")
        return c


    def _chat_of(self, who) -> dict | None:
        return next((c for c in self.chats if not c["closed"] and who in c["members"]), None)


    def _chat_guard(self) -> None:
        if self.phase != "day":
            raise ValueError("白天才能私聊")
        if self.winner:
            raise ValueError("本局已结束")
        if self.day_stage != "talk":
            raise ValueError("提名阶段暂停私聊")


    def create_chat(self, owner, invitees: list) -> dict:
        self._chat_guard()
        if not self._chat_who_ok(owner):
            raise ValueError("发起者需已入座、是旅行者或说书人")
        if self._chat_of(owner):
            raise ValueError("你已在私聊中,先退出再发起")
        if not isinstance(invitees, list) or not invitees:
            raise ValueError("需邀请至少一名玩家")
        inv: dict = {}
        for w in invitees:
            if not self._chat_who_ok(w):
                raise ValueError("邀请对象无效")
            if w == owner:
                raise ValueError("不能邀请自己")
            if self._chat_of(w):
                raise ValueError(f"{self._chat_who_name(w)} 已在别的私聊中")
            inv[w] = None
        used = {c["color"] for c in self.chats if not c["closed"]}
        color = next((c for c in self.CHAT_COLORS if c not in used), self.CHAT_COLORS[len(self.chats) % len(self.CHAT_COLORS)])
        chat = {"id": len(self.chats) + 1, "owner": owner, "color": color,
                "members": {owner: 0}, "invites": inv, "join_requests": {},
                "messages": [], "closed": False}
        self.chats.append(chat)
        self.save()
        return chat


    def respond_invite(self, who, cid: int, accept: bool) -> None:
        self._chat_guard()
        chat = self._active_chat(cid)
        if who not in chat["invites"]:
            raise ValueError("你没有该私聊的邀请")
        chat["invites"].pop(who)
        if accept:
            if self._chat_of(who):
                raise ValueError("你已在别的私聊中")
            chat["members"][who] = self._next_chat_seq(chat)  # 后加入者看不到之前的历史
        self.save()


    def request_join(self, who, cid: int) -> None:
        self._chat_guard()
        chat = self._active_chat(cid)
        if not self._chat_who_ok(who):
            raise ValueError("需已入座或为旅行者/说书人")
        if who in chat["members"] or who in chat["invites"]:
            raise ValueError("你已是成员或已有邀请")
        if self._chat_of(who):
            raise ValueError("你已在别的私聊中")
        chat["join_requests"][who] = None
        self.save()


    def invite_to_chat(self, owner, cid: int, invitees: list) -> None:
        """私聊进行中,发起者邀请更多玩家加入(新成员同样看不到历史)。"""
        self._chat_guard()
        chat = self._active_chat(cid)
        if chat["owner"] != owner:
            raise ValueError("只有发起者能邀请新成员")
        if not isinstance(invitees, list) or not invitees:
            raise ValueError("需邀请至少一名玩家")
        for w in invitees:
            if not self._chat_who_ok(w):
                raise ValueError("邀请对象无效")
            if w in chat["members"] or w in chat["invites"]:
                continue  # 已在群里或已有邀请,跳过
            if self._chat_of(w):
                raise ValueError(f"{self._chat_who_name(w)} 已在别的私聊中")
            chat["invites"][w] = None
        self.save()


    def approve_request(self, owner, cid: int, who, approve: bool) -> None:
        self._chat_guard()
        chat = self._active_chat(cid)
        if chat["owner"] != owner:
            raise ValueError("只有发起者能审批加入申请")
        if who not in chat["join_requests"]:
            raise ValueError("没有该玩家的申请")
        chat["join_requests"].pop(who)
        if approve:
            if self._chat_of(who):
                raise ValueError(f"{self._chat_who_name(who)} 已在别的私聊中")
            chat["members"][who] = self._next_chat_seq(chat)
        self.save()


    def _next_chat_seq(self, chat: dict) -> int:
        return chat["messages"][-1]["seq"] + 1 if chat["messages"] else 1


    def send_message(self, who, cid: int, text: str) -> None:
        self._chat_guard()
        chat = self._active_chat(cid)
        if who not in chat["members"]:
            raise ValueError("你不是该私聊的成员")
        text = (text or "").strip()
        if not text:
            raise ValueError("消息不能为空")
        if len(text) > 500:
            raise ValueError("消息过长(500 字内)")
        self.chat_seq += 1
        chat["messages"].append({"seq": self.chat_seq, "from": who,
                                 "name": self._chat_who_name(who), "text": text[:500]})
        self.save()


    def leave_chat(self, who, cid: int) -> None:
        chat = self._active_chat(cid)
        if who not in chat["members"]:
            raise ValueError("你不是该私聊的成员")
        chat["members"].pop(who)
        if chat["owner"] == who:  # 发起者退出 → 群解散
            chat["closed"] = True
        self.save()


    def close_chat(self, who, cid: int) -> None:
        chat = self._active_chat(cid)
        if chat["owner"] != who and who != "st":
            raise ValueError("只有发起者或说书人能关闭")
        chat["closed"] = True
        self.save()


    def recall_chats(self) -> None:
        """说书人召回:关闭全部私聊(天黑自动执行)。"""
        for c in self.chats:
            c["closed"] = True
        self.save()


    def _chat_st_view(self, c: dict) -> dict:
        """说书人侧的私聊视图:members/invites/join_requests 转数组并带名字(前端按数组渲染)。"""
        return {
            "id": c["id"], "owner": c["owner"], "color": c["color"], "closed": c["closed"],
            "members": [{"who": str(w), "name": self._chat_who_name(w)} for w in c["members"]],
            "invites": [{"who": str(w), "name": self._chat_who_name(w)} for w in c["invites"]],
            "join_requests": [{"who": str(w), "name": self._chat_who_name(w)}
                              for w in c["join_requests"]],
            "messages": c["messages"],
        }


    def chat_view_for(self, who) -> dict | None:
        """该玩家(或说书人)的私聊视图:自己的群(过滤历史)、邀请、公开列表(气泡)。"""
        if self.phase != "day" or self.winner:
            return None
        my = self._chat_of(who)
        view = {"who": str(who), "my_chat": None, "invites": [], "chats_public": []}
        if my is not None:
            joined = my["members"][who]
            view["my_chat"] = {
                "id": my["id"], "color": my["color"], "owner": my["owner"],
                "is_owner": my["owner"] == who,
                "members": [{"who": str(w), "name": self._chat_who_name(w)}
                            for w in my["members"]],
                "requests": [{"who": str(w), "name": self._chat_who_name(w)}
                             for w in my["join_requests"]] if my["owner"] == who else [],
                "messages": [m for m in my["messages"] if m["seq"] >= joined],
            }
        for c in self.chats:
            if c["closed"]:
                continue
            if who in c["invites"]:
                view["invites"].append({"id": c["id"], "color": c["color"],
                                        "owner_name": self._chat_who_name(c["owner"])})
            view["chats_public"].append({
                "id": c["id"], "color": c["color"], "owner": str(c["owner"]),
                "members": [{"who": str(w), "name": self._chat_who_name(w)}
                            for w in c["members"]],
                "requested": who in c["join_requests"],
            })
        return view
