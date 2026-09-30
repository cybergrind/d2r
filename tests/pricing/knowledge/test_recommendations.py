import pytest

from pricing.knowledge.recommendations import GUIDE_SOURCE_SHA256, build_recommendations


def candidate(name, context='leveling utility', kind='unique'):
    return {'name': name, 'item_kind': kind, 'context': context, 'utility_tags': ['life'], 'source_timestamp': '01:00'}


def build(items, facts=None, utility=None):
    facts = (
        facts
        if facts is not None
        else [{'name': item['name'], 'item_id': 'test:' + item['name'], 'aliases': []} for item in items]
    )
    return build_recommendations(
        {'items': items, 'generic_patterns': [], 'negative_or_scope_mentions': []},
        {'rows': facts},
        utility or {'rows': [], 'sources': []},
    )


def test_cross_class_defense_and_caster_weapon_are_reviewed_without_attack_claims():
    payload = build([candidate('Bloodfist'), candidate('Maelstrom')])
    blood = next(r for r in payload['rows'] if r['name'] == 'Bloodfist')
    assert {'sorceress', 'necromancer', 'warlock'} <= set(blood['classes'])
    assert blood['archetypes'] == ['general']
    assert 'attack speed' not in blood['reason'].lower()
    wand = next(r for r in payload['rows'] if r['name'] == 'Maelstrom')
    assert wand['archetypes'] == ['caster']
    assert 'sorceress' in wand['classes']


def test_conditional_set_requires_companion_and_incidental_is_not_recommendation():
    payload = build([candidate("Death's Hand", kind='set'), candidate("Sander's Superstition")])
    hand = payload['rows'][0]
    assert any("Death's Guard" in c for c in hand['conditions'])
    assert not any(r['name'] == "Sander's Superstition" for r in payload['rows'])
    assert payload['coverage']['named'][1]['status'] == 'gap'


def test_missing_identity_and_ambiguous_alias_are_explicit_gaps():
    items = [candidate('Bloodfist'), candidate('Maelstrom')]
    payload = build(
        items,
        facts=[
            {'name': 'x', 'aliases': ['Bloodfist'], 'item_id': '1'},
            {'name': 'y', 'aliases': ['Bloodfist'], 'item_id': '2'},
        ],
    )
    assert payload['rows'] == []
    assert {x['status'] for x in payload['coverage']['named']} == {'gap'}


def test_vendor_and_shared_planner_mentions_never_promoted():
    utility = {
        'sources': [],
        'rows': [
            {
                'name': 'Ring',
                'class': 'sorceress',
                'kind': 'leveling',
                'details': {'context_excerpt': 'pick up items to sell, like Rings'},
            },
            {
                'name': 'Bloodfist',
                'class': 'sorceress',
                'kind': 'leveling',
                'source_id': 'shared-planner',
                'details': {'recommended': True},
            },
        ],
    }
    assert build([], utility=utility)['rows'] == []


def test_class_items_and_patterns_cannot_become_universal_named_items():
    payload = build([candidate('The Oculus')])
    assert payload['rows'][0]['classes'] == ['sorceress']
    candidates = {
        'items': [],
        'generic_patterns': [
            {'name': 'leveling rings', 'context': 'Cast rate when needed', 'source_timestamp': '24:19'}
        ],
        'negative_or_scope_mentions': [{'name': 'Death Cleaver', 'context': 'endgame scope', 'timestamp': '46:28'}],
    }
    payload = build_recommendations(candidates, {'rows': []}, {'rows': [], 'sources': []})
    assert payload['rows'] == []
    assert payload['patterns'][0]['item_id'] is None
    assert payload['coverage']['exclusions'][0]['status'] == 'excluded'


def test_mercenary_survival_advice_preserves_equipment_prerequisites():
    payload = build([candidate('Rockstopper')])
    merc = next(r for r in payload['rows'] if r['side'] == 'merc')
    assert 'mercenary' in ' '.join(merc['conditions']).lower()
    assert merc['evidence_strength'] == 'explicit'


def test_reviewed_guide_advice_is_class_specific_and_priority_is_not_frequency():
    reviewed = {
        'name': 'Magefist',
        'class': 'sorceress',
        'kind': 'leveling',
        'source_id': 'leveling-sorceress',
        'source_locator': 'essentials-header/item/80@(77, 233)',
    }
    utility = {
        'sources': [{'id': 'leveling-sorceress', 'sha256': GUIDE_SOURCE_SHA256['leveling-sorceress']}],
        'rows': [reviewed] * 8,
    }
    payload = build([candidate('Magefist'), candidate('Nagelring')], utility=utility)
    explicit = [r for r in payload['rows'] if r['source_id'] == 'leveling-sorceress']
    assert len(explicit) == 1
    assert explicit[0]['classes'] == ['sorceress']
    assert explicit[0]['evidence_strength'] == 'explicit'
    assert explicit[0]['priority'] < next(r for r in payload['rows'] if r['name'] == 'Nagelring')['priority']


def test_portable_review_census_accounts_for_transcript_and_eight_classes():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    path = root / 'pricing/data/appraisal-recommendations.json'
    if not path.exists():
        pytest.skip('Separate local KB snapshot is not installed')
    payload = json.loads(path.read_text())
    assert len(payload['coverage']['named']) == 70
    assert len(payload['patterns']) == 13
    assert len(payload['coverage']['exclusions']) == 4
    assert len(payload['coverage']['classes']) == 8
    assert all(r['source_locator'] and r['reason'] for r in payload['rows'])
    assert all(p['item_id'] is None for p in payload['patterns'])
    assert len({r['id'] for r in payload['rows']}) == len(payload['rows'])


def test_amazon_leveling_advice_preserves_set_pair_and_exact_source_selection():
    selections = [
        ("Death's Hand", '97@(78, 80)'),
        ("Death's Guard", '98@(78, 149)'),
        ("Hsarus' Iron Heel", '104@(78, 1719)'),
        ("Sander's Riprap", '105@(78, 1795)'),
        ('Twitchthroe', '107@(78, 2816)'),
    ]
    items = [candidate(name) for name, _ in selections]
    utility = {
        'sources': [
            {'id': 'leveling-amazon', 'source_date': '2026-05-22', 'sha256': GUIDE_SOURCE_SHA256['leveling-amazon']}
        ],
        'rows': [
            {'name': name, 'source_id': 'leveling-amazon', 'source_locator': 'essentials-header/item/' + locator}
            for name, locator in selections
        ],
    }
    result = build(items, utility=utility)
    advice = [r for r in result['rows'] if r['source_id'] == 'leveling-amazon']
    assert {r['name'] for r in advice} == {name for name, _ in selections}
    assert all(r['classes'] == ['amazon'] and r['evidence_strength'] == 'explicit' for r in advice)
    assert not any(r['name'] == 'Twitchthroe' and r['source_id'] == 'mrllamasc-transcript' for r in result['rows'])
    hand = next(r for r in advice if r['name'] == "Death's Hand")
    assert any("Death's Guard" in c for c in hand['conditions'])
    assert all('2026-09-25' in r['review'] for r in advice)
    utility['rows'] = [{**r, 'source_locator': 'unreviewed'} for r in utility['rows']]
    assert not any(r['source_id'] == 'leveling-amazon' for r in build(items, utility=utility)['rows'])


@pytest.mark.parametrize(
    'sources',
    [
        [],
        [{'id': 'leveling-amazon', 'sha256': 'changed'}],
        [{'id': 'leveling-amazon', 'sha256': GUIDE_SOURCE_SHA256['leveling-amazon']}] * 2,
    ],
)
def test_guide_only_advice_requires_its_reviewed_source_snapshot(sources):
    utility = {
        'sources': sources,
        'rows': [
            {
                'name': 'Twitchthroe',
                'source_id': 'leveling-amazon',
                'source_locator': 'essentials-header/item/107@(78, 2816)',
            }
        ],
    }
    result = build([candidate('Twitchthroe')], utility=utility)
    assert not result['rows']
    gap = next(r for r in result['coverage']['guide_reviews'] if r['name'] == 'Twitchthroe')
    assert gap['status'] == 'gap'
    assert 'source' in gap['reason'].lower()


def test_titans_guide_only_recommendation_keeps_dexterity_and_speed_tradeoffs():
    name = "Titan's Revenge"
    utility = {
        'sources': [{'id': 'leveling-amazon', 'sha256': GUIDE_SOURCE_SHA256['leveling-amazon']}],
        'rows': [
            {'name': name, 'source_id': 'leveling-amazon', 'source_locator': 'essentials-header/item/106@(78, 2053)'}
        ],
    }
    result = build([], facts=[{'name': name, 'item_id': 'titan', 'aliases': []}], utility=utility)
    assert len(result['rows']) == 1
    row = result['rows'][0]
    assert row['classes'] == ['amazon']
    assert row['priority'] == 1
    assert row['source_id'] == 'leveling-amazon'
    assert any('dexterity' in c.lower() and 'vitality' in c.lower() for c in row['conditions'])
    assert any('attack speed' in c.lower() for c in row['conditions'])
    ambiguous = [{'name': name, 'item_id': key, 'aliases': []} for key in ('one', 'two')]
    assert not build([], facts=ambiguous, utility=utility)['rows']


def test_cow_king_leveling_pieces_keep_the_full_combination_and_source_scope():
    names = ["Cow King's Hooves", "Cow King's Hide", "Cow King's Horns"]
    locators = ['112@(78, 4158)', '113@(78, 4231)', '114@(78, 4306)']
    utility = {
        'sources': [{'id': 'leveling-amazon', 'sha256': GUIDE_SOURCE_SHA256['leveling-amazon']}],
        'rows': [
            {'name': name, 'source_id': 'leveling-amazon', 'source_locator': 'essentials-header/item/' + locator}
            for name, locator in zip(names, locators, strict=True)
        ],
    }
    result = build([], facts=[{'name': n, 'item_id': n, 'aliases': []} for n in names], utility=utility)
    assert len(result['rows']) == 3
    for row in result['rows']:
        assert row['classes'] == ['amazon']
        assert row['priority'] == 3
        conditions = ' '.join(row['conditions'])
        assert all(n in conditions for n in [*names, "Death's Hand", "Death's Guard", "Ancient's Pledge"])
        assert 'single piece' in conditions
        assert row['source_id'] == 'leveling-amazon'


@pytest.mark.parametrize(
    'cls', ['amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock']
)
def test_movement_boot_guide_recommendations_do_not_require_a_second_set_piece(cls):
    import json
    from pathlib import Path

    from pricing.knowledge.recommendations import GUIDE_REVIEW

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())
    names = ["Hsarus' Iron Heel", "Sander's Riprap"]
    result = build([candidate(n, kind='set') for n in names], utility=utility)
    rows = [r for r in result['rows'] if r['source_id'] == 'leveling-' + cls]
    assert {r['name'] for r in rows} == set(names)
    for row in rows:
        assert row['classes'] == [cls]
        assert 'movement' in row['reason'].lower()
        assert not any('second' in c.lower() or 'piece' in c.lower() for c in row['conditions'])
        assert row['priority'] == (3 if row['name'] == names[0] else 1)
        assert (cls, row['name'], row['source_locator']) in GUIDE_REVIEW
        assert row['review'].startswith('2026-09-25:')
        if cls in ('barbarian', 'paladin'):
            level = 31 if cls == 'barbarian' else 18
            assert any(f'level {level}' in c.lower() and 'respec' in c.lower() for c in row['conditions'])
        else:
            assert row['conditions'] == []
    # The separate transcript's conditional attack-rating advice is preserved.
    transcript = next(r for r in result['rows'] if r['name'] == names[0] and r['source_id'] == 'mrllamasc-transcript')
    assert any('second' in c for c in transcript['conditions'])
    bad = dict(
        utility, sources=[dict(s, sha256='changed') if s['id'] == 'leveling-' + cls else s for s in utility['sources']]
    )
    assert not any(
        r['source_id'] == 'leveling-' + cls for r in build([candidate(n) for n in names], utility=bad)['rows']
    )


@pytest.mark.parametrize('cls', ['druid', 'paladin'])
@pytest.mark.parametrize('name', ['Spectral Shard', 'Suicide Branch', 'Skin of the Vipermagi', 'Magefist'])
def test_caster_leveling_alternatives_retain_scope_and_skill_conditions(cls, name):
    import json
    from pathlib import Path

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())
    result = build([candidate(name)], utility=utility)
    row = next((r for r in result['rows'] if r['name'] == name and r['source_id'] == 'leveling-' + cls), None)
    assert row is not None
    assert row['classes'] == [cls]
    assert row['archetypes'] == ['caster']
    assert row['priority'] == (3 if name in ('Spectral Shard', 'Suicide Branch') else 1)
    assert row['review'].startswith('2026-09-25:')
    if cls == 'paladin':
        assert any('level 18' in c.lower() and 'respec' in c.lower() for c in row['conditions'])
    if name in ('Spectral Shard', 'Suicide Branch'):
        assert 'alternative' in row['reason'].lower()
        assert 'Spirit' in row['reason']
        assert any('breakpoint' in c.lower() for c in row['conditions'])
    if name == 'Magefist':
        assert any(
            ('Tornado' if cls == 'druid' else 'Blessed Hammer') in c and 'fire' in c.lower() for c in row['conditions']
        )
    # A locator/source change must not silently retain the reviewed recommendation.
    bad = dict(
        utility,
        rows=[
            dict(r, source_locator='changed') if r.get('source_id') == 'leveling-' + cls and r['name'] == name else r
            for r in utility['rows']
        ],
    )
    assert not any(
        r['name'] == name and r['source_id'] == 'leveling-' + cls for r in build([candidate(name)], utility=bad)['rows']
    )


@pytest.mark.parametrize('name', ["Death's Hand", "Death's Guard", 'Twitchthroe'])
def test_assassin_leveling_pair_and_shield_advice_requires_reviewed_source(name):
    import json
    from pathlib import Path

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())
    items = [candidate(name)]
    rows = build(items, utility=utility)['rows']
    row = next((r for r in rows if r['source_id'] == 'leveling-assassin'), None)
    assert row is not None
    assert row['classes'] == ['assassin']
    assert row['priority'] == 1
    advice = ' '.join([row['reason'], *row['conditions']])
    if name.startswith('Death'):
        assert "Death's Hand" in advice
        assert "Death's Guard" in advice
        assert '30%' in advice
        assert '15%' in advice
        assert 'Cannot Be Frozen' in advice
        assert 'belt itself' in advice
        assert "Ancient's Pledge" in advice
    else:
        assert 'shield' in advice
        assert 'recovery' in advice
    for mutation in ('locator', 'hash'):
        bad = json.loads(json.dumps(utility))
        if mutation == 'locator':
            for r in bad['rows']:
                if r.get('source_id') == 'leveling-assassin' and r['name'] == name:
                    r['source_locator'] = 'changed'
        else:
            for source in bad['sources']:
                if source['id'] == 'leveling-assassin':
                    source['sha256'] = 'changed'
        assert not any(r['source_id'] == 'leveling-assassin' for r in build(items, utility=bad)['rows'])


@pytest.mark.parametrize('name', ['The Stone of Jordan', 'The Eye of Etlich', 'Skin of the Vipermagi', 'Magefist'])
def test_assassin_skill_leveling_uses_source_specific_benefits(name):
    import json
    from pathlib import Path

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())
    row = next(
        (r for r in build([candidate(name)], utility=utility)['rows'] if r['source_id'] == 'leveling-assassin'), None
    )
    assert row is not None
    assert row['classes'] == ['assassin']
    assert row['priority'] == 1
    advice = ' '.join([row['reason'], *row['conditions']])
    if name == 'Magefist':
        assert 'Fire Traps' in advice
        assert 'Death Sentry' in advice
        assert 'Lightning Sentry' in advice
        assert 'cast rate' not in row['reason'].lower()
    if name == 'The Eye of Etlich':
        assert 'alternative' in advice
    utility['rows'] = [
        dict(r, source_locator='changed') if r.get('source_id') == 'leveling-assassin' and r['name'] == name else r
        for r in utility['rows']
    ]
    assert not any(r['source_id'] == 'leveling-assassin' for r in build([candidate(name)], utility=utility)['rows'])


@pytest.mark.parametrize(
    ('name', 'label', 'locator'),
    [
        ('Raven Frost', 'Ravenfrost', 'essentials-header/item/89@(77, 804)'),
        ("Mara's Kaleidoscope", 'Maras Kaleidoscope', 'essentials-header/item/95@(77, 2873)'),
    ],
)
def test_reviewed_guide_spelling_keeps_canonical_identity_and_exact_original_label(name, label, locator):
    utility = {
        'sources': [{'id': 'leveling-assassin', 'sha256': GUIDE_SOURCE_SHA256['leveling-assassin']}],
        'rows': [{'name': label, 'source_id': 'leveling-assassin', 'source_locator': locator}],
    }
    result = build([candidate(name)], utility=utility)
    rows = [r for r in result['rows'] if r['source_id'] == 'leveling-assassin']
    assert len(rows) == 1
    assert rows[0]['name'] == name
    assert rows[0]['item_id'] == 'test:' + name
    assert rows[0]['source_label'] == label
    assert rows[0]['source_locator'] == locator
    # The reviewed spelling binds to this occurrence, not arbitrary normalization.
    utility['rows'][0]['name'] = name
    assert not any(r['source_id'] == 'leveling-assassin' for r in build([candidate(name)], utility=utility)['rows'])
    utility['rows'][0]['name'] = label
    duplicate = {'name': 'other', 'item_id': 'other', 'aliases': [name]}
    assert not any(
        r['source_id'] == 'leveling-assassin'
        for r in build(
            [candidate(name)], facts=[{'name': name, 'item_id': 'one', 'aliases': []}, duplicate], utility=utility
        )['rows']
    )


@pytest.mark.parametrize(('cls', 'respec'), [('barbarian', 31), ('paladin', 18)])
@pytest.mark.parametrize('name', ["Death's Hand", "Death's Guard", 'Bloodfist'])
def test_early_melee_gloves_preserve_respec_scope_and_bloodfist_exception(cls, respec, name):
    import json
    from pathlib import Path

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())
    result = build([candidate(name)], utility=utility)
    row = next((r for r in result['rows'] if r['source_id'] == 'leveling-' + cls), None)
    assert row is not None
    assert row['review'].startswith('2026-09-26:')
    assert row['classes'] == [cls]
    advice = ' '.join([row['reason'], *row['conditions']])
    if name == 'Bloodfist':
        assert 'entire leveling' in advice
        assert 'casting' in advice
        assert row['archetypes'] == ['general']
    else:
        assert str(respec) in advice
        assert 'respec' in advice
        assert "Death's Hand" in advice
        assert "Death's Guard" in advice
        assert '30%' in advice
        assert '15%' in advice
        assert 'belt itself' in advice
        assert row['archetypes'] == ['melee']
    for r in utility['rows']:
        if r.get('source_id') == 'leveling-' + cls and r['name'] == name:
            r['source_locator'] = 'changed'
    assert not any(r['source_id'] == 'leveling-' + cls for r in build([candidate(name)], utility=utility)['rows'])


@pytest.mark.parametrize(
    ('cls', 'names', 'scope'),
    [
        (
            'barbarian',
            ['Skin of the Vipermagi', 'Magefist', 'The Eye of Etlich', 'The Stone of Jordan', "Arreat's Face"],
            'after level 31 respec',
        ),
        ('paladin', ['The Eye of Etlich', 'The Stone of Jordan'], 'after level 18 respec'),
        ('druid', ['The Eye of Etlich', 'The Stone of Jordan', 'Lidless Wall', "Jalal's Mane"], None),
    ],
)
def test_caster_leveling_options_preserve_stage_and_mechanics(cls, names, scope):
    import json
    from pathlib import Path

    utility = json.loads(Path('pricing/data/appraisal-utility.json').read_text())
    result = build([candidate(name) for name in names], utility=utility)
    rows = {r['name']: r for r in result['rows'] if r['source_id'] == 'leveling-' + cls}
    assert set(rows) == set(names)
    for name, row in rows.items():
        assert row['classes'] == [cls]
        assert row['archetypes'] == ['caster']
        assert row['review'].startswith('2026-09-26:')
        advice = ' '.join([row['reason'], *row['conditions']])
        if scope:
            assert scope in advice
        if name == 'Magefist':
            assert 'War Cry' in advice
            assert 'fire-skill bonus does not' in advice
        if name == 'The Eye of Etlich':
            assert 'alternative' in advice
        if name == 'The Stone of Jordan':
            assert 'already available' in advice
        if name == 'Lidless Wall':
            assert "Ancient's Pledge" in advice
            assert 'resistances elsewhere' in advice
        if name == "Jalal's Mane":
            assert '+2 to Druid Skills' in advice
            assert '+2 to All Skills' not in advice
            assert 'Lore' in advice
        if name == "Arreat's Face":
            assert 'attack rating does not improve War Cry' in advice
    for row in utility['sources']:
        if row['id'] == 'leveling-' + cls:
            row['sha256'] = 'changed'
    assert not any(
        r['source_id'] == 'leveling-' + cls for r in build([candidate(n) for n in names], utility=utility)['rows']
    )


def test_spirit_shroud_is_conditional_leveling_alternative_not_generic_best_armor():
    row = build([candidate('The Spirit Shroud')])['rows'][0]
    assert row['priority'] == 3
    assert row['evidence_strength'] == 'reviewed_inference'
    assert row['source_date'] == '2025-04-24'
    assert row['review'].startswith('2026-09-26:')
    assert 'Cannot Be Frozen' in row['reason']
    assert any('already' in condition and 'Cannot Be Frozen' in condition for condition in row['conditions'])
    assert 'warlock' in row['classes']
