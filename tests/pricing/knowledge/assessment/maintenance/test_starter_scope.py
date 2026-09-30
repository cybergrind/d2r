"""Reviewed ordinary starter variants exclude only their own source mentions."""

import hashlib
import json

import pytest

from pricing.knowledge.assessment.maintenance.starter_scope import starter_exclusions
from pricing.knowledge.assessment.maintenance.value_scope import SCOPE


BUILD = 'demo-build'
PURPOSE = 'Meets the minimum gear requirements for farming the Starter-tagged areas.'
VARIANTS = f'pricing/data/wp-a-variants/{BUILD}.json'
BUILDS = 'pricing/data/wp-a-builds.json'
GUIDE = f'pricing/raw/mr/guides__{BUILD}.html'
PLANNER = 'pricing/raw/mr/planners/ab01cd23.json'


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def pin(root, path):
    return {'path': path, 'sha256': hashlib.sha256((root / path).read_bytes()).hexdigest()}


def fixture(root):
    variant = {'name': 'Starter', 'purpose': PURPOSE, 'player': {'Weapon': ['Spirit']}}
    write(root, VARIANTS, json.dumps({'variants': [variant, {'name': 'Standard', 'purpose': 'Endgame.'}]}))
    write(root, BUILDS, json.dumps({BUILD: {'variants': [variant]}}))
    write(root, GUIDE, '<span class="d2planner-item" data-d2planner-profile="ab01cd23" data-d2planner-id="4">x</span>')
    profiles = [{'name': 'Starter'}, {'name': 'Standard'}]
    write(
        root,
        PLANNER,
        json.dumps({'name': 'Demo Build', 'data': json.dumps({'planner': {'items': {}, 'profiles': profiles}})}),
    )
    row = {
        'build': BUILD,
        'variant': 'Starter',
        'classification': 'generic_leveling',
        'reviewed_at': '2026-09-30',
        'reason': 'Ordinary starter progression; item identities stay in scope.',
        'source': {**pin(root, VARIANTS), 'locator': '/variants/0'},
        'quote': PURPOSE,
        'mirrors': [{**pin(root, BUILDS), 'locator': f'/{BUILD}/variants/0'}],
        'guide': pin(root, GUIDE),
        'planners': [{**pin(root, PLANNER), 'title': 'Demo Build', 'profile': '/profiles/0'}],
    }
    return {'schema_version': 1, 'scope': SCOPE, 'variants': [row]}


def occurrence(oid, source_id, locator, **extra):
    return {
        'id': oid,
        'build': BUILD,
        'variant': 'Starter',
        'source_id': source_id,
        'source_locator': locator,
        'source_status': 'verified',
        'identity_id': 'identity-' + oid,
        'source_rule_ids': [],
        **extra,
    }


def occurrences():
    return [
        occurrence('guide', VARIANTS, '/variants/0/player/Weapon/0'),
        occurrence('mirror', BUILDS, f'/{BUILD}/variants/0/player/Weapon/0'),
        occurrence('planner', PLANNER, '/profiles/0/items/rarm'),
        occurrence('standard-planner', PLANNER, '/profiles/1/items/rarm', variant='Standard'),
        occurrence('standard-guide', VARIANTS, '/variants/1/player/Weapon/0', variant='Standard'),
        occurrence('other-build', PLANNER, '/profiles/0/items/head', build='other-build'),
        occurrence('reviewed', VARIANTS, '/variants/0/player/Weapon/1'),
        occurrence('unverified', VARIANTS, '/variants/0/player/Weapon/2', source_status='missing'),
        occurrence('retained-rule', VARIANTS, '/variants/0/player/Amulet/0', source_rule_ids=['specialist-amulet']),
        occurrence('excluded-rule', VARIANTS, '/variants/0/player/Amulet/1', source_rule_ids=['starter-dagger']),
        occurrence('prefix', VARIANTS, '/variants/01/player/Weapon/0'),
    ]


PROFILES = [{'id': 'specialist-amulet', 'qualities': ['magic']}, {'id': 'starter-dagger', 'qualities': ['magic']}]
EXCLUDED_USES = {'use:starter-dagger:magic'}


def test_only_unreviewed_mentions_in_the_reviewed_starter_variant_are_excluded(tmp_path):
    review = fixture(tmp_path)
    result = starter_exclusions(review, occurrences(), tmp_path, {'reviewed'}, PROFILES, EXCLUDED_USES)
    assert set(result) == {'guide', 'mirror', 'planner', 'excluded-rule'}
    disposition = result['planner']
    assert disposition['state'] == 'excluded'
    assert disposition['source'] == {'artifact': 'value_scope', 'locator': '/variants/0'}
    assert disposition['identity_id'] == 'identity-planner'
    assert 'identities stay in scope' in disposition['reason']


def test_absent_variant_reviews_exclude_nothing(tmp_path):
    fixture(tmp_path)
    assert starter_exclusions(None, occurrences(), tmp_path, set(), PROFILES, EXCLUDED_USES) == {}
    review = {'schema_version': 1, 'scope': SCOPE}
    assert starter_exclusions(review, occurrences(), tmp_path, set(), PROFILES, EXCLUDED_USES) == {}


@pytest.mark.parametrize(
    'mutation',
    [
        'variant-file',
        'quote',
        'name',
        'classification',
        'date',
        'duplicate',
        'mirror-purpose',
        'mirror-build',
        'guide-link',
        'planner-title',
        'planner-profile',
        'planner-path',
        'locator',
        'reason',
    ],
)
def test_stale_or_unlinked_starter_reviews_are_rejected(tmp_path, mutation):
    review = fixture(tmp_path)
    row = review['variants'][0]
    if mutation == 'variant-file':
        write(tmp_path, VARIANTS, json.dumps({'variants': [{'name': 'Starter', 'purpose': PURPOSE + ' Changed.'}]}))
    elif mutation == 'quote':
        row['quote'] = 'Endgame.'
    elif mutation == 'name':
        row['variant'] = 'Standard'
    elif mutation == 'classification':
        row['classification'] = 'non_leveling_use'
    elif mutation == 'date':
        row['reviewed_at'] = 'recently'
    elif mutation == 'duplicate':
        review['variants'].append(dict(row))
    elif mutation == 'mirror-purpose':
        other = {BUILD: {'variants': [{'name': 'Starter', 'purpose': 'Different.'}]}}
        row['mirrors'][0]['sha256'] = write(tmp_path, BUILDS, json.dumps(other))
    elif mutation == 'mirror-build':
        row['mirrors'][0]['locator'] = '/other-build/variants/0'
    elif mutation == 'guide-link':
        row['guide']['sha256'] = write(tmp_path, GUIDE, '<p>no planner links</p>')
    elif mutation == 'planner-title':
        row['planners'][0]['title'] = 'Fury Druid'
    elif mutation == 'planner-profile':
        row['planners'][0]['profile'] = '/profiles/1'
    elif mutation == 'planner-path':
        row['planners'][0]['path'] = '../ab01cd23.json'
    elif mutation == 'locator':
        row['source']['locator'] = '/variants/1'
    elif mutation == 'reason':
        row['reason'] = ' '
    with pytest.raises(ValueError, match=r'(?i)starter|isoformat'):
        starter_exclusions(review, occurrences(), tmp_path, set(), PROFILES, EXCLUDED_USES)


def test_planner_links_accept_tooltip_attributes(tmp_path):
    review = fixture(tmp_path)
    tooltip = '<span class="d2-planner-tooltip" data-d2-id="ab01cd23" data-d2-set-id="X" data-d2-item-id="4">x</span>'
    review['variants'][0]['guide']['sha256'] = write(tmp_path, GUIDE, tooltip)
    result = starter_exclusions(review, occurrences(), tmp_path, set(), PROFILES, EXCLUDED_USES)
    assert 'planner' in result
