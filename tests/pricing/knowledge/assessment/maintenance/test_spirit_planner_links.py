"""Spirit source occurrences require the selected active loadout and complete recipe."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_swap_planner_links import GUIDE, PROFILES, USES, read


def example(profile_id='hammer-standard-spirit-shield'):
    import hashlib

    prepared = next(
        r for r in read('pricing/data/appraisal-spirit-loadout-audit.json')['rows'] if r['profile_id'] == profile_id
    )
    role = deepcopy(next(r for r in read(PROFILES)['profiles'] if r['id'] == profile_id))
    use = deepcopy(next(r for r in read(USES)['uses'] if r['profile_id'] == profile_id))
    source = role['source']
    variant_index = int(source['locator'].split('/')[3])
    variant = read(source['path'])[role['build']]['variants'][variant_index]
    quote_index, quote = next((i, q) for i, q in enumerate(variant[role['side']]['Off-Hand']) if q in source['quotes'])

    def pin(path):
        return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}

    planner = decode_planner(read(prepared['planner']['path']))
    profile = planner['profiles'][prepared['profile_index']]
    guide_path = f'pricing/raw/mr/guides__{role["build"]}.html'
    from pricing.knowledge.assessment.maintenance.planner_fcr import SOURCE_PATHS
    from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import SOURCES

    evidence = {
        'spirit_loadout': 'hammer_active',
        'coverage': 'player_runeword_component',
        'ethereal_scope': 'unrestricted_reviewed_role',
        'guide': pin(GUIDE),
        'guide_source': guide_path,
        'quote': quote,
        'equipment_quote': {
            **pin(source['path']),
            'locator': f'/{role["build"]}/variants/{variant_index}/{role["side"]}/Off-Hand/{quote_index}',
        },
        'variant_alias': role['variant'],
        'guide_tab': role['variant'],
        'planner': prepared['planner'],
        'profile_index': prepared['profile_index'],
        'profile_uid': prepared['profile_uid'],
        'profile_name': role['variant'],
        'player_class_code': profile['class'],
        'slot': 'larm',
        'item_id': prepared['item_id'],
        'expected_item': prepared['item'],
        'recipe_sources': {k: pin(p) for k, p in SOURCES.items()},
        'fcr_sources': {k: pin(p) for k, p in SOURCE_PATHS.items()},
        'stat_definitions': pin('third-parties/d2data/json/itemstatcost.json'),
    }
    inventory = read('pricing/data/appraisal-guide-inventory.json')
    parent = next(r for r in inventory['occurrences'] if r['id'] == prepared['parent_occurrence_id'])
    children = sorted(
        [
            r
            for r in inventory['occurrences']
            if r['source_id'] == parent['source_id']
            and r['source_locator'].startswith(parent['source_locator'] + '/socketedItems/')
        ],
        key=lambda r: r['source_locator'],
    )
    occurrences = [parent, *children]
    identities = {r['identity_id'] for r in occurrences}

    def ref(row):
        return {'occurrence_id': row['id'], 'sha256': fingerprint(row)}

    row = {
        'id': profile_id + ':planner:' + parent['id'],
        'profile_id': profile_id,
        'profile_sha256': fingerprint(role),
        'use_sha256': fingerprint(use),
        'parent': ref(parent),
        'children': [ref(r) for r in children],
        'planner_endorsement': evidence,
        'reviewed_at': '2026-09-30',
        'reason': 'Selected active Spirit with 125 FCR and named companions; complete native rune payload.',
    }
    paths = {
        PROFILES,
        USES,
        GUIDE,
        guide_path,
        source['path'],
        prepared['planner']['path'],
        'third-parties/d2data/json/itemstatcost.json',
        'third-parties/d2data/json/misc.json',
    }
    paths.update(ref['path'] for ref in evidence['recipe_sources'].values())
    paths.update(ref['path'] for ref in evidence['fcr_sources'].values())
    document = {
        'schema_version': 1,
        'scope': 'reviewed_spirit_loadouts',
        'inputs': {p: pin(p)['sha256'] for p in paths},
        'rows': [row],
    }
    subset = {
        'occurrences': occurrences,
        'identities': [r for r in inventory['identities'] if r['id'] in identities],
        'sources': [r for r in inventory['sources'] if r['id'] == parent['source_id']],
    }
    return deepcopy(document), deepcopy(subset), [role], [use]


def compile_example(document, inventory, profiles, uses):
    from pricing.knowledge.assessment.maintenance.spirit_planner_links import compile_spirit_planner_links

    return compile_spirit_planner_links(document, inventory, profiles, uses, ROOT)


@pytest.mark.parametrize('profile_id', ['hammer-standard-spirit-shield', 'hammer-mf-spirit-shield'])
def test_spirit_links_only_parent_and_four_native_runes(profile_id):
    document, inventory, roles, uses = example(profile_id)
    original = deepcopy((document, roles))
    result = compile_example(document, inventory, roles, uses)
    assert len(result) == 5
    assert {r['occurrence_id'] for r in result} == {r['id'] for r in inventory['occurrences']}
    assert (document, roles) == original


@pytest.mark.parametrize('change', ['source', 'slot', 'uid', 'runes', 'use', 'fingerprint', 'duplicate', 'fcr-source'])
def test_spirit_links_reject_changed_evidence(change):
    document, inventory, roles, uses = example()
    link = document['rows'][0]
    evidence = link['planner_endorsement']
    if change == 'source':
        evidence['equipment_quote']['locator'] = evidence['equipment_quote']['locator'].replace(
            '/Off-Hand/', '/Weapon/'
        )
    elif change == 'slot':
        evidence['slot'] = 'larm2'
    elif change == 'uid':
        evidence['profile_uid'] = 'different-profile'
    elif change == 'runes':
        link['children'].reverse()
    elif change == 'use':
        uses[0]['review_state'] = 'pending'
        link['use_sha256'] = fingerprint(uses[0])
    elif change == 'fingerprint':
        link['profile_sha256'] = 'stale'
    elif change == 'duplicate':
        document['rows'].append(deepcopy(link))
    else:
        document['inputs'][evidence['fcr_sources']['properties']['path']] = 'stale'
    with pytest.raises(ValueError, match=r'[Ss]pirit|[Pp]lanner|[Gg]uide|[Ee]quipment'):
        compile_example(document, inventory, roles, uses)


def test_completion_closes_only_validated_spirit_occurrences():
    from pricing.knowledge.assessment.maintenance.completion import compile_completion

    document, inventory, roles, uses = example()
    from pricing.knowledge.assessment.maintenance.guide_inventory import configurations

    inventory['configurations'] = configurations(roles)
    occurrence_ids = {r['id'] for r in inventory['occurrences']}
    for identity in inventory['identities']:
        identity['occurrence_ids'] = [i for i in identity['occurrence_ids'] if i in occurrence_ids]
    kwargs = {'profiles': roles, 'uses': uses, 'source_root': ROOT}
    before = compile_completion({'rows': []}, inventory, {'complete': False}, **kwargs)
    after = compile_completion({'rows': []}, inventory, {'complete': False}, spirit_planner_reviews=document, **kwargs)
    before_ids = {r['id'] for r in before['queue']}
    after_ids = {r['id'] for r in after['queue']}
    assert before_ids - after_ids == {'occurrence:' + r['id'] for r in inventory['occurrences']}
    assert not after_ids - before_ids
    assert after['complete'] is False
    assert len(after['spirit_planner_dispositions']) == 5
    assert before['scope'] != after['scope']
