from dataclasses import replace

from pricing.knowledge.assessment.handlers.runeword import RunewordHandler, definitions
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def enigma():
    stats = {'31:0': {'status': 'decoded', 'value': 1000}}
    for stat, raw, divisor in [(220, 6, 8), (240, 8, 8)]:
        stats[f'{stat}:0'] = {
            'status': 'decoded',
            'raw': raw,
            'value': raw * 91 // divisor,
            'viewer_level': 91,
            'per_level': {'numerator': raw, 'denominator': divisor},
        }
    return replace(
        facts('Mage Plate'),
        name='Enigma',
        runeword='Enigma',
        sockets=3,
        socket_contents='filled',
        stats=stats,
        projection_gaps=[f'No verified market mapping for native stat {s}:0.' for s in (220, 240)],
    )


def test_enigma_fixed_per_level_effects_clear_only_after_coefficient_verification():
    item = enigma()
    contract, gaps = RunewordHandler().contract(item, 'armor')
    assert contract is not None, gaps
    for key in ('220:0', '240:0'):
        changed = replace(item, stats={k: v for k, v in item.stats.items() if k != key}, projection_gaps=[])
        contract, gaps = RunewordHandler().contract(changed, 'armor')
        assert contract is None
        assert any('per-level' in g for g in gaps)


def test_fortitude_variable_coefficient_is_required_and_never_becomes_fixed():
    from pricing.knowledge.assessment.mechanics.per_level import variable_per_level_gaps

    definition = definitions()['Fortitude']
    assert not definition['fixed_per_level_effects']
    item = replace(facts('Archon Plate'), runeword='Fortitude')
    assert any('missing' in g for g in variable_per_level_gaps(item, definition))
    for raw in (2048, 3072):
        stat = {
            'status': 'decoded',
            'raw': raw,
            'value': raw * 91 // 2048,
            'viewer_level': 91,
            'per_level': {'numerator': raw, 'denominator': 2048},
        }
        gaps = variable_per_level_gaps(replace(item, stats={'216:0': stat}), definition)
        assert not gaps
    assert any(
        'invalid' in g
        for g in variable_per_level_gaps(replace(item, stats={'216:0': {**stat, 'raw': 2049}}), definition)
    )
