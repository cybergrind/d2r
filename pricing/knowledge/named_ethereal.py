"""Ethereal state forced by intrinsic unique properties, not socketed effects."""


def fixed_property(definition, name):
    game = definition.get('game_definition', {})
    return any(
        value == name
        and key.startswith('prop')
        and key[4:].isdigit()
        and type(game.get('min' + key[4:])) is int
        and type(game.get('max' + key[4:])) is int
        and game['min' + key[4:]] == game['max' + key[4:]] == 1
        for key, value in game.items()
    )


def intrinsic_ethereal(variants):
    states = set()
    for definition in variants:
        if fixed_property(definition, 'ethereal'):
            states.add(True)
        elif fixed_property(definition, 'indestruct'):
            states.add(False)
        else:
            states.add(None)
    return next(iter(states)) if len(states) == 1 else None
