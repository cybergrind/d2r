"""Exact Berserk Unbending Will swords; leech is not healing from converted magic damage."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    context = {'player_class': 'Barbarian'}
    raw = (
        (17, 0, 300),
        (18, 0, 300),
        (93, 0, 20),
        (188, 32, 3),
        (0, 0, 10),
        (3, 0, 10),
        (34, 0, 8),
        (60, 0, 8),
        (117, 0, 1),
    )
    for base in ('Phase Blade', 'Colossus Blade'):
        slug = base.lower().replace(' ', '-')
        role = f'berserk-barbarian-unbending-will-{slug}-combat-word-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base, quality, 'Unbending Will', raw, sockets=6, socket_contents='filled', runeword='Unbending Will'
            )
            rows = [
                ('minimum', item, context, 'true'),
                (
                    'maximum',
                    replace(
                        item,
                        raw_stats=tuple(
                            (s, layer, {17: 350, 18: 350, 93: 30, 60: 10}.get(s, v)) for s, layer, v in raw
                        ),
                    ),
                    context,
                    'true',
                ),
                ('uncited-base', replace(item, base='Crystal Sword'), context, 'absent'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('wrong-count', replace(item, sockets=5), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            ]
            if base == 'Colossus Blade':
                rows += [
                    ('ethereal', replace(item, ethereal=True), context, 'false'),
                    ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ]
            for label, candidate, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'absent':
                    expected = {'roles': FunctionCheck(lambda rows, target=role: all(r['id'] != target for r in rows))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in ('17:0', '93:0', '188:32', '0:0', '3:0', '34:0')
                            }
                        )
                    )
                yield Case(
                    id=f'berserk/unbending/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown', 'absent': 'negative'}[
                        truth
                    ],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations={'60:0': (role + '-stats',)},
                    report_contains=('Unbending Will',),
                    evidence=(
                        'pricing/data/wp-a-builds.json:/berserk-barbarian/slots/Weapon',
                        'third-parties/d2data/json/runes.json:/Unbending Will',
                    ),
                )


CASES = tuple(cases())
