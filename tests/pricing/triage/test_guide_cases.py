from pricing.triage.guide_cases import evaluate, extract


def test_extraction_preserves_context_and_does_not_read_alternative_as_drop_verdict():
    rows = extract(
        """
      <h2 id="s8">Worked examples — 2026-09-18</h2><table>
      <tr><th>Drop</th><th>Reason</th><th>Verdict</th></tr>
      <tr><td>Non-eth Bonehew</td><td>dated evidence</td>
      <td>vendor · eth: list Um-Mal</td></tr>
      </table><h2 id="s9">False positives</h2><ul>
      <li>Teleport amulets without +2 skills</li></ul>
      <h2 id="s10">Housekeeping</h2><ul><li>Delete files</li></ul>
    """,
        'guides/pricing.html',
    )
    assert len(rows) == 2
    assert rows[0]['expected'] == ['vendor']
    assert rows[0]['cells'] == ['Non-eth Bonehew', 'dated evidence', 'vendor · eth: list Um-Mal']
    assert rows[0]['source'] == 'guides/pricing.html#s8'
    assert rows[1]['kind'] == 'false_positive'
    assert rows[1]['expected'] is None  # broad prose needs explicit concrete cases


def test_missing_concrete_cases_do_not_disappear_from_score():
    cases = [
        {'id': 'a', 'kind': 'worked', 'expected': ['vendor'], 'item': {'name': 'A'}},
        {'id': 'b', 'kind': 'worked', 'expected': ['vendor']},
        {'id': 'c', 'kind': 'table', 'expected': None},
    ]
    report = evaluate(cases, lambda item: {'verdict': 'vendor', 'reason': 'No paid pattern', 'band': None})
    assert report['groups']['worked'] == {'total': 2, 'evaluated': 1, 'passed': 1, 'accuracy': 0.5}
    assert report['groups']['table']['accuracy'] == 0
    assert [r['id'] for r in report['unresolved']] == ['b', 'c']


def test_primer_miss_and_decision_table_outside_numbered_sections_are_included():
    rows = extract(
        """<div id="miss"><table><tr><td>Bad item</td><td>vendor</td></tr></table></div>
      <h2 id="s8">Decision</h2><div class="fbox" id="d3">Two jewel stats → sell</div>
    """,
        'guides/pricing-primer.html',
    )
    assert [r['source'] for r in rows] == ['guides/pricing-primer.html#miss', 'guides/pricing-primer.html#d3']


def test_inline_markup_preserves_words_and_does_not_infer_self_use_from_keep():
    rows = extract(
        """<h2 id="s8">Examples</h2><table><tr>
    <td>Magic <b>Greater Talons</b> with skills</td><td>Some build uses it</td>
    <td>keep — check rolls first</td></tr></table>""",
        'guides/pricing.html',
    )
    assert rows[0]['description'] == 'Magic Greater Talons with skills'
    assert rows[0]['expected'] is None


def test_guide_case_rejects_native_keys_that_cannot_arrive_from_capture():
    import pytest

    case = {
        'id': 'bad-native',
        'kind': 'worked',
        'expected': ['vendor'],
        'item': {'name': 'Example', 'native_rolls': {'60': 9}},
    }
    with pytest.raises(ValueError, match='native stat'):
        evaluate([case], lambda item: {'verdict': 'vendor'})


def test_guide_spec_uses_native_metadata_and_preserves_unknown_capture_flags():
    from pricing.triage.guide_cases import item_from_spec

    item = item_from_spec(
        {'base': 'Greater Talons', 'rarity': 'magic', 'stats': {'83:6': 1}, 'ethereal': None, 'sockets': None}
    )
    assert item['properties']['519'] == 1
    assert item['native_rolls'] == {'83:6': 1}
    assert item['ethereal'] is None
    assert item['sockets'] is None
    assert item['family'] == 'h2h2'


def test_broad_guide_row_only_passes_when_all_concrete_examples_pass():
    case = {
        'id': 'two',
        'kind': 'false_positive',
        'expected': ['vendor'],
        'items': [{'name': 'ordinary'}, {'name': 'exception'}],
    }
    report = evaluate(
        [case],
        lambda item: {'verdict': 'vendor' if item['name'] == 'ordinary' else 'check', 'reason': '', 'band': None},
    )
    assert report['groups']['false_positive'] == {'total': 1, 'evaluated': 1, 'passed': 0, 'accuracy': 0}
    assert len(report['failures']) == 1


def test_miss_checklist_separates_positive_patterns_from_false_positive_rows():
    rows = extract(
        """<div id="miss"><table>
      <tr><th>looks like junk, is not</th><th>gate</th></tr>
      <tr><td>Good jewel</td><td>two good affixes</td></tr>
      <tr><th>looks valuable, is not</th><th>why</th></tr>
      <tr><td>Bad jewel</td><td>no paid affixes</td></tr>
    </table></div>""",
        'guides/pricing-primer.html',
    )
    assert [r['kind'] for r in rows] == ['table', 'false_positive']


def test_mixed_guide_row_checks_each_branch_against_its_own_verdict():
    case = {
        'id': 'mixed',
        'kind': 'table',
        'examples': [
            {'item': {'name': 'ordinary'}, 'expected': ['vendor']},
            {'item': {'name': 'exception'}, 'expected': ['check']},
        ],
    }
    result = evaluate([case], lambda item: {'verdict': 'vendor', 'reason': '', 'band': None})
    assert result['groups']['table']['passed'] == 0
    assert result['failures'][0]['expected'] == ['check']


def test_rowspan_keeps_base_identity_on_following_variant_rows():
    rows = extract(
        """<h2 id="s5">Values</h2><table>
       <tr><td rowspan="2">Archon Plate</td><td>4os superior</td><td>keep</td></tr>
       <tr><td>3os normal</td><td>sell</td></tr>
       <tr><td>Mage Plate</td><td>3os normal</td><td>floor</td></tr>
       </table>""",
        'guides/pindle-anya.html',
    )
    assert rows[1]['resolved_cells'] == ['Archon Plate', '3os normal', 'sell']
    assert rows[2]['resolved_cells'] == ['Mage Plate', '3os normal', 'floor']


def test_base_table_transcription_preserves_ethereal_sockets_and_ed():
    from pricing.triage.guide_cases import base_table_examples

    c = {
        'source': 'guides/pindle-anya.html#s5',
        'resolved_cells': ['Berserker Axe (catalog id)', 'eth 6os Superior ≥15 ED', 'keep'],
    }
    examples = base_table_examples(c)
    assert examples[0]['spec']['ethereal'] is True
    assert examples[0]['spec']['sockets'] == 6
    assert examples[0]['spec']['stats'] == {'17:0': 15, '18:0': 15}
    c['resolved_cells'][2] = 'floor'
    assert base_table_examples(c) is None  # Floor is not an explicit VENDOR instruction.


def test_changed_rowspan_invalidates_old_item_transcription(tmp_path, monkeypatch):
    import json

    from pricing.triage import guide_cases

    (tmp_path / 'guides').mkdir()
    (tmp_path / 'pricing/triage').mkdir(parents=True)
    guide = tmp_path / 'guides/pricing.html'
    guide.write_text(
        '<h2 id="s2">Items</h2><table><tr><td rowspan="2">Old base</td><td>one</td></tr><tr><td>two</td></tr></table>'
    )
    monkeypatch.setattr(guide_cases, 'ROOT', tmp_path)
    monkeypatch.setattr(guide_cases, 'SOURCES', {'guides/pricing.html': {2}})
    rows = guide_cases.build_cases()
    rows[1]['item'] = {'name': 'Old base'}
    rows[1]['expected'] = ['vendor']
    (tmp_path / 'pricing/triage/guide-cases.json').write_text(json.dumps(rows))
    guide.write_text(guide.read_text().replace('Old base', 'New base'))
    refreshed = guide_cases.build_cases()
    assert 'item' not in refreshed[1]


def test_comparative_guide_row_checks_price_and_verdict_without_inventing_a_verdict():
    case = {
        'id': 'superior-is-plain',
        'kind': 'false_positive',
        'comparisons': [
            {
                'left': {'item': {'name': 'plain'}},
                'right': {'item': {'name': 'superior'}},
                'equal': ['verdict', 'decision_ist'],
            }
        ],
    }
    matching = evaluate([case], lambda item: {'verdict': 'slow', 'decision_ist': 0.5})
    assert matching['groups']['false_positive']['passed'] == 1
    mismatch = evaluate(
        [case],
        lambda item: {
            'verdict': 'slow',
            'decision_ist': 0.5 if item['name'] == 'plain' else 2,
        },
    )
    assert mismatch['groups']['false_positive']['passed'] == 0
    assert mismatch['failures'][0]['differences'] == {'decision_ist': [0.5, 2]}


def test_reference_headings_and_unverified_appendix_are_retained_outside_verdict_score():
    heading = extract(
        """<h2 id="s3">Pickup rules</h2><table>
        <tr><td colspan="4"><b>Runes and gems</b></td></tr>
        <tr><td>Rune</td><td>keep</td></tr></table>""",
        'guides/pindle-anya.html',
    )
    appendix = extract(
        """<h2 id="s7">7 · Verify in-game (not asserted)</h2>
        <ul><li>Verify whether the recipe works.</li></ul>""",
        'guides/warlock.html',
    )
    report = evaluate(heading + appendix, lambda item: {'verdict': 'vendor'})
    assert report['groups']['table']['total'] == 1
    assert len(report['unresolved']) == 1
    assert len(report['context']) == 2
    assert all(row['reason'] for row in report['context'])
    assert heading[0]['text'] == 'Runes and gems'


def test_guide_price_order_needs_two_estimates_and_detects_reversed_premium():
    case = {
        'id': 'discount',
        'kind': 'false_positive',
        'comparisons': [
            {
                'left': {'item': {'name': 'ethereal'}},
                'right': {'item': {'name': 'ordinary'}},
                'not_greater': ['decision_ist'],
            }
        ],
    }
    for prices, passed in (((1, 2), 1), ((2, 2), 1), ((3, 2), 0), ((None, 2), 0), ((None, None), 0)):
        report = evaluate(
            [case],
            lambda item, prices=prices: {
                'decision_ist': prices[item['name'] == 'ordinary'],
                'verdict': 'slow',
            },
        )
        assert report['groups']['false_positive']['passed'] == passed
        if not passed:
            assert report['failures'][0]['differences']['decision_ist'] == list(prices)


def test_observed_price_premium_requires_strict_order_and_two_estimates():
    case = {
        'id': 'documented-variant-premium',
        'kind': 'false_positive',
        'comparisons': [
            {
                'left': {'item': {'name': 'ordinary'}},
                'right': {'item': {'name': 'premium'}},
                'less_than': ['decision_ist'],
            }
        ],
    }
    for prices, passed in (((1, 2), 1), ((2, 2), 0), ((3, 2), 0), ((None, 2), 0), ((None, None), 0)):
        report = evaluate(
            [case],
            lambda item, prices=prices: {
                'decision_ist': prices[item['name'] == 'premium'],
                'verdict': 'slow',
            },
        )
        assert report['groups']['false_positive']['passed'] == passed
