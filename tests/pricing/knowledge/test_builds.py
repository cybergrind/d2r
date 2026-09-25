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


def test_build_catalog_resolves_new_localized_names_and_keeps_internal_aliases():
    from pricing.knowledge.builds import load_catalog

    catalog = load_catalog()
    assert catalog['unique408']['name'] == "Ars Al'Diabolos"
    assert "Ars Al'Diablolos" in catalog['unique408']['aliases']
    assert catalog['unique419']['name'] == "Hellwarden's Will"
    assert 'Unique Warlock Helm' in catalog['unique419']['aliases']
