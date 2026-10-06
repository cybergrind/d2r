from pricing.triage.guide_cases import evaluate, extract


def test_guide_lot_quantity_reaches_the_assessor():
    from pricing.triage.guide_cases import item_from_spec

    spec = {'base': 'Chipped Sapphire', 'category': 'gems', 'rarity': 'normal', 'ethereal': False, 'sockets': 0}
    assert item_from_spec(spec)['quantity'] == 1
    assert item_from_spec(spec | {'quantity': 10})['quantity'] == 10


def test_review_history_is_preserved_without_becoming_current_verdict_guidance():
    rows = extract(
        """<h2 id="s6">Filter</h2>
        <details><summary>Current recommendations</summary>
          <ul><li>Keep useful bases</li></ul></details>
        <details><summary><b>Review log</b> / corrections (collapsed)</summary>
          <div><ul><li>Old rule: vendor these bases</li></ul></div></details>
        <ul><li>Keep valuable jewels</li></ul>""",
        'guides/warlock.html',
    )
    assert [row['kind'] for row in rows] == ['table', 'context', 'table']
    assert rows[1]['id'] == 'guides/warlock.html#s6:2'
    assert rows[1]['text'] == 'Old rule: vendor these bases'
    assert 'Historical review log' in rows[1]['context_reason']
    score = evaluate(rows, lambda item: {'verdict': 'vendor'})
    assert score['groups']['table']['total'] == 2
    assert len(score['unresolved']) == 2


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


def test_shield_variants_retain_sockets_quality_and_resistance():
    from pricing.triage.guide_cases import base_table_examples

    def row(name, variant):
        return {'source': 'guides/pindle-anya.html#s5', 'resolved_cells': [name, variant, 'keep']}

    eth = base_table_examples(row('Sacred Targe (2588089657)', 'eth 45@ any sockets'))
    assert {e['spec']['sockets'] for e in eth} == {0, 1, 2, 3, 4}
    assert all(e['spec']['ethereal'] for e in eth)
    superior = base_table_examples(row('Targe (3933241232)', '0os Superior 45@'))
    assert all(e['spec']['stats']['39:0'] == 45 for e in superior)
    mixed = base_table_examples(
        row('Sacred Rondache (2317685657)', '4os 45@ (bimodal: normal 2.6-4, Superior 15 ED 57-69)')
    )
    assert {e['spec']['rarity'] for e in mixed} == {'normal', 'superior'}
    assert {e['spec']['stats'].get('16:0', 0) for e in mixed} == {0, 15}


def test_skull_song_nova_reconstruction_matches_native_affix_semantics():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    suffixes = json.loads((root / 'third-parties/d2data/json/magicsuffix.json').read_text())
    rows = suffixes.values() if isinstance(suffixes, dict) else suffixes
    candidates = [
        r
        for r in rows
        if r.get('spawnable') == 1
        and r.get('rare') == 1
        and r.get('mod1param') == 48
        and r.get('mod1min') == 12
        and r.get('itype1') == 'weap'
    ]
    assert len(candidates) == 1
    assert (candidates[0]['mod1code'], candidates[0]['mod1max']) == ('hit-skill', 4)
    props = json.loads((root / 'third-parties/d2data/json/properties.json').read_text())
    assert props['hit-skill']['stat1'] == 'item_skillonhit'


def test_mummified_trophy_unknown_suffixes_cover_legal_native_ranges():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    suffixes = json.loads((root / 'third-parties/d2data/json/magicsuffix.json').read_text())
    rows = list(suffixes.values()) if isinstance(suffixes, dict) else suffixes
    values = {}
    for code in ('res-pois-len', 'thorns'):
        values[code] = {
            v
            for r in rows
            if r.get('spawnable') == 1
            and r.get('rare') == 1
            and r.get('mod1code') == code
            and {'armo', 'shld'} & {r.get(f'itype{i}') for i in range(1, 8)}
            for v in range(r['mod1min'], r['mod1max'] + 1)
        }
    assert values == {'res-pois-len': {25, 50, 75}, 'thorns': set(range(1, 10))}
    cases = json.loads((root / 'pricing/triage/guide-cases.json').read_text())
    row = next(c for c in cases if c['id'] == 'guides/pricing.html#s8:19')
    from itertools import product

    assert {
        (e['spec']['stats']['110:0'], e['spec']['stats']['78:0'], e['spec']['ethereal']) for e in row['examples']
    } == set(product(values['res-pois-len'], values['thorns'], [False, True]))


def test_guide_item_level_reaches_socket_preparation():
    from pricing.triage.guide_cases import item_from_spec
    from pricing.triage.socket_potential import preparation

    spec = {'base': 'Phase Blade', 'rarity': 'normal', 'ethereal': False, 'sockets': 0}
    rules = {'socket_caps': {'Phase Blade': [3, 4, 6]}}
    for level, maximum in ((25, 3), (26, 4), (40, 4), (41, 6)):
        item = item_from_spec(spec | {'item_level': level})
        assert preparation(item, rules) == {
            'larzuk': [maximum],
            'cube': list(range(1, maximum + 1)),
            'conditional': False,
        }
        superior = item_from_spec(spec | {'item_level': level, 'rarity': 'superior'})
        assert preparation(superior, rules) == {'larzuk': [maximum], 'cube': [], 'conditional': False}
    unknown = preparation(item_from_spec(spec), rules)
    assert unknown['larzuk'] == [3, 4, 6]
    assert unknown['conditional'] is True


def test_classified_score_keeps_failing_and_untranscribed_verdicts_in_denominator():
    cases = [
        {
            'id': 'failed',
            'kind': 'table',
            'classification': 'verdict',
            'classification_reason': 'Explicit sell instruction',
            'item': {'name': 'A'},
            'expected': ['slow'],
        },
        {
            'id': 'missing',
            'kind': 'table',
            'classification': 'verdict',
            'classification_reason': 'Base variant needs transcription',
            'unresolved_reason': 'Socket variants not transcribed',
        },
        {
            'id': 'own',
            'kind': 'table',
            'classification': 'own-use',
            'classification_reason': 'Player equipment upgrade',
            'item': {'name': 'B'},
            'expected': ['self'],
        },
        {
            'id': 'pickup',
            'kind': 'table',
            'classification': 'pickup',
            'classification_reason': 'Before identification',
            'text': 'Pick up blue gloves',
        },
        {
            'id': 'context',
            'kind': 'table',
            'classification': 'context',
            'classification_reason': 'Recipe mechanics',
            'text': 'Socket recipe',
        },
    ]
    result = evaluate(
        cases,
        lambda item: {
            'verdict': 'self' if item['name'] == 'B' else 'vendor',
            'reason': 'Test outcome',
            'own_use': {'label': 'Upgrade'} if item['name'] == 'B' else None,
        },
    )
    assert result['classifications'] == {'verdict': 2, 'own-use': 1, 'pickup': 1, 'context': 1}
    assert result['table_score'] == {'total': 3, 'evaluated': 2, 'passed': 1, 'accuracy': 1 / 3}
    assert [row['id'] for row in result['failures']] == ['failed']
    assert [row['id'] for row in result['unresolved']] == ['missing']
    assert result['pickup'][0]['reason'] == 'Before identification'


def test_guide_classification_does_not_depend_on_current_assessment_or_case_presence():
    from pricing.triage.guide_classification import classify

    cases = [
        ('guides/pricing-primer.html#s2:6', 'verdict'),
        ('guides/pricing-primer.html#s2-why:1', 'context'),
        ('guides/pricing-primer.html#s2-2:4', 'context'),
        ('guides/pricing-primer.html#s2-2:1', 'verdict'),
        ('guides/warlock.html#s1:1', 'own-use'),
        ('guides/warlock.html#s6:1', 'pickup'),
        ('guides/pindle-anya.html#s3:30', 'verdict'),
        ('guides/pricing.html#s8:5', 'context'),
        ('guides/pricing.html#s8:17', 'context'),
        ('guides/pricing.html#s8:18', 'verdict'),
    ]
    for identity, expected in cases:
        row = {'id': identity, 'source': identity.rsplit(':', 1)[0], 'kind': 'table', 'text': 'Example'}
        result = classify(row)
        assert result['classification'] == expected
        assert result['classification_reason']
        assert classify(row | {'item': {'name': 'Example'}, 'expected': ['vendor']}) == result


def test_own_use_row_requires_qualification_even_when_sale_takes_precedence():
    case = {
        'id': 'own',
        'kind': 'table',
        'classification': 'own-use',
        'classification_reason': 'Player upgrade',
        'item': {'name': 'Upgrade'},
        'expected': ['self', 'slow'],
    }
    result = evaluate([case], lambda item: {'verdict': 'slow', 'reason': 'Tradeable'})
    assert result['groups']['own-use']['passed'] == 0
    assert result['failures'][0]['expected'] == ['self', 'sell', 'slow', 'check']
    assert result['failures'][0]['unmet_conditions'] == ['own_use: required qualification is absent']
    for verdict in ('self', 'sell', 'slow', 'check'):
        result = evaluate([case], lambda item, verdict=verdict: {'verdict': verdict, 'own_use': {'label': 'Upgrade'}})
        assert result['groups']['own-use']['passed'] == 1
    for verdict in ('self', 'check', 'sell'):
        result = evaluate([case], lambda item, verdict=verdict: {'verdict': verdict, 'own_use': None})
        assert result['groups']['own-use']['passed'] == 0


def test_guide_example_checks_preparation_as_well_as_verdict():
    case = {
        'id': 'socket',
        'kind': 'table',
        'examples': [
            {
                'item': {'name': 'Base'},
                'expected': ['check'],
                'expected_fields': {'preparation': {'larzuk': [3, 4], 'cube': [], 'conditional': True}},
            }
        ],
    }
    wrong = evaluate([case], lambda _: {'verdict': 'check', 'reason': 'test', 'preparation': None})
    assert wrong['groups']['table']['passed'] == 0
    assert wrong['failures'][0]['expected_fields'] == case['examples'][0]['expected_fields']
    assert any('preparation' in condition for condition in wrong['failures'][0]['unmet_conditions'])
    right = evaluate([case], lambda _: {'verdict': 'check', 'reason': 'test', **case['examples'][0]['expected_fields']})
    assert right['groups']['table']['passed'] == 1


def test_mixed_guide_row_requires_comparisons_and_examples_both_to_pass():
    case = {
        'id': 'mixed',
        'kind': 'table',
        'comparisons': [
            {'left': {'item': {'name': 'A'}}, 'right': {'item': {'name': 'B'}}, 'less_than': ['decision_ist']}
        ],
        'examples': [{'item': {'name': 'C'}, 'expected': ['check']}],
    }
    result = evaluate(
        [case], lambda i: {'verdict': 'slow', 'reason': 'test', 'decision_ist': 1 if i['name'] == 'A' else 2}
    )
    assert result['groups']['table']['evaluated'] == 1
    assert result['groups']['table']['passed'] == 0
    assert result['failures'][0]['expected'] == ['check']


def test_mixed_gear_table_keeps_explicit_starter_non_use_cases():
    case = {
        'id': 'gear',
        'kind': 'table',
        'classification': 'own-use',
        'examples': [
            {'item': {'name': 'Upgrade'}, 'expected': ['self']},
            {
                'item': {'name': 'Starter'},
                'expected': ['vendor', 'sell', 'slow', 'check'],
                'expected_fields': {'own_use': None},
            },
        ],
    }

    def assess(item):
        return (
            {'verdict': 'self', 'own_use': {'label': 'Upgrade'}}
            if item['name'] == 'Upgrade'
            else {'verdict': 'vendor', 'own_use': None}
        )

    report = evaluate([case], assess)
    assert report['groups']['own-use']['evaluated'] == 1
    assert report['groups']['own-use']['passed'] == 1
    wrong = evaluate([case], lambda _: {'verdict': 'self', 'own_use': {'label': 'Automatic keep'}})
    assert wrong['groups']['own-use']['passed'] == 0
    assert len(wrong['failures']) == 1
    assert 'own_use' in str(wrong['failures'][0]['unmet_conditions'])
