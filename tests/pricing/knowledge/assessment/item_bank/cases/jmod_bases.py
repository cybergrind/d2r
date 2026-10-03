"""Source-specific empty JMOD preparation bases; filled shields are separate uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    (
        'blizzard-sorceress',
        'Sorceress',
        (
            ('main-shield', '/slots/Off-Hand/2'),
            ('main-swap', '/slots/Off-Hand-Swap/3'),
            ('standard-swap', '/variants/1/player/Off-Hand Swap/0'),
        ),
    ),
    (
        'fissure-druid',
        'Druid',
        (('main-shield', '/slots/Off-Hand/1'), ('magic-find-shield', '/variants/2/player/Off-Hand/0')),
    ),
    (
        'lightning-sentry-assassin',
        'Assassin',
        (('main-shield', '/slots/Off-Hand/2'), ('main-swap', '/slots/Off-Hand-Swap/1')),
    ),
    ('lightning-sorceress', 'Sorceress', (('main-shield', '/slots/Off-Hand/3'),)),
    ('lightning-strike-amazon', 'Amazon', (('main-shield', '/slots/Off-Hand/4'),)),
    ('poison-nova-necromancer', 'Necromancer', (('main-shield', '/slots/Off-Hand/9'),)),
    (
        'lightning-fury-amazon-guide',
        'Amazon',
        (('main-shield', '/slots/Off-Hand/3'), ('ubers-shield', '/variants/3/player/Off-Hand/0')),
    ),
)


def shield(defense=133, *, sockets=4, blocking=True):
    # Native Monarch block 22 plus the Deflecting/Blocking suffix modifier.
    return Item(
        'Monarch',
        'magic',
        None,
        ((20, 0, 42 if blocking else 32), (102, 0, 30 if blocking else 15), (31, 0, defense), (194, 0, sockets)),
        sockets=sockets,
        complete=True,
        affix_records=(('prefix', 422 if sockets == 4 else 421), ('suffix', 173 if blocking else 172)),
    )


def cases():
    for guide, klass, uses in USES:
        roles = tuple(guide + '-' + slug + '-jmod-base' for slug, _ in uses)
        configs = tuple(role + '-stats' for role in roles)
        item = shield()
        context = {'player_class': klass}
        examples = [
            ('minimum-defense', item, context, 'true'),
            ('maximum-defense', shield(148), context, 'true'),
            ('blocking-suffix', shield(blocking=False), context, 'false'),
            (
                'insufficient-bonus',
                replace(item, raw_stats=((20, 0, 41), *item.raw_stats[1:]), affix_records=None),
                context,
                'false',
            ),
            ('three-sockets', shield(sockets=3), context, 'false'),
            ('ethereal', replace(shield(199), ethereal=True), context, 'false'),
            (
                'different-base',
                replace(item, base='Aegis', raw_stats=((20, 0, 44), (102, 0, 30), (31, 0, 145), (194, 0, 4))),
                context,
                'false',
            ),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unknown-contents', replace(item, socket_contents=None), context, 'unknown'),
            (
                'unknown-sockets',
                replace(item, sockets=None, raw_stats=item.raw_stats[:-1], affix_records=None),
                context,
                'unknown',
            ),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            (
                'one-ist-inserted',
                replace(
                    item,
                    socket_contents='filled',
                    socket_items=(SocketItem('Ist Rune'),),
                    raw_stats=(*item.raw_stats, (80, 0, 25)),
                ),
                context,
                'false',
            ),
        ]
        for stat, label in ((20, 'block'), (102, 'block-rate')):
            examples.append(
                (
                    'unread-' + label,
                    replace(
                        item,
                        raw_stats=tuple(s for s in item.raw_stats if s[0] != stat),
                        complete=False,
                        affix_records=None,
                    ),
                    context,
                    'unknown',
                )
            )
        for label, candidate, ctx, truth in examples:
            role_rows = []
            for role in roles:
                row = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
                if truth == 'true':
                    payload = 'Ist' if 'magic-find-shield' in role else 'Rainbow Facets'
                    row.update(status='partial', missing=Contains(Contains(payload)))
                role_rows.append(IsPartialDict(**row))
            expected = {'roles': Contains(*role_rows)}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('20:0', '102:0')}
                    )
                )
            yield Case(
                id=f'jmod-bases/{guide}/{label}',
                item=candidate,
                context=ctx,
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(
                    'Monarch',
                    'Sockets: 4',
                    '4 empty',
                    'Needs: four Rainbow Facets',
                    *(('Needs: four Ist runes',) if guide == 'fissure-druid' else ()),
                )
                if truth == 'true'
                else (candidate.base,),
                evidence=(
                    *(f'pricing/data/wp-a-builds.json:/{guide}{locator}' for _, locator in uses),
                    'third-parties/d2data/json/armor.json:/uit',
                    'third-parties/d2data/json/armor.json:/uow',
                    'third-parties/d2data/json/gems.json:/r24',
                    'third-parties/d2data/json/magicprefix.json:/422',
                    'third-parties/d2data/json/magicprefix.json:/421',
                    'third-parties/d2data/json/magicsuffix.json:/173',
                    'third-parties/d2data/json/magicsuffix.json:/172',
                ),
            )


CASES = tuple(cases())
