from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.test_base_use import capture


def test_archon_fortitude_keeps_player_and_mercenary_ethereal_preferences():
    result = assess(capture('Archon Plate', sockets=4, ethereal=True), profiles=[])
    fortitude = [r for r in result['base_uses'] if r['runeword'] == 'Fortitude']
    assert {r['ethereal_preference']['preference'] for r in fortitude} == {'preferred', 'avoid'}
    assert result['ethereal_preference']['preference'] == 'mixed'


def test_nova_caster_use_does_not_inherit_mercenary_damage_preference():
    result = assess(capture('Scythe', sockets=4, quality='normal', ethereal=True), profiles=[])
    nova = next(r for r in result['base_uses'] if r['role'] == 'Nova player caster')
    assert nova['ethereal_preference']['preference'] == 'neutral'
    assert result['ethereal_preference']['preference'] == 'mixed'


def test_failed_role_cannot_change_global_ethereal_color():
    from pricing.knowledge.assessment.ethereal import ethereal_preference

    facts = normalize(capture('Cryptic Axe', sockets=4, ethereal=True))
    role = {
        'id': 'player',
        'status': 'failed',
        'role': 'player melee',
        'ethereal_preference': {'preference': 'avoid', 'reason': 'Player repairs'},
    }
    assert ethereal_preference(facts, roles=[role])['preference'] == 'preferred'
    role['status'] = 'partial'
    result = ethereal_preference(facts, roles=[role])
    assert result['preference'] == 'mixed'
    assert result['uses'][0]['role'] == 'player melee'


def test_mixed_ethereal_preference_is_neutral_in_terminal_and_osd():
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.appraisal.text import roll_styles
    from inventory_tracking.presentation import PALETTE, Tone

    for base, expected in [('Archon Plate', Tone.DEFAULT), ('Cryptic Axe', Tone.ETHEREAL_DESIRED)]:
        extraction = capture(base, sockets=4, ethereal=True)
        result = {
            'extraction': {'item': extraction['item']},
            'assessment': assess(extraction, profiles=[]),
            'decision': {'price_status': 'unknown'},
        }
        record = {'state': 'complete', 'request_id': 1, 'result': result}
        document = ItemAssessment.from_record(record)
        line = next(line for line in document.to_osd() if line.text.startswith('Ethereal:'))
        assert line.tone == expected
        assert roll_styles(record).get(line.text, PALETTE[Tone.DEFAULT]) == PALETTE[expected]
        assert document.to_rich().plain == document.to_text()
