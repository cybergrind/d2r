"""Verified unmodified base defense for the original Horazon's Legacy boots."""

from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition


MODE = 'horazon_legacy'
IDENTITY = ('set', "Horazon's Legacy")
FORBIDDEN = ('16:0', '214:0', '215:0')


def definition_bounds(definition):
    if (definition.get('rarity'), definition.get('name')) != IDENTITY:
        return None
    base = definition.get('base_definition', {})
    game = definition.get('game_definition', {})
    declared = definition.get('base_defense_range') or {}
    bounds = (base.get('minac'), base.get('maxac'))
    if (
        definition.get('base_name') != 'Mirrored Boots'
        or base.get('type') != 'boot'
        or base.get('gemsockets') != 0
        or not base.get('code')
        or base.get('code') != base.get('ultracode')
        or definition.get('base_code') != base['code']
        or list(definition.get('base_codes', ())) != [base['code']]
        or game.get('item') != base['code']
        or any(type(v) is not int or v < 0 for v in bounds)
        or bounds[0] >= bounds[1]
        or bounds != (declared.get('min'), declared.get('max'))
        or any(str(s) in definition.get('roll_ranges', {}) for s in (16, 31, 214, 215))
        or any(
            v not in {'move1', 'str', 'dex', 'res-mag', 'nofreeze', 'ease'}
            for k, v in game.items()
            if k.startswith('prop')
        )
        or any(v != 'move2' for k, v in game.items() if k.startswith('aprop'))
        or definition.get('native_socket_range')
        or definition.get('property_groups')
        or definition.get('variable_per_level_effects')
    ):
        return None
    return bounds


def capture_bounds(facts, *, captured=True):
    if (
        (facts.rarity, facts.name) != IDENTITY
        or facts.identified is not True
        or facts.ethereal is not False
        or type(facts.sockets) is not int
        or facts.sockets != 0
        or facts.socket_contents != 'empty'
        or facts.gaps
        or (captured and facts.capture_complete is not True)
        or any(key in facts.stats for key in FORBIDDEN)
    ):
        return None
    definition, errors = resolve_named_definition(facts, identity_only=True)
    if errors or definition is None or facts.base_code != definition['base_code']:
        return None
    return definition_bounds(definition)


def valid_base_defense(review, facts, *, market_properties=None):
    mode = review.get('base_defense')
    if mode is None:
        return True
    if mode != MODE or (market_properties is not None and any(k in market_properties for k in ('399', '425'))):
        return False
    bounds = capture_bounds(facts, captured=market_properties is None)
    row = facts.stats.get('31:0', {})
    value = row.get('value')
    return bool(bounds and row.get('status') == 'decoded' and type(value) is int and bounds[0] <= value <= bounds[1])
