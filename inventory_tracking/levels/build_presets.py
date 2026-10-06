"""Regenerate levels/data/level_presets.json from the d2data checkout (third-parties/).

Runtime code reads only the bundled table; the git-ignored checkout is a build input.
Run: uv run --offline python -m inventory_tracking.levels.build_presets
"""

import json
from pathlib import Path

from inventory_tracking.reports import publish


D2DATA = Path('third-parties/d2data')
OUTPUT = Path(__file__).parent / 'data' / 'level_presets.json'


def build(d2data: Path) -> dict:
    presets = json.loads((d2data / 'json' / 'lvlprest.json').read_text())
    levels = json.loads((d2data / 'json' / 'levels.json').read_text())
    commit = next(
        repo['commit']
        for repo in json.loads((d2data.parent / 'repos.json').read_text())['repositories']
        if repo['directory'] == d2data.name
    )
    return {
        'source': f'blizzhackers/d2data {commit[:12]} json/lvlprest.json, json/levels.json',
        'presets': {str(p['Def']): p['Name'] for p in presets.values() if 'Def' in p and 'Name' in p},
        # LevelName is the in-game name ("Halls of Death's Calling"); Name is internal ("Act 5 - Temple 2").
        'levels': {str(v['Id']): v.get('LevelName') or v['Name'] for v in levels.values() if 'Id' in v and 'Name' in v},
        # *StringName is what the game shows today ("Halls of Pain", "Crystalline Passage").
        'names': {str(v['Id']): v['*StringName'] for v in levels.values() if v.get('Id') and v.get('*StringName')},
        # Vis0..7: the level behind each warp slot (levels/ds1.py), 0 = none.
        'links': {
            str(v['Id']): [v.get(f'Vis{slot}', 0) for slot in range(8)]
            for v in levels.values()
            if v.get('Id') and any(v.get(f'Vis{slot}') for slot in range(8))
        },
    }


def main():
    publish(OUTPUT, build(D2DATA))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
