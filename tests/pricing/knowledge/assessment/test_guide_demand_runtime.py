import json

import pytest

from pricing.knowledge.assessment.guide_demand import demand_for, validate_demand


def test_runtime_reads_only_prepared_summary_and_legacy_bundle_has_no_claim():
    assert demand_for('Insight', {'profiles': []}) is None
    doc = {'guide_demand': {'summaries': {'Insight': {'grade': 'Pending', 'distinct_builds': 5}}}}
    assert demand_for('Insight', doc)['distinct_builds'] == 5
    assert demand_for('Other', doc) is None


def test_publication_rejects_forged_demand_count():
    doc = {'profiles': [], 'guide_demand': {'uses': [], 'summaries': {'Insight': {'distinct_builds': 99}}}}
    with pytest.raises(ValueError, match='demand'):
        validate_demand(doc)
    doc['guide_demand']['summaries'] = {}
    validate_demand(json.loads(json.dumps(doc)))


def test_pinned_legacy_bundle_never_reads_new_worktree_demand():
    from pricing.knowledge.artifacts import Artifact, supplied_artifacts
    from pricing.knowledge.assessment.build_profiles import OUTPUT

    with supplied_artifacts({OUTPUT.resolve(): Artifact(b'{"profiles": []}', 'legacy')}):
        assert demand_for('Insight') is None


def test_reviewed_infinity_and_sazabi_uses_preserve_distinct_builds_and_conditional_roles():
    from pricing.knowledge.assessment.build_profiles import build

    document = build()
    infinity = demand_for('Infinity', document)
    assert infinity is not None
    assert infinity['distinct_builds'] == 2
    assert {r['side'] for r in infinity['contexts']} == {'player', 'merc'}
    assert len([r for r in infinity['contexts'] if r['build'] == 'nova-sorceress-guide']) == 2
    for name in ("Sazabi's Mental Sheath", "Sazabi's Ghost Liberator", "Sazabi's Cobalt Redeemer"):
        summary = demand_for(name, document)
        assert summary['grade'] == 'Pending'
        assert summary['distinct_builds'] == 1
        assert summary['contexts'][0]['variant'] == 'Ubers'
        uses = [r for r in document['guide_demand']['uses'] if r.get('item') == name]
        profile = next(p for p in document['profiles'] if p['id'] == uses[0]['profile_id'])
        assert len(profile['companions']) == 2
        assert profile['mercenary_type'] == 'Act 5 Frenzy'
        assert profile['required_rune']


def test_deaths_set_tail_batch_keeps_leveling_and_companion_requirements_separate_from_breadth():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.policies.leveling import assess_leveling
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    document = build()
    hand = demand_for("Death's Hand", document)
    guard = demand_for("Death's Guard", document)
    assert hand is not None
    assert guard is not None
    assert hand['distinct_builds'] == 1
    assert hand['lower_bound_grade'] == 'Low'
    assert guard['distinct_builds'] == 3
    assert hand['grade'] == guard['grade'] == 'Pending'
    leveling = assess_leveling(facts('Leather Gloves', 'set', "Death's Hand"))
    assert leveling
    assert any("Death's Guard" in condition for use in leveling for condition in use['conditions'])
    profile = next(p for p in document['profiles'] if p['id'] == "enchant-sorceress-starter-set-Death's Hand")
    assert profile['depends_on'][0]['when']['value'] == "Death's Guard"


def test_utility_demand_counts_alternatives_without_promoting_them_to_combat_gear():
    from pricing.knowledge.assessment.build_profiles import build

    document = build()
    naj = demand_for("Naj's Puzzler", document)
    demon = demand_for('Demon Limb', document)
    assert naj is not None
    assert demon is not None
    assert naj['distinct_builds'] == 13
    assert naj['preferred_builds'] == []
    assert len(naj['alternative_builds']) == 13
    assert demon['distinct_builds'] == 3
    assert demon['alternative_builds'] == ['strafe-amazon']
    assert len(demon['contexts']) == 4
    reviewed_ids = {
        u['profile_id']
        for u in document['guide_demand']['uses']
        if u.get('item') in {"Naj's Puzzler", 'Demon Limb'} and u['strength'] != 'example'
    }
    roles = [p for p in document['profiles'] if p['id'] in reviewed_ids]
    assert {p['slot'] for p in roles} == {'Weapon-Swap', 'Prebuff'}
    assert all(p['depends_on'] for p in roles)


def test_mercenary_and_cbf_alternatives_count_distinct_endorsing_builds():
    from pricing.knowledge.assessment.build_profiles import build

    document = build()
    expected = {
        'Vampire Gaze': 4,
        'Crown of Thieves': 1,
        'Stealskull': 3,
        "Duriel's Shell": 2,
        "Kira's Guardian": 1,
        'Rockstopper': 1,
        'Undead Crown': 1,
    }
    for name, count in expected.items():
        summary = demand_for(name, document)
        assert summary is not None, name
        assert summary['distinct_builds'] == count, name
        assert summary['grade'] == 'Pending'
    crown = demand_for('Crown of Thieves', document)
    assert {c['variant'] for c in crown['contexts']} == {'Standard', 'War Cry', 'Whirlwind'}
    duriel = demand_for("Duriel's Shell", document)
    assert duriel['preferred_builds'] == []
    assert {c['side'] for c in duriel['contexts']} == {'player', 'merc'}


def test_sigons_starter_demand_does_not_expand_to_uncited_set_pieces():
    from pricing.knowledge.assessment.build_profiles import build

    document = build()
    for name, count in {"Sigon's Visor": 2, "Sigon's Gage": 3, "Sigon's Sabot": 3, "Sigon's Wrap": 1}.items():
        summary = demand_for(name, document)
        assert summary is not None, name
        assert summary['distinct_builds'] == count
        assert summary['grade'] == 'Pending'
        assert {c['variant'] for c in summary['contexts']} == {'Starter'}
        assert {c['side'] for c in summary['contexts']} == {'player'}
    assert demand_for("Sigon's Shelter", document) is None
    assert demand_for("Sigon's Guard", document) is None
    roles = [p for p in document['profiles'] if p['id'].endswith("starter-set-Sigon's Gage")]
    companions = {p['build']: {d['when']['value'] for d in p['depends_on']} for p in roles}
    assert companions['strafe-amazon'] == {"Sigon's Visor", "Sigon's Sabot"}
    assert companions['berserk-barbarian'] == {"Sigon's Wrap", "Sigon's Sabot"}
