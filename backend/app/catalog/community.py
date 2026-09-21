"""Offline, source-backed community script loader.

Source JSON is deliberately retained alongside this adapter: editions can be
audited or replaced without copying role definitions into another Python file.
Unknown mechanics remain explicit storyteller-managed steps.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from .compiler import compile_script_pack
from .zh_cn import OFFICIAL_CHARACTER_NAMES


SOURCE_DIR = Path(__file__).with_name("source_json")
SOURCES = {
    "qieqiesiyu": ("窃窃私语", "Laissez un Faire", 5),
    "yebankuanghuan": ("夜半狂欢", "Midnight Oasis", 7),
    "sunaomituan": ("宿脑谜团", "A Lleech of Distrust", 5),
    "huyanluanyu": ("胡言乱语", "胡言乱语", 7),
    "kaixinkuailehou": ("开心快乐猴", "开心快乐猴", 7),
}

# A community JSON may use an arbitrary icon key instead of a game character id.
# These mappings are reviewed by displayed character name, not by its asset URL.
NAME_IDS = {
    **{name: role_id for role_id, name in OFFICIAL_CHARACTER_NAMES.items()},
    "小精灵": "pixie", "阴阳师": "custom-yinyangshi", "变脸师": "custom-bianlianshi",
    "郎中": "custom-langzhong", "村夫": "villageidiot", "女祭司": "highpriestess",
    "养蛊人": "custom-yangguren", "典狱长": "custom-dianyuzhang",
    "牙噶巴卜": "yaggababble", "魔像": "golem", "落难少女": "damsel",
    "工程师": "engineer", "巡山人": "huntsman", "农夫": "farmer",
    "罂粟种植者": "poppygrower", "无神论者": "atheist", "灵言师": "mezepheles",
    "精神病患者": "psychopath", "哈迪寂亚": "hadikhia", "痢蛭": "lleech",
    "杂耍艺人": "juggler", "魔鬼代言人": "devilsadvocate",
    "提线木偶": "marionette",
    "守夜人": "nightwatchman", "告密者": "snitch", "鹰身女妖": "harpy",
    "刀客": "custom-daoke", "锦衣卫": "custom-jinyiwei", "悟道者": "custom-wudaozhe",
    "限": "custom-xian", "开心猴": "custom-kaixinhou",
    "地精": "goblin", "利维坦": "leviathan",
}

EXPERIMENTAL_ROLES = {
    "goblin": {"id": "goblin", "name": "地精", "en": "Goblin", "team": "minion",
               "ability": "若你在被提名时公开宣称自己是地精，并在当天被处决，你的阵营获胜。"},
    "leviathan": {"id": "leviathan", "name": "利维坦", "en": "Leviathan", "team": "demon",
                  "ability": "若超过一名善良玩家被处决，邪恶阵营获胜。所有玩家知道利维坦在场。第五天结束后，邪恶阵营获胜。"},
}

DUSK = {"key": "dusk", "name": "天黑", "hint": "所有玩家闭眼"}
DAWN = {"key": "dawn", "name": "天亮", "hint": "所有玩家睁眼；宣告昨夜死者，进入白天"}
MINIONINFO = {"key": "minioninfo", "name": "爪牙会面", "hint": "唤醒爪牙并指出恶魔；若罂粟种植者在场，按其规则处理"}
DEMONINFO = {"key": "demoninfo", "name": "恶魔会面", "hint": "指出爪牙并展示三个不在场善良角色；按当前剧本特殊规则调整"}


def _known_roles(existing_packs) -> tuple[dict[str, dict], dict[str, dict]]:
    by_id, by_name = {}, {}
    for pack in existing_packs.values():
        for character in pack.characters:
            role = {
                "id": character.id,
                "name": pack.locale[character.name_key],
                "en": character.english_name,
                "team": character.team,
                "ability": pack.locale[character.ability_key],
            }
            by_id.setdefault(character.id, role)
            by_name.setdefault(role["name"], role)
    return by_id, by_name


def _source_roles(script_id: str, items: list[dict], known_by_id: dict, known_by_name: dict) -> list[dict]:
    roles = []
    for source in items:
        source_id = source.get("id", "")
        known_source = known_by_id.get(source_id) or EXPERIMENTAL_ROLES.get(source_id, {})
        team = source.get("team") or known_source.get("team")
        if team not in {"townsfolk", "outsider", "minion", "demon"}:
            continue  # metadata, travelers, Fabled, jinxes are not in the bag
        name = source.get("name") or known_source.get("name")
        role_id = (NAME_IDS.get(name) or known_by_name.get(name, {}).get("id")
                   or (source_id if source_id in known_by_id or source_id in EXPERIMENTAL_ROLES else None))
        if not role_id:
            raise ValueError(f"{script_id}: unmapped character {name!r} ({source_id})")
        known = known_by_id.get(role_id) or EXPERIMENTAL_ROLES.get(role_id, {})
        ability = source.get("ability") or known.get("ability")
        if not name or not ability:
            raise ValueError(f"{script_id}: missing name or ability for {role_id}")
        roles.append({"id": role_id, "name": name, "en": source.get("name_eng") or known.get("en", name),
                      "team": team, "ability": ability,
                      "firstNight": source.get("firstNight"), "otherNight": source.get("otherNight"),
                      "firstNightReminder": source.get("firstNightReminder", ""),
                      "otherNightReminder": source.get("otherNightReminder", "")})
    return roles


def _night_order(roles: list[dict], official_sheet: dict | None = None) -> dict[str, list[dict]]:
    result = {}
    for kind, field in (("first", "firstNight"), ("other", "otherNight")):
        timed = []
        for role in roles:
            position = role.get(field)
            if not position and official_sheet:
                official_key = role["id"].replace("fang-gu", "fanggu")
                sheet = official_sheet[f"{kind}Night"]
                if official_key in sheet:
                    position = sheet.index(official_key) + 1
            if isinstance(position, (float, int)) and position > 0:
                hint = role[f"{kind}NightReminder"] or role["ability"]
                timed.append((float(position), {"key": role["id"], "name": role["name"], "hint": hint}))
        timed.sort(key=lambda item: item[0])
        steps = [DUSK]
        if kind == "first":
            # Poppy Grower and some custom effects act before evil introduction.
            before_meeting = [step for position, step in timed if position < 5 and step["key"] != "lunatic"]
            remaining = [step for position, step in timed if position >= 5 and step["key"] != "lunatic"]
            steps.extend(before_meeting)
            steps.append(MINIONINFO)
            lunatic = next((step for _, step in timed if step["key"] == "lunatic"), None)
            if lunatic:
                steps.append(lunatic)
            steps.append(DEMONINFO)
            steps.extend(remaining)
        else:
            steps.extend(step for _, step in timed)
            keys = [step["key"] for step in steps]
            if "lunatic" in keys:
                first_demon = next((i for i, step in enumerate(steps)
                                    if any(role["id"] == step["key"] and role["team"] == "demon"
                                           for role in roles)), None)
                if first_demon is not None and keys.index("lunatic") > first_demon:
                    lunatic = steps.pop(keys.index("lunatic"))
                    steps.insert(first_demon, lunatic)
        steps.append(DAWN)
        result[kind] = steps
    return result


def compile_community_packs(existing_packs, night_order):
    known_by_id, known_by_name = _known_roles(existing_packs)
    official_sheet = json.loads((Path(__file__).resolve().parents[2] / "tools" / "sources" / "nightsheet.json").read_text(encoding="utf-8"))
    packs = {}
    for script_id, (name, english, min_players) in SOURCES.items():
        items = json.loads((SOURCE_DIR / f"{script_id}.json").read_text(encoding="utf-8"))
        roles = _source_roles(script_id, items, known_by_id, known_by_name)
        use_sheet = official_sheet if script_id == "qieqiesiyu" else None
        order = _night_order(roles, use_sheet)
        night_order[script_id] = order
        module = SimpleNamespace(SCRIPT_ID=script_id, NAME=name, EN=english,
                                 MIN_PLAYERS=min_players, ADJUST_ROLES=(), ROLES=roles,
                                 NIGHT_ACTIONS={})
        packs[script_id] = compile_script_pack(module, order)
    return packs
