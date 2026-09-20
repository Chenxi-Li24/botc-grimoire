"""Simplified-Chinese display data kept separate from stable character ids."""

OFFICIAL_SCRIPT_NAMES = {
    "trouble-brewing": "暗流涌动",
    "bad-moon-rising": "黯月初升",
    "sects-and-violets": "梦殒春宵",
}

# Confirmed official mainland/community-standard labels for the official editions.
# Unlisted entries retain their source label until their wording is audited.
OFFICIAL_CHARACTER_NAMES = {
    "virgin": "贞洁者",
    "slayer": "猎手",
    "mayor": "镇长",
    "scarletwoman": "红唇女郎",
    "innkeeper": "旅店老板",
    "gossip": "造谣者",
    "courtier": "侍臣",
    "fool": "弄臣",
    "goon": "莽夫",
    "zombuul": "僵怖",
    "shabaloth": "沙巴洛斯",
    "flowergirl": "卖花女孩",
    "towncrier": "城镇公告员",
    "seamstress": "女裁缝",
    "eviltwin": "镜像双子",
    "nodashii": "诺-达鲺",
    "vortox": "涡流",
}


def build_locale(module, orders: dict[str, list[dict]]) -> dict[str, str]:
    """Build one pack-local catalog so community wording cannot alter official data."""
    script_id = module.SCRIPT_ID
    official = script_id in OFFICIAL_SCRIPT_NAMES
    locale = {
        f"script.{script_id}.name": OFFICIAL_SCRIPT_NAMES.get(script_id, module.NAME),
    }
    for role in module.ROLES:
        role_id = role["id"]
        locale[f"character.{role_id}.name"] = (
            OFFICIAL_CHARACTER_NAMES.get(role_id, role["name"])
            if official else role["name"]
        )
        locale[f"character.{role_id}.ability"] = role["ability"]
    for kind in ("first", "other"):
        for step in orders.get(kind, ()):
            key = step["key"]
            locale[f"night.{kind}.{key}.name"] = (
                OFFICIAL_CHARACTER_NAMES.get(key, step["name"])
                if official else step["name"]
            )
            locale[f"night.{kind}.{key}.reminder"] = step["hint"]
    return locale
