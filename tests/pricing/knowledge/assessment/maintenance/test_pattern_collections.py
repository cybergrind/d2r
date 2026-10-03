"""Collection discovery preserves independently reviewed source configurations."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


def inputs():
    identity = {'id': 'collection', 'name': 'Gemmed armor', 'category': 'unresolved', 'occurrence_ids': ['a', 'b']}
    occurrences = [
        {'id': key, 'identity_id': 'collection', 'side': side} for key, side in [('a', 'player'), ('b', 'merc')]
    ]
    profiles = [{'id': 'mf'}, {'id': 'resists'}]
    review = {
        'identity_id': 'collection',
        'identity_fingerprint': fingerprint(identity),
        'review_date': '2026-09-28',
        'reason': 'Same base label, distinct player MF and merc resistance payloads.',
        'members': [
            {
                'occurrence_id': o['id'],
                'occurrence_fingerprint': fingerprint(o),
                'profile_id': p['id'],
                'profile_fingerprint': fingerprint(p),
            }
            for o, p in zip(occurrences, profiles, strict=True)
        ],
    }
    return review, identity, occurrences, profiles, {('a', 'mf'), ('b', 'resists')}


def test_collection_discovery_preserves_every_configuration():
    from pricing.knowledge.assessment.maintenance.pattern_collections import validate_collection

    review, identity, occurrences, profiles, links = inputs()
    result = validate_collection(review, identity, occurrences, profiles, links)
    assert result['occurrence_ids'] == ['a', 'b']
    assert result['profile_ids'] == ['mf', 'resists']
    assert result['identity_id'] == 'collection'
    assert 'price' not in result


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'new', 'stale', 'wrong-link', 'role', 'identity', 'date'])
def test_collection_does_not_hide_unreviewed_or_changed_members(change):
    from pricing.knowledge.assessment.maintenance.pattern_collections import validate_collection

    review, identity, occurrences, profiles, links = deepcopy(inputs())
    if change == 'missing':
        review['members'].pop()
    elif change == 'duplicate':
        review['members'].append(review['members'][0])
    elif change == 'new':
        occurrences.append({'id': 'c', 'identity_id': 'collection'})
    elif change == 'stale':
        occurrences[0]['side'] = 'merc'
    elif change == 'wrong-link':
        links.remove(('a', 'mf'))
        links.add(('a', 'resists'))
    elif change == 'role':
        profiles[0]['must'] = {}
    elif change == 'identity':
        identity['category'] = 'unique'
    else:
        review['review_date'] = 'unknown'
    with pytest.raises(ValueError, match=r'[Cc]ollection'):
        validate_collection(review, identity, occurrences, profiles, links)


@pytest.mark.parametrize(
    ('label', 'count'),
    [
        ('Gemmed Dusk Shroud', 25),
        ('Gemmed Dusk Shroud (4x Perfect Topaz )', 1),
        ('Gemmed Dusk Shroud (4x Perfect Topaz es )', 3),
        ('Gemmed Dusk Shroud (4x Perfect Topaz)', 2),
        ('Gemmed Crown (3x Perfect Topaz)', 2),
        ("Artisan's Crown (3x Perfect Topaz es )", 1),
        ("Artisan's Crown ( Ral Rune , Ort Rune , Thul Rune )", 1),
        ('Ethereal Rare Weapon', 1),
        ('Blood Crafted Armet', 1),
        ('Sharp Grand Charm of Vita', 8),
        ('Sharp Grand Charm of Balance', 7),
        ('Sharp Grand Charm of Inertia', 2),
        ('Sharp Grand Charm of Maiming', 3),
        ('Sharp Grand Charm', 5),
    ],
)
def test_real_armor_collection_closes_only_discovery(label, count):
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix

    def read(path):
        return json.loads(Path(path).read_text())

    inventory = read('pricing/data/appraisal-guide-inventory.json')
    profiles = read('pricing/data/appraisal-build-profiles.json')
    result = build_matrix(
        inventory,
        {'rows': []},
        {'rows': []},
        profiles,
        pattern_reviews=read('pricing/knowledge/assessment/rules/pattern_collection_reviews.json'),
        uses=read('pricing/knowledge/assessment/rules/guide_use_reviews.json'),
        table_reviews=read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json'),
        source_context_reviews=read('pricing/knowledge/assessment/rules/source_context_reviews.json'),
        hardcore_reviews=read('pricing/knowledge/assessment/rules/hardcore_reviews.json'),
    )
    row = next(r for r in result['rows'] if r.get('name') == label)
    assert row['dimensions']['discovery']['state'] == 'reviewed'
    assert row['dimensions']['named_tiers']['state'] == 'excluded'
    assert row['category'] == 'unresolved'  # Collection label remains distinct from the base.
    assert len(row['occurrence_ids']) == count
    for key in ('market', 'report', 'leveling', 'socket_mechanics', 'recipe_eligibility', 'stat_annotations'):
        assert row['dimensions'][key]['state'] == 'pending'
    assert not result['complete']


@pytest.mark.parametrize(
    ('qualities', 'expected'),
    [
        ((['magic'], ['normal', 'superior']), ['magic', 'normal', 'superior']),
        ((['magic'], ['set']), ['magic', 'set']),
        ((['unique'], ['normal']), ['normal', 'unique']),
        ((['magic'], []), []),
        ((['magic'], None), []),
    ],
)
def test_collection_retains_quality_union_or_unknown(qualities, expected):
    from pricing.knowledge.assessment.maintenance.pattern_collections import validate_collection

    review, identity, occurrences, profiles, links = inputs()
    for profile, quality in zip(profiles, qualities, strict=True):
        if quality is not None:
            profile['qualities'] = quality
    for member, profile in zip(review['members'], profiles, strict=True):
        member['profile_fingerprint'] = fingerprint(profile)
    result = validate_collection(review, identity, occurrences, profiles, links)
    assert result['qualities'] == expected


def test_sentry_collection_preserves_separate_conditional_prose_use():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.pattern_collections import compile_collections

    root = Path.cwd()

    def read(path):
        return json.loads((root / path).read_text())

    inventory = read('pricing/data/appraisal-guide-inventory.json')
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    tables = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')
    reviews = read('pricing/knowledge/assessment/rules/pattern_collection_reviews.json')
    context = read('pricing/knowledge/assessment/rules/source_context_reviews.json')
    hardcore = read('pricing/knowledge/assessment/rules/hardcore_reviews.json')
    identity = next(i for i in inventory['identities'] if i['name'] == 'Entrapping Grand Charm of Vita')
    result = compile_collections(
        reviews, inventory, profiles, uses, tables, root, context_reviews=context, hardcore_reviews=hardcore
    )
    assert result[identity['id']]['profile_ids'] == [
        'lightning-sentry-assassin-main-skiller-vita',
        'lightning-sentry-assassin-mf-high-player-skiller',
    ]
    assert len(result[identity['id']]['occurrence_ids']) == 3
    assert result[identity['id']]['qualities'] == ['magic']
    # The main table alone cannot certify the conditional prose occurrence.
    with pytest.raises(ValueError, match='validated source configuration'):
        compile_collections(reviews, inventory, profiles, uses, tables, root, hardcore_reviews=hardcore)


def test_collection_accepts_only_source_verified_foreign_mode_exclusion():
    from pricing.knowledge.assessment.maintenance.pattern_collections import validate_collection

    review, identity, occurrences, profiles, links = inputs()
    excluded = occurrences[1]
    review['members'][1] = {
        'occurrence_id': excluded['id'],
        'occurrence_fingerprint': fingerprint(excluded),
        'excluded_by': 'hardcore-prose',
    }
    proof = {'b': {'id': 'hardcore-prose', 'state': 'excluded'}}
    result = validate_collection(review, identity, occurrences, profiles, links, excluded_occurrences=proof)
    assert result['profile_ids'] == ['mf']
    assert result['occurrence_ids'] == ['a', 'b']
    assert result['excluded_occurrence_ids'] == ['b']
    for invalid in (
        {},
        {'b': {'id': 'other', 'state': 'excluded'}},
        {'b': {'id': 'hardcore-prose', 'state': 'pending'}},
    ):
        with pytest.raises(ValueError, match='scope exclusion'):
            validate_collection(review, identity, occurrences, profiles, links, excluded_occurrences=invalid)
    ambiguous = deepcopy(review)
    ambiguous['members'][1]['profile_id'] = 'resists'
    with pytest.raises(ValueError, match='scope exclusion'):
        validate_collection(ambiguous, identity, occurrences, profiles, links, excluded_occurrences=proof)
