import unittest

from app.scripts import SCRIPTS, SCRIPT_PACKS
from app.night_order import NIGHT_ORDER


class CommunityCatalogTests(unittest.TestCase):
    def test_source_backed_scripts_have_unique_roles_and_night_steps(self):
        for script_id, minimum in (
            ("qieqiesiyu", 11),
            ("yebankuanghuan", 23),
            ("sunaomituan", 11),
            ("huyanluanyu", 25),
            ("kaixinkuailehou", 22),
        ):
            with self.subTest(script_id=script_id):
                pack = SCRIPT_PACKS[script_id]
                self.assertGreaterEqual(len(pack.characters), minimum)
                ids = {role.id for role in pack.characters}
                self.assertEqual(len(ids), len(pack.characters))
                self.assertEqual(ids, {r["id"] for r in SCRIPTS[script_id]["roles"]})
                for kind in ("first", "other"):
                    steps = NIGHT_ORDER[script_id][kind]
                    self.assertEqual(steps[0]["key"], "dusk")
                    self.assertEqual(steps[-1]["key"], "dawn")
                    self.assertTrue(all(step["key"] in ids | {"dusk", "dawn", "minioninfo", "demoninfo"} for step in steps))

    def test_lunatic_precedes_demon_action_in_each_night(self):
        for script_id in ("qieqiesiyu", "sunaomituan", "huyanluanyu"):
            with self.subTest(script_id=script_id):
                roles = {r["id"]: r for r in SCRIPTS[script_id]["roles"]}
                for kind in ("first", "other"):
                    keys = [step["key"] for step in NIGHT_ORDER[script_id][kind]]
                    if "lunatic" in keys:
                        for key in keys:
                            if key in roles and roles[key]["team"] == "demon":
                                self.assertLess(keys.index("lunatic"), keys.index(key))


if __name__ == "__main__":
    unittest.main()
