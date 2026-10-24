"""pricing/knowledge/base_evidence.py and its build (pricing/tools/build_base_evidence.py): fills, asks and bids per
plain-base facet from the 2026-10-23 pulls, the KB's bands per plain key; the runtime reads the built file only."""

import ast
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import base_floor
from pricing.knowledge import base_evidence as module
from pricing.tools.build_base_evidence import FACETS, band_record, facts_of, match, wpb_records


def _row(**given):
    found = {'name': 'Archon Plate', 'rarity': 'normal', 'eth': True, 'sockets': 4, 'ed': 0, 'res': 0,
             'p': {797: 'normal', 402: 4, 738: True}, 'price': 1.0, 'when': '2026-10-20', 'who': 'a'}  # fmt: skip
    return found | given


def _spec(facet_id):
    return next(spec for spec in FACETS if spec['id'] == facet_id)


def test_the_runtime_reads_the_built_file_never_the_raw_pulls():
    source = Path(module.__file__).read_text()
    imported = {node.module for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
    assert 'raw' not in source.replace('raw/traderie (read only at build time)', '')
    assert not any(name and name.startswith('pricing.tools') for name in imported)
    evidence = module.base_evidence()
    assert {'facets', 'kb', 'wpb', 'sources', 'pulled'} <= set(evidence)
    for facet_id, facet in evidence['facets'].items():
        assert {'fills', 'asks', 'bids', 'codes', 'grade'} <= set(facet), facet_id


def test_the_key_is_the_ground_s():
    for args in (('utp', 'normal', True, 4, False), ('fla', 'superior', False, 0, True)):
        code, rarity, ethereal, sockets, perfect = args
        assert module.key(code, rarity, ethereal=ethereal, sockets=sockets, perfect=perfect) == base_floor.key(
            code, rarity, ethereal=ethereal, sockets=sockets, perfect=perfect
        )


def test_the_facts_come_from_the_game_data():
    facts = facts_of(_spec('dagger-3os-plus3-eldritch-blast-alone'))
    by_name = {base['name']: base['code'] for base in metadata()['bases'].values()}
    assert facts['codes'] == [by_name[name] for name in facts['bases']]
    assert 'Kriss' in facts['bases']  # Traderie's "Kris"
    skills = metadata()['skills']
    [(skill, level)] = facts['skills_exact']
    assert (skills[str(skill)]['name'], skills[str(skill)]['class'], level) == ('Eldritch Blast', 'war', 3)
    assert facts['others_max'] == 1


def test_a_plain_facet_matches_only_plain_white_rows():
    spec = _spec('archon-plate-eth-4os-normal')
    assert match(spec, _row())
    assert not match(spec, _row(ed=8))  # a seller's "normal" with an ED roll is a superior
    assert not match(spec, _row(sockets=3))
    assert not match(spec, _row(rarity='magic'))
    assert not match(spec, _row(p={797: 'normal', 402: 4, 738: True, 105: 20}))  # FCR: a magic item labelled normal


def test_one_vote_per_seller_and_per_buyer():
    asks = band_record('asks', [_row(price=9.0), _row(price=5.0), _row(who='b', price=20.0)])
    assert (asks['sellers'], asks['listings'], asks['min'], asks['max']) == (2, 3, 5.0, 20.0)
    bids = band_record('bids', [_row(price=2.0), _row(price=11.0), _row(who='b', price=4.0)])
    assert (bids['buyers'], bids['buyers_ge4'], bids['offers']) == (2, 2, [11.0, 4.0])
    fills = band_record('fills', [_row(price=2.58), _row(price=2.58, when='2026-09-28'), _row(price=40.0)])
    assert (fills['n'], fills['median'], fills['max'], fills['dates']) == (3, 2.58, 40.0, ['2026-09-28', '2026-10-20'])


def test_wp_b_plain_buckets_become_keys_split_by_ed():
    def bucket(n, median):
        return {'n_priced': n, 'min_ist': median / 2, 'median_ist': median, 'cheapest': [{'updated': '2026-09-18'}]}

    prices = {
        'wire-fleece': {'name': 'Wire Fleece', 'buckets': {
            '4os/noneth/superior': bucket(6, 0.895),
            '4os/noneth/superior/15ed': bucket(9, 9.32),
            '4os/noneth/normal/15ed': bucket(5, 30.0),  # a superior labelled normal: not a key
            '4os/noneth/superior/res45': bucket(5, 30.0),  # not a plain bucket
            '3os/noneth/superior/15ed': bucket(2, 11.4),  # thin
        }},
        'sacred-targe': {'name': 'Sacred Targe', 'buckets': {'4os/noneth/normal': bucket(9, 20.0)}},  # res pooled
    }  # fmt: skip
    found = wpb_records(prices, metadata()['bases'])
    assert set(found) == {'utu/superior/noneth/4os/ordinary', 'utu/superior/noneth/4os/perfect'}
    assert found['utu/superior/noneth/4os/ordinary']['median_ist'] == 0.895
    assert found['utu/superior/noneth/4os/perfect']['n'] == 9
