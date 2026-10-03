"""User scope exclusions cannot erase unrelated valuable configurations."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.value_scope import profile_fingerprint, use_exclusions


def inputs(tmp_path):
    import hashlib

    source = tmp_path / 'source.json'
    source.write_text('temporary gear source')
    profile = {
        'id': 'temporary-dagger',
        'qualities': ['magic', 'rare'],
        'must': {'skill': 1},
        'source': {
            'path': 'source.json',
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'quotes': ['Temporary gear before Spirit'],
        },
    }
    review = {
        'schema_version': 1,
        'scope': 'non_ladder_value_and_exceptional_leveling',
        'uses': [
            {
                'profile_id': profile['id'],
                'profile_sha256': profile_fingerprint(profile),
                'classification': 'generic_leveling',
                'reason': 'Temporary modest skill bonus.',
                'source': profile['source'],
                'quote': profile['source']['quotes'][0],
            }
        ],
    }
    return profile, review


def test_exact_use_exclusion_preserves_other_uses_and_whole_item(tmp_path):
    profile, review = inputs(tmp_path)
    result = use_exclusions([profile, {**profile, 'id': 'valuable-dagger'}], review, tmp_path)
    assert set(result) == {'use:temporary-dagger:magic', 'use:temporary-dagger:rare'}
    assert result['use:temporary-dagger:rare']['reason'] == 'Temporary modest skill bonus.'


@pytest.mark.parametrize('mutation', ['profile', 'source', 'quote', 'classification', 'duplicate', 'missing'])
def test_stale_or_unreviewed_scope_exclusions_are_rejected(tmp_path, mutation):
    profile, review = inputs(tmp_path)
    if mutation == 'profile':
        profile['must']['skill'] = 3
    elif mutation == 'source':
        (tmp_path / 'source.json').write_text('valuable version')
    elif mutation == 'quote':
        review['uses'][0]['quote'] = 'not reviewed'
    elif mutation == 'classification':
        review['uses'][0]['classification'] = 'unknown'
    elif mutation == 'duplicate':
        review['uses'].append(deepcopy(review['uses'][0]))
    elif mutation == 'missing':
        review['uses'][0]['profile_id'] = 'missing'
    with pytest.raises(ValueError, match=r'scope profile|generic leveling'):
        use_exclusions([profile], review, tmp_path)


def test_completion_keeps_identity_market_and_migration_work(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from pricing.knowledge.assessment.maintenance.guide_inventory import configurations
    from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs as completion_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_guide_inventory import profile as make_profile

    scoped, review = inputs(tmp_path)
    profile = {**make_profile(), **scoped}
    review['uses'][0]['profile_sha256'] = profile_fingerprint(profile)
    matrix, inventory = completion_inputs()
    inventory['occurrences'] = []
    inventory['configurations'] = configurations([profile])
    inventory['identities'][0].update(name='Test', category='unique', catalog_ids=['unique1'], occurrence_ids=[])
    matrix['rows'][0]['dimensions']['market']['state'] = 'pending'
    for quality in profile['qualities']:
        matrix['rows'].append(
            {
                'id': f'use:{profile["id"]}:{quality}',
                'kind': 'use_quality',
                'profile_id': profile['id'],
                'quality': quality,
                'dimensions': {},
            }
        )
    result = compile_completion(
        matrix, inventory, {'complete': True}, profiles=[profile], value_scope=review, source_root=tmp_path
    )
    ids = {r['id'] for r in result['queue']}
    assert 'identity:a/market' in ids
    assert 'scope:value-migration' in ids
    assert not any(key.startswith('use:temporary-dagger:') for key in ids)
    assert len(result['use_scope_dispositions']) == 2
    assert not result['complete']


def test_occurrence_exclusion_requires_exact_named_source_and_context(tmp_path):
    from pricing.knowledge.assessment.maintenance.value_scope import occurrence_exclusions

    profile, review = inputs(tmp_path)
    profile.update(names=['Temporary Armor'], build='one', variant='early', side='merc', slot='Body Armor')
    profile['source']['locator'] = '/one/merc/early/0'
    review['uses'][0]['profile_sha256'] = profile_fingerprint(profile)
    excluded = use_exclusions([profile], review, tmp_path)
    row = {
        'id': 'exact',
        'name': 'Temporary Armor',
        'original_label': 'Temporary Armor',
        'build': 'one',
        'variant': 'early',
        'side': 'merc',
        'slot': 'Body Armor',
        'source_id': 'source.json',
        'source_locator': '/one/merc/early/0',
        'source_rule_ids': [profile['id']],
        'source_status': 'verified',
        'identity_status': 'resolved',
    }
    neighbours = [
        {**row, 'id': 'player', 'side': 'player'},
        {**row, 'id': 'premium', 'original_label': 'Ethereal Temporary Armor'},
        {**row, 'id': 'other-source', 'source_locator': '/one/merc/early/1'},
        {**row, 'id': 'mixed', 'source_rule_ids': [profile['id'], 'valuable-role']},
        {**row, 'id': 'unknown', 'source_status': 'unknown'},
    ]
    result = occurrence_exclusions([profile], excluded, [row, *neighbours])
    assert set(result) == {'exact'}


def test_reviewed_temporary_merc_uses_do_not_exclude_aura_or_player_roles():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = use_exclusions(profiles, review, root)
    for profile in profiles:
        temporary = profile.get('names') == ['Ground'] and profile['variant'] == 'early' and profile['side'] == 'merc'
        temporary |= profile['id'] == 'strafe-amazon-strength-early-source-recipe'
        protected = profile.get('names') in (['Cure'], ['Lawbringer'], ['Hustle (weapon)'])
        if temporary or protected:
            for quality in profile['qualities']:
                assert (f'use:{profile["id"]}:{quality}' in excluded) is temporary


def test_basic_starter_amulet_uses_preserve_specialist_and_stronger_sources():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = use_exclusions(profiles, review, root)
    ordinary = {
        'nova-starter-amulet',
        'fist-of-the-heavens-paladin-0-magic-skill-fcr-amulet',
        'fist-of-the-heavens-paladin-1-magic-skill-fcr-amulet',
        'fire-warlock-guide-0-magic-skill-fcr-amulet',
        'fissure-druid-0-magic-skill-fcr-amulet',
    }
    protected = {
        'enchant-budget-amulet',
        'enchant-prebuff-amulet',
        'lightning-starter-amulet',
        'poison-nova-necromancer-starter-venomous',
        'poison-nova-necromancer-budget-venomous',
    }
    for role in ordinary | protected:
        assert (f'use:{role}:magic' in excluded) is (role in ordinary)
    # The excluded Fire profile describes only the modest magic item, not the
    # stronger crafted amulet embedded in the same source variant.
    fire = next(p for p in profiles if p['id'] == 'fire-warlock-guide-0-magic-skill-fcr-amulet')
    assert fire['qualities'] == ['magic']
    assert f'use:{fire["id"]}:crafted' not in excluded
    assert any('Bitter Mark' in quote for quote in fire['source']['quotes'])


def dimension_inputs(tmp_path):
    profile, review = inputs(tmp_path)
    entry = review['uses'].pop()
    entry.update(
        classification='non_leveling_use',
        dimension='leveling',
        reviewed_at='2026-09-29',
        reason='Reviewed farming use; item-level leveling review remains separate.',
    )
    review['dimensions'] = [entry]
    return profile, review


def test_modest_crafted_thrower_exclusions_keep_named_and_premium_rare_uses():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = use_exclusions(profiles, review, root)
    for slot in ('weapon', 'offhand'):
        assert f'use:double-throw-starter-crafted-{slot}:crafted' in excluded
        assert f'use:double-throw-rare-planner-{slot}:rare' not in excluded
    for ethereal in ('ethereal', 'nonethereal'):
        for slot in ('weapon', 'off-hand'):
            assert f'use:double-throw-scalper-{ethereal}-{slot}:unique' not in excluded


def test_dimension_scope_excludes_only_leveling_for_the_exact_use(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import compile_completion
    from pricing.knowledge.assessment.maintenance.guide_inventory import configurations
    from tests.pricing.knowledge.assessment.maintenance.test_completion import inputs as completion_inputs
    from tests.pricing.knowledge.assessment.maintenance.test_guide_inventory import profile as make_profile

    scoped, review = dimension_inputs(tmp_path)
    profile = {**make_profile(), **scoped}
    review['dimensions'][0]['profile_sha256'] = profile_fingerprint(profile)
    matrix, inventory = completion_inputs()
    inventory['occurrences'] = []
    inventory['configurations'] = configurations([profile])
    inventory['identities'][0].update(name='Test', category='unique', catalog_ids=['unique1'], occurrence_ids=[])
    matrix['rows'][0]['dimensions']['leveling']['state'] = 'pending'
    for quality in profile['qualities']:
        matrix['rows'].append(
            {
                'id': f'use:{profile["id"]}:{quality}',
                'kind': 'use_quality',
                'profile_id': profile['id'],
                'quality': quality,
                'dimensions': {},
            }
        )
    result = compile_completion(
        matrix, inventory, {'complete': True}, profiles=[profile], value_scope=review, source_root=tmp_path
    )
    ids = {r['id'] for r in result['queue']}
    assert 'identity:a/leveling' in ids
    for quality in profile['qualities']:
        prefix = f'use:{profile["id"]}:{quality}/'
        assert prefix + 'leveling' not in ids
        for dimension in ('market', 'stat_annotations', 'report', 'socket_mechanics'):
            assert prefix + dimension in ids
    assert result['use_scope_dispositions'] == []
    assert len(result['dimension_scope_dispositions']) == 2
    assert not result['complete']


@pytest.mark.parametrize('mutation', ['dimension', 'classification', 'profile', 'source', 'quote', 'date', 'duplicate'])
def test_dimension_scope_rejects_unreviewed_or_overbroad_exclusions(tmp_path, mutation):
    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    profile, review = dimension_inputs(tmp_path)
    entry = review['dimensions'][0]
    if mutation == 'dimension':
        entry['dimension'] = 'market'
    elif mutation == 'classification':
        entry['classification'] = 'unknown'
    elif mutation == 'profile':
        profile['must']['skill'] = 3
    elif mutation == 'source':
        (tmp_path / 'source.json').write_text('changed')
    elif mutation == 'quote':
        entry['quote'] = 'invented'
    elif mutation == 'date':
        entry['reviewed_at'] = 'not reviewed'
    else:
        review['dimensions'].append(deepcopy(entry))
    with pytest.raises(ValueError, match=r'scope profile|non-leveling|scope source|isoformat'):
        dimension_exclusions([profile], review, tmp_path)


def test_reviewed_skullder_farming_dimensions_leave_uses_in_scope():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    dimensions = dimension_exclusions(profiles, review, root)
    farming = [p for p in profiles if '-skullder-body-armor' in p['id'] and p['id'].endswith('-utility-alternative')]
    assert len(farming) == 19
    expected = {f'use:{p["id"]}:unique/leveling' for p in farming}
    assert expected <= dimensions.keys()
    excluded_uses = use_exclusions(profiles, review, root)
    assert not {key.removesuffix('/leveling') for key in expected} & excluded_uses.keys()
    assert all(key.endswith('/leveling') for key in dimensions)


def test_reviewed_jewelry_alternatives_keep_trade_uses_without_leveling_walkthroughs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    selected = [
        p
        for p in profiles
        if p['id'].endswith(
            (
                '-metalgrid-jewelry-casting-alternative',
                '-nature-s-peace-jewelry-casting-alternative',
                '-the-cat-s-eye-jewelry-casting-alternative',
            )
        )
    ]
    assert len(selected) == 17
    dimensions = dimension_exclusions(profiles, review, root)
    expected = {f'use:{p["id"]}:unique/leveling' for p in selected}
    assert expected <= dimensions.keys()
    excluded = use_exclusions(profiles, review, root)
    assert not {key.removesuffix('/leveling') for key in expected} & excluded.keys()
    assert all(key.endswith('/leveling') for key in dimensions)
    assert review['migration_status'] == 'partial'


def test_reviewed_defensive_accessories_keep_trade_and_build_coverage():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    counts = {
        '-dwarf-star-defensive-alternative': 12,
        '-wisp-projector-find-absorb-alternative': 9,
        '-verdungo-s-hearty-cord-defensive-alternative': 17,
        '-string-of-ears-defensive-alternative': 7,
        '-thundergod-s-vigor-defensive-alternative': 12,
        '-highlord-s-wrath-jewelry-casting-alternative': 8,
        '-bk-ring-rings-utility-alternative': 20,
    }
    selected = []
    for suffix, count in counts.items():
        rows = [p for p in profiles if p['id'].endswith(suffix)]
        assert len(rows) == count
        selected.extend(rows)
    dimensions = dimension_exclusions(profiles, review, root)
    expected = {f'use:{p["id"]}:unique/leveling' for p in selected}
    assert len(expected) == 85
    assert expected <= dimensions.keys()
    excluded = use_exclusions(profiles, review, root)
    assert not {key.removesuffix('/leveling') for key in expected} & excluded.keys()
    assert all(key.endswith('/leveling') for key in dimensions)
    assert review['migration_status'] == 'partial'


def test_reviewed_boot_alternatives_preserve_progression_and_set_combination_reviews():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    counts = {
        '-aldur-boots-alternative': 19,
        '-waterwalk-boots-alternative': 14,
        '-trek-boots-alternative': 17,
        '-natalya-s-soul-boots-belts-alternative': 5,
        '-goblin-toe-boots-belts-alternative': 4,
        '-gore-rider-boots-belts-alternative': 5,
    }
    selected = []
    for suffix, count in counts.items():
        rows = [p for p in profiles if p['id'].endswith(suffix)]
        assert len(rows) == count
        selected.extend(rows)
    dimensions = dimension_exclusions(profiles, review, root)
    expected = {f'use:{p["id"]}:{quality}/leveling' for p in selected for quality in p['qualities']}
    assert len(expected) == 64
    assert expected <= dimensions.keys()
    excluded = use_exclusions(profiles, review, root)
    assert not {key.removesuffix('/leveling') for key in expected} & excluded.keys()
    protected = [
        p
        for p in profiles
        if p['id'].endswith(
            (
                '-silkweave-caster-progression-alternative',
                '-sander-s-riprap-boots-belts-alternative',
                '-immortal-king-s-pillar-qualified-equipment',
            )
        )
    ]
    assert len(protected) == 11
    assert not {f'use:{p["id"]}:{q}/leveling' for p in protected for q in p['qualities']} & dimensions.keys()
    assert review['migration_status'] == 'partial'


def test_reviewed_uber_uses_preserve_item_and_non_leveling_obligations():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    dimensions = dimension_exclusions(profiles, review, root)
    uses = use_exclusions(profiles, review, root)
    selected = {
        'echoing-ubers-sazabi-helm',
        'lightning-ubers-ring',
        'hammer-ubers-ias-fire-jewel',
        'echoing-ubers-mercenary-enchant-prebuff',
        'summoner-necromancer-guide-2-torch',
    }
    for profile in profiles:
        if profile['id'] in selected:
            for quality in profile['qualities']:
                key = f'use:{profile["id"]}:{quality}'
                assert key + '/leveling' in dimensions
                assert key not in uses
                assert not any(key + '/' + dimension in dimensions for dimension in ('market', 'stats', 'reports'))
    assert selected <= {p['id'] for p in profiles}
    # Older profiles may retain empty quote arrays only when this review pins
    # the exact raw slot quote; no runtime profile rewrite is needed.
    linked = {'lightning-fury-ubers-boots', 'fissure-druid-ubers-charges-91'}
    for profile in profiles:
        if profile['id'] in linked:
            row = next(r for r in review['dimensions'] if r['profile_id'] == profile['id'])
            assert row['quote_source']['path'] == profile['source']['path']
            assert row['quote_source']['sha256'] == profile['source']['sha256']
            assert all(f'use:{profile["id"]}:{q}/leveling' in dimensions for q in profile['qualities'])
    assert review['migration_status'] == 'partial'


@pytest.mark.parametrize('mutation', [None, 'other-slot', 'other-file', 'hash', 'invented', 'parent', 'no-link'])
def test_dimension_review_can_pin_an_exact_quote_when_profile_has_none(tmp_path, mutation):
    import hashlib
    import json

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    profile, review = dimension_inputs(tmp_path)
    source = tmp_path / 'source.json'
    source.write_text(
        json.dumps({'variants': [{'player': {'Boots': ['Rare Boots 30 FRW / tri-res'], 'Gloves': ['Different slot']}}]})
    )
    profile['source'].update(
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(), locator='/variants/0/player/Boots', quotes=[]
    )
    entry = review['dimensions'][0]
    entry.update(
        profile_sha256=profile_fingerprint(profile),
        source=deepcopy(profile['source']),
        quote='Rare Boots 30 FRW / tri-res',
        quote_source={
            'path': 'source.json',
            'sha256': profile['source']['sha256'],
            'locator': '/variants/0/player/Boots/0',
        },
    )
    if mutation == 'other-slot':
        entry['quote_source']['locator'] = '/variants/0/player/Gloves/0'
        entry['quote'] = 'Different slot'
    elif mutation == 'other-file':
        entry['quote_source']['path'] = 'other.json'
    elif mutation == 'hash':
        entry['quote_source']['sha256'] = 'wrong'
    elif mutation == 'invented':
        entry['quote'] = 'Desired but absent boots'
    elif mutation == 'parent':
        entry['quote_source']['locator'] = '/variants/0'
    elif mutation == 'no-link':
        del entry['quote_source']
    if mutation:
        with pytest.raises(ValueError, match='scope source'):
            dimension_exclusions([profile], review, tmp_path)
    else:
        result = dimension_exclusions([profile], review, tmp_path)
        assert set(result) == {'use:temporary-dagger:magic/leveling', 'use:temporary-dagger:rare/leveling'}
        assert use_exclusions([profile], review, tmp_path) == {}


@pytest.mark.parametrize('mutation', [None, 'other-slot', 'other-file', 'hash', 'invented', 'parent', 'no-link'])
def test_use_review_can_pin_its_exact_equipment_quote_without_rewriting_profile(tmp_path, mutation):
    import hashlib
    import json

    profile, review = inputs(tmp_path)
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'gear': {'Weapon': ['Temporary +1 skill dagger'], 'Swap': ['Valuable prebuff']}}))
    profile['source'] = {
        'path': 'source.json',
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'locator': '/gear/Weapon',
    }
    row = review['uses'][0]
    row.update(
        profile_sha256=profile_fingerprint(profile),
        source=deepcopy(profile['source']),
        quote='Temporary +1 skill dagger',
        quote_source={**profile['source'], 'locator': '/gear/Weapon/0'},
    )
    if mutation == 'other-slot':
        row['quote_source']['locator'] = '/gear/Swap/0'
        row['quote'] = 'Valuable prebuff'
    elif mutation == 'other-file':
        row['quote_source']['path'] = 'other.json'
    elif mutation == 'hash':
        row['quote_source']['sha256'] = 'wrong'
    elif mutation == 'invented':
        row['quote'] = 'Not in this source'
    elif mutation == 'parent':
        row['quote_source']['locator'] = '/gear'
    elif mutation == 'no-link':
        del row['quote_source']
    if mutation:
        with pytest.raises(ValueError, match='generic leveling source'):
            use_exclusions([profile], review, tmp_path)
    else:
        result = use_exclusions([profile, {**profile, 'id': 'valuable-prebuff'}], review, tmp_path)
        assert set(result) == {'use:temporary-dagger:magic', 'use:temporary-dagger:rare'}
        assert 'quotes' not in profile['source']


def test_farming_scope_preserves_trade_and_exceptional_leveling_identity_reviews():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    dimensions = dimension_exclusions(profiles, review, root)
    uses = use_exclusions(profiles, review, root)
    targets = {
        'fire-warlock-mf-boots',
        'nova-mf-amulet',
        'lightning-mf-tal-armor',
        'nova-mf-sc-mana-mf',
        'nova-mf-insight-merc',
        'fissure-druid-magic-find-shield-jmod-base',
    }
    selected = [p for p in profiles if p['id'] in targets]
    assert {p['id'] for p in selected} == targets
    for profile in selected:
        for quality in profile['qualities']:
            key = f'use:{profile["id"]}:{quality}'
            assert key + '/leveling' in dimensions
            assert key not in uses
    assert all(key.startswith('use:') and key.endswith('/leveling') for key in dimensions)
    assert review['migration_status'] == 'partial'


def test_standard_farming_review_does_not_exclude_valuable_gear():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    targets = {
        'fissure-merc-standard-fortitude',
        'fissure-merc-standard-andariel',
        'fissure-standard-pelt',
        'fissure-player-standard-ravenlore',
        'hammer-standard-spirit-shield',
        'meteor-standard-cta-prebuff',
    }
    selected = [p for p in profiles if p['id'] in targets]
    assert {p['id'] for p in selected} == targets
    dimensions = dimension_exclusions(profiles, review, root)
    excluded = use_exclusions(profiles, review, root)
    for profile in selected:
        for quality in profile['qualities']:
            key = f'use:{profile["id"]}:{quality}'
            assert key + '/leveling' in dimensions
            assert key not in excluded
    assert all(key.endswith('/leveling') for key in dimensions)
    assert review['migration_status'] == 'partial'


def test_advanced_socket_bases_keep_assessment_without_leveling_walkthroughs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    ids = {
        'double-throw-barbarian-guide-speed-diadem-socket-base',
        'double-throw-barbarian-guide-nirvana-diadem-socket-base',
        'double-throw-barbarian-guide-luck-diadem-socket-base',
        'strafe-amazon-nirvana-diadem-socket-base',
        'strafe-amazon-speed-diadem-socket-base',
        'strafe-amazon-stability-shroud-socket-base',
        'strafe-amazon-precision-shroud-socket-base',
    }
    dimensions = dimension_exclusions(profiles, review, root)
    expected = {f'use:{ident}:magic/leveling' for ident in ids}
    assert expected <= dimensions.keys()
    excluded = use_exclusions(profiles, review, root)
    assert not {key.removesuffix('/leveling') for key in expected} & excluded.keys()
    assert all(key.endswith('/leveling') for key in dimensions)


def test_harmony_movement_swaps_keep_value_assessment_without_leveling_walkthroughs():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.value_scope import dimension_exclusions

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    builds = (
        'double-throw-barbarian-guide',
        'fissure-druid',
        'lightning-fury-amazon-guide',
        'lightning-sorceress',
        'lightning-strike-amazon',
        'poison-nova-necromancer',
    )
    expected = {
        f'use:{build}-player-harmony-weapon-swap-main-alternatives-word-utility-alternative:{quality}'
        for build in builds
        for quality in ('normal', 'superior', 'low_quality')
    }
    dimensions = dimension_exclusions(profiles, review, root)
    assert {key + '/leveling' for key in expected} <= dimensions.keys()
    assert not expected & use_exclusions(profiles, review, root).keys()


def test_ordinary_starter_fillers_do_not_exclude_premium_candidates():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = use_exclusions(profiles, review, root)
    for role in (
        'summoner-necromancer-guide-starter-rare-amulet',
        'fire-blast-starter-rare-resistance-ring',
        'nova-starter-boots',
    ):
        assert excluded[f'use:{role}:rare']['state'] == 'excluded'
    # These remain review leads: do not infer low demand from a Starter label.
    retained = {
        'nova-starter-ring',
        'lightning-starter-ring',
        'poison-nova-necromancer-0-rhyme',
        'fire-blast-starter-rare-amulet',
        'poison-nova-white-alternative',
        'smite-starter-crafted-belt',
    }
    selected = [profile for profile in profiles if profile['id'] in retained]
    assert {profile['id'] for profile in selected} == retained
    for profile in selected:
        for quality in profile['qualities']:
            assert f'use:{profile["id"]}:{quality}' not in excluded
    assert all(key.startswith('use:') for key in excluded)
    assert review['migration_status'] == 'partial'


def test_ordinary_bulwark_survival_uses_preserve_specialist_and_item_scope():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = use_exclusions(profiles, review, root)
    ordinary = {
        'fissure-starter-merc-bulwark',
        'smite-paladin-0-merc-bulwark-native',
        'zeal-paladin-early-merc-bulwark',
        *{
            build + '-0-merc-bulwark-native'
            for build in (
                'abyss-warlock-build-guide',
                'berserk-barbarian',
                'blessed-hammer-paladin',
                'blizzard-sorceress',
                'double-throw-barbarian-guide',
                'echoing-strike-warlock-guide',
                'fire-warlock-guide',
                'lightning-fury-amazon-guide',
                'lightning-sentry-assassin',
                'lightning-sorceress',
                'lightning-strike-amazon',
                'nova-sorceress-guide',
                'poison-nova-necromancer',
                'strafe-amazon',
                'wake-of-fire-assassin',
            )
        },
    }
    retained = {
        'enchant-sorceress-0-merc-bulwark-native',
        'fist-of-the-heavens-paladin-0-merc-bulwark-native',
        'fist-of-the-heavens-paladin-1-merc-bulwark-native',
        'zeal-paladin-bulwark-player-equipment-alternative',
        'abyss-warlock-merc-table-bulwark',
    }
    selected = {p['id']: p for p in profiles if p['id'] in ordinary | retained}
    assert selected.keys() == ordinary | retained
    for ident, profile in selected.items():
        for quality in profile['qualities']:
            assert (f'use:{ident}:{quality}' in excluded) == (ident in ordinary)
    assert all(key.startswith('use:') for key in excluded)
    assert review['migration_status'] == 'partial'


def test_medium_sigon_walkthroughs_keep_exceptional_leveling_and_item_scope():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    profiles = json.loads((root / 'pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    review = json.loads((root / 'pricing/knowledge/assessment/rules/value_scope_reviews.json').read_text())
    excluded = use_exclusions(profiles, review, root)
    sigon = [p for p in profiles if '-starter-set-Sigon' in p['id']]
    assert len(sigon) == 9
    assert all(f'use:{p["id"]}:set' in excluded for p in sigon)
    valuable = [p for p in profiles if p.get('names') in (["Death's Hand"], ["Death's Guard"], ["Sander's Riprap"])]
    assert valuable
    assert all(f'use:{p["id"]}:set' not in excluded for p in valuable)
    assert all(key.startswith('use:') for key in excluded)
    assert 'pricing/data/appraisal-recommendations.json' in review['inputs']
