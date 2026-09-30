"""Explicit endgame Duress alternatives: native offensive rolls and mercenary use."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SOURCES = (
    ('dream-paladin', 'Paladin', 3),
    ('fissure-druid', 'Druid', 3),
    ('lightning-sorceress', 'Sorceress', 2),
    ('lightning-strike-amazon', 'Amazon', 4),
    ('poison-nova-necromancer', 'Necromancer', 3),
)


def duress(quality, damage=10, defense=150):
    # Off-weapon ED and armor ED are independent native rolls. Rune effects are
    # part of the captured totals: Shael contributes 20 FHR, Um 15 all resists,
    # and Thul 30 cold resistance. Total armor is intentionally not fabricated.
    return Item(
        'Mage Plate',
        quality,
        'Duress',
        (
            (17, 0, damage),
            (18, 0, damage),
            (16, 0, defense),
            (136, 0, 15),
            (135, 0, 33),
            (99, 0, 40),
            (39, 0, 15),
            (41, 0, 15),
            (43, 0, 45),
            (45, 0, 15),
            (54, 0, 37),
            (55, 0, 133),
            (56, 0, 50),
            (194, 0, 3),
        ),
        runeword='Duress',
        sockets=3,
        socket_contents='filled',
        socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Um Rune', 'Thul Rune')),
    )


def cases():
    for build, klass, index in SOURCES:
        role = build + '-duress-end-merc-resistance-alternative'
        config = role + '-stats'
        context = {'player_class': klass, 'mercenary_type': 'Act 2 Might'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = duress(quality)
            examples = [
                (f'rolls-{damage}-{defense}', duress(quality, damage, defense), context, 'true')
                for damage in (10, 20)
                for defense in (150, 200)
            ]
            examples += [
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('elite-base', replace(item, base='Dusk Shroud'), context, 'true'),
                ('insufficient-capacity', replace(item, base='Quilted Armor'), context, 'false'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('count-recovered-from-stats', replace(item, sockets=None), context, 'true'),
                (
                    'unknown-sockets',
                    replace(
                        item,
                        sockets=None,
                        socket_contents='unknown',
                        socket_items=(),
                        raw_stats=tuple(row for row in item.raw_stats if row[0] != 194),
                    ),
                    context,
                    'unknown',
                ),
                ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ]
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                assessment = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            side='merc',
                            rule_trace=IsPartialDict(truth=truth),
                        )
                    )
                }
                if active:
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    configuration_ids=Contains(config),
                                    contributions=Contains(
                                        IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                                    ),
                                )
                                for key, grade in (
                                    ('136:0', 'desirable'),
                                    ('135:0', 'desirable'),
                                    *(
                                        (key, 'supporting')
                                        for key in ('17:0', '18:0', '99:0', '39:0', '41:0', '43:0', '45:0')
                                    ),
                                )
                            }
                        )
                    )
                yield Case(
                    id=f'duress-endgame-merc/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario='unknown' if label.startswith('unknown-') else 'positive' if active else 'negative',
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(('60:0', '1:0', '3:0'), (config,)),
                    report_contains=(
                        'Duress',
                        'Shael, Um, Thul',
                        '15% Chance of Crushing Blow',
                        '33% Chance of Open Wounds',
                        '40% Faster Hit Recovery',
                        'Cold Resist +45%',
                    )
                    if active
                    else (),
                    report_absent=('Life stolen per hit',),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/end/{index}',
                        'third-parties/d2data/json/runes.json:/Duress',
                        'third-parties/d2data/json/gems.json:/r13',
                        'third-parties/d2data/json/gems.json:/r22',
                        'third-parties/d2data/json/gems.json:/r10',
                    ),
                )


CASES = tuple(cases())
