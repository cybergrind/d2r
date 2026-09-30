import json

import pytest

from pricing.knowledge.builds import decode_planner, planner_rows


@pytest.mark.parametrize('nested', [False, True])
def test_retains_swaps_dual_merc_cube_and_socket_fillers(nested):
    planner = {
        'items': {
            '1': {
                'base': 'verified-base',
                'unique': 'known-item',
                'sockets': 1,
                'socketedItems': ['verified-gem'],
                'stats': {'damage': 12},
            },
            '2': {'base': 'verified-base', 'stats': {'damage': 99}},
        },
        'profiles': [
            {
                'uid': 'set-a',
                'name': 'Standard',
                'items': {'rarm2': 1},
                'mercItems': {'rarm': 1, 'larm': 2},
                'cube': [2],
                'inventory': ['verified-gem', 404],
            }
        ],
    }
    document = {'data': json.dumps({'planner': planner} if nested else planner)}
    catalog = {
        'verified-base': {'name': 'Verified Sword', 'category': 'weapon'},
        'verified-gem': {'name': 'Verified Gem', 'category': 'gem'},
        'known-item': {'name': 'Known Item', 'category': 'unique'},
    }
    assert decode_planner(document) == planner
    rows, coverage = planner_rows(document, catalog, 'source', 'a-build', 'Class')
    assert any(r['side'] == 'merc' and r['slot'] == 'larm' for r in rows)
    assert any(r['slot'] == 'rarm2' for r in rows)
    assert any(r.get('sockets') == 1 for r in rows)
    assert any(r['details']['container'] == 'cube' for r in rows)
    assert any(r['details']['role'] == 'socket_filler' for r in rows)
    assert any(r['details']['resolution_status'] == 'unresolved' for r in rows)
    assert any(r['details'].get('stats') == {'damage': 99} for r in rows)
    assert len({r['id'] for r in rows}) == len(rows)
    assert coverage['unresolved_references'] == 1


def test_skills_sets_remain_visible_without_recommended_demand():
    document = {'data': {'items': {}, 'profiles': [{'name': 'Skill Tree', 'uid': 's', 'cube': ['x']}]}}
    rows, coverage = planner_rows(document, {'x': {'name': 'Prebuff Tool'}}, 's', 'b', 'c')
    assert rows[0]['details']['recommended'] is False
    assert rows[0]['name'] == 'Prebuff Tool'
    assert coverage['sets'] == 1


def test_legacy_tooltip_labels_are_not_lost():
    from pricing.knowledge.builds import guide_mentions

    html = """<table><tr><td>Weapon</td><td><span class="d2planner-item"
    data-d2planner-profile="legacy12" data-d2planner-id="1">Alternative Sword</span></td></tr></table>"""
    mentions = guide_mentions(html)
    assert mentions[0]['label'] == 'Alternative Sword'
    assert mentions[0]['profile_id'] == 'legacy12'
    assert mentions[0]['item_id'] == '1'


def test_unreferenced_definitions_are_retained_as_nonrecommended():
    document = {'data': {'items': {'9': {'base': 'x', 'stats': {'life': 17}}}, 'profiles': []}}
    rows, coverage = planner_rows(document, {'x': {'name': 'Unused Charm'}}, 's', 'b', 'c')
    assert rows[0]['name'] == 'Unused Charm'
    assert rows[0]['details']['stats'] == {'life': 17}
    assert rows[0]['details']['recommended'] is False
    assert coverage['unreferenced_item_ids'] == ['9']
    assert coverage['referenced_item_definitions'] == 0


def test_named_setup_labels_resolve_without_substring_guessing():
    from pricing.knowledge.builds import resolve_named_label

    catalog = {
        'set1': {'name': "Sazabi's Mental Sheath", 'category': 'set'},
        'r1': {'name': 'Spirit', 'category': 'runeword'},
        'base': {'name': 'Monarch', 'category': 'armor'},
    }
    assert resolve_named_label("Sazabi's Mental Sheath [set] (Basinet; Cham)", catalog) == catalog['set1']
    assert resolve_named_label('Spirit Monarch (35 FCR)', catalog) == catalog['r1']
    assert resolve_named_label('Ethereal Spirit Monarch', catalog) == catalog['r1']
    assert resolve_named_label('Spirit Keeper', catalog) is None
    assert resolve_named_label('Rare Monarch with skills', catalog) is None


def test_class_prefixed_torches_resolve_without_consuming_composite_prose():
    from inventory_tracking.items.stat_constants import CLASS_NAMES
    from pricing.knowledge.builds import resolve_named_label

    row = {'name': 'Hellfire Torch', 'category': 'unique'}
    catalog = {'torch': row}
    for class_name in CLASS_NAMES:
        assert resolve_named_label(f'{class_name} Hellfire Torch', catalog) == row
        assert resolve_named_label(f'{class_name} Hellfire Torch (20/20)', catalog) == row
    assert resolve_named_label('Sorceress Hellfire Torch + Annihilus', catalog) is None
    assert resolve_named_label('Kill Ubers for a Sorceress Hellfire Torch', catalog) is None
    assert resolve_named_label('Sorceress Spirit', {'spirit': {'name': 'Spirit', 'category': 'runeword'}}) is None


def test_build_catalog_resolves_new_localized_names_and_keeps_internal_aliases():
    from pricing.knowledge.builds import load_catalog

    catalog = load_catalog()
    assert catalog['unique408']['name'] == "Ars Al'Diabolos"
    assert "Ars Al'Diablolos" in catalog['unique408']['aliases']
    assert catalog['unique419']['name'] == "Hellwarden's Will"
    assert 'Unique Warlock Helm' in catalog['unique419']['aliases']


def test_exact_typographic_named_aliases_preserve_composite_rejection():
    from pricing.knowledge.builds import resolve_named_label

    torch = {'name': 'Hellfire Torch', 'category': 'unique'}
    gheed = {'name': "Gheed's Fortune", 'category': 'unique'}
    catalog = {'torch': torch, 'gheed': gheed, 'spirit': {'name': 'Spirit', 'category': 'runeword'}}
    assert resolve_named_label('Hellfiretorch', catalog) == torch
    assert resolve_named_label('Gheeds Fortune', catalog) == gheed
    assert resolve_named_label('Gheed\u2019s Fortune', catalog) == gheed
    assert resolve_named_label('Spirit+', catalog) is None
    assert resolve_named_label('Spirit + Monarch', catalog) is None
    assert resolve_named_label('Hellfiretorch + Annihilus', catalog) is None
    ambiguous = {'one': {'name': 'Foo-Bar', 'category': 'unique'}, 'two': {'name': 'Foo Bar', 'category': 'set'}}
    assert resolve_named_label('FooBar', ambiguous) is None


def test_raw_guide_named_base_labels_keep_original_text():
    from pricing.knowledge.builds import build_dataset

    document = build_dataset()
    rows = [
        r
        for r in document['rows']
        if r['details'].get('role') == 'guide_mention' and r['details'].get('original_label') == 'Spirit Monarch'
    ]
    assert rows
    assert all(r['name'] == 'Spirit' and r['category'] == 'runeword' for r in rows)
    assert all(r['original_label'] == 'Spirit Monarch' for r in rows)
    plural = [r for r in document['rows'] if r.get('original_label') == 'Lawbringers']
    assert plural
    assert all(r['name'] == 'Lawbringer' and r['category'] == 'runeword' for r in plural)
    assert all(r['details']['original_label'] == 'Lawbringers' for r in plural)


def test_reviewed_lawbringer_plural_resolves_identity_without_guessing_other_plurals():
    from pricing.knowledge.builds import resolve_named_label

    word = {'name': 'Lawbringer', 'category': 'runeword'}
    catalog = {'word': word, 'spirit': {'name': 'Spirit', 'category': 'runeword'}}
    for label in ('Lawbringers', 'Lawbringer(s)'):
        assert resolve_named_label(label, catalog) == word
    for label in ('Lawbringers + Insight', 'Lawbringers or Spirit', 'Spirits', 'Buy Lawbringers'):
        assert resolve_named_label(label, catalog) is None
    assert resolve_named_label('Lawbringers', {}) is None
    assert resolve_named_label('Lawbringers', {'wrong': {'name': 'Lawbringer', 'category': 'misc'}}) is None
