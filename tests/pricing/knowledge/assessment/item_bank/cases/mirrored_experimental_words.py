"""Experimental Mirrored Blades proc words retain trigger and damage-type distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    (
        'Rift',
        'War Scepter',
        'Thresher',
        ('Hel', 'Ko', 'Lem', 'Gul'),
        (
            (198, 15696, 20),
            (195, 4117, 16),
            (52, 0, 160),
            (53, 0, 250),
            (48, 0, 60),
            (49, 0, 180),
            (114, 0, 38),
            (0, 0, 5),
            (1, 0, 5),
            (2, 0, 15),
            (3, 0, 5),
            (119, 0, 20),
            (79, 0, 75),
            (91, 0, -20),
            (204, 4879, 40 | (40 << 8)),
        ),
        ('198:15696', '195:4117'),
        ('52:0', '53:0', '48:0', '49:0', '114:0', '0:0', '1:0', '2:0', '3:0', '119:0'),
        ('204:4879',),
    ),
    (
        'Destruction',
        'Phase Blade',
        'Thresher',
        ('Vex', 'Lo', 'Ber', 'Jah', 'Ko'),
        (
            (198, 14679, 5),
            (195, 3094, 15),
            (198, 15628, 23),
            (197, 3629, 100),
            (17, 0, 350),
            (18, 0, 350),
            (52, 0, 100),
            (53, 0, 180),
            (136, 0, 20),
            (141, 0, 20),
            (62, 0, 7),
            (115, 0, 1),
            (2, 0, 10),
            (117, 0, 1),
        ),
        ('198:14679', '195:3094', '198:15628', '17:0', '18:0', '136:0', '141:0'),
        ('52:0', '53:0', '62:0', '115:0', '2:0'),
        ('197:3629',),
    ),
)


def cases():
    context = {'player_class': 'Warlock'}
    for name, base, alternative, runes, raw, primary, support, excluded in SPECS:
        role = f'mirrored-blades-warlock-guide-{name.lower()}-experimental-proc-recipe'
        config = role + '-stats'
        count = len(runes)
        for quality in ('normal', 'superior', 'low_quality'):
            original = Item(
                base,
                quality,
                name,
                (*raw, (194, 0, count)),
                sockets=count,
                socket_contents='filled',
                socket_items=tuple(SocketItem(r + ' Rune') for r in runes),
                runeword=name,
            )
            rows = [
                ('native', original, context, 'true'),
                ('polearm', replace(original, base=alternative), context, 'true'),
                ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
                ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
                ('unidentified', replace(original, identified=False), context, 'false'),
                ('empty', replace(original, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(original, socket_contents='unknown', socket_items=()), context, 'unknown'),
                (
                    'wrong-count',
                    replace(
                        original,
                        sockets=count - 1,
                        raw_stats=(*raw, (194, 0, count - 1)),
                        socket_items=original.socket_items[:-1],
                    ),
                    context,
                    'false',
                ),
                (
                    'uncaptured-procs',
                    replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] not in (195, 198))),
                    context,
                    'true',
                ),
                ('uncaptured-stats', replace(original, raw_stats=((194, 0, count),)), context, 'true'),
            ]
            if name == 'Rift':
                rows += [
                    (
                        'maximum-attributes',
                        replace(
                            original,
                            raw_stats=tuple(
                                (a, b, 20 if a == 2 else 10) if a in (0, 1, 2, 3) else (a, b, c)
                                for a, b, c in original.raw_stats
                            ),
                        ),
                        context,
                        'true',
                    ),
                    ('ethereal-scepter', replace(original, ethereal=True), context, 'false'),
                ]
            for label, item, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                captured = {f'{a}:{b}' for a, b, _ in item.raw_stats}
                active = truth == 'true'
                priorities = {**dict.fromkeys(primary, 'desirable'), **dict.fromkeys(support, 'supporting')}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                                    )
                                )
                                for key, grade in priorities.items()
                                if key in captured
                            }
                        )
                    )
                yield Case(
                    id=f'mirrored-experimental/{name}/{quality}/{label}',
                    item=item,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario='unknown'
                    if truth == 'unknown' or label.startswith('uncaptured')
                    else 'positive'
                    if active
                    else 'negative',
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(
                        (*excluded, *(k for k in priorities if k not in captured)), (config,)
                    ),
                    report_contains=(name, 'Experimental Mirrored Blades', f'Sockets: {count}') if active else (),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__mirrored-blades-warlock-guide.html/sections/9',
                        f'third-parties/d2data/json/runes.json:/{name}',
                    ),
                )


CASES = tuple(cases())
