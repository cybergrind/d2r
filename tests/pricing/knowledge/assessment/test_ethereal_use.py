"""The slot rule is derived from the game's item types, not from a list of unique names."""

import json
from pathlib import Path

from pricing.knowledge.assessment.ethereal_use import MARKET_BASIS, NO_USE_TYPES, SOURCE, market_item, no_ethereal_use


MERCENARY_LOCATIONS = {'head', 'tors', 'rarm', 'larm'}
ETHEREAL_ARMOR_TYPES = {'ashd', 'belt', 'boot', 'circ', 'glov', 'head', 'helm', 'pelt', 'phlm', 'shie', 'tors'}


def test_no_use_types_are_exactly_the_unsocketable_non_mercenary_armor_slots():
    types = json.loads((Path(__file__).parents[4] / SOURCE).read_text())
    derived = {
        row['Code']
        for row in types.values()
        if row.get('Code') in ETHEREAL_ARMOR_TYPES
        and row.get('BodyLoc1') not in MERCENARY_LOCATIONS
        and not any(row.get(f'MaxSockets{n}') for n in (1, 2, 3))
    }
    assert derived == set(NO_USE_TYPES)
    for code in ETHEREAL_ARMOR_TYPES - NO_USE_TYPES:
        assert not no_ethereal_use(code)


def test_market_item_prices_ethereal_gloves_as_normal_but_leaves_other_slots_alone():
    gloves = {'category': 'uniques', 'name': 'Example', 'ethereal': True, 'family': 'glov'}
    assert market_item(gloves) == (gloves | {'ethereal': False}, MARKET_BASIS)
    by_base = {'category': 'uniques', 'name': 'Example', 'ethereal': True, 'base_code': 'tgl'}
    assert market_item(by_base) == (by_base | {'ethereal': False}, MARKET_BASIS)
    for item in (
        gloves | {'ethereal': False},
        gloves | {'ethereal': None},
        gloves | {'family': 'dagg'},
        gloves | {'family': 'helm'},
        gloves | {'family': None},
    ):
        assert market_item(item) == (item, None)
