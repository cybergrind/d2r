"""Late-game mobility is not a perfect-base or whole-build claim."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import ROOT, inputs


def enigma_inputs():
    document, links, profiles, uses = inputs(18)
    role = next(r for r in profiles if r['id'] == 'echoing-late-game-enigma-player')
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row = document['rows'][0]
    row.pop('native_source')
    path = 'third-parties/d2data/json/runes.json'
    row.update(
        kind='echoing_enigma',
        profile_id=role['id'],
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
        recipe_source={'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()},
        reason='Late-game Enigma replaces Blade Warp with Teleport; repairable legal armor bases support player use.',
    )
    return document, links, profiles, uses


def test_late_game_teleport_replacement_has_its_own_review():
    assert compile_embedded_reviews(*enigma_inputs(), ROOT)[0]['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['base', 'ethereal', 'mercenary', 'priority', 'quality', 'companion'])
def test_refreshed_review_does_not_change_the_mobility_contribution(change):
    document, links, profiles, uses = deepcopy(enigma_inputs())
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'base':
        role['must']['all'].append({'op': 'fact_eq', 'field': 'base_code', 'value': 'xtp'})
    elif change == 'ethereal':
        role['must']['all'] = [r for r in role['must']['all'] if r.get('field') != 'ethereal']
    elif change == 'mercenary':
        role['side'] = use['side'] = 'merc'
    elif change == 'priority':
        role['important_stats'] = ['31:0']
    elif change == 'quality':
        role['qualities'].remove('low_quality')
    else:
        role['depends_on'] = [
            {'label': 'CTA', 'when': {'op': 'context_contains', 'field': 'player_items', 'value': 'Call to Arms'}}
        ]
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Enigma'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['runes', 'skill', 'replacement_text'])
def test_late_game_review_requires_recipe_and_explicit_teleport_replacement(monkeypatch, change):
    from pricing.knowledge.assessment.maintenance import embedded_echoing_enigma as module
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = enigma_inputs()
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    resolved = validate_embedded_evidence(row['evidence'], ROOT)
    if change == 'runes':
        resolved['item']['socketedItems'].reverse()
    elif change == 'skill':
        resolved['item']['stats']['item_nonclassskill#54'] = 0
    else:
        original = module._read_pin
        monkeypatch.setattr(module, '_read_pin', lambda pin, root: original(pin, root).replace('Blade Warp', 'Changed'))
    with pytest.raises(ValueError, match='Echoing Enigma'):
        module.validate_echoing_enigma(row, resolved, role, ROOT)
