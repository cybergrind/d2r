"""Native Wealth farming armor, with separate player and mercenary utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


USES = (
    ('double-throw-barbarian-guide', 'Barbarian', 'player', '/slots/Body Armor/6'),
    ('fissure-druid', 'Druid', 'player', '/slots/Body Armor/2'),
    ('gold-find-barbarian', 'Barbarian', 'player', '/slots/Body Armor/1'),
    ('fist-of-the-heavens-paladin', 'Paladin', 'merc', '/merc/Body Armor/mid/5'),
    ('lightning-fury-amazon-guide', 'Amazon', 'merc', '/merc/Body Armor/mid/6'),
    ('summoner-necromancer-guide', 'Necromancer', 'merc', '/merc/Body Armor/mid/6'),
    ('blood-boil-warlock-guide', 'Warlock', 'merc', None),
    ('summoner-warlock-guide', 'Warlock', 'merc', None),
)
# Wealth adds250 GF/100 MF; armor rune effects add50 GF,10 dex and2 MAEK.
RAW = ((79, 0, 300), (80, 0, 100), (2, 0, 10), (138, 0, 2), (194, 0, 3))


def cases():
    for build, klass, side, locator in USES:
        merc = side == 'merc'
        role = (
            build + '-wealth-merc-survival-gear'
            if locator is None
            else build
            + f'-{side}-wealth-body-armor-'
            + ('mid' if merc else 'main-alternatives')
            + '-word-utility-alternative'
        )
        source = (
            f'pricing/data/wp-a-builds.json:/{build}{locator}'
            if locator
            else 'pricing/data/appraisal-guide-sections.json:/sources/'
            + f'pricing~1raw~1mr~1guides__{build}.html/sections/40'
        )
        context = {'player_class': klass, **({'mercenary_type': 'Act 2 Might'} if merc else {})}
        config = role + '-stats'
        for quality in ('normal', 'superior', 'low_quality'):
            original = NativeRunewordItem(
                'Dusk Shroud',
                quality,
                'Wealth',
                RAW,
                sockets=3,
                socket_contents='filled',
                runeword='Wealth',
                socket_items=tuple(SocketItem(name) for name in ('Lem Rune', 'Ko Rune', 'Tir Rune')),
            )
            variants = [
                ('native', original, context, 'true'),
                ('mage-plate', replace(original, base='Mage Plate'), context, 'true'),
                ('ethereal', replace(original, ethereal=True), context, 'true' if merc else 'false'),
                ('wrong-class', original, {**context, 'player_class': 'Assassin'}, 'false'),
                ('unknown-class', original, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
                ('unread-mf', replace(original, raw_stats=tuple(r for r in RAW if r[0] != 80)), context, 'true'),
            ]
            if locator is None:
                variants += [
                    ('wrong-merc', original, {**context, 'mercenary_type': 'Act 1 Fire'}, 'false'),
                    ('unknown-merc', original, {'player_class': klass}, 'unknown'),
                ]
            for label, item, ctx, truth in variants:
                active = truth == 'true'
                keys = ('79:0', '2:0') + (() if label == 'unread-mf' else ('80:0',)) + (() if merc else ('138:0',))
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                excluded = (() if label != 'unread-mf' else ('80:0',)) + (('138:0',) if merc else ())
                yield Case(
                    id=f'wealth-farming/{build}/{quality}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                    report_contains=('Wealth', 'Sockets: 3 — Lem, Ko, Tir'),
                    detail_contains=(
                        'Mercenary Magic Find and Gold Find count on its credited killing blows, not every player kill.'
                        if merc
                        else 'Mana after each kill is kill credit, not leech.',
                    )
                    if label == 'native'
                    else (),
                    evidence=(
                        source,
                        'third-parties/d2data/json/runes.json:/Wealth',
                        'third-parties/d2data/json/gems.json:/r20',
                        'third-parties/d2data/json/gems.json:/r18',
                        'third-parties/d2data/json/gems.json:/r03',
                    ),
                )


CASES = tuple(cases())
