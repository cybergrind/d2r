"""A slot can cite its own variant purpose, never another setup's context."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.value_scope import (
    dimension_exclusions,
    profile_fingerprint,
    use_exclusions,
)


def variant_review(tmp_path, layout):
    build = 'example-build'
    variants = [
        {'name': 'Starter', 'purpose': 'Ordinary leveling equipment', 'player': {'Weapon': ['Spirit']}},
        {
            'name': 'Standard',
            'purpose': 'Farm immune monsters with self-wielded Infinity',
            'player': {'Weapon': ['Infinity Scythe']},
        },
    ]
    wrapped = layout == 'builds'
    path = 'pricing/data/wp-a-builds.json' if wrapped else f'pricing/data/wp-a-variants/{build}.json'
    source_file = tmp_path / path
    source_file.parent.mkdir(parents=True)
    source_file.write_text(json.dumps({build: {'variants': variants}} if wrapped else {'variants': variants}))
    anchor = f'/{build}/variants/1' if wrapped else '/variants/1'
    source = {
        'path': path,
        'sha256': hashlib.sha256(source_file.read_bytes()).hexdigest(),
        'locator': anchor + '/player/Weapon/0',
    }
    profile = {
        'id': 'reviewed-weapon',
        'build': build,
        'variant': 'Standard',
        'qualities': ['normal', 'superior'],
        'source': source,
    }
    row = {
        'profile_id': profile['id'],
        'profile_sha256': profile_fingerprint(profile),
        'dimension': 'leveling',
        'classification': 'non_leveling_use',
        'reviewed_at': '2026-09-30',
        'reason': 'Only the additional leveling walkthrough is excluded; retain the farming weapon assessment.',
        'source': deepcopy(source),
        'quote': variants[1]['purpose'],
        'quote_source': {**source, 'locator': anchor + '/purpose'},
        'variant_context': {'locator': anchor, 'name': 'Standard'},
    }
    review = {
        'schema_version': 1,
        'scope': 'non_ladder_value_and_exceptional_leveling',
        'uses': [],
        'dimensions': [row],
    }
    return profile, review


@pytest.mark.parametrize('layout', ['builds', 'variants'])
def test_exact_containing_variant_purpose_can_support_a_dimension_review(tmp_path, layout):
    profile, review = variant_review(tmp_path, layout)
    result = dimension_exclusions([profile], review, tmp_path)
    assert set(result) == {'use:reviewed-weapon:normal/leveling', 'use:reviewed-weapon:superior/leveling'}


def test_variant_purpose_does_not_authorize_excluding_the_whole_use(tmp_path):
    profile, review = variant_review(tmp_path, 'builds')
    row = review['dimensions'].pop()
    row['classification'] = 'generic_leveling'
    review['uses'] = [row]
    with pytest.raises(ValueError, match='generic leveling source'):
        use_exclusions([profile], review, tmp_path)


@pytest.mark.parametrize(
    'mutation',
    [
        'other-variant',
        'other-build',
        'other-name',
        'item-instead-of-purpose',
        'missing-source-slot',
        'noncanonical-index',
        'invented-quote',
        'missing-quote-link',
        'extra-context-field',
        'arbitrary-parent',
    ],
)
def test_variant_context_cannot_borrow_unrelated_or_fabricated_evidence(tmp_path, mutation):
    profile, review = variant_review(tmp_path, 'builds')
    row = review['dimensions'][0]
    if mutation == 'other-variant':
        row['variant_context'] = {'locator': '/example-build/variants/0', 'name': 'Starter'}
        row['quote_source']['locator'] = '/example-build/variants/0/purpose'
        row['quote'] = 'Ordinary leveling equipment'
    elif mutation == 'other-build':
        profile['build'] = 'different-build'
    elif mutation == 'other-name':
        profile['variant'] = row['variant_context']['name'] = 'Different setup'
    elif mutation == 'item-instead-of-purpose':
        row['quote_source']['locator'] = profile['source']['locator']
        row['quote'] = 'Infinity Scythe'
    elif mutation == 'missing-source-slot':
        profile['source']['locator'] = '/example-build/variants/1/player/Absent/0'
    elif mutation == 'noncanonical-index':
        profile['source']['locator'] = '/example-build/variants/01/player/Weapon/0'
        row['variant_context']['locator'] = '/example-build/variants/01'
        row['quote_source']['locator'] = '/example-build/variants/01/purpose'
    elif mutation == 'invented-quote':
        row['quote'] = 'Endgame wording never present in the source'
    elif mutation == 'missing-quote-link':
        del row['quote_source']
    elif mutation == 'extra-context-field':
        row['variant_context']['allow_other_builds'] = True
    elif mutation == 'arbitrary-parent':
        row['variant_context']['locator'] = '/example-build'
    row['source'] = deepcopy(profile['source'])
    row['profile_sha256'] = profile_fingerprint(profile)
    with pytest.raises(ValueError, match='scope source'):
        dimension_exclusions([profile], review, tmp_path)
