"""Build data/rune_cube.json: the cube's rune recipes and the resource tabs' slots, from the installed game's
cubemain.txt and bankexpansionlayouthd.json ("cubed, aim to 80 or lower", the player, 2026-10-18; recipes from the
game's data, never from memory).

    uv run --offline python -m inventory_tracking.macros.build_rune_cube <install>

A recipe: an enabled, not ladder-only row (the player is Non-Ladder) turning a rune with a quantity into the next, plus
any gem it takes ("loop should use required gems + runes", 2026-10-18). Slots and the convert button are in the left
panel's layout units.
"""

import json
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

from inventory_tracking.combat.mechanics.tables import rows
from inventory_tracking.items.metadata import metadata
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'rune_cube.json'
LAYOUT = 'data/global/ui/layouts/bankexpansionlayouthd.json'
RUNE = re.compile(r'^r\d\d$')


def classes() -> dict[str, int]:
    """Item code -> class, by the items' metadata (the decoder's)."""
    return {base['code']: int(cid) for cid, base in metadata()['bases'].items() if base.get('code')}


def recipes(table: Iterable[Mapping[str, str]], by_code: Mapping[str, int]) -> dict[str, dict]:
    """Rune-to-rune recipes by input rune class: output class, rune count, extra gem classes, description."""
    found: dict[str, dict] = {}
    for row in table:
        if row.get('enabled') != '1' or row.get('firstLadderSeason'):
            continue
        first = row.get('input 1', '').strip('"').split(',')
        output = row.get('output', '').strip('"')
        if not (RUNE.match(first[0]) and RUNE.match(output)):
            continue
        qty = next((int(part.removeprefix('qty=')) for part in first[1:] if part.startswith('qty=')), 1)
        others = [row.get(f'input {n}', '').strip('"') for n in range(2, 8)]
        if any(',' in other for other in others if other):
            continue  # an input with qualifiers: not a plain item
        gems = [by_code[other] for other in others if other]
        found[str(by_code[first[0]])] = {
            'into': by_code[output],
            'runes': qty,
            'gems': gems,
            'description': row.get('description', ''),
        }
    return found


def _strip(text: str) -> str:
    """The layout file's JSON without its comments and trailing commas."""
    text = re.sub(r'//[^\n]*', '', text)
    return re.sub(r',(\s*[}\]])', r'\1', text)


def layout(text: str, by_code: Mapping[str, int]) -> tuple[dict[str, list[int]], list[int]]:
    """The Runes and Gems tabs' slot rects (x, y, width, height) by class, and the convert button's corner."""
    tree = json.loads(_strip(text))
    slots: dict[str, list[int]] = {}
    convert: list[int] = []

    def walk(node: dict, path: str) -> None:
        nonlocal convert
        here = f'{path}/{node.get("name", "")}'
        fields = node.get('fields', {})
        rect = fields.get('rect', {})
        tabs = ('/advancedstash_runes/', '/advancedstash_gems/')
        if any(tab in here for tab in tabs) and node.get('type') == 'AdvancedStashSlotWidget':
            slots[str(by_code[fields['itemCode']])] = [rect['x'], rect['y'], rect['width'], rect['height']]
        if here.endswith('/advancedstash_horadriccube/convert'):
            convert = [rect['x'], rect['y']]
        for child in node.get('children', []):
            walk(child, here)

    walk(tree, '')
    return slots, convert


def main() -> None:
    game = GameFiles(Path(sys.argv[1]))
    by_code = classes()
    slots, convert = layout(game.read(LAYOUT).decode('utf-8'), by_code)
    data = {
        'source': 'the installed game: data/global/excel/cubemain.txt (enabled, not ladder-only rows, a rune into the '
        f"next), {LAYOUT} (the Runes and Gems tabs' slots and the cube's convert button); read 2026-10-18",
        'recipes': recipes(rows(game, 'cubemain'), by_code),
        'slots': slots,
        'convert': convert,
    }
    OUTPUT.write_text(json.dumps(data, indent=1) + '\n')
    print(f'{len(data["recipes"])} recipes, {len(slots)} slots -> {OUTPUT}')


if __name__ == '__main__':
    main()
