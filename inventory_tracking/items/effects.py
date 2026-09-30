"""Reviewed native item effects that are not plain scalar tooltip labels."""

# Local d2data properties.reanimate uses monstats hcIdx as the layer (func24).
# Tomb Reaver is the item definition using it: skeleton2/hcIdx1/NameStr Returned.
REANIMATE_TARGETS = {1: 'Returned'}
# properties.state func24 uses a state ID as layer, with value1. These are the
# two states referenced by the current sets table; names/IDs from states.json.
SET_STATES = {175: 'fullsetgeneric', 176: 'monsterset'}
DIFFICULTIES = ('Normal', 'Nightmare', 'Hell')
VISUAL_EFFECTS = {140: 'Extra blood', 181: 'Fade'}


def decode_reanimate(ctx):
    target = REANIMATE_TARGETS.get(ctx.layer)
    if target and 0 <= ctx.raw <= 100:
        return {'value': ctx.raw, 'text': f'{ctx.raw}% Reanimate as: {target}'}
    return None


def decode_quest_difficulty(ctx):
    # D2Game ITEMS_CreateItemEx stores nDifficulty in stat356, layer0.
    if ctx.layer == 0 and 0 <= ctx.raw < len(DIFFICULTIES):
        return {
            'value': ctx.raw,
            'text': f'Quest item difficulty: {DIFFICULTIES[ctx.raw]}',
            'presentation': 'internal',
        }
    return None


def decode_visual_effect(ctx):
    # properties.bloody/fade are explicitly "Visuals Only". Preserve magnitude;
    # fade here is not a skill/aura, and implies no resistance or damage bonus.
    if ctx.layer == 0 and ctx.raw >= 0:
        return {
            'value': ctx.raw,
            'text': f'{VISUAL_EFFECTS[ctx.stat["id"]]} visual effect: {ctx.raw}',
            'presentation': 'internal',
        }
    return None


def decode_set_state(ctx):
    state = SET_STATES.get(ctx.layer)
    if state and ctx.raw == 1:
        return {'value': ctx.raw, 'text': f'Set state: {state}', 'presentation': 'internal'}
    return None


def decode_magic_pierce(ctx):
    # d2data/allstrings-eng.json ModStrMagPierce; planner strings omit this key.
    if ctx.layer == 0:
        return {
            'value': ctx.raw,
            'range_label': '-{{value}}% to Enemy Magic Resistance',
            'text': f'{-ctx.raw:+d}% to Enemy Magic Resistance',
        }
    return None


def decode_numeric_text_effect(ctx):
    """Text-only tooltip effects whose native payload is a magnitude, not a flag.

    D2MOO Items.cpp adds stat254 to max stack; D2Skills.cpp returns stat157/158
    as the level of Magic Arrow/Exploding Arrow. Never coerce the value to one.
    """
    if ctx.layer != 0 or ctx.raw <= 0 or not ctx.spec.get('label'):
        return None
    label = ctx.spec['label']
    suffix = f'(+{ctx.raw})' if ctx.stat['id'] == 254 else f'(Level {ctx.raw})'
    return {'value': ctx.raw, 'label': label, 'text': f'{label} {suffix}'}
