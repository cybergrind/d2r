"""Tomb Reaver casting versus melee, native sockets and observed ethereal safety."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ECHO = 'echoing-strike-warlock-guide-tomb-reaver-weapon-tail-alternative'
MIRROR = 'mirrored-blades-warlock-guide-tomb-reaver-weapon-tail-alternative'
COMMON = {
    '17:0': 'desirable',
    '18:0': 'desirable',
    '194:0': 'desirable',
    **dict.fromkeys(('39:0', '41:0', '43:0', '45:0', '80:0', '86:0', '122:0', '124:0'), 'supporting'),
}
RAW = (
    (93, 0, 60),
    (89, 0, 4),
    (17, 0, 200),
    (18, 0, 200),
    (122, 0, 150),
    (80, 0, 50),
    *((sid, 0, 30) for sid in (39, 41, 43, 45)),
    (124, 0, 250),
    (155, 1, 10),
    (86, 0, 10),
    (194, 0, 1),
)
ROLLS = {17: (200, 280), 122: (150, 230), 80: (50, 80), 39: (30, 50), 124: (250, 350), 86: (10, 14)}


def cases():
    original = Item('Cryptic Axe', 'unique', 'Tomb Reaver', RAW, sockets=1, named_table_id=298)
    ctx = {'player_class': 'Warlock'}
    rows = [('minimum', original, ctx, 'true', 'true')]
    for stat, (_low, high) in ROLLS.items():
        group = (17, 18) if stat == 17 else (39, 41, 43, 45) if stat == 39 else (stat,)
        raw = tuple((s, p, high if s in group else v) for s, p, v in RAW)
        rows.append((f'maximum-{stat}', replace(original, raw_stats=raw), ctx, 'true', 'true'))
    for count in (0, 2, 3, 4):
        item = replace(original, sockets=count, raw_stats=tuple((s, p, count if s == 194 else v) for s, p, v in RAW))
        truth = 'true' if count in (2, 3) else 'false'
        rows.append((f'sockets-{count}', item, ctx, truth, truth))
    rows += [
        ('ethereal-unverified-safety', replace(original, ethereal=True), ctx, 'true', 'unknown'),
        ('ethereal-known-destructible', replace(original, ethereal=True, complete=True), ctx, 'true', 'false'),
        (
            'ethereal-zod',
            replace(
                original,
                ethereal=True,
                socket_contents='filled',
                socket_items=(SocketItem('Zod Rune'),),
                raw_stats=(*RAW, (152, 0, 1)),
            ),
            ctx,
            'true',
            'true',
        ),
        (
            'unread-indestructible',
            replace(original, ethereal=True, socket_contents='filled', socket_items=(SocketItem('Zod Rune'),)),
            ctx,
            'true',
            'unknown',
        ),
        ('unknown-ethereal', replace(original, ethereal=None), ctx, 'true', 'unknown'),
        (
            'unknown-sockets',
            replace(original, sockets=None, socket_contents='unknown', raw_stats=tuple(s for s in RAW if s[0] != 194)),
            ctx,
            'unknown',
            'unknown',
        ),
        ('unknown-filler', replace(original, socket_contents='unknown'), ctx, 'true', 'true'),
        (
            'shael',
            replace(
                original,
                socket_contents='filled',
                socket_items=(SocketItem('Shael Rune'),),
                raw_stats=tuple((s, p, 80 if s == 93 else v) for s, p, v in RAW),
            ),
            ctx,
            'true',
            'true',
        ),
        ('unidentified', replace(original, identified=False), ctx, 'false', 'false'),
        ('wrong-class', original, {'player_class': 'Barbarian'}, 'false', 'false'),
        ('unknown-class', original, {}, 'unknown', 'unknown'),
        ('unread-all', replace(original, raw_stats=((194, 0, 1),)), ctx, 'true', 'true'),
    ]
    for key in (*COMMON, '93:0'):
        if key == '194:0':
            continue  # its absence is the dedicated unknown-sockets case
        pair = tuple(map(int, key.split(':')))
        rows.append(
            ('unread-' + key, replace(original, raw_stats=tuple(s for s in RAW if s[:2] != pair)), ctx, 'true', 'true')
        )
    for label, item, context, echo, mirror in rows:
        present = {f'{s}:{p}' for s, p, _ in item.raw_stats}
        roles = []
        annotations = {}
        absent = {}
        inactive = []
        for role, truth in ((ECHO, echo), (MIRROR, mirror)):
            config = role + '-stats'
            roles.append(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
            grades = {**COMMON, **({'93:0': 'desirable'} if role == MIRROR else {})}
            if truth == 'true':
                for key, grade in grades.items():
                    if key in present:
                        annotations.setdefault(key, []).append(
                            IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                        )
            else:
                inactive.append(config)
            for key in (*grades, '93:0', '155:1', '89:0'):
                if key not in present or key not in grades:
                    absent.setdefault(key, []).append(config)
        expected = {
            'assessment': IsPartialDict(
                roles=Contains(*roles),
                stat_evaluation=IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(contributions=Contains(*v)) for k, v in annotations.items()}
                    )
                ),
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        }
        checks = []
        if label == 'minimum' or label.startswith('maximum-') or label in ('sockets-2', 'sockets-3'):
            values = {s: v for s, p, v in item.raw_stats}
            expected['extraction'] = IsPartialDict(
                decoded_stats=Contains(
                    *[
                        IsPartialDict(
                            **(
                                {'memory_stats': Contains(IsPartialDict(id=stat, layer=0))}
                                if stat == 17
                                else {'memory_stat': IsPartialDict(id=stat, layer=0)}
                            ),
                            roll_range=IsPartialDict(min=lo, max=hi),
                            roll_quality='perfect' if values[stat] == hi else 'low' if values[stat] == lo else 'normal',
                        )
                        for stat, (lo, hi) in {**ROLLS, 194: (1, 3)}.items()
                    ]
                )
            )
            checks = ['Tomb Reaver', 'Trade tier:', '10% Reanimate as: Returned']
        if label == 'ethereal-zod':
            checks.append('Sockets: 1 (1-3) — Zod')
        if label == 'shael':
            checks.append('Sockets: 1 (1-3) — Shael')
        yield Case(
            id='tomb-reaver/' + label,
            item=item,
            context=context,
            expected=expected,
            covers=(ECHO, MIRROR),
            scenario='unknown'
            if 'unknown' in (echo, mirror) or label.startswith('unread')
            else 'positive'
            if 'true' in (echo, mirror)
            else 'negative',
            absent_configurations=tuple(inactive),
            absent_stat_configurations={k: tuple(v) for k, v in absent.items()},
            report_contains=tuple(checks),
            detail_contains=(
                'Echoing Strike uses FCR',
                'Mirrored Blades uses IAS',
                'Life after each kill requires wearer kill credit',
            )
            if 'true' in (echo, mirror)
            else (),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/298',
                'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/slots/Weapon/12',
                'pricing/data/wp-a-builds.json:/mirrored-blades-warlock-guide/slots/Weapon/0',
            ),
        )


CASES = tuple(cases())
