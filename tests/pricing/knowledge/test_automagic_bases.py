import json
from pathlib import Path

from pricing.knowledge.definitions import build_definitions


def test_automagic_requires_bases_native_group_not_only_type_ancestry():
    root = Path(__file__).parents[3]
    definitions = build_definitions(root)
    bases = {}
    for table in ('weapons', 'armor', 'misc'):
        bases.update(json.loads((root / f'pricing/raw/d2data/{table}.json').read_text()))
    automagic = [r for r in definitions['rows'] if r.get('affix_table') == 'auto']
    assert automagic
    raw = root / 'third-parties/d2data/json'
    ordinal_keys = sorted(json.loads((raw / 'automagic.json').read_text()), key=int)
    offset = sum(len(json.loads((raw / name).read_text())) for name in ('magicsuffix.json', 'magicprefix.json'))
    for row in automagic:
        assert row['table_id'] == offset + ordinal_keys.index(row['source']['record_key']) + 1
        group = row['game_definition']['group']
        assert group > 0
        assert all(bases[code].get('auto prefix') == group for code in row['base_codes']), row['name']
    orb = next(code for code, row in bases.items() if row.get('name') == 'Demon Heart')
    assert any(orb in row['base_codes'] for row in automagic)
