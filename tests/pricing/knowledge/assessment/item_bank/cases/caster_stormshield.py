"""Shared Stormshield captures verify four independently sourced Sorceress uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


BUILDS = ('fire-wall-sorceress-guide', 'frozen-orb-meteor-sorceress', 'frozen-orb-sorceress', 'hydra-sorceress')
ROLES = tuple(build + '-stormshield-caster-defense-gear' for build in BUILDS)
CONFIGS = tuple(role + '-stats' for role in ROLES)
RAW = (
    (214, 0, 30),
    (36, 0, 35),
    (0, 0, 30),
    (152, 0, 1),
    (102, 0, 35),
    (41, 0, 25),
    (20, 0, 25),
    (43, 0, 60),
    (128, 0, 10),
)
PRIORITIES = {
    '36:0': 'desirable',
    '0:0': 'supporting',
    '102:0': 'desirable',
    '41:0': 'desirable',
    '20:0': 'desirable',
    '43:0': 'desirable',
    '214:0': 'supporting',
}


def cases():
    context = {'player_class': 'Sorceress'}
    original = Item('Monarch', 'unique', 'Stormshield', RAW, named_table_id=253)
    rows = [
        ('native-stats', original, context, 'true'),
        ('level-73', replace(original, viewer_level=73), context, 'true'),
        ('level-99', replace(original, viewer_level=99), context, 'true'),
        ('ethereal-invalid', replace(original, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
        ('wrong-class', original, {'player_class': 'Necromancer'}, 'false'),
        ('unknown-class', original, {}, 'unknown'),
        ('unidentified', replace(original, identified=False), context, 'false'),
        ('unread-stats', replace(original, raw_stats=()), context, 'true'),
        ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ('empty-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), context, 'true'),
        (
            'unknown-filler',
            replace(original, sockets=1, socket_contents='unknown', raw_stats=(*RAW, (194, 0, 1))),
            context,
            'true',
        ),
        (
            'shael-socket',
            replace(
                original,
                sockets=1,
                socket_contents='filled',
                socket_items=(SocketItem('Shael Rune'),),
                raw_stats=(*((s, p, 55 if s == 102 else v) for s, p, v in RAW), (194, 0, 1)),
            ),
            context,
            'true',
        ),
        ('invalid-two-sockets', replace(original, sockets=2, raw_stats=(*RAW, (194, 0, 2))), context, 'false'),
    ]
    for key in PRIORITIES:
        stat, layer = map(int, key.split(':'))
        rows.append(
            (
                'unread-' + key,
                replace(original, raw_stats=tuple(s for s in RAW if s[:2] != (stat, layer))),
                context,
                'true',
            )
        )
    for label, item, loadout, truth in rows:
        captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
        active = truth == 'true'
        expected = {
            'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
        }
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(
                            contributions=Contains(
                                *(
                                    IsPartialDict(configuration_id=role + '-stats', role_id=role, desirability=grade)
                                    for role in ROLES
                                )
                            )
                        )
                        for key, grade in PRIORITIES.items()
                        if key in captured
                    }
                )
            )
        yield Case(
            id='caster-stormshield/' + label,
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=ROLES,
            scenario='unknown'
            if truth == 'unknown' or label.startswith('unread')
            else 'positive'
            if active
            else 'negative',
            absent_configurations=() if active else CONFIGS,
            absent_stat_configurations={
                key: CONFIGS
                for key in (*PRIORITIES, '128:0', '152:0')
                if key not in captured or key in ('128:0', '152:0')
            },
            report_contains=(('Stormshield',) if item.identified else ())
            + (('Sockets: 1 — Shael',) if label == 'shael-socket' else ())
            + (
                (f'+{30 * item.viewer_level // 8} Defense (Based on Character Level)',)
                if item.identified and '214:0' in captured
                else ()
            ),
            detail_contains=(
                'the shield alone does not establish maximum block',
                'preserve needed Faster Cast Rate elsewhere',
                'Lightning thorns are not caster spell damage',
            )
            if active
            else (),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/253',
                *(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__{build}.html/sections/{30 if build == BUILDS[0] else 29}'
                    for build in BUILDS
                ),
            ),
        )


CASES = tuple(cases())
