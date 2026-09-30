import pytest

from pricing.knowledge.assessment.maintenance.planner_reachability import (
    guide_references,
    planner_reachability,
)


def test_all_profiles_containers_and_recursive_socket_children_remain_live():
    document = {
        'items': {str(i): {'socketedItems': ['6'] if i == 5 else []} for i in range(8)},
        'profiles': [
            {'name': 'Testing', 'items': {'head': '0'}, 'mercItems': {'head': '1'}},
            {'name': 'Hardcore', 'inventory': ['2'], 'cube': ['3']},
        ],
    }
    result = planner_reachability(document, ['5'])
    assert result['reachable'] == ['0', '1', '2', '3', '5', '6']
    assert result['unreachable_candidates'] == ['4', '7']
    assert not result['issues']


def test_inline_item_children_and_literal_bases_are_not_missing_definitions():
    result = planner_reachability(
        {'items': {'1': {}}, 'profiles': [{'cube': [{'base': 'x', 'socketedItems': ['1', 'r01']}]}]},
        [],
    )
    assert result['reachable'] == ['1']
    assert not result['issues']


@pytest.mark.parametrize(
    'document',
    [
        {'items': {'1': {}}, 'profiles': [{'newInventory': ['1']}]},
        {'items': {'1': {}}, 'profiles': [{'items': '1'}]},
        {'items': {'1': {'socketedItems': ['1']}}, 'profiles': [{'items': ['1']}]},
        {'items': {'1': {}}, 'profiles': [{'items': ['999']}]},
        {'items': {'1': {}}, 'profiles': [], 'notes': {'text': 'Use item 1'}},
    ],
)
def test_uncertain_structure_never_produces_exclusion_candidates(document):
    result = planner_reachability(document, [])
    assert result['issues']
    assert result['unreachable_candidates'] == []


def test_guide_references_include_non_span_and_cross_guide_links():
    result = guide_references(
        '<a data-d2planner-profile="other" data-d2planner-id="7">item</a>'
        '<span data-d2planner-profile="other" data-d2planner-id="8">item</span>'
    )
    assert result['references'] == {'other': ['7', '8']}
    assert not result['issues']


def test_guide_reference_without_planner_is_not_silently_ignored():
    result = guide_references('<span data-d2planner-id="7">item</span>')
    assert result['issues']


def test_native_catalog_links_do_not_reference_planner_definitions():
    result = guide_references(
        '<span data-d2planner-id="unique123">item</span>'
        '<span data-d2planner-id="runeword123#helm">word</span>'
        '<span data-d2planner-id="unknown123">unknown</span>',
        catalog_ids={'unique123', 'runeword123'},
    )
    assert result['references'] == {}
    assert result['catalog_references'] == ['runeword123#helm', 'unique123']
    assert [issue['item'] for issue in result['issues']] == ['unknown123']


def test_unreachable_cycle_also_prevents_exclusion():
    result = planner_reachability(
        {'items': {'1': {'socketedItems': ['2']}, '2': {'socketedItems': ['1']}}, 'profiles': []},
        [],
    )
    assert result['issues']
    assert result['unreachable_candidates'] == []


def test_equipment_inside_metadata_cannot_be_silently_excluded():
    result = planner_reachability(
        {'items': {'1': {}}, 'profiles': [], 'summons': {'valkyrie': {'items': {'head': '1'}}}},
        [],
    )
    assert result['reachable'] == ['1']
    assert result['issues'] == [{'kind': 'additional_equipment_context', 'path': '/summons/valkyrie/items'}]
    assert result['unreachable_candidates'] == []


def test_exact_empty_editor_shell_has_no_source_mentions():
    empty_paragraph = {
        'children': [],
        'direction': None,
        'format': '',
        'indent': 0,
        'type': 'paragraph',
        'version': 1,
    }
    result = planner_reachability(
        {
            'items': {'1': {}},
            'profiles': [],
            'notes': {'root': {**empty_paragraph, 'type': 'root', 'children': [empty_paragraph]}},
        },
        [],
    )
    assert not result['issues']
    assert result['unreachable_candidates'] == ['1']


def test_modern_tooltips_preserve_unlabeled_and_cross_planner_item_roots():
    result = guide_references(
        '<span class="d2-planner-tooltip" data-d2-id="gsg0p0l0" '
        'data-d2-set-id="dm4EcrJ5" data-d2-item-id="143"></span>'
        '<a data-d2-id="other" data-d2-item-id="142"></a>'
        '<i data-d2planner-profile="other" data-d2planner-id="141"></i>'
    )
    assert result['references'] == {'gsg0p0l0': ['143'], 'other': ['141', '142']}
    assert not result['issues']


@pytest.mark.parametrize(
    'attributes',
    [
        'data-d2-item-id="143"',
        'data-d2-id="" data-d2-item-id="143"',
        'data-d2-id="a" data-d2-item-id=""',
    ],
)
def test_incomplete_modern_item_references_are_not_silently_ignored(attributes):
    assert guide_references(f'<span {attributes}></span>')['issues']


def test_both_reference_formats_on_one_element_are_conservatively_retained():
    result = guide_references(
        '<span data-d2-id="a" data-d2-item-id="1" data-d2planner-profile="b" data-d2planner-id="2"></span>'
    )
    assert result['references'] == {'a': ['1'], 'b': ['2']}


def test_guide_root_order_does_not_renumber_missing_definition_tasks():
    document = {'items': {'1': {'socketedItems': ['99']}, '2': {}}, 'profiles': []}
    roots = ['47', '1', '75', '59']
    result = planner_reachability(document, roots)
    assert result == planner_reachability(document, list(reversed(roots)))
    assert result == planner_reachability(document, set(roots))
    assert result['reachable'] == ['1']
    assert result['unreachable_candidates'] == []
    assert {row['path'] for row in result['issues']} == {
        '/guide/1/socketedItems/0',
        '/guide/47',
        '/guide/59',
        '/guide/75',
        '/items/1/socketedItems/0',
    }
