"""Guide-table Cure alternatives retain legal bases and actual mercenary branches."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SOURCES = (
    ('Warlock', (('blood-boil-warlock-guide', 40), ('summoner-warlock-guide', 40))),
    (
        'Sorceress',
        (
            ('fire-wall-sorceress-guide', 41),
            ('frozen-orb-meteor-sorceress', 40),
            ('frozen-orb-sorceress', 40),
            ('hydra-sorceress', 40),
        ),
    ),
    ('Paladin', (('zeal-paladin', 44),)),
)


def cure(quality):
    # Native modifiers only: neither total armor nor a numeric price is fabricated.
    return Item(
        'Mask',
        quality,
        'Cure',
        ((151, 109, 1), (45, 0, 40), (110, 0, 50), (76, 0, 5), (99, 0, 20), (16, 0, 75), (3, 0, 10), (194, 0, 3)),
        ethereal=True,
        sockets=3,
        socket_contents='filled',
        runeword='Cure',
        socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Io Rune', 'Tal Rune')),
    )


def cases():
    for klass, sources in SOURCES:
        roles = tuple(build + '-cure-merc-survival-gear' for build, _ in sources)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass, 'mercenary_type': 'Act 2 Might', 'mercenary_items': []}
        for quality in ('normal', 'superior', 'low_quality'):
            item = cure(quality)
            examples = (
                ('minimum-without-insight', item, context, 'true'),
                (
                    'maximum-rolls',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 60 if stat == 45 else 100 if stat == 16 else value)
                            for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                ),
                ('nonethereal', replace(item, ethereal=False), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('diadem', replace(item, base='Diadem'), context, 'true'),
                ('insufficient-base-capacity', replace(item, base='Cap'), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Druid'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('uncited-prayer', item, {**context, 'mercenary_type': 'Act 2 Prayer'}, 'false'),
                (
                    'frenzy-branch',
                    item,
                    {**context, 'mercenary_type': 'Act 5 Frenzy'},
                    'true' if klass == 'Paladin' else 'false',
                ),
                ('unknown-mercenary', item, {'player_class': klass}, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*configs))
                                for key in ('151:109', '45:0', '110:0', '76:0', '99:0')
                            }
                        )
                    )
                yield Case(
                    id=f'cure-gear-alternatives/{klass}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario='unknown' if label.startswith('unknown-') else 'positive' if active else 'negative',
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else configs,
                    # Item Vitality does not improve mercenary life; Cure has no life leech or regen stat.
                    absent_stat_configurations=dict.fromkeys(('3:0', '74:0', '60:0'), configs),
                    report_contains=('Cure', 'Level 1 Cleansing Aura', 'Shael, Io, Tal') if active else (),
                    report_absent=('Replenish Life', 'Life stolen per hit'),
                    evidence=(
                        *(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{build}.html/sections/{section}'
                            for build, section in sources
                        ),
                        'third-parties/d2data/json/runes.json:/Cure',
                        'third-parties/d2data/json/gems.json:/r13',
                        'third-parties/d2data/json/gems.json:/r16',
                        'third-parties/d2data/json/gems.json:/r07',
                    ),
                )


CASES = tuple(cases())
