"""Abyss guide candidates: starter staffmods and the rare 2/20 circlet alternative."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def case(role, label, item, truth, keys=(), *, scenario=None):
    config = role + '-stats'
    expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
    if keys:
        expected['stat_evaluation'] = IsPartialDict(
            annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
        )
    return Case(
        id=f'abyss/affixed-candidates/{role}/{item.rarity}/{label}',
        item=item,
        context={'player_class': 'Warlock'},
        expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
        covers=(role,),
        scenario=scenario or {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
        absent_configurations=() if keys else (config,),
        absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '19:0'), (config,)),
        evidence=('pricing/data/wp-a-builds.json', 'pricing/data/wp-a-variants/abyss-warlock-build-guide.json'),
        report_contains=('Warlock',) if keys else (),
    )


def cases():
    role = 'abyss-starter-dagger'
    for quality in ('magic', 'rare'):
        original = Item('Kriss', quality, raw_stats=((107, 402, 1),))
        for label, stats, keys in (
            ('abyss', ((107, 402, 1),), ('107:402',)),
            ('miasma', ((107, 399, 1),), ('107:399',)),
            ('both-staffmods', ((107, 402, 1), (107, 399, 1)), ('107:402', '107:399')),
        ):
            yield case(role, label, replace(original, raw_stats=stats), 'true', keys)
        yield case(role, 'unknown-sockets', replace(original, sockets=None), 'true', ('107:402',))
        yield case(role, 'unread-skills', replace(original, raw_stats=()), 'unknown')
        yield case(role, 'no-skills', replace(original, raw_stats=((17, 0, 51), (18, 0, 51)), complete=True), 'false')
        yield case(role, 'attack-rating-alone', replace(original, raw_stats=((19, 0, 10),), complete=True), 'false')
        yield case(role, 'different-staffmod', replace(original, raw_stats=((107, 374, 1),), complete=True), 'false')
        if quality != 'crafted':
            yield case(role, 'ethereal', replace(original, ethereal=True), 'true', ('107:402',))
    role = 'abyss-standard-circlet'
    original = Item('Diadem', 'rare', raw_stats=((83, 7, 2), (105, 0, 20)))
    yield case(role, 'minimum', original, 'true', ('83:7', '105:0'))
    yield case(role, 'other-circlet-base', replace(original, base='Circlet'), 'true', ('83:7', '105:0'))
    yield case(role, 'unknown-sockets', replace(original, sockets=None), 'true', ('83:7', '105:0'))
    yield case(
        role,
        'supporting-frw',
        replace(original, raw_stats=(*original.raw_stats, (96, 0, 30)), sockets=2),
        'true',
        ('83:7', '105:0', '96:0'),
    )
    yield case(role, 'one-skill', replace(original, raw_stats=((83, 7, 1), (105, 0, 20)), complete=True), 'false')
    yield case(role, 'ten-fcr', replace(original, raw_stats=((83, 7, 2), (105, 0, 10)), complete=True), 'false')
    yield case(
        role, 'wrong-class-bonus', replace(original, raw_stats=((83, 1, 2), (105, 0, 20)), complete=True), 'false'
    )
    yield case(role, 'unread-fcr', replace(original, raw_stats=((83, 7, 2),)), 'unknown')
    yield case(role, 'unread-skills', replace(original, raw_stats=((105, 0, 20),)), 'unknown')
    yield case(role, 'unknown-ethereal', replace(original, ethereal=None), 'true', scenario='unknown')


def belt_cases():
    role = 'abyss-starter-crafted-belt'
    stats = ((105, 0, 5), (99, 0, 10), (9, 0, 20 * 256), (27, 0, 10), (39, 0, 10), (41, 0, 10), (43, 0, 10))
    item = Item('Sharkskin Belt', 'crafted', raw_stats=stats)
    context = {'player_class': 'Warlock', 'player_total_fcr': 75}
    keys = tuple(f'{stat}:0' for stat, _, _ in stats)
    yield replace(case(role, 'cited-rolls', item, 'true', keys), context=context)
    for stat, _, _ in stats:
        remaining = tuple(row for row in stats if row[0] != stat)
        yield replace(
            case(role, f'missing-{stat}', replace(item, raw_stats=remaining, complete=True), 'false'), context=context
        )
        yield replace(case(role, f'unread-{stat}', replace(item, raw_stats=remaining), 'unknown'), context=context)
    for label, fcr, truth in (('below-breakpoint', 74, 'false'), ('unknown-breakpoint', None, 'unknown')):
        row = case(role, label, item, 'true', scenario='negative' if fcr is not None else 'unknown')
        yield replace(
            row,
            context={**context, 'player_total_fcr': fcr},
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(
                        IsPartialDict(id=role, status='partial', dependencies=Contains(IsPartialDict(status=truth)))
                    )
                ),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
        )


CASES = (*cases(), *belt_cases())
