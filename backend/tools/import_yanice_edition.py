"""One-time conversion of a publicly viewable Yanice script page to BOTC JSON.

Usage: python tools/import_yanice_edition.py URL OUTPUT
The output is vendored for offline use; this script never runs on the server.
"""

import html
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen


def convert(page: str) -> list[dict]:
    pattern = re.compile(
        r'<div class="item"\s+data-name="([^"]+)"\s+data-team="([^"]+)".*?'
        r'<img src="([^"]+)".*?<p>\s*<b>.*?</b><br>\s*(.*?)\s*</p>',
        re.S,
    )
    roles = []
    for name, team, icon, ability in pattern.findall(page):
        icon_key = icon.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        roles.append({
            'id': icon_key,
            'name': html.unescape(name),
            'team': team,
            'ability': html.unescape(re.sub(r'<[^>]+>', '', ability)).strip(),
            'icon': icon,
        })
    if len(roles) < 20:
        raise ValueError(f'Expected a full character sheet, found {len(roles)} roles')
    for kind, marker in (('firstNight', 'left-fixed'), ('otherNight', 'right-fixed')):
        section = page.split(f'<div class="{marker}">', 1)[1].split('</div>\n\n    <', 1)[0]
        icons = re.findall(r'<img src="([^"]+)"', section)
        position = 0
        for icon in icons:
            if '/script/static/img/' in icon:
                continue
            position += 1
            for role in roles:
                if role['icon'] == icon:
                    role[kind] = position
                    break
    return [{"id": "_meta", "name": "开心快乐猴", "author": "开心猴·祥东 & 开心猴·小赤"}, *roles]


if __name__ == '__main__':
    source, output = sys.argv[1:]
    with urlopen(source, timeout=20) as response:
        page = response.read().decode('utf-8')
    Path(output).write_text(json.dumps(convert(page), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
