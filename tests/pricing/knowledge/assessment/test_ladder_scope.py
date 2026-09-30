"""Ladder use evidence cannot enter the fixed Softcore / Non-Ladder assessment."""

from copy import deepcopy
from pathlib import Path

import pytest

from tests.pricing.knowledge.assessment.test_hardcore_scope import source_fixture


@pytest.mark.parametrize('variant', ['Ladder', 'Ladder Only', 'Hardcore Ladder'])
def test_ladder_variant_requires_explicit_ladder_review(tmp_path, variant):
    from pricing.knowledge.assessment.profile_sources import validate_profile_sources

    profile = source_fixture(tmp_path, variant=variant, scope='hardcore' if 'Hardcore' in variant else 'softcore')
    with pytest.raises(ValueError, match='season'):
        validate_profile_sources({'profiles': [profile]}, tmp_path, Path.read_bytes)
    profile['season'] = 'ladder'
    validate_profile_sources({'profiles': [profile]}, tmp_path, Path.read_bytes)


@pytest.mark.parametrize('variant', ['Non-Ladder', 'Non Ladder', 'Nonladder'])
def test_non_ladder_source_cannot_be_mislabeled_ladder(tmp_path, variant):
    from pricing.knowledge.assessment.profile_sources import validate_profile_sources

    profile = source_fixture(tmp_path, variant=variant, scope='softcore')
    validate_profile_sources({'profiles': [profile]}, tmp_path, Path.read_bytes)
    profile['season'] = 'ladder'
    with pytest.raises(ValueError, match='season'):
        validate_profile_sources({'profiles': [profile]}, tmp_path, Path.read_bytes)


def test_ladder_demand_does_not_vote_for_non_ladder_value():
    from pricing.knowledge.assessment.demand_counts import summarize_demand
    from tests.pricing.knowledge.assessment.maintenance.test_guide_demand import use

    assert summarize_demand([use('ladder-build', season='ladder')], complete=False)['distinct_builds'] == 0
    assert summarize_demand([use('non-ladder-build', season='non_ladder')], complete=False)['distinct_builds'] == 1


def test_ladder_profile_is_archived_but_not_a_runtime_candidate(tmp_path):
    import json

    from pricing.knowledge.assessment.repository import ProfileRepository
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    document = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    active = deepcopy(
        next(
            p
            for p in document['profiles']
            if p.get('names') == ['Rainbow Facet'] and p.get('scope', 'softcore') == 'softcore'
        )
    )
    archived = deepcopy(active)
    archived.update(id=active['id'] + '-ladder', season='ladder')
    document['profiles'] = [active, archived]
    document.pop('stat_evaluation', None)
    path = tmp_path / 'profiles.json'
    path.write_text(json.dumps(document))
    loaded = ProfileRepository(path).load()
    assert not loaded.issues
    assert len(loaded.bundle.profiles) == 2
    selected = loaded.bundle.candidates.select(facts('Jewel', 'unique', 'Rainbow Facet'))
    assert {r['id'] for r in selected} == {active['id']}


def test_ladder_exclusion_requires_pinned_ladder_source(tmp_path):
    from pricing.knowledge.assessment.maintenance.value_scope import SCOPE, profile_fingerprint, use_exclusions

    role = source_fixture(tmp_path, variant='Ladder', scope='softcore')
    role['season'] = 'ladder'
    row = {
        'profile_id': role['id'],
        'profile_sha256': profile_fingerprint(role),
        'classification': 'ladder_only',
        'reviewed_at': '2026-09-30',
        'reason': 'Exact Ladder-only source use is outside the Non-Ladder task.',
        'source': role['source'],
        'quote': 'Facet',
    }
    review = {'schema_version': 1, 'scope': SCOPE, 'uses': [row]}
    assert use_exclusions([role], review, tmp_path)['use:facet:unique']['state'] == 'excluded'
    role = source_fixture(tmp_path, variant='Standard', scope='softcore')
    role['season'] = 'ladder'
    row.update(profile_sha256=profile_fingerprint(role), source=role['source'])
    with pytest.raises(ValueError, match='Ladder'):
        use_exclusions([role], review, tmp_path)


def test_ladder_guide_use_cannot_default_to_non_ladder():
    from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
    from pricing.knowledge.assessment.maintenance.value_scope import profile_fingerprint
    from tests.pricing.knowledge.assessment.maintenance.test_guide_demand import use

    profile = {
        'id': 'example',
        'names': ['Facet'],
        'build': 'example',
        'variant': 'Ladder',
        'side': 'player',
        'source': {'path': 'source'},
        'scope': 'softcore',
        'season': 'ladder',
    }
    review = dict(
        use('example', variant='Ladder'),
        profile_id='example',
        item='Facet',
        source=profile['source'],
        profile_fingerprint=profile_fingerprint(profile),
    )
    with pytest.raises(ValueError, match='season'):
        compile_demand([review], [profile])
    review['season'] = 'ladder'
    assert compile_demand([review], [profile])['Facet']['distinct_builds'] == 0
