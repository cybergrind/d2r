import json
from dataclasses import replace
from pathlib import Path

from inventory_tracking.appraisal.text import format_appraisal
from inventory_tracking.items.metadata import metadata
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from pricing.knowledge.pipeline import retrieve_draft


FIXTURE = Path('tests/inventory_tracking/fixtures/sacred_rondache_res27.json')


def test_saved_sacred_rondache_explains_spirit_resistances_and_socket_preparation():
    result = retrieve_draft(json.loads(FIXTURE.read_text()), DEFAULT_DATABASE)
    text = format_appraisal({'state': 'complete', 'request_id': 'sacred-rondache', 'result': result})
    assert 'Spirit / Paladin caster' in text
    assert '+27 all resistances' in text
    assert '+45 all resistances' in text
    assert 'Larzuk' in text
    assert 'item level' in text
    assert 'Non-ethereal suits player use' in text
    assert 'perfect preferred base' not in text


def test_all_native_paladin_shields_have_conditional_spirit_use():
    facts = normalize(json.loads(FIXTURE.read_text()))
    shields = [b for b in metadata()['bases'].values() if b['type'] == 'ashd']
    assert len(shields) == 15
    for base in shields:
        rows = assess_runeword_base(replace(facts, base_name=base['name'], base_code=base['code']))
        use = next(row for row in rows if row['runeword'] == 'Spirit')
        assert use['role'] == 'Paladin caster'
        assert use['preparation']
        assert '+45 all resistances' in ' '.join(use['missing'])
    for rarity in ('magic', 'rare', 'unique', 'set'):
        assert assess_runeword_base(replace(facts, rarity=rarity)) == []
    use = next(row for row in assess_runeword_base(replace(facts, ethereal=True)) if row['runeword'] == 'Spirit')
    assert any('non-ethereal' in need for need in use['missing'])
    assert use['ethereal_preference']['preference'] == 'avoid'
