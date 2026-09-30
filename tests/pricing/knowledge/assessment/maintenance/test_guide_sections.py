from pricing.knowledge.assessment.maintenance.guide_sections import legacy_item_references, section_inventory


def test_sections_keep_prose_without_item_markup_and_skip_scripts():
    html = (
        '<p>Introduction</p><h2 id="merc">Mercenary</h2><p>Use an ethereal base.</p>'
        '<script>fake</script><h3>Budget</h3><p>Empty sockets matter.</p>'
    )
    result = section_inventory(html)
    assert [r['heading'] for r in result['sections']] == ['Introduction', 'Mercenary', 'Budget']
    assert result['sections'][1]['text'] == 'Use an ethereal base.'
    assert result['sections'][1]['anchor'] == 'merc'
    assert result['sections'][2]['text'] == 'Empty sockets matter.'
    assert all(r['review_state'] == 'pending' for r in result['sections'])


def test_unchanged_source_reuses_sections_and_changed_source_invalidates_cache():
    first = section_inventory('<h2>Gear</h2><p>One</p>')
    assert section_inventory('<h2>Gear</h2><p>One</p>', first) is first
    changed = section_inventory('<h2>Gear</h2><p>Two</p>', first)
    assert changed['source_sha256'] != first['source_sha256']
    assert changed['sections'][1]['text'] == 'Two'


def test_empty_planner_tooltip_keeps_exact_profile_set_and_item_references():
    html = '<span class="d2-planner-tooltip" data-d2-id="profile1" data-d2-set-id="set1" data-d2-item-id="115"></span>'
    result = section_inventory(html)
    assert result['embedded_item_refs'] == [
        {
            'profile_id': 'profile1',
            'set_id': 'set1',
            'item_id': '115',
            'position': [1, 0],
            'section_locator': '/sections/0',
        }
    ]


def test_legacy_item_reference_preserves_planner_without_inventing_set():
    html = (
        '<h2>Gear</h2><span class="d2planner-item" data-d2planner-profile="zb01066h" '
        'data-d2planner-id="7">Dream Shield</span>'
    )
    result = legacy_item_references(html)
    assert result == [
        {
            'profile_id': 'zb01066h',
            'set_id': None,
            'item_id': '7',
            'position': [1, 13],
            'section_locator': '/sections/1',
            'format': 'legacy_item',
        }
    ]
    assert section_inventory(html)['embedded_item_refs'] == []


def test_legacy_skill_and_hidden_or_incomplete_markup_do_not_become_items():
    html = (
        '<span class="d2planner-skill" data-d2planner-profile="p" data-d2planner-id="7">Skill</span>'
        '<script><span class="d2planner-item" data-d2planner-profile="p" data-d2planner-id="7"></span></script>'
        '<span class="d2planner-item" data-d2planner-id="7">Missing planner</span>'
    )
    assert legacy_item_references(html) == []
