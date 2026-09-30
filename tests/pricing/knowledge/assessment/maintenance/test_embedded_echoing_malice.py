"""The exact mercenary Malice tooltip retains its Ubers setup requirements."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence
from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import ROOT, inputs


ROLE = 'echoing-strike-warlock-guide-malice-ubers-source-recipe'


def malice_inputs():
    document, links, profiles, uses = inputs(14)
    role = next(r for r in profiles if r['id'] == ROLE)
    use = next(u for u in uses if u['profile_id'] == ROLE)
    row = document['rows'][0]
    row.pop('native_source')
    path = 'third-parties/d2data/json/runes.json'
    row.update(
        kind='echoing_malice',
        profile_id=ROLE,
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
        recipe_source={'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()},
        reason=(
            'Exact ethereal Mythical Sword Malice on Act 5 Frenzy mercenary, alongside full Sazabi. '
            'Open Wounds are mercenary hit support; Prevent Monster Heal and active prebuffs are not credited.'
        ),
    )
    return document, links, profiles, uses


def test_malice_reference_preserves_full_sazabi_and_mercenary_open_wounds():
    result = compile_embedded_reviews(*malice_inputs(), ROOT)
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_id'] == ROLE


@pytest.mark.parametrize('change', ['companion', 'side', 'mercenary', 'class', 'pmh', 'ethereal', 'base'])
def test_refreshed_fingerprint_cannot_change_malice_semantics(change):
    document, links, profiles, uses = deepcopy(malice_inputs())
    role = next(r for r in profiles if r['id'] == ROLE)
    use = next(r for r in uses if r['profile_id'] == ROLE)
    if change == 'companion':
        role['depends_on'].pop()
    elif change == 'side':
        role['side'] = use['side'] = 'player'
    elif change == 'pmh':
        role['important_stats'].append('117:0')
    else:
        field, value = {
            'mercenary': ('mercenary_type', 'Act 2 Might'),
            'class': ('player_class', 'Paladin'),
            'ethereal': ('ethereal', False),
            'base': ('base_code', 'crs'),
        }[change]
        next(p for p in role['must']['all'] if p.get('field') == field)['value'] = value
    row = document['rows'][0]
    use['profile_fingerprint'] = row['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Malice'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['runes', 'base', 'ethereal', 'stats'])
def test_planner_parent_recipe_and_socket_payload_cannot_be_conflated(change):
    from pricing.knowledge.assessment.maintenance.embedded_echoing_malice import validate_echoing_malice

    document, _, profiles, _ = malice_inputs()
    review = document['rows'][0]
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    if change == 'runes':
        resolved['item']['socketedItems'].reverse()
    elif change == 'stats':
        resolved['item']['stats']['item_openwounds'] = 0
    else:
        resolved['item'][change] = 'crs' if change == 'base' else False
    with pytest.raises(ValueError, match='Malice'):
        validate_echoing_malice(review, resolved, next(r for r in profiles if r['id'] == ROLE), ROOT)
