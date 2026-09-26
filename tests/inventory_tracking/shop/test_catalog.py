import json
from pathlib import Path

import pytest

from inventory_tracking.shop.catalog import catalog, match_catalog, predicate
from inventory_tracking.shop.rules import match_item
from tests.inventory_tracking.shop.test_rules import observation


def observed(base, stats, **kwargs):
    from inventory_tracking.items.metadata import metadata

    result = observation(base, stats, **kwargs)
    code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == base)
    result['item'].update(
        base_code=code, ethereal=False, socket_contents='empty', sockets=next((v for s, _, v in stats if s == 194), 0)
    )
    return result


@pytest.mark.parametrize(
    ('base', 'stats'),
    [
        ('Ring', [(80, 0, 40)]),
        ('Ring', [(39, 0, 28), (79, 0, 30)]),
        ('Heavy Gloves', [(39, 0, 30), (80, 0, 25)]),
        ('Vambraces', [(43, 0, 30), (93, 0, 20)]),
        ('Demonhide Sash', [(43, 0, 30), (7, 0, 100 * 256)]),
        ('Sharkskin Belt', [(39, 0, 30), (99, 0, 24)]),
        ('Heavy Boots', [(43, 0, 35), (96, 0, 40)]),
        ('Amulet', [(188, 9, 3)]),
        ('Amulet', [(188, 42, 3), (80, 0, 35)]),
        ('Amulet', [(188, 34, 1), (79, 0, 70)]),
        ('Amulet', [(39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20)]),
        ('Circlet', [(188, 8, 3)]),
        ('Diadem', [(83, 6, 2), (96, 0, 30)]),
        ('Crown', [(194, 0, 3)]),
        ('Winged Axe', [(17, 0, 201), (18, 0, 201)]),
        ('Javelin', [(93, 0, 40)]),
        ('Jewel', [(17, 0, 40), (18, 0, 40), (93, 0, 15)]),
        ('Jewel', [(79, 0, 30)]),
        ('Grand Charm', [(188, 57, 1), (7, 0, 45 * 256)]),
        ('Grand Charm', [(188, 16, 1), (99, 0, 12)]),
        ('Small Charm', [(22, 0, 3), (19, 0, 20), (7, 0, 20 * 256)]),
    ],
)
def test_previously_missing_build_list_combinations_reach_shop_alerts(base, stats):
    assert match_item(observed(base, stats), build_candidates=True)


def test_prefix_and_suffix_magic_find_are_summed_not_individually_tested():
    from inventory_tracking.shop.catalog import by_type

    target = next(t for t in by_type()['ring'] if 'Fortuitous Ring of Fortune' in t['label'])
    assert predicate(target['must'], {}, {(80, 0): 27}, set()) is True
    assert predicate(target['must'], {}, {(80, 0): 26}, set()) is False


def test_wrong_skill_tree_or_unknown_negated_stat_cannot_pass():
    assert predicate({'not': {'op': 'stat_at_least', 'key': '54:0', 'value': 1}}, {}, {(54, 0): None}, set()) is None
    target = next(t for t in catalog()['targets'] if t['id'] == 'named:Powered Amulet:0')
    assert predicate(target['must'], {}, {(188, 8): 3}, set()) is False
    assert predicate(target['must'], {}, {(188, 9): 3}, set()) is True


def test_nonmagic_and_unidentified_items_do_not_use_magic_catalog():
    for kwargs in ({'rarity': 'rare'}, {'identified': False}):
        assert not match_catalog(observed('Ring', [(80, 0, 40)], **kwargs), {(80, 0): 40})


def test_inventory_census_covers_all_builds_and_named_magic_entries():
    root = Path(__file__).resolve().parents[3]
    builds = json.loads((root / 'pricing/data/wp-a-builds.json').read_text())
    blues = json.loads((root / 'pricing/data/wp-a-blues.json').read_text())
    data = catalog()
    assert set(data['builds']) == set(builds)
    assert {r['build'] for r in data['equipment_inventory']} == set(builds)
    reviewed = {r['name']: r for r in data['named_audit']}
    expected = {n for n in blues if not any(token in n for token in ('Rare ', 'Crafted '))}
    assert expected <= reviewed.keys()
    targets = {t['id'] for t in data['targets']}
    for name, row in reviewed.items():
        assert row['status'] != 'needs_review', name
        assert row['targets'], name
        assert set(row['targets']) <= targets


def test_all_reviewed_magic_profiles_keep_their_item_predicates():
    from inventory_tracking.shop.build_catalog import ROOT, item_predicate

    profiles = json.loads((ROOT / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    compiled = {t['id']: t for t in catalog()['targets']}
    for profile in profiles:
        if 'magic' in profile.get('qualities', []):
            target = compiled['profile:' + profile['id']]
            assert target['must'] == item_predicate(profile['must'])
            assert target['conditions'] == profile['conditions']


def test_context_alternatives_cannot_be_silently_removed():
    from inventory_tracking.shop.build_catalog import item_predicate

    with pytest.raises(ValueError, match='Context'):
        item_predicate({'any': [{'op': 'context_eq', 'field': 'player_class', 'value': 'Amazon'}]})


def test_every_named_affix_target_has_a_decodable_native_witness():
    from inventory_tracking.items.metadata import metadata

    meta = metadata()
    bases = {b['code']: b['name'] for b in meta['bases'].values()}
    for target in catalog()['targets']:
        if not target['id'].startswith('named:'):
            continue
        native = []
        for node in target['must']['all']:
            if node['op'] == 'charge_skill':
                native.append((204, node['skill_id'] * 64 + 1, 30 * 256))
            else:
                stat_id, layer = map(int, node['key'].split(':'))
                raw = node['value'] * (1 << meta['stats'][str(stat_id)]['shift'])
                native.append((stat_id, layer, raw))
        item = observed(bases[target['base_codes'][0]], native)
        assert not item['unresolved_stats'], target['id']
        assert target['label'] in match_item(item, build_candidates=True), target['id']


def test_named_combinations_do_not_drop_a_required_modifier():
    from inventory_tracking.shop.catalog import by_type

    for kind, label in [
        ('glov', 'Garnet Gloves of Fortune'),
        ('jewl', 'Ruby Jewel of Fervor'),
        ('scha', 'Fine Small Charm of Vita'),
    ]:
        target = next(t for t in by_type()[kind] if label in t['label'])
        values = {tuple(map(int, n['key'].split(':'))): n['value'] for n in target['must']['all']}
        assert predicate(target['must'], {}, values, set()) is True
        for key in values:
            assert predicate(target['must'], {}, {**values, key: values[key] - 1}, set()) is False
