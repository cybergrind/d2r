"""Completed class shields: useful recipe bonuses do not replace cited staffmods."""

from dataclasses import replace
from itertools import product

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Independently transcribed equipment and native skill IDs from the cached sources.
SPECS = (
    ('blessed-hammer-paladin-0-rhyme', 'blessed-hammer-paladin', 'Paladin', 'Targe', ()),
    ('poison-nova-necromancer-0-rhyme', 'poison-nova-necromancer', 'Necromancer', 'Fetish Trophy', ((92, 2),)),
    (
        'echoing-strike-warlock-guide-0-rhyme',
        'echoing-strike-warlock-guide',
        'Warlock',
        'Codex',
        ((389, 1), (381, 1), (377, 1)),
    ),
    ('smite-paladin-0-rhyme', 'smite-paladin', 'Paladin', 'Targe', ()),
    ('fire-warlock-guide-0-rhyme', 'fire-warlock-guide', 'Warlock', 'Codex', ()),
    (
        'mirrored-starter-rhyme-grimoire',
        'mirrored-blades-warlock-guide',
        'Warlock',
        'Grimoire',
        ((392, 1), (389, 1), (377, 1)),
    ),
)
# Native armor.json base blocking, independent of recipe data.
BASE_BLOCK = {'Targe': 10, 'Fetish Trophy': 5, 'Codex': 8, 'Grimoire': 12, 'Bone Shield': 20}
NATIVE = (
    (153, 0, 1),
    (80, 0, 25),
    (79, 0, 50),
    (102, 0, 40),
    (27, 0, 15),
    *((sid, 0, 25) for sid in (39, 41, 43, 45)),
    (194, 0, 2),
)


def cases():
    for (role, build, klass, base, skills), quality in product(SPECS, ('normal', 'superior', 'low_quality')):
        if role == 'poison-nova-necromancer-0-rhyme' and quality == 'low_quality':
            # Rhyme adds no Poison Nova; inferior staffmods cannot supply +2.
            continue
        item = Item(
            base,
            quality,
            'Rhyme',
            (*NATIVE, (20, 0, BASE_BLOCK[base] + 20), *((107, skill, value) for skill, value in skills)),
            ethereal=False,
            sockets=2,
            socket_contents='filled',
            runeword='Rhyme',
            socket_items=(SocketItem('Shael Rune'), SocketItem('Eth Rune')),
        )
        context = {'player_class': klass}
        examples = [
            ('native', item, context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            (
                'wrong-base',
                replace(
                    item,
                    base='Bone Shield',
                    raw_stats=tuple((sid, layer, 40 if sid == 20 else value) for sid, layer, value in item.raw_stats),
                ),
                context,
                'false',
            ),
            (
                'empty-preparation-base',
                replace(item, runeword=None, name=None, socket_contents='empty', socket_items=()),
                context,
                'false',
            ),
        ]
        for skill, minimum in skills:
            maximum = 1 if quality == 'low_quality' else 3
            for label, value, truth in (('below', minimum - 1, 'false'), ('maximum', maximum, 'true')):
                stats = tuple(
                    (sid, layer, value if sid == 107 and layer == skill else n)
                    for sid, layer, n in item.raw_stats
                    if not (value == 0 and sid == 107 and layer == skill)
                )
                examples.append(
                    (f'{label}-skill-{skill}', replace(item, raw_stats=stats, complete=True), context, truth)
                )
            missing = tuple(stat for stat in item.raw_stats if stat[:2] != (107, skill))
            examples.append((f'unread-skill-{skill}', replace(item, raw_stats=missing), context, 'unknown'))
        if klass == 'Paladin':
            total = tuple((sid, layer, 70 if sid in (39, 41, 43, 45) else n) for sid, layer, n in item.raw_stats)
            examples.append(('45-inherent-plus-25-recipe', replace(item, raw_stats=total), context, 'true'))
        for label, candidate, ctx, truth in examples:
            config = role + '-stats'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if label in ('wrong-base', 'empty-preparation-base'):
                expected['roles'] = ~Contains(IsPartialDict(id=role))
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('153:0', '80:0', '39:0', *(f'107:{s}' for s, _ in skills))
                        }
                    )
                )
            yield Case(
                id=f'rhyme-class/{role}/{quality}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (config,),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/0',
                    'third-parties/d2data/json/runes.json:/Rhyme',
                ),
            )


CASES = tuple(cases())
