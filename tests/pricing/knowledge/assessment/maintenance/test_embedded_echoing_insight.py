"""Same word, different guide variants and mercenary auras."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import ROOT, inputs


def insight_inputs(span=6):
    variant = {1: 0, 6: 1, 8: 2, 127: 'overview', 130: 'overview'}[span]
    document, links, profiles, uses = inputs(span)
    role = next(r for r in profiles if r['id'] == f'echoing-{variant}-insight-merc')
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row = document['rows'][0]
    row.pop('native_source')
    path = 'third-parties/d2data/json/runes.json'
    row.update(
        kind='echoing_insight',
        profile_id=role['id'],
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
        recipe_source={'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()},
        reason=(
            'Exact Echoing mercenary Insight example; preserve starter Blessed Aim versus later Prayer/Cure context. '
            'No active auras or fixed healing rate inferred.'
        ),
    )
    return document, links, profiles, uses


@pytest.mark.parametrize('span', [1, 6, 8, 127, 130])
def test_insight_tooltip_preserves_guide_variant_and_bearer(span):
    result = compile_embedded_reviews(*insight_inputs(span), ROOT)
    assert result[0]['state'] == 'reviewed'
    variant = {1: 0, 6: 1, 8: 2, 127: 'overview', 130: 'overview'}[span]
    assert result[0]['profile_id'] == f'echoing-{variant}-insight-merc'


@pytest.mark.parametrize('change', ['aura', 'class', 'companion', 'variant', 'leech', 'base'])
def test_updated_fingerprint_does_not_erase_insight_context(change):
    document, links, profiles, uses = deepcopy(insight_inputs())
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'companion':
        role['depends_on'] = []
    elif change == 'variant':
        role['variant'] = use['variant'] = 'Starter'
    elif change == 'leech':
        role['important_stats'].append('60:0')
    else:
        field, value = {
            'aura': ('mercenary_type', 'Act 2 Blessed Aim'),
            'class': ('player_class', 'Paladin'),
            'base': ('base_code', '9pa'),
        }[change]
        next(p for p in role['must']['all'] if p.get('field') == field)['value'] = value
    use['profile_fingerprint'] = row['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Insight'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['cure', 'ethereal', 'base', 'prayer'])
def test_general_mana_use_cannot_inherit_extra_setup_requirements(change):
    document, links, profiles, uses = deepcopy(insight_inputs(127))
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'cure':
        role['depends_on'] = [
            {'label': 'Cure', 'when': {'op': 'context_contains', 'field': 'mercenary_items', 'value': 'Cure'}}
        ]
    elif change == 'ethereal':
        role['must']['all'].append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
    elif change == 'base':
        role['must']['all'].append({'op': 'fact_eq', 'field': 'base_code', 'value': '7wc'})
    else:
        role['important_stats'].append('151:99')
    use['profile_fingerprint'] = row['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Insight'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


def test_progression_requires_its_prayer_mercenary_parent(monkeypatch):
    from pricing.knowledge.assessment.maintenance import embedded_echoing_insight as policy
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = insight_inputs(130)
    review = document['rows'][0]
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    original = policy._read_pin

    def changed(pin, root):
        raw = original(pin, root)
        changed = raw.replace('Prayer', 'Might')
        assert changed != raw
        return changed

    monkeypatch.setattr(policy, '_read_pin', changed)
    role = next(r for r in profiles if r['id'] == review['profile_id'])
    with pytest.raises(ValueError, match='Echoing Insight'):
        policy.validate_echoing_insight(review, resolved, role, ROOT)
