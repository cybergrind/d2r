"""Cure component advice retains Prayer wearer and independent Cleansing benefit."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_echoing_pairing import ROOT, inputs


def cure_inputs(span=5):
    variant = {5: 1, 7: 2, 155: 'progression'}[span]
    document, links, profiles, uses = inputs(span)
    role_id = 'echoing-progression-cure-merc' if span == 155 else f'echoing-strike-warlock-guide-{variant}-merc-cure'
    role = next(r for r in profiles if r['id'] == role_id)
    use = next(u for u in uses if u['profile_id'] == role['id'])
    row = document['rows'][0]
    row.pop('native_source')
    path = 'third-parties/d2data/json/runes.json'
    row.update(
        kind='echoing_cure',
        profile_id=role['id'],
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
        recipe_source={'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()},
        reason=(
            'Exact Prayer mercenary Cure component. Cleansing is useful without Insight; '
            'no full healing combination or active aura inferred.'
        ),
    )
    return document, links, profiles, uses


@pytest.mark.parametrize('span', [5, 7])
def test_cure_component_can_be_reviewed_without_claiming_full_healing_setup(span):
    assert compile_embedded_reviews(*cure_inputs(span), ROOT)[0]['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['weapon', 'aura', 'prayer_stat', 'quality'])
def test_refreshed_review_cannot_change_cure_component_semantics(change):
    document, links, profiles, uses = deepcopy(cure_inputs())
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    if change == 'weapon':
        role['depends_on'] = [
            {'label': 'Insight', 'when': {'op': 'context_contains', 'field': 'mercenary_items', 'value': 'Insight'}}
        ]
    elif change == 'aura':
        role['must']['all'][-1]['any'][0]['value'] = 'Act 2 Might'
    elif change == 'prayer_stat':
        role['important_stats'].append('151:99')
    else:
        role['qualities'].remove('low_quality')
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Cure'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('change', ['runes', 'parent_total', 'aura'])
def test_cure_parent_roll_is_not_captured_total_with_tal(change):
    from pricing.knowledge.assessment.maintenance.embedded_echoing_cure import validate_echoing_cure
    from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence

    document, _, profiles, _ = cure_inputs()
    review = document['rows'][0]
    resolved = validate_embedded_evidence(review['evidence'], ROOT)
    if change == 'runes':
        resolved['item']['socketedItems'].reverse()
    elif change == 'parent_total':
        resolved['item']['stats']['poisonresist'] = 60
    else:
        resolved['item']['stats']['item_aura#109'] = 2
    role = next(r for r in profiles if r['id'] == review['profile_id'])
    with pytest.raises(ValueError, match='Echoing Cure'):
        validate_echoing_cure(review, resolved, role, ROOT)


def test_progression_cure_is_mercenary_support_despite_raw_player_label():
    document, links, profiles, uses = cure_inputs(155)
    assert document['rows'][0]['evidence']['expected_context']['side'] == 'player'
    assert compile_embedded_reviews(document, links, profiles, uses, ROOT)[0]['state'] == 'reviewed'


@pytest.mark.parametrize(('field', 'value'), [('ethereal', True), ('base_code', 'xrn')])
def test_progression_cleansing_cannot_gain_example_only_requirements(field, value):
    document, links, profiles, uses = deepcopy(cure_inputs(155))
    row = document['rows'][0]
    role = next(r for r in profiles if r['id'] == row['profile_id'])
    use = next(u for u in uses if u['profile_id'] == role['id'])
    role['must']['all'].append({'op': 'fact_eq', 'field': field, 'value': value})
    row['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    row['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Echoing Cure'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)


@pytest.mark.parametrize('phrase', ['Prayer', 'Cure Grand Crown'])
def test_progression_review_requires_parent_and_helmet_example(monkeypatch, phrase):
    from pricing.knowledge.assessment.maintenance import embedded_echoing_cure as module

    document, links, profiles, uses = cure_inputs(155)
    original = module._read_pin

    def changed(pin, root):
        text = original(pin, root)
        return text.replace(phrase, 'changed') if pin['path'].endswith('.html') else text

    # Semantic text is checked separately from the generic source-hash guard.
    monkeypatch.setattr(module, '_read_pin', changed)
    with pytest.raises(ValueError, match='Echoing Cure progression'):
        compile_embedded_reviews(document, links, profiles, uses, ROOT)
