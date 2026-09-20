import unittest

from app.roles import SCRIPT_PACKS
from app.save_codec import decode_save, encode_save


class SaveCodecTest(unittest.TestCase):
    def test_legacy_save_migrates_roles_to_unclaimed_seats(self):
        state = decode_save({
            "player_count": 3,
            "phase": "night",
            "night_no": 2,
            "seat_roles": {"1": "chef", "2": "imp"},
            "players": {},
        }, SCRIPT_PACKS["trouble-brewing"])
        self.assertEqual(state.seat(1).character_id, "chef")
        self.assertIsNone(state.seat(1).claimed_by)
        self.assertEqual(encode_save(state)["schema_version"], 2)

    def test_v2_round_trip_preserves_effect_and_event_collections(self):
        state = decode_save({
            "schema_version": 2,
            "player_count": 2,
            "players": {},
            "seats": {
                "1": {"seat": 1, "character_id": "chef"},
                "2": {"seat": 2, "character_id": "imp", "alignment": "evil"},
            },
        }, SCRIPT_PACKS["trouble-brewing"])
        payload = encode_save(state)
        restored = decode_save(payload, SCRIPT_PACKS["trouble-brewing"])
        self.assertEqual(restored.seat(2).character_id, "imp")
        self.assertEqual(restored.seat(2).alignment, "evil")


if __name__ == "__main__":
    unittest.main()
