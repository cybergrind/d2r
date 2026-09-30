"""Mang Song's three independent pierce rolls and build-specific spell utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ECHO = 'echoing-strike-warlock-guide-mang-song-s-lesson-caster-utility-alternative'
FIRE = 'fire-warlock-guide-mang-song-s-lesson-caster-utility-alternative'
RAW = ((127, 0, 5), (105, 0, 30), (27, 0, 10), (333, 0, 7), (334, 0, 7), (335, 0, 7))


def cases():
    original = Item('Archon Staff', 'unique', "Mang Song's Lesson", RAW, named_table_id=322)
    context = {'player_class': 'Warlock'}
    rows = [('minimum', original, context, 'true')]
    for sid in (333, 334, 335):
        rows.append(
            (
                f'maximum-{sid}',
                replace(original, raw_stats=tuple((s, p, 15 if s == sid else v) for s, p, v in RAW)),
                context,
                'true',
            )
        )
    rows += [
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
    for sid in (127, 105, 27, 333, 334, 335):
        rows.append(
            (f'unread-{sid}', replace(original, raw_stats=tuple(s for s in RAW if s[0] != sid)), context, 'true')
        )
    for label, item, ctx, truth in rows:
        present = {f'{s}:{p}' for s, p, _ in item.raw_stats}
        annotations = {}
        absent = {}
        for role in (ECHO, FIRE):
            config = role + '-stats'
            grades = {'127:0': 'desirable', '105:0': 'desirable', '27:0': 'supporting'}
            if role == FIRE:
                grades['333:0'] = 'desirable'
            if truth == 'true':
                for key, grade in grades.items():
                    if key in present:
                        annotations.setdefault(key, []).append(
                            IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                        )
            for key in ('127:0', '105:0', '27:0', '333:0', '334:0', '335:0'):
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
        if label == 'minimum' or label.startswith('maximum-'):
            values = {s: v for s, _, v in item.raw_stats}
            expected['extraction'] = IsPartialDict(
                decoded_stats=Contains(
                    *(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=s, layer=0),
                            roll_range=IsPartialDict(min=7, max=15),
                            roll_quality='perfect' if values[s] == 15 else 'low',
                        )
                        for s in (333, 334, 335)
                    )
                )
            )
        yield Case(
            id='mang-song/' + label,
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
            report_contains=("Mang Song's Lesson", 'Trade tier:') if label == 'minimum' else (),
            detail_contains=(
                'Elemental resistance piercing does not increase physical or magic damage',
                'Casting-only use does not authorize melee durability safety',
            )
            if truth == 'true'
            else (),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/322',
                'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Weapon/6',
                'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/slots/Weapon/14',
            ),
        )


CASES = tuple(cases())
