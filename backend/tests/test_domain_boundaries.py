import unittest

from app.domain.chat import ChatMixin
from app.domain.legacy_night import LegacyNightMixin
from app.domain.lobby import LobbyMixin
from app.domain.nomination import NominationMixin
from app.domain.review import ReviewMixin
from app.domain.seat_admin import SeatAdministrationMixin
from app.game import GameManager


class DomainBoundaryTest(unittest.TestCase):
    def test_game_manager_composes_domain_methods_without_reimplementing_them(self):
        expected = {
            ChatMixin: "create_chat",
            LegacyNightMixin: "submit_night_choice_seat",
            LobbyMixin: "assign_manual",
            NominationMixin: "resolve_nomination",
            ReviewMixin: "build_review",
            SeatAdministrationMixin: "set_marker",
        }
        for mixin, method in expected.items():
            self.assertTrue(issubclass(GameManager, mixin))
            self.assertIn(method, mixin.__dict__)
            self.assertNotIn(method, GameManager.__dict__)


if __name__ == "__main__":
    unittest.main()
