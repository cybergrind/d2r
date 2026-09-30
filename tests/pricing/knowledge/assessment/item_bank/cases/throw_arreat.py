"""Double Throw Arreat's Face keeps native rolls, upgrades and attack utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'double-throw-barbarian-guide-arreat-s-face-equipment-tail-alternative'
CONFIG = ROLE + '-stats'
RAW = (
    (83, 4, 2),
    (188, 32, 2),
    (99, 0, 30),
    (119, 0, 20),
    (0, 0, 20),
    (2, 0, 20),
    *((s, 0, 30) for s in (39, 41, 43, 45)),
)
PRIORITIES = {f'{s}:{p}': 'desirable' if s in (83, 188, 99) else 'supporting' for s, p, _ in RAW} | {
    '60:0': 'desirable'
}


def cases():
    context = {'player_class': 'Barbarian'}
    for base in ('Slayer Guard', 'Guardian Crown'):
        original = Item(base, 'unique', "Arreat's Face", (*RAW, (16, 0, 150), (60, 0, 3)), named_table_id=279)
        rows = [
            (f'rolls-{ed}-{leech}', replace(original, raw_stats=(*RAW, (16, 0, ed), (60, 0, leech))), context, 'true')
            for ed in (150, 200)
            for leech in (3, 6)
        ]
        rows += [
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unread-stats', replace(original, raw_stats=()), context, 'true'),
            (
                'empty-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'unknown-filler',
                replace(original, sockets=1, socket_contents='unknown', raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ]
        for key in PRIORITIES:
            stat, layer = map(int, key.split(':'))
            rows.append(
                (
                    'unread-' + key,
                    replace(original, raw_stats=tuple(s for s in original.raw_stats if s[:2] != (stat, layer))),
                    context,
                    'true',
                )
            )
        for label, item, loadout, truth in rows:
            active = truth == 'true'
            captured = {f'{s}:{p}': v for s, p, v in item.raw_stats}
            assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(configuration_id=CONFIG, role_id=ROLE, desirability=grade)
                                )
                            )
                            for key, grade in PRIORITIES.items()
                            if key in captured
                        }
                    )
                )
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            if label.startswith('rolls'):
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat={'id': stat, 'layer': 0, 'raw': captured[f'{stat}:0']},
                                roll_quality='perfect' if captured[f'{stat}:0'] == maximum else 'low',
                            )
                            for stat, maximum in ((16, 200), (60, 6))
                        )
                    )
                )
            yield Case(
                id=f'throw-arreat/{base}/{label}',
                item=item,
                context=loadout,
                expected=expected,
                covers=(ROLE,),
                scenario='unknown'
                if truth == 'unknown' or label.startswith('unread')
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations={
                    key: (CONFIG,) for key in (*PRIORITIES, '16:0') if key not in captured or key == '16:0'
                },
                report_contains=(("Arreat's Face", 'Trade tier:') if item.identified and item.ethereal is False else ())
                + (
                    ('(150-200%) Enhanced Defense', '% (3-6%) Life stolen per hit') if label.startswith('rolls') else ()
                ),
                detail_contains=('attack speed still depends on the full setup', 'do not assume a socket filler')
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots/Helmets/10',
                    'third-parties/d2data/json/uniqueitems.json:/279',
                ),
            )


CASES = tuple(cases())
