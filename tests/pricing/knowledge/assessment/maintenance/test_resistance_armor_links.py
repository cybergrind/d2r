import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


def inputs():
    def read(path):
        return json.loads(Path(path).read_text())

    doc = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')
    inventory = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    return doc, inventory, profiles, uses


def test_all_mercenary_resistance_armor_occurrences_have_validated_links():
    doc, inventory, profiles, uses = inputs()
    expected = {o['id'] for o in inventory if o['name'] == 'Gemmed Dusk Shroud' and o['side'] == 'merc'}
    assert len(expected) == 21
    actual = compile_table_equivalence(doc, inventory, profiles, uses, Path.cwd())
    linked = {r['occurrence_id'] for r in actual}
    from pricing.knowledge.assessment.maintenance.review_dossiers import compile_dossiers

    inv = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())
    dossiers = compile_dossiers(inv, profiles, uses)
    existing = {oid for row in dossiers['identities'] for oid in row['reviewed_pattern_occurrence_ids']}
    assert expected - linked == {'3863dc65ed53476e967a4527'}
    assert expected <= linked | existing


@pytest.mark.parametrize(
    'change', ['bearer', 'payload', 'class', 'side', 'span', 'planner-hash', 'gems-hash', 'guide-hash', 'endorsement']
)
def test_resistance_links_reject_changed_context_even_with_refingerprinted_role(change):
    doc, inventory, profiles, uses = inputs()
    review = deepcopy(next(r for r in doc['rows'] if r.get('pattern_kind') == 'merc_resistance_armor'))
    role = next(p for p in profiles if p['id'] == review['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change in ('bearer', 'payload'):
        key = 'any' if change == 'bearer' else 'op'
        predicate = next(
            p for p in role['must']['all'] if ('any' in p if key == 'any' else p.get('op') == 'socket_runes_equal')
        )
        if change == 'bearer':
            predicate['any'][0]['value'] = 'Act 3 Fire'
        else:
            predicate['value'] = ['Perfect Topaz'] * 4
        review['profile_fingerprint'] = fingerprint(role)
        use['profile_fingerprint'] = fingerprint(role)
        review['use_fingerprint'] = fingerprint(use)
    elif change in ('class', 'side'):
        occurrence = next(o for o in inventory if o['id'] == review['occurrence_id'])
        occurrence[change] = 'Assassin' if change == 'class' else 'player'
        review['occurrence_fingerprint'] = fingerprint(occurrence)
    elif change == 'endorsement':
        occurrence = next(o for o in inventory if o['id'] == review['occurrence_id'])
        occurrence['details']['recommended'] = False
        review['occurrence_fingerprint'] = fingerprint(occurrence)
    elif change == 'span':
        review['span'] += 1
    else:
        review[change.removesuffix('-hash')]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match=r'[Rr]esistance armor|Stale table equivalence|early body armor'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, inventory, profiles, uses, Path.cwd())


@pytest.mark.parametrize('change', ['quality', 'payload', 'sockets', 'base', 'effect'])
def test_native_payload_and_armor_effects_are_validated_beyond_source_hashes(change):
    from pricing.knowledge.assessment.maintenance.resistance_armor_links import validate_native
    from pricing.knowledge.builds import decode_planner

    doc, _, profiles, _ = inputs()
    review = next(r for r in doc['rows'] if r.get('pattern_kind') == 'merc_resistance_armor')
    role = next(p for p in profiles if p['id'] == review['profile_id'])

    def read(pin):
        value = json.loads(Path(pin['path']).read_text())
        if pin['path'].endswith('fc01065b.json'):
            value = decode_planner(value)
            item = value['items']['93']
            if change == 'quality':
                item['quality'] = 3
            elif change == 'payload':
                item['socketedItems'] = item['socketedItems'][:3]
            elif change == 'sockets':
                item['sockets'] = 3
            elif change == 'base':
                item['base'] = 'unresolved'
        elif change == 'effect':
            next(r for r in value.values() if r['name'] == 'Ral Rune')['helmMod1Min'] = 29
        return value

    with pytest.raises(ValueError, match='native'):
        validate_native(review, role, read)


@pytest.mark.parametrize('change', ['variant', 'locator', 'source-pin'])
def test_structured_links_cannot_reuse_another_progression_entry(change):
    doc, inventory, profiles, uses = inputs()
    review = deepcopy(
        next(r for r in doc['rows'] if r.get('pattern_kind') == 'merc_resistance_armor' and 'structured_source' in r)
    )
    occurrence = next(o for o in inventory if o['id'] == review['occurrence_id'])
    if change == 'variant':
        occurrence['variant'] = 'end'
    elif change == 'locator':
        occurrence['source_locator'] = occurrence['source_locator'].replace('/early/', '/mid/')
    else:
        review['structured_source']['sha256'] = '0' * 64
    review['occurrence_fingerprint'] = fingerprint(occurrence)
    with pytest.raises(ValueError, match=r'[Rr]esistance armor|Stale table equivalence|early body armor'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, inventory, profiles, uses, Path.cwd())
