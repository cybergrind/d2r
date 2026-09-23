import json
from pathlib import Path

import pytest

from pricing.knowledge.definitions import build_definitions


def test_every_local_unique_and_set_preserves_complete_source_information():
    root = Path(__file__).parents[3]
    if not (root / 'third-parties/d2data/json/sets.json').exists():
        pytest.skip('Optional pinned game-data checkout unavailable')
    document = build_definitions(root)
    sets = json.loads((root / 'third-parties/d2data/json/sets.json').read_text())
    for rarity, filename in [('unique', 'uniqueitems'), ('set', 'setitems')]:
        source = json.loads((root / f'pricing/raw/d2data/{filename}.json').read_text())
        actual = [r for r in document['rows'] if r['rarity'] == rarity]
        assert len(actual) == len(source)
        by_id = {r['table_id']: r for r in actual}
        assert len(by_id) == len(source)
        for record in source.values():
            row = by_id[record['*ID']]
            assert row['game_definition'] == record
            assert row['base_definition'] or not row['base_codes']
            if rarity == 'set':
                assert row['set_definition'] == sets[record['set']]
