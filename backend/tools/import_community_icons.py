"""One-time, source-linked role icon conversion for bundled community editions.

Run from backend: .venv/bin/python tools/import_community_icons.py
Requires Pillow. Existing icons are never overwritten.
"""

import io
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.catalog.community import NAME_IDS, SOURCE_DIR
from app.scripts import SCRIPT_PACKS


ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "frontend" / "public" / "role-icons"
MANIFEST = ROOT / "frontend" / "src" / "presentation" / "role-icon-ids.json"
SOURCE_FILES = [SOURCE_DIR / f"{script_id}.json" for script_id in (
    "huyanluanyu", "sunaomituan", "yebankuanghuan", "kaixinkuailehou")]
SOURCE_FILES.append(ROOT / "backend" / "tools" / "sources" / "museum" / "892280963319463958.json")
KNOWN_NAMES = {pack.locale[character.name_key]: character.id
               for pack in SCRIPT_PACKS.values() for character in pack.characters}
EXTRA_URLS = {
    role_id: f"https://oss.gstonegames.com/data_file/clocktower/web/icons/{role_id}.png"
    for role_id in ("goblin", "leviathan")
}


def candidates():
    items = dict(EXTRA_URLS)
    for path in SOURCE_FILES:
        for role in json.loads(path.read_text(encoding="utf-8")):
            if role.get("team") not in {"townsfolk", "outsider", "minion", "demon"}:
                continue
            role_id = NAME_IDS.get(role.get("name")) or KNOWN_NAMES.get(role.get("name"))
            url = role.get("image") or role.get("icon")
            if role_id and url:
                items.setdefault(role_id, url)
    return items


def main():
    existing = set(json.loads(MANIFEST.read_text(encoding="utf-8")))
    for role_id, url in candidates().items():
        if role_id in existing:
            continue
        try:
            parsed = urlsplit(url)
            request = Request(url, headers={"User-Agent": "BOTC-Grimoire-asset-import/1.0",
                                            "Referer": f"{parsed.scheme}://{parsed.netloc}/"})
            try:
                with urlopen(request, timeout=15) as response:
                    raw = response.read(3_000_001)
            except Exception:
                raw = subprocess.run(
                    ["curl", "--fail", "--silent", "--show-error", "--location",
                     "--referer", f"{parsed.scheme}://{parsed.netloc}/", url],
                    capture_output=True, check=True, timeout=20,
                ).stdout
            if len(raw) > 3_000_000:
                raise ValueError("oversized image")
            image = Image.open(io.BytesIO(raw)).convert("RGBA")
            image.thumbnail((128, 128))
            image.save(ICONS / f"{role_id}.webp", "WEBP", quality=86)
            existing.add(role_id)
            print(role_id, "imported")
        except Exception as exc:
            print(role_id, "skipped:", exc)
    MANIFEST.write_text(json.dumps(sorted(existing), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
