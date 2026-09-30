"""String of Ears defense rolls; life leech is not applied to spells, traps or Smite."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Barbarian': (('double-throw-barbarian-guide', 6, True),),
    'Assassin': (
        ('dragon-talon-assassin', 3, True),
        ('lightning-sentry-assassin', 2, False),
        ('wake-of-fire-assassin', 2, False),
    ),
    'Paladin': (('dream-paladin', 1, True), ('smite-paladin', 2, False)),
    'Sorceress': (('nova-sorceress-guide', 4, False),),
}
SUFFIX = '-string-of-ears-defensive-alternative'
RANGES = {35: (10, 15), 36: (10, 15), 60: (6, 8), 16: (150, 180)}
ROLLS = (
    ('minimum', 10, 10, 6, 150),
    ('perfect', 15, 15, 8, 180),
    ('mdr-perfect', 15, 10, 6, 150),
    ('dr-perfect', 10, 15, 6, 150),
    ('leech-perfect', 10, 10, 8, 150),
    ('defense-perfect', 10, 10, 6, 180),
)


def belt(base, defense, mdr=10, dr=10, leech=6, ed=150):
    return Item(
        base,
        'unique',
        'String of Ears',
        (
            (35, 0, mdr),
            (36, 0, dr),
            (60, 0, leech),
            (16, 0, ed),
            (31, 0, defense * (100 + ed) // 100 + 15),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + SUFFIX for g, _, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        leech_configs = tuple(g + SUFFIX + '-stats' for g, _, leech in uses if leech)
        context = {'player_class': player_class}
        examples = [
            (base + '/' + label, belt(base, defense, mdr, dr, leech, ed), context, 'true')
            for base, defense in (('Demonhide Sash', 35), ('Spiderweb Sash', 62))
            for label, mdr, dr, leech, ed in ROLLS
        ]
        item = belt('Demonhide Sash', 35)
        examples.extend(
            (
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('impossible-socket', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                (
                    'unread-leech',
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 60), complete=False),
                    context,
                    'true',
                ),
            )
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                annotations = {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('35:0', '36:0')}
                if leech_configs and label != 'unread-leech':
                    annotations['60:0'] = IsPartialDict(configuration_ids=Contains(*leech_configs))
                expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=RANGES[stat][0], max=RANGES[stat][1]),
                                roll_quality='perfect' if value == RANGES[stat][1] else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in RANGES
                        )
                    )
                )
            absent = dict.fromkeys(('16:0', '31:0'), configs)
            absent['60:0'] = configs if label == 'unread-leech' else tuple(c for c in configs if c not in leech_configs)
            yield Case(
                id=f'string-ears-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-leech'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('String of Ears', 'Trade tier:') if truth == 'true' else (candidate.base,),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/242',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Belts/{i}' for g, i, _ in uses),
                ),
            )


CASES = tuple(cases())
