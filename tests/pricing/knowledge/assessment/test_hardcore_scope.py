"""Hardcore source configurations remain auditable without entering Softcore appraisal."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


def source_fixture(tmp_path, *, variant='Hardcore', scope=None):
    path = tmp_path / 'pricing/data/wp-a-builds.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'example': {'variants': [{'name': variant, 'player': {'Helmet': ['Facet']}}]}}))
    role = {
        'id': 'facet',
        'build': 'example',
        'variant': variant,
        'qualities': ['unique'],
        'source': {
            'path': 'pricing/data/wp-a-builds.json',
            'locator': '/example/variants/0/player/Helmet/0',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'quotes': ['Facet'],
        },
    }
    if scope is not None:
        role['scope'] = scope
    return role


@pytest.mark.parametrize(('variant', 'scope'), [('Hardcore', None), ('Hardcore', 'softcore'), ('Standard', 'hardcore')])
def test_structured_variant_cannot_change_game_mode(tmp_path, variant, scope):
    from pricing.knowledge.assessment.profile_sources import validate_profile_sources

    with pytest.raises(ValueError, match='scope'):
        validate_profile_sources(
            {'profiles': [source_fixture(tmp_path, variant=variant, scope=scope)]}, tmp_path, Path.read_bytes
        )


def test_explicit_hardcore_scope_is_valid_but_excluded_from_softcore_candidates(tmp_path):
    from pricing.knowledge.assessment.repository import ProfileRepository
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    document = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    archived = deepcopy(
        next(
            r
            for r in document['profiles']
            if r['id'] == 'blizzard-sorceress-rainbow-facet-v4-weapon-0-named-socket-jewel'
        )
    )
    active = deepcopy(
        next(
            r
            for r in document['profiles']
            if r.get('names') == ['Rainbow Facet'] and 'hardcore' not in r['variant'].lower()
        )
    )
    archived['scope'] = 'hardcore'
    document['profiles'] = [archived, active]
    document.pop('stat_evaluation', None)
    path = tmp_path / 'profiles.json'
    path.write_text(json.dumps(document))
    loaded = ProfileRepository(path).load()
    assert not loaded.issues
    assert len(loaded.bundle.profiles) == 2  # Retain the reviewed source configuration.
    selected = loaded.bundle.candidates.select(facts('Jewel', 'unique', 'Rainbow Facet'))
    assert {r['id'] for r in selected} == {active['id']}


def test_hardcore_use_exclusion_requires_actual_pinned_variant(tmp_path):
    from pricing.knowledge.assessment.maintenance.value_scope import SCOPE, use_exclusions

    role = source_fixture(tmp_path, scope='hardcore')
    row = {
        'profile_id': role['id'],
        'profile_sha256': fingerprint(role),
        'classification': 'hardcore_only',
        'reviewed_at': '2026-09-30',
        'reason': 'This exact source setup is Hardcore, outside the Softcore task.',
        'source': role['source'],
        'quote': 'Facet',
    }
    review = {'schema_version': 1, 'scope': SCOPE, 'uses': [row]}
    assert use_exclusions([role], review, tmp_path)['use:facet:unique']['state'] == 'excluded'
    role = source_fixture(tmp_path, variant='Standard', scope='hardcore')
    row.update(profile_sha256=fingerprint(role), source=role['source'])
    with pytest.raises(ValueError, match=r'[Hh]ardcore'):
        use_exclusions([role], review, tmp_path)


def test_staged_hardcore_roles_cannot_supply_softcore_stat_priorities():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.repository import ProfileRepository

    loaded = ProfileRepository(Path('pricing/data/appraisal-build-profiles.json')).load()
    assert not loaded.issues
    bundle = loaded.bundle
    archived = {p['id'] for p in bundle.profiles if p.get('scope') == 'hardcore'}
    assert archived  # Exercise archived configurations, not an empty fixture.
    unspecified = SimpleNamespace(rarity=None, item_type=None, name=None, base_code=None)
    roles = bundle.candidates.select(unspecified)
    stats = bundle.stat_candidates.select(unspecified)
    assert not archived.intersection(p['id'] for p in roles)
    assert not archived.intersection(p['role_id'] for p in stats)
    assert {p['id'] for p in roles} == {p['id'] for p in bundle.profiles} - archived


def test_guide_demand_cannot_relabel_a_hardcore_profile_as_softcore():
    from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand

    document = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    profile = next(p for p in document['profiles'] if p.get('scope') == 'hardcore')
    use = deepcopy(next(r for r in document['guide_demand']['uses'] if r['profile_id'] == profile['id']))
    assert compile_demand([use], [profile])[use['item']]['distinct_builds'] == 0
    use['scope'] = 'softcore'
    with pytest.raises(ValueError, match='scope'):
        compile_demand([use], [profile])
