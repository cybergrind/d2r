"""Named socket links preserve native stat and source-specific rune proof."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from tests.pricing.knowledge.assessment.maintenance.test_named_socket_endorsement import IDS, endorsement
from tests.pricing.knowledge.assessment.maintenance.test_spirit_loadout_endorsement import pin
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import PROFILES, USES, read


def example(suffix=IDS[0]):
    evidence, role, _ = endorsement(suffix)
    use = next(r for r in read(USES)['uses'] if r['profile_id'] == role['id'])
    inventory = read('pricing/data/appraisal-guide-inventory.json')
    container = 'mercItems' if role['side'] == 'merc' else 'items'
    locator = f'/profiles/{evidence["profile_index"]}/{container}/{evidence["slot"]}'
    parent = next(
        r
        for r in inventory['occurrences']
        if r['source_id'] == evidence['planner']['path'] and r['source_locator'] == locator
    )
    children = sorted(
        [
            r
            for r in inventory['occurrences']
            if r['source_id'] == parent['source_id'] and r['source_locator'].startswith(locator + '/socketedItems/')
        ],
        key=lambda r: r['source_locator'],
    )
    occurrences = [parent, *children]

    def ref(row):
        return {'occurrence_id': row['id'], 'sha256': fingerprint(row)}

    row = {
        'id': role['id'] + ':planner:' + parent['id'],
        'profile_id': role['id'],
        'profile_sha256': fingerprint(role),
        'use_sha256': fingerprint(use),
        'parent': ref(parent),
        'children': [ref(r) for r in children],
        'planner_endorsement': evidence,
        'reviewed_at': '2026-09-30',
        'reason': 'Named item with source-specific native stats and rune payload; no numerical pricing claim.',
    }
    paths = {
        'pricing/data/wp-a-builds.json',
        PROFILES,
        USES,
        role['source']['path'],
        evidence['guide']['path'],
        evidence['guide_source'],
        evidence['planner']['path'],
        'third-parties/d2data/json/misc.json',
    }
    paths.update(p['path'] for p in evidence['native_sources'].values())
    document = {
        'schema_version': 1,
        'scope': 'reviewed_named_sockets',
        'inputs': {p: pin(p)['sha256'] for p in paths},
        'rows': [row],
    }
    ids = {r['identity_id'] for r in occurrences}
    subset = {
        'occurrences': occurrences,
        'identities': [r for r in inventory['identities'] if r['id'] in ids],
        'sources': [r for r in inventory['sources'] if r['id'] == parent['source_id']],
    }
    return deepcopy(document), deepcopy(subset), [deepcopy(role)], [deepcopy(use)]


def compile_example(document, inventory, roles, uses):
    from pricing.knowledge.assessment.maintenance.named_planner_links import compile_named_planner_links

    return compile_named_planner_links(document, inventory, roles, uses, ROOT)


@pytest.mark.parametrize('suffix', IDS)
def test_named_links_only_its_parent_and_inserted_rune(suffix):
    args = example(suffix)
    original = deepcopy(args)
    result = compile_example(*args)
    assert len(result) == 2
    assert {r['occurrence_id'] for r in result} == {r['id'] for r in args[1]['occurrences']}
    assert args == original


@pytest.mark.parametrize(
    'change', ['player-slot', 'missing-rune', 'wrong-child', 'duplicate', 'native-pin', 'stale-use']
)
def test_named_occurrence_proof_rejects_mismatched_sources(change):
    args = example()
    document, _, _, uses = args
    row = document['rows'][0]
    if change == 'player-slot':
        row['planner_endorsement']['coverage'] = 'player_set_component'
    elif change == 'missing-rune':
        row['children'].clear()
    elif change == 'wrong-child':
        row['children'][0] = row['parent']
    elif change == 'duplicate':
        document['rows'].append(deepcopy(row))
    elif change == 'native-pin':
        document['inputs'][row['planner_endorsement']['native_sources']['uniques']['path']] = 'stale'
    else:
        uses[0]['review_state'] = 'pending'
    with pytest.raises(ValueError, match=r'Named|Planner|Armor planner'):
        compile_example(*args)


def test_completion_closes_only_validated_named_occurrences():
    from pricing.knowledge.assessment.maintenance.completion import compile_completion

    document, inventory, roles, uses = example()
    from pricing.knowledge.assessment.maintenance.guide_inventory import configurations

    inventory['configurations'] = configurations(roles)
    occurrence_ids = {r['id'] for r in inventory['occurrences']}
    for identity in inventory['identities']:
        identity['occurrence_ids'] = [i for i in identity['occurrence_ids'] if i in occurrence_ids]
    kwargs = {'profiles': roles, 'uses': uses, 'source_root': ROOT}
    before = compile_completion({'rows': []}, inventory, {'complete': False}, **kwargs)
    after = compile_completion({'rows': []}, inventory, {'complete': False}, named_planner_reviews=document, **kwargs)
    before_ids = {r['id'] for r in before['queue']}
    after_ids = {r['id'] for r in after['queue']}
    assert before_ids - after_ids == {'occurrence:' + r['id'] for r in inventory['occurrences']}
    assert not after_ids - before_ids
    assert after['complete'] is False
    assert len(after['named_planner_dispositions']) == 2
    assert before['scope'] != after['scope']
