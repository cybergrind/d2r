"""Bounded normalization → socketing routes, separate from observed item state.

Sources: d2data fc469993502d cubemain rows 127/128 use usetype,nor with
no level coefficients; D2MOO 5596f5cb6c52 PlrTrade.cpp 569-595 clamps this to 1.
The recipe creates an item: existing modifiers are not destination evidence.
"""

from dataclasses import replace

from pricing.knowledge.assessment.domain.preparation import PreparationOption, SocketPreparation
from pricing.knowledge.assessment.registry import classify


def prepare_normalized_sockets(facts, recipe):
    if facts.sockets != 0 or facts.socket_contents != 'empty':
        return SocketPreparation('low-quality base needs review', ('Normalization of socketed bases is not reviewed.',))
    family = classify(facts)[0]
    if family not in ('weapon', 'armor', 'helm', 'shield'):
        return SocketPreparation(
            'low-quality base needs review', ('No reviewed normalization recipe for this family.',)
        )
    from pricing.knowledge.assessment.mechanics.preparation import prepare_sockets

    cap = recipe['details']['socket_options']['maximum_by_ilvl_bracket'][0]
    normalized_recipe = {
        **recipe,
        'details': {
            **recipe['details'],
            'socket_options': {'possible_sockets': [cap], 'maximum_by_ilvl_bracket': [cap]},
        },
    }
    downstream = prepare_sockets(replace(facts, rarity='normal', item_level=1), normalized_recipe)
    row_id, rune = ('127', 'Eld Rune') if family == 'weapon' else ('128', 'El Rune')
    normalize_step = {
        'action': 'normalize_low_quality',
        'outcomes': [{'quality': 'normal', 'item_level': 1}],
        'preconditions': ['horadric_cube', 'ingredients_available', 'recheck_regenerated_item'],
        'resources': [{'name': rune, 'quantity': 1}, {'name': 'Chipped Gem (Any)', 'quantity': 1}],
        'source': f'third-parties/d2data/json/cubemain.json#{row_id}',
    }
    routes = tuple(
        PreparationOption(
            option.destination,
            option.target_sockets,
            'normalize_then_socket',
            option.feasibility,
            tuple(dict.fromkeys((*normalize_step['preconditions'], *option.preconditions))),
            option.outcomes,
            resources=(*normalize_step['resources'], *option.resources),
            source=normalize_step['source'],
            steps=(normalize_step, option.to_dict()),
        )
        for option in downstream.options
    )
    possible = any(route.feasibility != 'impossible' for route in routes)
    messages = [
        f'Normalize to normal quality at item level 1; the socket cap becomes {cap}.',
        'Recheck the regenerated item: existing defense, staffmods, inherent bonuses '
        'and ethereal state are not assumed.',
    ]
    if possible:
        messages.append(f'Then Larzuk gives {cap} sockets; cube socketing remains random.')
        cube = next(route for route in routes if route.steps[-1]['action'] == 'cube_socket')
        chance = cube.outcomes[0]
        percent = 100 * chance['success_weight'] / chance['denominator']
        messages.append(f'Cube chance for {recipe["sockets"]} sockets after normalization: {percent:.3g}%.')
    else:
        messages.append(f'Normalization cannot produce the required {recipe["sockets"]} sockets.')
    return SocketPreparation(
        'needs normalization and sockets' if possible else 'normalization cannot supply sockets',
        tuple(messages),
        routes,
    )
