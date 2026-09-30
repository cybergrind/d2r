"""Poison Nova's Homunculus alternative preserves shield and casting distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'poison-nova-necromancer-homunculus-equipment-tail-alternative'
CONFIG = ROLE + '-stats'
RAW = (
    (83, 2, 2),
    (188, 16, 2),
    (102, 0, 30),
    (20, 0, 40),
    (1, 0, 20),
    (27, 0, 33),
    (138, 0, 5),
    *((s, 0, 40) for s in (39, 41, 43, 45)),
)
PRIORITIES = {f'{s}:{p}': 'desirable' if s in (83, 39, 41, 43, 45) else 'supporting' for s, p, _ in RAW}


def cases():
    context = {'player_class': 'Necromancer'}
    for base in ('Heirophant Trophy', 'Bloodlord Skull'):
        original = Item(base, 'unique', 'Homunculus', (*RAW, (16, 0, 150)), named_table_id=280)
        rows = [
            ('minimum-defense', original, context, 'true'),
            ('perfect-defense', replace(original, raw_stats=(*RAW, (16, 0, 200))), context, 'true'),
            ('ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('wrong-class', original, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('unread-stats', replace(original, raw_stats=()), context, 'true'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
            (
                'one-empty-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'one-unknown-filler',
                replace(original, sockets=1, socket_contents='unknown', raw_stats=(*original.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'um-socket',
                replace(
                    original,
                    sockets=1,
                    socket_contents='filled',
                    socket_items=(SocketItem('Um Rune'),),
                    raw_stats=(
                        *tuple((s, p, 62 if s in (39, 41, 43, 45) else v) for s, p, v in original.raw_stats),
                        (194, 0, 1),
                    ),
                ),
                context,
                'true',
            ),
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
            captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
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
            yield Case(
                id=f'poison-homunculus/{base}/{label}',
                item=item,
                context=loadout,
                expected={
                    'assessment': IsPartialDict(**expected),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                    **(
                        {
                            'extraction': IsPartialDict(
                                decoded_stats=Contains(
                                    IsPartialDict(
                                        memory_stat={
                                            'id': 16,
                                            'layer': 0,
                                            'raw': 200 if label == 'perfect-defense' else 150,
                                        },
                                        roll_quality='perfect' if label == 'perfect-defense' else 'low',
                                    )
                                )
                            )
                        }
                        if label in ('minimum-defense', 'perfect-defense')
                        else {}
                    ),
                },
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
                report_contains=(('Homunculus', 'Trade tier:') if item.identified else ())
                + (('Sockets: 1 — Um',) if label == 'um-socket' else ())
                + (('(150-200%) Enhanced Defense',) if label in ('minimum-defense', 'perfect-defense') else ()),
                detail_contains=(
                    'Maximum block requires character level and Dexterity',
                    'Mana after each kill needs wearer kill credit',
                )
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/poison-nova-necromancer/slots/Off-Hand/2',
                    'third-parties/d2data/json/uniqueitems.json:/280',
                ),
            )


CASES = tuple(cases())
