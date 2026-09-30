"""Trap magic-item combinations retain exact suffix thresholds and unknown stats."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BUILDS = ('lightning-sentry-assassin', 'wake-of-fire-assassin')
SPECS = (
    ('magus', 'Circlet', 105, 20, 10, ('Helmets/1', 'Helmets/0')),
    ('apprentice', 'Amulet', 105, 10, 0, ('Amulets/2', 'Amulets/2')),
    ('whale', 'Amulet', 7, 81 * 256, 80 * 256, ('Amulets/1', 'Amulets/1')),
)


def cases():
    context = {'player_class': 'Assassin'}
    for suffix, base, stat, value, below, slots in SPECS:
        roles = tuple(build + '-cunning-' + suffix for build in BUILDS)
        configs = tuple(role + '-stats' for role in roles)
        item = Item(base, 'magic', raw_stats=((188, 48, 3), (stat, 0, value)))
        variants = [
            ('qualifying', item, context, 'true'),
            ('two-trap-skills', replace(item, raw_stats=((188, 48, 2), (stat, 0, value))), context, 'false'),
            ('lower-suffix', replace(item, raw_stats=((188, 48, 3), (stat, 0, below))), context, 'false'),
            ('unread-suffix', replace(item, raw_stats=((188, 48, 3),), complete=False), context, 'unknown'),
            ('known-no-suffix', replace(item, raw_stats=((188, 48, 3),), complete=True), context, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
        ]
        if suffix == 'whale':
            variants.append(
                ('perfect-life', replace(item, raw_stats=((188, 48, 3), (7, 0, 100 * 256))), context, 'true')
            )
        if suffix == 'magus':
            variants.append(('diadem', replace(item, base='Diadem'), context, 'true'))
        for label, specimen, ctx, truth in variants:
            active = truth == 'true'
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles))
            }
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('188:48', f'{stat}:0')}
                    )
                )
            yield Case(
                id=f'cunning-assassin-magic/{suffix}/{label}',
                item=specimen,
                context=ctx,
                covers=roles,
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else configs,
                report_contains=('+3 to Traps',) if active else (),
                evidence=tuple(
                    'pricing/data/wp-a-builds.json:/' + build + '/slots/' + slot
                    for build, slot in zip(BUILDS, slots, strict=True)
                ),
            )


CASES = tuple(cases())
