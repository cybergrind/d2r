"""Every native named item with an item-level proc gets a reviewed disposition."""

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.variable_triggers import variable_trigger_properties
from pricing.knowledge.definition_store import catalog


# Independently enumerated native uniqueitems rows, ItemMods PropertyFunc11,
# skills required levels, and cached market-field labels. At item level90.
ITEMS = (
    ('Stormrider', 198, 38, 10, 20, None),
    ('Boneslayer Blade', 201, 101, 50, 20, None),
    ('Snowclash', 201, 59, 5, 17, None),
    ('Hellslayer', 195, 47, 10, 20, None),
    ('Lightsabre', 195, 53, 5, 19, '547'),
    ('Stormspire', 201, 38, 2, 20, '433'),
    ('The Rising Sun', 201, 56, 2, 17, None),
)


@pytest.mark.parametrize(('name', 'stat', 'skill', 'chance', 'level', 'market'), ITEMS)
@pytest.mark.parametrize('mutation', ['unchanged', 'wrong-level', 'missing'])
def test_all_native_variable_proc_identities_preserve_level_requirement(
    name, stat, skill, chance, level, market, mutation
):
    observed_level = level - 1 if mutation == 'wrong-level' else level
    raw = [] if mutation == 'missing' else [{'id': stat, 'layer': skill * 64 + observed_level, 'raw': chance}]
    decoded, _, unresolved = decode_stats(raw)
    assert not unresolved
    facts = normalize({'item': {'item_level': 90}, 'decoded_stats': decoded})
    props, levels, consumed, gaps = variable_trigger_properties(facts, catalog().named['unique', name])
    if market and mutation == 'unchanged':
        assert props == {market: chance}
        assert levels == {market: level}
        assert consumed == {f'{stat}:{skill * 64 + level}'}
        assert gaps == []
    else:
        assert gaps
        assert props == {}
        assert levels == {}
        assert consumed == set()


def test_reviewed_catalog_accounts_for_every_named_variable_proc():
    codes = {'att-skill', 'gethit-skill', 'hit-skill', 'death-skill', 'kill-skill', 'levelup-skill'}
    found = set()
    for (quality, name), definition in catalog().named.items():
        record = definition['game_definition']
        for slot in range(1, 13):
            code, level = record.get(f'prop{slot}'), record.get(f'max{slot}')
            if isinstance(code, str) and code.casefold() in codes and type(level) is int and level <= 0:
                found.add((quality, name))
    assert found == {('unique', row[0]) for row in ITEMS}
