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
