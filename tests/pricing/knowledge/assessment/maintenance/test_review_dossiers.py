from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import compile_inventory, fingerprint
from pricing.knowledge.assessment.maintenance.review_dossiers import compile_dossiers, expand_dossier
from tests.pricing.knowledge.assessment.maintenance.test_guide_inventory import CATALOG, occurrence, profile


def reviewed(role, **changes):
    return {
        'profile_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'item': 'Insight',
        **{key: role[key] for key in ('build', 'variant', 'side', 'source')},
        'review_state': 'reviewed',
        'scope': 'softcore',
        'strength': 'alternative',
        **changes,
    }


def test_dossiers_keep_full_denominator_and_deduplicate_builds_without_merging_requirements():
    first = profile()
    second = profile('other', must={'op': 'fact_eq', 'field': 'sockets', 'value': 3})
    inventory = compile_inventory([occurrence(), occurrence('copy')], [first, second], CATALOG)
    before = deepcopy(inventory)
    result = compile_dossiers(inventory, [first, second], [reviewed(first), reviewed(second)])
    insight = next(r for r in result['identities'] if r['name'] == 'Insight')
    unused = next(r for r in result['identities'] if r['name'] == 'Unused Unique')
    assert insight['demand']['distinct_builds'] == 1
    assert insight['demand']['grade'] == 'Pending'
    assert len(insight['source_linked_configuration_ids']) == 2
    assert insight['occurrence_ids'] == ['copy', 'one']
    assert unused['next_action'] == 'review_non_guide_evidence'
    assert unused['review_state'] == 'pending'
    assert result['counts']['identities'] == 2
    assert result['counts']['occurrences'] == 2
    assert inventory == before
    expanded = expand_dossier(result, inventory, insight['identity_id'])
    assert len(expanded['occurrences']) == 2
    assert len(expanded['configurations']) == 2
    assert expanded['occurrences'][0]['details']['companions'] == ['Cure']
    assert 'price' not in insight


def test_discovery_and_pattern_links_are_review_leads_not_named_endorsements():
    role = profile(names=[])
    use = reviewed(role, pattern=role['id'])
    del use['item']
    inventory = compile_inventory([occurrence(details={'recommended': False})], [role], CATALOG)
    result = compile_dossiers(inventory, [role], [use])
    unresolved = next(r for r in result['identities'] if r['category'] == 'unresolved')
    assert unresolved['demand']['distinct_builds'] == 0
    assert unresolved['source_linked_configuration_ids']
    assert unresolved['next_action'] == 'resolve_identity'
    assert all(r['demand']['distinct_builds'] == 0 for r in result['identities'])


def test_same_name_different_quality_does_not_inherit_runeword_demand():
    role = profile()
    inventory = compile_inventory([], [role], {**CATALOG, 'unique': {'name': 'Insight', 'category': 'unique'}})
    result = compile_dossiers(inventory, [role], [reviewed(role)])
    assert next(r for r in result['identities'] if r['category'] == 'runeword')['demand']['distinct_builds'] == 1
    assert (
        next(r for r in result['identities'] if r['category'] == 'unique' and r['name'] == 'Insight')['demand'][
            'distinct_builds'
        ]
        == 0
    )


def test_changed_rule_rejects_stale_inventory_or_review_before_generating_dossiers():
    role = profile()
    inventory = compile_inventory([occurrence()], [role], CATALOG)
    changed = deepcopy(role)
    changed['must']['value'] = 3
    with pytest.raises(ValueError, match='Stale inventory configurations'):
        compile_dossiers(inventory, [changed], [reviewed(changed)])
    fresh = compile_inventory([occurrence()], [changed], CATALOG)
    with pytest.raises(ValueError, match='Stale guide-use review'):
        compile_dossiers(fresh, [changed], [reviewed(role)])
    assert (
        compile_dossiers(fresh, [changed], [reviewed(changed)])['configurations'][0]['id']
        != inventory['configurations'][0]['id']
    )


def test_dossiers_preserve_source_blockers_and_reject_dangling_evidence():
    role = profile()
    inventory = compile_inventory([occurrence()], [role], CATALOG)
    inventory['source_conflicts'] = [{'reason': 'missing_set', 'affected_references': ['reference']}]
    inventory['reviewed_source_issues'] = [{'id': 'bad-affixes', 'status': 'reviewed_conflict'}]
    result = compile_dossiers(inventory, [role], [])
    assert result['reviewed_source_issues'] == inventory['reviewed_source_issues']
    assert result['source_conflicts'] == inventory['source_conflicts']
    inventory['occurrences'][0]['source_rule_ids'] = ['missing-rule']
    with pytest.raises(ValueError, match='Unknown source rule'):
        compile_dossiers(inventory, [role], [])


def test_dossier_retains_reviewed_source_without_matching_occurrence_and_is_deterministic():
    role = profile(
        source={
            'path': 'guide.json',
            'locator': '/items/0',
            'sha256': 'source',
            'quote': 'Use this for mana support',
            'source_date': '2026-05-22',
        }
    )
    inventory = compile_inventory([], [role], CATALOG)
    result = compile_dossiers(inventory, [role], [reviewed(role)])
    identity = next(r for r in result['identities'] if r['name'] == 'Insight')
    expanded = expand_dossier(result, inventory, identity['identity_id'])
    assert expanded['configurations'][0]['sources'][0]['quote'] == 'Use this for mana support'
    assert expanded['configurations'][0]['sources'][0]['source_date'] == '2026-05-22'
    assert identity['source_linked_configuration_ids'] == []
    reversed_inventory = {**inventory, 'identities': list(reversed(inventory['identities']))}
    assert compile_dossiers(reversed_inventory, [role], [reviewed(role)]) == result


def test_source_validation_rejects_changed_missing_and_conflicting_inputs(tmp_path):
    import hashlib

    from pricing.knowledge.assessment.maintenance.review_dossiers import verify_inputs

    path = tmp_path / 'guide.json'
    path.write_bytes(b'cached guide')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory = {'input_hashes': {'guide.json': digest}, 'sources': [{'path': 'guide.json', 'sha256': digest}]}
    verify_inputs(inventory, tmp_path)
    with pytest.raises(ValueError, match='Conflicting inventory hashes'):
        verify_inputs({**inventory, 'input_hashes': {'guide.json': 'other'}}, tmp_path)
    path.write_bytes(b'changed guide')
    with pytest.raises(ValueError, match='Stale inventory source'):
        verify_inputs(inventory, tmp_path)
    path.unlink()
    with pytest.raises(ValueError, match='Stale inventory source'):
        verify_inputs(inventory, tmp_path)


def test_review_queues_expose_new_identity_breadth_without_inventing_endorsements():
    role = profile()
    rows = [
        occurrence(),
        occurrence('new', name='Unused Unique', category='unique', build='build-b'),
        occurrence('copy', name='Unused Unique', category='unique', build='build-b'),
        occurrence('independent', name='Unused Unique', category='unique', build='build-c'),
    ]
    inventory = compile_inventory(rows, [role], CATALOG)
    for row in inventory['occurrences']:
        row['source_status'] = 'verified'
    result = compile_dossiers(inventory, [role], [reviewed(role)])
    new = next(r for r in result['identities'] if r['name'] == 'Unused Unique')
    assert new['review_leads']['builds'] == ['build-b', 'build-c']
    assert new['review_leads']['distinct_builds'] == 2
    assert new['demand']['distinct_builds'] == 0
    assert result['review_queues']['new_named_identities'] == [new['identity_id']]
    assert result['review_queues']['named_use_expansion']
    reversed_inventory = {**inventory, 'occurrences': list(reversed(inventory['occurrences']))}
    assert compile_dossiers(reversed_inventory, [role], [reviewed(role)]) == result


def test_review_leads_keep_blocked_discovery_and_hardcore_out_of_candidate_breadth():
    rows = [
        occurrence('good'),
        occurrence('planner', build='shared-planner'),
        occurrence('hc', build='hardcore-build', variant='Hardcore'),
        occurrence(
            'old', build='old-build', details={'historical': True, 'recommended': True, 'resolution_status': 'resolved'}
        ),
        occurrence('missing', build='missing-build'),
        occurrence(
            'discovery', build='discovery-build', details={'recommended': False, 'resolution_status': 'resolved'}
        ),
    ]
    inventory = compile_inventory(rows, [], CATALOG)
    for row in inventory['occurrences']:
        row['source_status'] = 'missing' if row['id'] == 'missing' else 'verified'
    result = compile_dossiers(inventory, [], [])
    insight = next(r for r in result['identities'] if r['name'] == 'Insight')
    assert insight['review_leads']['builds'] == ['build-a']
    assert insight['review_leads']['occurrence_ids'] == ['good']
    assert set(insight['occurrence_ids']) == {r['id'] for r in rows}
    assert insight['demand']['distinct_builds'] == 0
    unused = next(r for r in result['identities'] if r['name'] == 'Unused Unique')
    assert unused['identity_id'] in result['review_queues']['no_verified_guide_leads']


def test_hustle_census_includes_reviewed_variants_without_merging_their_requirements():
    armor = profile('armor', names=['Hustle (armor)'], slot='Body Armor', types=['tors'])
    weapon = profile('weapon', names=['Hustle (weapon)'], types=['swor'])
    unsupported = profile('unsupported', names=['Hustle (shield)'], types=['shie'])
    catalog = {
        'armor': {'name': 'Hustle', 'category': 'runeword'},
        'weapon': {'name': 'Hustle', 'category': 'runeword'},
        'same-name-unique': {'name': 'Hustle', 'category': 'unique'},
        'explicit-armor': {'name': 'Hustle (armor)', 'category': 'runeword'},
    }
    roles = [armor, weapon, unsupported]
    uses = [reviewed(r, item=r['names'][0]) for r in roles]
    inventory = compile_inventory([], roles, catalog)
    before = deepcopy(inventory)
    result = compile_dossiers(inventory, roles, uses)
    parent = next(r for r in result['identities'] if r['category'] == 'runeword' and r['name'] == 'Hustle')
    assert parent['guide_review_profile_ids'] == ['armor', 'weapon']
    assert next(r for r in result['identities'] if r['name'] == 'Hustle (armor)')['guide_review_profile_ids'] == [
        'armor'
    ]
    assert len(parent['guide_review_configuration_ids']) == 2
    assert parent['demand']['distinct_builds'] == 1
    assert not next(r for r in result['identities'] if r['category'] == 'unique')['guide_review_profile_ids']
    assert inventory == before
    assert result['counts']['occurrences'] == 0
