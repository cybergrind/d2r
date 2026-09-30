"""Wisp absorb/MF priorities never infer passive damage from on-hit or charge effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Assassin': (('dragon-talon-assassin', 0),),
    'Paladin': (('dream-paladin', 7), ('fist-of-the-heavens-paladin', 5), ('smite-paladin', 0)),
    'Druid': (('fissure-druid', 7),),
    'Sorceress': (('lightning-sorceress', 7),),
    'Necromancer': (('poison-nova-necromancer', 9),),
}
CHARGES = ((226, 2, 15), (236, 5, 13), (246, 7, 11))


def ring(absorb=10, mf=10, *, empty=False):
    return Item(
        'Ring',
        'unique',
        'Wisp Projector',
        (
            (144, 0, absorb),
            (80, 0, mf),
            (198, 49 * 64 + 16, 10),
            *((204, skill * 64 + level, (count << 8) + (0 if empty else count)) for skill, level, count in CHARGES),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-wisp-projector-find-absorb-alternative' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = ring()
        context = {'player_class': player_class}
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', ring(20, 20), context, 'true'),
            ('absorb-perfect', ring(20, 10), context, 'true'),
            ('mf-perfect', ring(10, 20), context, 'true'),
            ('depleted-spirits', ring(empty=True), context, 'true'),
            ('unread-spirits', replace(item, raw_stats=item.raw_stats[:3], complete=False), context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('144:0', '80:0')}
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=10, max=20),
                                roll_quality='perfect' if raw == 20 else 'low',
                            )
                            for stat, _, raw in candidate.raw_stats
                            if stat in (144, 80)
                        ),
                        *(
                            IsPartialDict(memory_stat=IsPartialDict(id=204, layer=skill * 64 + level), status='decoded')
                            for skill, level, _ in CHARGES
                            if label != 'unread-spirits'
                        ),
                    )
                )
            yield Case(
                id=f'wisp-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-spirits'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=dict.fromkeys(
                    (f'198:{49 * 64 + 16}', *(f'204:{s * 64 + level}' for s, level, _ in CHARGES)), configs
                ),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Wisp Projector', 'Trade tier:') if truth == 'true' else ('Ring',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/319',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Rings/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
