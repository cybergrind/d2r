"""Remaining Abyss mercenary table configurations and native boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_tail import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


EXTRA = (
    (
        'chains-of-honor',
        108,
        Item(
            'Archon Plate',
            'normal',
            'Chains of Honor',
            (
                (127, 0, 2),
                (60, 0, 8),
                (0, 0, 20),
                (16, 0, 70),
                (36, 0, 8),
                (74, 0, 7),
                (80, 0, 25),
                (121, 0, 200),
                (122, 0, 100),
                *((s, 0, 65) for s in (39, 41, 43, 45)),
            ),
            ethereal=True,
            sockets=4,
            socket_contents='filled',
            runeword='Chains of Honor',
        ),
        ('127:0', '60:0', '36:0', '39:0', '121:0', '122:0'),
        (),
    ),
    (
        'crown-of-thieves-ral',
        117,
        Item(
            'Grand Crown',
            'unique',
            'Crown of Thieves',
            ((60, 0, 9), (39, 0, 63), (7, 0, 50 * 256), (9, 0, 35 * 256), (79, 0, 80), (2, 0, 25), (16, 0, 160)),
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem('Ral Rune'),),
        ),
        ('60:0', '39:0', '7:0', '79:0', '2:0'),
        ('9:0',),
    ),
)


def cases():
    examples = [row for row in EXAMPLES if row[0] in ('undead-crown', 'resistance-mask')]
    examples.extend(EXTRA)
    result = []
    context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    for slug, _span, item, keys, irrelevant in examples:
        role = 'abyss-warlock-merc-' + slug
        rows = [
            ('native', item, context, 'positive'),
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-merc', item, {'player_class': 'Warlock'}, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'negative'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ]
        if slug == 'chains-of-honor':
            rows.extend(
                (
                    ('nonethereal', replace(item, ethereal=False), context, 'negative'),
                    ('wrong-word', replace(item, runeword='Fortitude'), context, 'negative'),
                )
            )
        elif slug in ('resistance-mask', 'crown-of-thieves-ral'):
            rows.extend(
                (
                    (
                        'wrong-filler',
                        replace(item, socket_items=(SocketItem('El Rune'), *item.socket_items[1:])),
                        context,
                        'negative',
                    ),
                    ('unread-filler', replace(item, socket_items=()), context, 'unknown'),
                )
            )
        else:
            rows.extend(
                (
                    ('upgraded', replace(item, base='Corona'), context, 'positive'),
                    ('ethereal', replace(item, ethereal=True), context, 'positive'),
                )
            )
        for label, candidate, ctx, scenario in rows:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'abyss/merc-remaining/{slug}/{label}',
                    item=candidate,
                    context=ctx,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                    report_contains=(candidate.name or candidate.base,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/sections/40',
                    ),
                )
            )
    return tuple(result)


CASES = cases()

# Both qualities retain the reviewed recipe/payload mechanics; they are not new named identities.
CASES += tuple(
    replace(case, id=case.id + '/' + quality, item=replace(case.item, rarity=quality))
    for case in CASES
    if case.item.rarity == 'normal'
    for quality in ('superior', 'low_quality')
)
