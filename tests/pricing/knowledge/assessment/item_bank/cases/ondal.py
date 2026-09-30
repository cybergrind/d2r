"""Ondal skill and utility rolls; experience gain never implies damage or Magic Find."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ECHO = 'echoing-strike-warlock-guide-ondal-s-wisdom-caster-utility-alternative'
FIRE = 'fire-warlock-guide-ondal-s-wisdom-caster-utility-alternative'
RAW = ((127, 0, 2), (105, 0, 45), (1, 0, 40), (31, 0, 450), (85, 0, 5), (35, 0, 5))
ROLLS = {127: (2, 4), 1: (40, 50), 31: (450, 550), 35: (5, 8)}


def cases():
    original = Item('Elder Staff', 'unique', "Ondal's Wisdom", RAW, named_table_id=388)
    context = {'player_class': 'Warlock'}
    rows = [('minimum', original, context, 'true')]
    for sid, (_low, high) in ROLLS.items():
        rows.append(
            (
                f'maximum-{sid}',
                replace(original, raw_stats=tuple((s, p, high if s == sid else v) for s, p, v in RAW)),
                context,
                'true',
            )
        )
    rows += [
        ('complete-minimum', replace(original, complete=True), context, 'true'),
        (
            'tir-filled',
            replace(
                original,
                sockets=1,
                socket_contents='filled',
                socket_items=(SocketItem('Tir Rune'),),
                raw_stats=(*RAW, (194, 0, 1), (138, 0, 2)),
            ),
            context,
            'true',
        ),
        ('ethereal', replace(original, ethereal=True), context, 'true'),
        ('unknown-ethereal', replace(original, ethereal=None), context, 'true'),
        ('one-open-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), context, 'true'),
        (
            'unknown-filler',
            replace(original, sockets=1, socket_contents='unknown', raw_stats=(*RAW, (194, 0, 1))),
            context,
            'true',
        ),
        ('invalid-two-sockets', replace(original, sockets=2, raw_stats=(*RAW, (194, 0, 2))), context, 'false'),
        ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ('unidentified', replace(original, identified=False), context, 'false'),
        ('wrong-class', original, {'player_class': 'Barbarian'}, 'false'),
        ('unknown-class', original, {}, 'unknown'),
        ('unread-all', replace(original, raw_stats=()), context, 'true'),
    ]
    for sid in (127, 105, 1, 31, 85, 35):
        rows.append(
            (f'unread-{sid}', replace(original, raw_stats=tuple(s for s in RAW if s[0] != sid)), context, 'true')
        )
    for label, item, ctx, truth in rows:
        present = {f'{s}:{p}' for s, p, _ in item.raw_stats}
        annotations = {}
        absent = {}
        for role in (ECHO, FIRE):
            config = role + '-stats'
            grades = {
                '127:0': 'desirable',
                '105:0': 'desirable',
                **dict.fromkeys(('1:0', '31:0', '85:0', '35:0'), 'supporting'),
            }
            if truth == 'true':
                for key, grade in grades.items():
                    if key in present:
                        annotations.setdefault(key, []).append(
                            IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                        )
            for key in ('127:0', '105:0', '1:0', '31:0', '85:0', '35:0'):
                if key not in grades or key not in present:
                    absent.setdefault(key, []).append(config)
        expected = {
            'assessment': IsPartialDict(
                roles=Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in (ECHO, FIRE))),
                stat_evaluation=IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(contributions=Contains(*v)) for k, v in annotations.items()}
                    )
                ),
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        }
        if label in ('minimum', 'complete-minimum') or label.startswith('maximum-'):
            values = {s: v for s, _, v in item.raw_stats}
            expected['extraction'] = IsPartialDict(
                decoded_stats=Contains(
                    *(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=s, layer=0),
                            roll_range=IsPartialDict(min=low, max=high),
                            roll_quality='perfect' if values[s] == high else 'low',
                        )
                        for s, (low, high) in ROLLS.items()
                    )
                )
            )
        yield Case(
            id='ondal/' + label,
            item=item,
            context=ctx,
            expected=expected,
            covers=(ECHO, FIRE),
            scenario='unknown'
            if truth == 'unknown' or label.startswith('unread')
            else 'positive'
            if truth == 'true'
            else 'negative',
            absent_configurations=tuple(r + '-stats' for r in (ECHO, FIRE)) if truth != 'true' else (),
            absent_stat_configurations={k: tuple(v) for k, v in absent.items()},
            report_contains=("Ondal's Wisdom", 'Trade tier:')
            if label == 'minimum'
            else ('Sockets: 1 — Tir',)
            if label == 'tir-filled'
            else (),
            detail_contains=(
                'Experience gain requires the staff to be active and does not multiply damage or Magic Find',
                'Flat defense and magic damage reduction are separate',
                'Casting-only use does not authorize melee durability safety',
            )
            if truth == 'true'
            else (),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/388',
                'third-parties/d2data/json/gems.json:/r03',
                'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Weapon/7',
                'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/slots/Weapon/15',
            ),
        )


CASES = tuple(cases())
