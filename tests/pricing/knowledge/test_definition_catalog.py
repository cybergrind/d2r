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
    ordinary_sets = json.loads((root / 'third-parties/d2data/json/base/sets.json').read_text())
    ordinary_unique_ids = {12, 51, 54, 59, 62, 80, 101, 121, 154}
    ordinary_set_names = {'Angelic Halo', 'Angelic Wings', 'Angelic Mantle', 'Angelic Sickle'}
    for rarity, filename in [('unique', 'uniqueitems'), ('set', 'setitems')]:
        source = json.loads((root / f'pricing/raw/d2data/{filename}.json').read_text())
        ordinary = json.loads((root / f'third-parties/d2data/json/base/{filename}.json').read_text())
        ordinary_by_id = {record['*ID']: record for record in ordinary.values()}
        actual = [r for r in document['rows'] if r['rarity'] == rarity]
        assert len(actual) == len(source)
        by_id = {r['table_id']: r for r in actual}
        assert len(by_id) == len(source)
        for record in source.values():
            row = by_id[record['*ID']]
            non_ladder_primary = (rarity == 'unique' and record['*ID'] in ordinary_unique_ids) or (
                rarity == 'set' and record['index'] in ordinary_set_names
            )
            if non_ladder_primary:
                assert row['game_definition'] == ordinary_by_id[record['*ID']]
                assert row['ladder_definition']['game_definition'] == record
                assert row['mode_review']['scope'] == 'softcore_non_ladder'
            else:
                assert row['game_definition'] == record
            assert row['base_definition'] or not row['base_codes']
            if rarity == 'set':
                assert row['set_definition'] == (ordinary_sets if non_ladder_primary else sets)[record['set']]
                if non_ladder_primary:
                    assert row['ladder_definition']['set_definition'] == sets[record['set']]

    names = {row['game_definition']['index']: row['name'] for row in document['rows'] if row['rarity'] == 'unique'}
    assert names['Unique Warlock Helm'] == "Hellwarden's Will"
    assert names["Ars Al'Diablolos"] == "Ars Al'Diabolos"
    assert names['PreCrafted Cold Rupture'] == 'Latent Cold Rupture'
    assert names['Crafted Cold Rupture'] == 'Renewed Cold Rupture'
