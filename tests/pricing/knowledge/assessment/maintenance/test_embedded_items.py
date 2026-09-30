import pytest

from pricing.knowledge.assessment.maintenance.embedded_items import resolve_embedded_item


def test_embedded_item_links_exact_set_occurrences_without_copying_rolls_as_requirements():
    planner = {
        'items': {'7': {'base': 'base', 'stats': {'damage': 99}}},
        'profiles': [{'uid': 'set-a', 'name': 'Budget'}, {'uid': 'set-b', 'name': 'Endgame'}],
    }
    rows = [
        {'id': 'correct', 'source_locator': '/profiles/0/items/rarm', 'details': {'item_ref': '7'}},
        {'id': 'other', 'source_locator': '/profiles/1/items/rarm', 'details': {'item_ref': '7'}},
    ]
    result = resolve_embedded_item({'set_id': 'set-a', 'item_id': '7'}, planner, rows)
    assert result['status'] == 'linked'
    assert result['occurrence_ids'] == ['correct']
    assert result['item_definition']['stats']['damage'] == 99
    assert result['review_state'] == 'pending'
    assert 'requirements' not in result


def test_missing_or_ambiguous_sets_never_fall_back_to_another_profile():
    reference = {'set_id': 'set-a', 'item_id': '7'}
    planner = {'items': {'7': {'base': 'base'}}, 'profiles': []}
    missing = resolve_embedded_item(reference, planner, [])
    assert missing['status'] == 'missing_set'
    assert missing['item_definition'] == {'base': 'base'}
    planner['profiles'] = [{'uid': 'set-a'}, {'uid': 'set-a'}]
    assert resolve_embedded_item(reference, planner, [])['status'] == 'ambiguous_set'
    planner['profiles'] = [{'uid': 'set-a'}]
    assert resolve_embedded_item(reference, planner, [])['status'] == 'definition_only'
    reference['item_id'] = '8'
    assert resolve_embedded_item(reference, planner, [])['status'] == 'missing_item'


def test_blank_embedded_tooltip_retains_exact_guide_equipment_context():
    from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
    from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory

    html = (
        '<h2>Gear Options</h2><table><tr><td>Helmets</td><td>'
        '<span class="d2-planner-tooltip" data-d2-id="p" data-d2-set-id="s" '
        'data-d2-item-id="143"></span></td></tr></table>'
    )
    reference = section_inventory(html)['embedded_item_refs'][0]
    context = embedded_guide_context(html, reference)
    assert context == {'span_index': 0, 'label': '', 'side': 'player', 'slot': 'Helmets', 'reference': reference}
    for field, value in [('item_id', '144'), ('set_id', 'other'), ('section_locator', '/sections/0')]:
        with pytest.raises(ValueError, match='reference'):
            embedded_guide_context(html, {**reference, field: value})


def test_legacy_reference_resolves_definition_without_selecting_a_variant():
    reference = {'format': 'legacy_item', 'profile_id': 'p', 'set_id': None, 'item_id': '7'}
    planner = {
        'items': {'7': {'base': 'pab', 'unique': 'runeword055'}},
        'profiles': [{'uid': 'a', 'name': 'Standard'}, {'uid': 'b', 'name': 'Hardcore'}],
    }
    occurrences = [{'id': 'a', 'source_locator': '/profiles/0/items/larm', 'details': {'item_ref': '7'}}]
    result = resolve_embedded_item(reference, planner, occurrences)
    assert result['status'] == 'definition_only'
    assert result['item_definition'] == planner['items']['7']
    assert result['occurrence_ids'] == []
    assert result['review_state'] == 'pending'
    assert 'profile_locator' not in result
    assert resolve_embedded_item({**reference, 'item_id': '8'}, planner, [])['status'] == 'missing_item'
    # Missing set on newer markup is still a source gap, not a legacy fallback.
    assert resolve_embedded_item({**reference, 'format': 'modern'}, planner, [])['status'] == 'missing_set'


def test_legacy_item_retains_guide_label_and_position_without_inferring_slot():
    from pricing.knowledge.assessment.maintenance.embedded_items import embedded_guide_context
    from pricing.knowledge.assessment.maintenance.guide_sections import legacy_item_references

    html = (
        '<p>Combine <span class="d2planner-item" data-d2planner-profile="p" '
        'data-d2planner-id="7">Dream Shield</span> with the helmet.</p>'
    )
    reference = legacy_item_references(html)[0]
    context = embedded_guide_context(html, reference)
    assert context == {
        'span_index': 0,
        'label': 'Dream Shield',
        'side': 'player',
        'slot': 'unspecified',
        'reference': reference,
    }
    with pytest.raises(ValueError, match='reference'):
        embedded_guide_context(html, {**reference, 'item_id': '6'})


def test_legacy_native_ammunition_retains_definition_and_source_without_planner_rolls():
    import hashlib
    import json
    from pathlib import Path

    path = Path('third-parties/d2data/json/misc.json')
    raw = path.read_bytes()
    native = json.loads(raw)
    for name in ('Arrows', 'Bolts'):
        code, definition = next((k, v) for k, v in native.items() if v['name'] == name)
        reference = {'format': 'legacy_item', 'profile_id': 'p', 'set_id': None, 'item_id': code}
        evidence = {
            code: {
                'definition': definition,
                'source': {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'locator': '/' + code},
            }
        }
        planner = {'items': {}, 'profiles': []}
        result = resolve_embedded_item(reference, planner, [], native_items=evidence)
        assert result['status'] == 'native_definition_only'
        assert result['native_item'] == evidence[code]
        assert result['review_state'] == 'pending'
        assert result['occurrence_ids'] == []
        malformed = {code: {**evidence[code], 'definition': {**definition, 'code': 'wrong'}}}
        with pytest.raises(ValueError, match='differs from its definition'):
            resolve_embedded_item(reference, planner, [], native_items=malformed)
        assert 'item_definition' not in result
        assert 'profile_locator' not in result
        assert resolve_embedded_item(reference, planner, [])['status'] == 'missing_item'
        assert (
            resolve_embedded_item({**reference, 'format': 'modern'}, planner, [], native_items=evidence)['status']
            == 'missing_set'
        )
        planner['items'][code] = {'base': 'explicit-planner-item', 'stats': {'value': 1}}
        result = resolve_embedded_item(reference, planner, [], native_items=evidence)
        assert result['status'] == 'definition_only'
        assert result['item_definition'] == planner['items'][code]
        assert 'native_item' not in result
