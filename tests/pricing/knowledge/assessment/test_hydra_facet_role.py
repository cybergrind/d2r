from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_hydra_standard_accepts_low_fire_facets_without_claiming_complete_setup():
    profile = next((p for p in build()['profiles'] if p['id'] == 'hydra-standard-fire-facet'), None)
    assert profile is not None
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        stats={
            '329:0': {'status': 'decoded', 'value': 3},
            '333:0': {'status': 'decoded', 'value': 3},
        },
    )
    result = assess_roles(item, [profile], {'player_class': 'Sorceress'})[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    assert '105%' in ' '.join(result['missing'])
    assert all(pref['status'] == 'false' for pref in result['preferences'])
    perfect = replace(item, stats={k: {**v, 'value': 5} for k, v in item.stats.items()})
    assert all(
        pref['status'] == 'true'
        for pref in assess_roles(perfect, [profile], {'player_class': 'Sorceress'})[0]['preferences']
    )
    for changed in (
        replace(item, stats={}),
        replace(item, stats={'330:0': {'status': 'decoded', 'value': 5}, '334:0': {'status': 'decoded', 'value': 5}}),
        replace(item, stats={**item.stats, '333:0': {'status': 'decoded', 'value': 6}}),
    ):
        assert assess_roles(changed, [profile], {'player_class': 'Sorceress'})[0]['status'] == 'failed'
    unknown = replace(item, capture_complete=False, stats={})
    assert assess_roles(unknown, [profile], {'player_class': 'Sorceress'})[0]['status'] == 'partial'


def test_hydra_fcr_dependency_resolves_only_from_the_assessed_loadout_total():
    profile = next(p for p in build()['profiles'] if p['id'] == 'hydra-standard-fire-facet')
    item = replace(
        facts('Jewel', 'unique', 'Rainbow Facet'),
        stats={
            '329:0': {'status': 'decoded', 'value': 3},
            '333:0': {'status': 'decoded', 'value': 3},
        },
    )
    for total, expected in ((None, 'unknown'), (104, 'false'), (105, 'true')):
        role = assess_roles(item, [profile], {'player_class': 'Sorceress', 'player_total_fcr': total})[0]
        assert len(role['dependencies']) == 1
        assert role['dependencies'][0]['status'] == expected
        assert role['status'] == 'partial'  # Recipient and survivability still need review.
        assert any('105%' in text for text in role['missing']) == (expected != 'true')
