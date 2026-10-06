import json
from pathlib import Path

from pricing.triage.adapters import from_listing
from pricing.triage.base_demand import compile_bases
from pricing.triage.demand import compile_demand, demand_for
from tests.pricing.triage.test_bands import listing
from tests.pricing.triage.test_demand import mention


def test_recommended_base_inherits_only_live_endgame_recipe_and_matching_facets():
    bases = json.loads(Path('pricing/data/wp-a-bases.json').read_text())
    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())['rows']
    demand = compile_demand([mention(name='Heart of the Oak', category='runeword')])
    evidence = compile_bases(bases, utility, demand)
    row = listing('a') | {'name': 'Flail', 'category': 'base', 'rarity': 'normal', 'sockets': 4, 'ethereal': False}
    item = from_listing(row)
    assert demand_for(item, evidence)[0]['runeword'] == 'Heart of the Oak'
    for change in ({'sockets': 5}, {'socket_contents': 'filled'}, {'ethereal': True}, {'rarity': 'rare'}):
        assert not demand_for(item | change, evidence)
    assert not compile_bases(
        bases, utility, compile_demand([mention('Starter', name='Heart of the Oak', category='runeword')])
    )
    assert not compile_bases(bases, [], demand)


def test_base_demand_preserves_supported_sale_but_never_supplies_a_price():
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import assess, prepare_tables
    from pricing.triage.listing_scores import cohort_key

    bases = json.loads(Path('pricing/data/wp-a-bases.json').read_text())
    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())['rows']
    demand = compile_bases(bases, utility, compile_demand([mention(name='Heart of the Oak', category='runeword')]))
    rows = [
        listing(i, 0.6) | {'name': 'Flail', 'category': 'base', 'rarity': 'normal', 'sockets': 4, 'ethereal': False}
        for i in range(3)
    ]
    doc = build_bands(rows, [])
    tables = prepare_tables(doc, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    item = from_listing(rows[0])
    result = assess(item, tables)
    key = cohort_key(item, result, None, tables)
    tables['market_demand'] = {'complete': True, 'cohorts': {key: {'previous_listings': 3, 'current_listings': 3}}}
    assert assess(item, tables)['verdict'] == 'vendor'
    tables['demand'] = demand
    result = assess(item, tables)
    assert (result['verdict'], result['decision_ist']) == ('slow', 0.6)
    empty = prepare_tables({'bands': [], 'demand': demand}, {'rows': [], 'keep_ist': 0.25}, {'rows': []})
    assert assess(item, empty)['decision_ist'] is None


def test_named_watch_prose_is_not_a_base_predicate():
    evidence = compile_demand(
        [],
        [
            {
                'name': 'Example',
                'rarity': 'unique',
                'details': {'priority': 'valuable_candidate', 'guide_conditions': 'Prefer ethereal'},
            }
        ],
    )
    assert demand_for({'category': 'uniques', 'name': 'Example', 'ethereal': False}, evidence)


def test_explicit_variant_base_does_not_require_the_older_recommended_shortlist():
    from inventory_tracking.items.metadata import metadata

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())['rows']
    demand = compile_demand(
        [
            mention(name='Treachery', category='runeword')
            | {'original_label': 'Treachery Archon Plate (ethereal)', 'side': 'merc'},
        ]
    )
    evidence = compile_bases({}, utility, demand)
    row = listing('a') | {
        'name': 'Archon Plate',
        'category': 'base',
        'rarity': 'normal',
        'sockets': 3,
        'ethereal': True,
    }
    item = from_listing(row)
    assert demand_for(item, evidence)[0]['runeword'] == 'Treachery'
    for change in ({'ethereal': False}, {'sockets': 4}, {'socket_contents': 'filled'}):
        assert not demand_for(item | change, evidence)
    other = next(b for b in metadata()['bases'].values() if b['name'] == 'Dusk Shroud')
    assert not demand_for(item | {'name': other['name'], 'base_code': other['code']}, evidence)
    # A mention is not a recipe-compatible base, or a reviewed endgame variant.
    for label, variant in [('Treachery Military Pick', 'Standard'), ('Treachery Archon Plate', 'Starter')]:
        invalid = compile_demand([mention(variant, name='Treachery', category='runeword') | {'original_label': label}])
        assert not compile_bases({}, utility, invalid)


def test_explicit_mercenary_base_does_not_invent_ethereal_requirement():
    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())['rows']
    demand = compile_demand(
        [
            mention(name='Faith', category='runeword') | {'original_label': 'Faith Crusader Bow', 'side': 'merc'},
        ]
    )
    evidence = compile_bases({}, utility, demand)
    item = from_listing(
        listing('a')
        | {
            'name': 'Crusader Bow',
            'category': 'base',
            'rarity': 'normal',
            'sockets': 4,
            'ethereal': False,
        }
    )
    assert demand_for(item, evidence)[0]['runeword'] == 'Faith'
