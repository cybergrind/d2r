"""Blank tooltip labels still require exact native identity and wearer proof."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import ROOT, inputs


def starter_inputs(span=2):
    document, links, profiles, uses = inputs(span)
    suffix = {2: 'treachery', 3: 'bulwark'}[span]
    role = next(r for r in profiles if r['id'] == f'echoing-strike-warlock-guide-0-merc-{suffix}-native')
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row = document['rows'][0]
    row.pop('native_source')
    path = 'third-parties/d2data/json/runes.json'
    row.update(
        kind='echoing_starter',
        profile_id=role['id'],
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
        recipe_source={'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()},
        reason=(
            'Exact starter Blessed Aim mercenary recipe, resolved from blank-label tooltip. '
            'Native contribution is wearer-only; active Fade and successful life leech are not inferred.'
        ),
    )
    return document, links, profiles, uses


@pytest.mark.parametrize('span', [2, 3])
def test_starter_armor_tooltip_has_exact_recipe_and_bearer(span):
    result = compile_embedded_reviews(*starter_inputs(span), ROOT)
    assert result[0]['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['aura', 'class', 'ethereal', 'quality', 'priority'])
def test_refreshed_fingerprint_cannot_relax_starter_semantics(change):
    document, links, profiles, uses = deepcopy(starter_inputs())
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'quality':
        role['qualities'].remove('low_quality')
    elif change == 'priority':
        role['important_stats'].append('60:0')
    else:
        field, value = {
            'aura': ('mercenary_type', 'Act 2 Prayer'),
            'class': ('player_class', 'Paladin'),
            'ethereal': ('ethereal', False),
        }[change]
        next(p for p in role['must']['all'] if p.get('field') == field)['value'] = value
    use['profile_fingerprint'] = row['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing starter'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('span', [2, 3])
@pytest.mark.parametrize('change', ['runes', 'ethereal', 'base'])
def test_starter_tooltip_requires_exact_recipe_payload(span, change):
    from pricing.knowledge.assessment.maintenance.embedded_echoing_starter import validate_echoing_starter
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = starter_inputs(span)
    review = document['rows'][0]
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    if change == 'runes':
        resolved['item']['socketedItems'].reverse()
    else:
        resolved['item'][change] = False if change == 'ethereal' else 'unreviewed-base'
    role = next(r for r in profiles if r['id'] == review['profile_id'])
    with pytest.raises(ValueError, match='Echoing starter'):
        validate_echoing_starter(review, resolved, role, ROOT)
