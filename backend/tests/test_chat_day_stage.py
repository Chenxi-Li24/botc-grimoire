import copy
import unittest
from types import SimpleNamespace

from app.domain.chat import ChatMixin
from app.domain.nomination import NominationMixin


class ChatDayHarness(ChatMixin, NominationMixin):
    def __init__(self):
        self.phase = "day"
        self.day_stage = "talk"
        self.winner = None
        self.current = None
        self.seats = {seat: SimpleNamespace(name=f"{seat}号") for seat in range(1, 5)}
        self.travelers = []
        self.chats = []
        self.chat_seq = 0

    def save(self):
        pass


class ChatDayStageTest(unittest.TestCase):
    def setUp(self):
        self.game = ChatDayHarness()
        self.chat = self.game.create_chat(1, [2, 4])
        self.cid = self.chat["id"]
        self.game.respond_invite(2, self.cid, True)
        self.game.request_join(3, self.cid)
        self.game.send_message(1, self.cid, "提名前的消息")

    def test_nomination_pauses_chat_mutations_without_changing_existing_chat(self):
        self.game.set_day_stage("nom")
        original = copy.deepcopy(self.chat)
        operations = [
            lambda: self.game.create_chat(3, [4]),
            lambda: self.game.respond_invite(4, self.cid, True),
            lambda: self.game.request_join(3, self.cid),
            lambda: self.game.invite_to_chat(1, self.cid, [3]),
            lambda: self.game.approve_request(1, self.cid, 3, True),
            lambda: self.game.send_message(1, self.cid, "提名中的消息"),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ValueError, "提名阶段"):
                    operation()

        self.assertEqual(self.chat, original)
        self.assertEqual(self.game.chat_view_for(1)["my_chat"]["messages"][0]["text"], "提名前的消息")

    def test_talk_stage_resumes_the_same_chat_and_message_history(self):
        self.game.set_day_stage("nom")
        self.game.set_day_stage("talk")
        self.game.send_message(2, self.cid, "恢复后的消息")

        view = self.game.chat_view_for(1)["my_chat"]
        self.assertEqual(view["id"], self.cid)
        self.assertEqual([message["text"] for message in view["messages"]], ["提名前的消息", "恢复后的消息"])


if __name__ == "__main__":
    unittest.main()
