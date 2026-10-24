"""loot/build_base_pickups.py: the allowlist builder, its sales-first rule per facet (the player, 2026-10-23 ~17:20:
"Sales-backed now"; "Drop both" on the two conflicts) and the built file against its evidence
(pricing/data/base-evidence.json)."""

from dataclasses import replace

import pytest

from inventory_tracking.loot import base_floor
from inventory_tracking.loot.build_base_pickups import (
    MIN_IST,
    NARROWED,
    SALES,
    class_skills,
    decide,
    facet_keys,
    facet_row,
    representatives,
)
from inventory_tracking.loot.facts import SINGLE_SKILL
from inventory_tracking.loot.wants import parse
from pricing.api import base_evidence


FILLS_PASS = {'n': 3, 'median': 4.0, 'max': 9.0}
NO = {}


@pytest.mark.parametrize(
    ('fills', 'asks', 'bids', 'expected'),
    [
        # 1. 3+ fills decide, whatever the asks and bids say
        (FILLS_PASS, {'sellers': 9, 'median': 1.0}, NO, ('pass', 'fills')),
        ({'n': 83, 'median': 2.58, 'max': 40.0}, {'sellers': 98, 'median': 9.32}, {'buyers_ge4': 3}, ('fail', 'fills')),
        # 2. else 2+ distinct buyers bidding 4+ pass
        ({'n': 2, 'median': 1.0, 'max': 1.0}, {'sellers': 1, 'median': 1.0}, {'buyers_ge4': 2}, ('pass', 'bids')),
        # 3. else asks from 3+ sellers at a median of 4+ pass ...
        ({'n': 2, 'median': 3.44, 'max': 5.88}, {'sellers': 3, 'median': 4.05}, {'buyers_ge4': 1}, ('pass', 'asks')),
        (NO, {'sellers': 3, 'median': 4.0}, NO, ('pass', 'asks')),
        # ... unless 1-2 fills all sit under 4: contested, it fails (the Sacred Rondache 0os 45 res normal)
        ({'n': 1, 'median': 2.0, 'max': 2.0}, {'sellers': 11, 'median': 4.05}, NO, ('fail', 'contested')),
        # asks under 4 fail unless the 1-2 fills' median holds 4
        (NO, {'sellers': 29, 'median': 2.58}, NO, ('fail', 'asks')),
        ({'n': 1, 'median': 5.88, 'max': 5.88}, {'sellers': 42, 'median': 3.46}, NO, ('unproven', 'thin')),
        # 4. else unproven
        ({'n': 2, 'median': 91.0, 'max': 120.0}, {'sellers': 0}, {'buyers_ge4': 1}, ('unproven', 'thin')),
    ],
    ids=[
        'fills-pass',
        'fills-fail',
        'bids',
        'asks',
        'asks-no-fills',
        'contested',
        'asks-fail',
        'asks-under-fills',
        'thin',
    ],
)
def test_the_rule_per_branch(fills, asks, bids, expected):
    assert decide(fills, asks, bids) == expected


def _facets():
    return base_evidence()['facets']


def _allowed(facts, doc):
    from inventory_tracking.loot.ground_judge import BASE_CLASSES
    from inventory_tracking.loot.wants import wants

    rows = [row for row in wants() if row.klass in BASE_CLASSES]
    return base_floor.allowed_by(facts, doc, base_floor.allowed_rows(doc, rows), base_floor.denied_rows(doc))


def test_every_entry_records_what_decided_it():
    built = base_floor.pickups()
    for section in ('rows', 'custom', 'kb', 'denied'):
        for name, entry in built[section].items():
            assert entry['decided_by'] in ('fills', 'bids', 'asks', 'contested'), (section, name)
            evidence = entry if section == 'kb' else entry['evidence']
            if section != 'denied':
                assert evidence['median_ist'] >= MIN_IST, (section, name)
    for name, entry in built['held'].items():
        assert entry['decided_by'] == 'asks' or 'least copy' in entry['why'], name
    assert built['unresolved'] == {}
    assert built['conflicts'] == []


def test_the_built_file_follows_the_evidence_per_facet():
    """Every facet the rule passes on sales is picked (unless a narrower facet that fails or is held is its least
    copy: no pooling), every asks-only pass no entry takes is held and left, every failing facet is left."""
    built = base_floor.pickups()
    decided = built['facets']
    for facet_id, facet in _facets().items():
        result, by = decided[facet_id]
        assert (result, by) == decide(facet['fills'], facet['asks'], facet['bids']), facet_id
        picked = [_allowed(item, built) is not None for item in representatives(facet)]
        if facet_id in built['held']:
            assert not all(picked), facet_id
        elif result == 'pass' and by in SALES:
            assert all(picked), facet_id
        elif result == 'fail':
            assert not any(picked), facet_id


# The base-price study's rows (rca/2026-10-23/base-prices-proposal.json): sales-backed adds in, drops and the two
# conflicts out, asks-only adds held
SALES_ADDS = [
    'rondache-45res-3os-normal',
    'rondache-45res-3os-sup<15',
    'rondache-45res-4os-sup<15',
    'archon-plate-eth-3os-sup<15',
    'balrog-skin-eth-4os-sup<15',
    'boneweave-eth-4os-sup15',
    'great-hauberk-eth-4os-sup15',
    'hellforge-plate-eth-4os-sup15',
    'hellforge-plate-eth-4os-sup<15',
    'kraken-shell-eth-4os-sup15',
    'kraken-shell-eth-4os-sup<15',
    'lacquered-plate-3os-sup15',
    'lacquered-plate-4os-sup15',
    'loricated-mail-eth-4os-sup15',
    'scarab-husk-eth-4os-sup15',
    'shadow-plate-eth-4os-sup15',
    'wyrmhide-3os-sup15',
    'wyrmhide-eth-4os-sup15',
    'bone-visage-3os-sup15',
    'colossus-voulge-eth-4os-sup15',
    'cryptic-axe-eth-4os-sup<15',
    'naga-5os-sup15',
    'decapitator-eth-5os-sup15',
    'decapitator-eth-5os-sup<15',
    'grim-shield-2os-sup15',
    'hydra-bow-4os-sup15',
    'hydra-bow-5os-sup15',
    'troll-nest-3os-sup15',
    'claw-0os-plus3-lightning-sentry',
    'dagger-3os-abyss2only-mchain2',
    'dagger-3os-fwave3',
    'dagger-3os-plus2-hex-purge-alone',
]
DROPS = [
    'claw-3os-plus3-lightning-sentry-alone',
    'archon-plate-0os-sup<15',
    'archon-plate-eth-4os-normal',
    'balrog-skin-3os-sup<15',
    'balrog-skin-eth-0os-sup<15',
    'diamond-mail-eth-4os-sup<15',
    'mage-plate-0os-sup15',
    'sacred-armor-3os-sup<15',
    'sacred-armor-4os-sup<15',
    'sacred-armor-eth-4os-normal',
    'scarab-husk-3os-sup15',
    'shadow-plate-3os-sup<15',
    'colossus-blade-eth-6os-normal',
    'colossus-blade-eth-6os-sup<15',
    'cryptic-axe-4os-sup<15',
    'great-bow-4os-sup15',
    'great-poleaxe-eth-6os-sup<15',
    'mancatcher-4os-sup15',
    'mancatcher-eth-4os-sup<15',
    'phase-blade-5os-sup<15',
    'spired-helm-eth-3os-sup<15',
    'decapitator-5os-sup15',
    'giant-thresher-5os-sup<15',
    'thresher-eth-4os-normal',
    'dagger-3os-plus3-eldritch-blast-alone',
    'dagger-3os-plus3-hex-siphon-alone',
    'tome-2os-plus3-apocalypse',
]
CONFLICTS = ['rondache-45res-0os-normal', 'archon-staff-6os-normal']


@pytest.mark.parametrize('facet_id', SALES_ADDS)
def test_a_sales_backed_add_is_picked(facet_id):
    assert all(_allowed(item, base_floor.pickups()) for item in representatives(_facets()[facet_id])), facet_id


@pytest.mark.parametrize('facet_id', DROPS + CONFLICTS)
def test_a_drop_and_the_conflicts_are_left(facet_id):
    assert not any(_allowed(item, base_floor.pickups()) for item in representatives(_facets()[facet_id])), facet_id


def test_the_asks_only_adds_are_held_with_their_evidence():
    held = base_floor.pickups()['held']
    for facet_id in (
        'archon-plate-eth-0os-sup<15',
        'sacred-armor-eth-3os-sup<15',
        'claw-0os-plus3-mind-blast',
        'rondache-45res-3os-sup15',
        'archon-staff-6os-sup<15',
    ):
        entry = held[facet_id]
        assert entry['decided_by'] == 'asks'
        assert entry['asks']['sellers'] >= 3
        assert {'fills', 'asks', 'bids'} <= set(entry)
        assert not any(_allowed(item, base_floor.pickups()) for item in representatives(_facets()[facet_id]))


def _custom(rule):
    return parse(base_floor.pickups()['custom'][rule])


def test_the_six_narrowings_as_ruled():
    custom = base_floor.pickups()['custom']
    second_war = {'keys': list(class_skills('war')), 'min': 2, 'count': 2}
    second_ass = {'keys': list(class_skills('ass')), 'min': 2, 'count': 2}
    assert second_war in custom['void-3os-plus3-no-abyss']['ground']
    assert second_ass in custom['claw-3os-plus3-lightning-sentry']['ground']
    grimoire = custom['grimoire-2os-plus3-abyss']
    assert grimoire['narrows'] == 'grimoire-white-2os-plus3-abyss-apocalypse'
    assert {'key': f'{SINGLE_SKILL}:402', 'min': 3} in grimoire['ground']  # Abyss (skills metadata 402)
    assert not any('401' in str(need) for need in grimoire['ground'])  # no Apocalypse
    archon = custom['merc-coh-archon-eth-4os-superior']
    assert (archon['narrows'], archon['qualities']) == ('merc-coh-archon-eth-4os', ['superior'])
    armor = _custom('merc-sacred-armor-eth-no-normal-4os')
    assert custom['merc-sacred-armor-eth-no-normal-4os']['narrows'] == 'merc-sacred-armor-eth'
    mage = custom['enigma-mage-plate-superior-15ed-3os']
    assert mage['narrows'] == 'enigma-mage-plate-superior-15ed'
    assert {'key': 'sockets', 'in': [3]} in mage['ground']
    rows = base_floor.pickups()['rows']
    for old in (
        'grimoire-white-2os-plus3-abyss-apocalypse',
        'merc-coh-archon-eth-4os',
        'merc-sacred-armor-eth',
        'enigma-mage-plate-superior-15ed',
    ):
        assert old not in rows, old
    # the eth Sacred Armor: 0os any quality, 4os superior only
    [eth_4os_normal] = representatives(_facets()['sacred-armor-eth-4os-normal'])
    [eth_0os_normal] = representatives(_facets()['sacred-armor-eth-0os-normal'])
    [eth_4os_superior] = representatives(_facets()['sacred-armor-eth-4os-sup<15'])
    assert armor.picks(eth_4os_normal) is False
    assert armor.picks(eth_0os_normal) is True
    assert armor.picks(eth_4os_superior) is True


def test_the_narrowed_rows_are_narrower():
    """The verifier's OVERBROAD and the study's narrowings: each wants row is replaced by its narrower rule."""
    rules = base_floor.pickups()['custom']
    for row, rule in NARROWED.items():
        assert rule['id'] in rules, row
        assert row not in base_floor.pickups()['rows'], row
        assert rules[rule['id']]['evidence']['median_ist'] >= base_floor.PICKUP_IST, rule['id']
    assert parse(rules['merc-polearm-eth-4os-superior-poleaxe']).codes == {'7h7'}
    grounds = {rule: rules[rule]['ground'] for rule in rules}
    assert {'key': 'sockets', 'in': [2]} in grounds['grimoire-2os-plus3-paid']
    assert {'key': 'sockets', 'in': [3]} in grounds['sacred-targe-40-res-exactly-3os']
    assert {'key': 'ethereal', 'equals': True} in grounds['exile-shield-eth-0-4os-40res']
    assert {'key': 'sockets', 'in': [3]} in grounds['claw-3os-plus3-phoenix-strike']


def test_a_facet_of_plain_facts_is_a_key_and_the_others_are_rows():
    facets = _facets()
    assert facet_keys(facets['archon-plate-eth-4os-normal']) == ['utp/normal/eth/4os/ordinary']
    assert facet_keys(facets['archon-plate-eth-3os-sup<15']) == ['utp/superior/eth/3os/ordinary']
    assert facet_keys(facets['rondache-45res-3os-normal']) is None  # a res band
    assert facet_keys(facets['dagger-3os-plus3-eldritch-blast-alone']) is None  # a staff mod
    row = parse(facet_row('rondache-45res-3os-normal', facets['rondache-45res-3os-normal']) | {'source': ''})
    [least] = representatives(facets['rondache-45res-3os-normal'])
    assert row.picks(least) is True
    assert row.picks(replace(least, sockets=4)) is False
    assert (
        row.picks(replace(least, rolls={**(least.rolls or {}), **{f'{stat}:0': 44 for stat in (39, 41, 43, 45)}}))
        is False
    )
    alone = parse(facet_row('a', facets['dagger-3os-plus3-eldritch-blast-alone']) | {'source': ''})
    eb = representatives(facets['dagger-3os-plus3-eldritch-blast-alone'])[0]  # one per Void dagger code
    assert alone.picks(eb) is True
    assert alone.picks(replace(eb, rolls={**(eb.rolls or {}), f'{SINGLE_SKILL}:402': 2})) is False  # a companion at +2
