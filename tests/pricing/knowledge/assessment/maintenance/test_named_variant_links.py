"""Decorated named-item labels retain their reviewed socket requirements."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope='module')
def records():
    def read(path):
        return json.loads((ROOT / path).read_text())

    inventory = read('pricing/data/appraisal-guide-inventory.json')
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    rows = []
    for index, oid in ((1, 'f4fab9131288b44f1d692920'), (2, 'be5a31b757a62177f1368f83')):
        role = next(p for p in profiles if p['id'] == f'poison-nova-necromancer-{index}-merc-andariel-ias-fire')
        occurrence = next(o for o in inventory['occurrences'] if o['id'] == oid)
        use = next(u for u in uses if u['profile_id'] == role['id'])
        review = {
            'pattern_kind': 'structured_named_variant',
            'occurrence_id': oid,
            'occurrence_fingerprint': fingerprint(occurrence),
            'profile_id': role['id'],
            'profile_fingerprint': fingerprint(role),
            'use_fingerprint': fingerprint(use),
            'review_date': '2026-09-28',
            'reason': 'Exact variant helmet label; verified IAS/fire child and ethereal mercenary conditions retained.',
            'canonical_name': "Andariel's Visage",
            'required_predicates': [
                {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
                {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
                {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'},
                {'op': 'socket_jewel_matches', 'stats': {'93:0': 15, '39:0': 30}, 'count': 1},
            ],
        }
        rows.append((review, occurrence, role, use))
    return rows


def validate(inputs):
    from pricing.knowledge.assessment.maintenance.structured_named_variants import validate_link
    from pricing.knowledge.assessment.maintenance.table_equivalence import _read

    review, occurrence, role, use = inputs
    return validate_link(review, occurrence, role, [use], ROOT, lambda pin: json.loads(_read(ROOT, pin)))


def test_exact_named_variant_bindings_preserve_independent_configurations(records):
    result = [validate(r) for r in records]
    assert len({r['profile_id'] for r in result}) == 2
    assert all(r['state'] == 'reviewed' for r in result)
    assert all('market' not in r and 'price' not in r for r in result)


@pytest.mark.parametrize(
    'change',
    [
        'native-only',
        'optional-jewel',
        'wrong-side',
        'wrong-variant',
        'wrong-name',
        'stale-source',
        'wrong-label',
        'historical',
        'missing-predicates',
        'stale-role',
        'prose-locator',
        'unrecommended',
    ],
)
def test_named_variant_binding_rejects_lost_conditions(records, change):
    review, occurrence, role, use = deepcopy(records[0])
    if change == 'native-only':
        role['must']['all'] = role['must']['all'][:5]
    elif change == 'optional-jewel':
        role['must']['all'][-1] = {
            'any': [role['must']['all'][-1], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    elif change == 'wrong-side':
        occurrence['side'] = 'player'
    elif change == 'wrong-variant':
        occurrence['variant'] = 'Hardcore'
    elif change == 'wrong-name':
        review['canonical_name'] = 'Vampire Gaze'
    elif change == 'stale-source':
        role['source']['sha256'] = '0' * 64
    elif change == 'wrong-label':
        occurrence['name'] = occurrence['original_label'] = "Andariel's Visage (Ral)"
    elif change == 'historical':
        use['historical'] = True
    elif change == 'missing-predicates':
        review['required_predicates'] = []
    elif change == 'prose-locator':
        occurrence['source_locator'] = '/poison-nova-necromancer/prose_only_items/7'
    elif change == 'unrecommended':
        occurrence['details']['recommended'] = False
    else:
        review['profile_fingerprint'] = '0' * 64
    if change != 'stale-role':
        review['profile_fingerprint'] = fingerprint(role)
    review['occurrence_fingerprint'] = fingerprint(occurrence)
    use['source'] = role['source']
    use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'[Nn]amed variant|Source changed'):
        validate((review, occurrence, role, use))


def test_registered_named_variant_reviews_compile_through_source_audit(records):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    ids = {record[1]['id'] for record in records}
    rows = [row for row in reviews['rows'] if row['occurrence_id'] in ids]
    assert len(rows) == 2
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        [record[1] for record in records],
        [record[2] for record in records],
        [record[3] for record in records],
        ROOT,
    )
    assert {row['occurrence_id'] for row in result} == ids
    assert all(row['state'] == 'reviewed' for row in result)


@pytest.mark.parametrize('change', ['retained', 'removed', 'optional', 'different'])
def test_named_variant_binding_preserves_required_dependencies(records, change):
    review, occurrence, role, use = deepcopy(records[0])
    jewel = role['must']['all'].pop()
    review['required_predicates'].remove(jewel)
    review['required_dependencies'] = [jewel]
    role['depends_on'] = [{'label': 'Actual linked jewel', 'when': deepcopy(jewel)}]
    if change == 'removed':
        role['depends_on'] = []
    elif change == 'optional':
        role['depends_on'][0]['when'] = {'any': [jewel, {'op': 'fact_eq', 'field': 'identified', 'value': True}]}
    elif change == 'different':
        role['depends_on'][0]['when']['stats'] = {'93:0': 15, '17:0': 40}
    review['profile_fingerprint'] = fingerprint(role)
    use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    if change == 'retained':
        assert validate((review, occurrence, role, use))['state'] == 'reviewed'
    else:
        with pytest.raises(ValueError, match='dependency'):
            validate((review, occurrence, role, use))


def test_reviewed_socket_variants_bind_without_collapsing_payloads():
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    def read(path):
        return json.loads((ROOT / path).read_text())

    expected = {
        'lightning-strike-amazon-1-griffon-eye',
        'lightning-sorceress-2-griffon-eye',
        'lightning-sentry-assassin-1-griffon-eye',
        'lightning-sorceress-1-griffon-eye',
        'meteor-sorceress-4-stormshield',
        'lightning-sorceress-3-stormshield',
        'wake-of-fire-assassin-0-rhyme',
    }
    reviews = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')
    rows = [row for row in reviews['rows'] if row['profile_id'] in expected]
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert len(result) == 7
    assert {row['profile_id'] for row in result} == expected


def test_fissure_flame_prose_binds_recipe_without_inventing_ideal_staffmods():
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    def read(path):
        return json.loads((ROOT / path).read_text())

    identity = 'fissure-player-standard-flickering-flame'
    rows = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['profile_id'] == identity
    ]
    assert len(rows) == 1
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        profiles,
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert len(result) == 1
    assert result[0]['state'] == 'reviewed'
    # The prose calls an ideal base great, but supplies no mandatory staffmod threshold.
    # Useful non-staffmod bases are covered independently by the constructed-item bank.
    assert '107:234' not in json.dumps(rows[0]['required_predicates'])
    assert {'op': 'fact_eq', 'field': 'runeword', 'value': 'Flickering Flame'} in rows[0]['required_predicates']


def test_strafe_nagelring_source_retains_equipped_helmet_dependency():
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    def read(path):
        return json.loads((ROOT / path).read_text())

    identity = 'strafe-mf-stealskull-nagelring'
    rows = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['profile_id'] == identity
    ]
    assert len(rows) == 1
    assert rows[0]['required_dependencies'][0]['op'] == 'equipped_item_matches'
    assert rows[0]['required_dependencies'][0]['field'] == 'player_equipment'
    assert rows[0]['required_dependencies'][0]['slot'] == 'head'
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert len(result) == 1
    assert result[0]['state'] == 'reviewed'


@pytest.mark.parametrize(
    ('variant', 'oid'),
    [
        ('standard', 'cee2f50d84a070bbed67e2dd'),
        ('magic-find', 'f90a0d77f48889f941ef6c9e'),
    ],
)
def test_resolved_fissure_identity_still_requires_exact_socket_configuration(variant, oid):
    def read(path):
        return json.loads((ROOT / path).read_text())

    role = next(
        r
        for r in read('pricing/data/appraisal-build-profiles.json')['profiles']
        if r['id'] == f'fissure-merc-{variant}-andariel'
    )
    occurrence = next(o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if o['id'] == oid)
    use = next(
        u
        for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
        if u['profile_id'] == role['id']
    )
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': oid,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': "Andariel's Visage",
        'review_date': '2026-09-28',
        'reason': 'Resolved identity does not replace actual IAS/damage jewel and companion requirements.',
        'required_predicates': [role['must']],
        'required_dependencies': [dep['when'] for dep in role['depends_on']],
    }
    assert validate((review, occurrence, role, use))['state'] == 'reviewed'
    registered = next(
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['occurrence_id'] == oid
    )
    assert registered['required_dependencies'] == review['required_dependencies']
    assert validate((registered, occurrence, role, use))['state'] == 'reviewed'
    for change in ('wrong-name', 'wrong-basis', 'removed-jewel', 'optional-jewel'):
        rr, oo, pp, uu = deepcopy((review, occurrence, role, use))
        if change == 'wrong-name':
            oo['name'] = 'Vampire Gaze'
        elif change == 'wrong-basis':
            oo['identity_basis'] = 'unverified_guess'
        elif change == 'removed-jewel':
            pp['depends_on'].pop()
        else:
            pp['depends_on'][-1]['when'] = {'any': [pp['depends_on'][-1]['when'], pp['must']]}
        rr['occurrence_fingerprint'] = fingerprint(oo)
        rr['profile_fingerprint'] = uu['profile_fingerprint'] = fingerprint(pp)
        rr['use_fingerprint'] = fingerprint(uu)
        with pytest.raises(ValueError, match=r'named variant context|required dependency'):
            validate((rr, oo, pp, uu))


def test_registered_resolved_jewelry_keeps_variant_class_and_fcr_requirements():
    def read(path):
        return json.loads((ROOT / path).read_text())

    maras = {
        'blizzard-sorceress-1': 105,
        'echoing-strike-warlock-guide-1': 125,
        'abyss-warlock-build-guide-1': 125,
        'lightning-sorceress-1': 117,
        'summoner-necromancer-guide-1': 125,
        'blessed-hammer-paladin-1': 125,
        'fissure-druid-3': None,
        'lightning-sentry-assassin-1': 65,
        'summoner-necromancer-guide-2': 75,
        'echoing-strike-warlock-guide-3': None,
        'echoing-strike-warlock-guide-2': 125,
    }
    raven = (
        'dream-paladin-0',
        'dream-paladin-1',
        'dream-paladin-2',
        'strafe-amazon-1',
        'strafe-amazon-2',
        'lightning-strike-amazon-1',
        'lightning-strike-amazon-2',
        'blessed-hammer-paladin-3',
        'berserk-barbarian-1',
        'mirrored-blades-warlock-guide-1',
        'mirrored-blades-warlock-guide-2',
        'dragon-talon-assassin-0',
        'dragon-talon-assassin-1',
        'smite-paladin-1',
        'smite-paladin-2',
        'lightning-fury-amazon-guide-1',
        'lightning-fury-amazon-guide-2',
        'lightning-fury-amazon-guide-3',
    )
    expected = {key + '-maras' for key in maras} | {key + '-raven-frost' for key in raven}
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in expected
    ]
    assert len(rows) == len(expected) == 29
    profiles = {p['id']: p for p in read('pricing/data/appraisal-build-profiles.json')['profiles']}
    occurrences = {o['id']: o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences']}
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    for review in rows:
        role = profiles[review['profile_id']]
        use = next(u for u in uses if u['profile_id'] == role['id'])
        occurrence = occurrences[review['occurrence_id']]
        assert occurrence['name'] == occurrence['original_label'] == review['canonical_name']
        assert validate((review, occurrence, role, use))['state'] == 'reviewed'
        required = review['required_predicates']
        assert {'op': 'context_eq', 'field': 'player_class', 'value': occurrence['class']} in required
        if role['id'].endswith('-maras'):
            target = maras[role['id'].removesuffix('-maras')]
            thresholds = [r for r in required if r.get('field') == 'player_total_fcr']
            assert thresholds == (
                [] if target is None else [{'op': 'context_at_least', 'field': 'player_total_fcr', 'value': target}]
            )


def test_soj_source_links_preserve_two_ring_occurrences_and_phoenix_requirements():
    def read(path):
        return json.loads((ROOT / path).read_text())

    # Independent variant counts retain two listed ring slots as two source links.
    expected = {
        'lightning-sentry-assassin-1-soj': (2, 65),
        'fissure-druid-1-soj': (1, 99),
        'fissure-druid-2-soj': (1, None),
        'fissure-druid-3-soj': (1, None),
        'nova-sorceress-guide-1-soj': (2, 105),
        'nova-sorceress-guide-2-soj': (2, None),
        'nova-sorceress-guide-3-soj': (2, None),
        'blizzard-sorceress-1-soj': (2, 105),
        'summoner-necromancer-guide-1-soj': (1, 125),
        'summoner-necromancer-guide-2-soj': (2, 75),
        'lightning-sorceress-1-soj': (2, 117),
        'fire-blast-standard-soj-phoenix': (1, 102),
        'poison-nova-necromancer-1-soj': (1, 125),
        'poison-nova-necromancer-2-soj': (1, 125),
        'enchant-sorceress-1-soj': (1, None),
    }
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in expected
    ]
    assert Counter(r['profile_id'] for r in rows) == {key: count for key, (count, _) in expected.items()}
    assert len({r['occurrence_id'] for r in rows}) == 22
    profiles = {p['id']: p for p in read('pricing/data/appraisal-build-profiles.json')['profiles']}
    occurrences = {o['id']: o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences']}
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    for review in rows:
        role = profiles[review['profile_id']]
        use = next(u for u in uses if u['profile_id'] == role['id'])
        occurrence = occurrences[review['occurrence_id']]
        assert occurrence['name'] == occurrence['original_label'] == 'The Stone of Jordan'
        assert validate((review, occurrence, role, use))['state'] == 'reviewed'
        threshold = expected[role['id']][1]
        fcr = [r for r in review['required_predicates'] if r.get('field') == 'player_total_fcr']
        assert fcr == (
            [] if threshold is None else [{'op': 'context_at_least', 'field': 'player_total_fcr', 'value': threshold}]
        )
        if role['id'] == 'fire-blast-standard-soj-phoenix':
            deps = review['required_dependencies']
            assert {d['slot'] for d in deps} == {'amulet', 'off_hand'}
            assert all(d['op'] == 'equipped_item_matches' and d['field'] == 'player_equipment' for d in deps)
            amulet = next(d for d in deps if d['slot'] == 'amulet')['when']['all']
            assert {'op': 'stat_at_least', 'key': '105:0', 'value': 12, 'absent_is_zero': True} in amulet
            shield = next(d for d in deps if d['slot'] == 'off_hand')['when']['all']
            assert {'op': 'fact_eq', 'field': 'runeword', 'value': 'Phoenix'} in shield
