from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory


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
