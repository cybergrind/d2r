"""Summoner armor alternative: native/upgraded identity, defense and legal sockets."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = (
    'summoner-necromancer-spirit-shroud-alternative',
    'summoner-necromancer-guide-the-spirit-shroud-caster-armor-remainder',
)
CONFIGS = tuple(role + '-stats' for role in ROLES)
ARMOR = Item(
    'Ghost Armor',
    'unique',
    'The Spirit Shroud',
    ((127, 0, 1), (153, 0, 1), (35, 0, 7), (74, 0, 10), (16, 0, 150)),
    named_table_id=209,
)


def cases():
    for base in ('Ghost Armor', 'Dusk Shroud'):
        item = replace(ARMOR, base=base)
        context = {'player_class': 'Necromancer'}
        for label, candidate, loadout, supported, scenario in (
            ('minimum', item, context, True, 'positive'),
            (
                'maximum',
                replace(item, raw_stats=tuple((s, p, 11 if s == 35 else v) for s, p, v in item.raw_stats)),
                context,
                True,
                'positive',
            ),
            ('one-empty-socket', replace(item, sockets=1, socket_contents='empty'), context, True, 'positive'),
            ('invalid-two-sockets', replace(item, sockets=2, socket_contents='empty'), context, False, 'negative'),
            ('unknown-sockets', replace(item, sockets=None, socket_contents='unknown'), context, False, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, False, 'negative'),
            ('unknown-ethereal', replace(item, ethereal=None), context, False, 'unknown'),
            ('wrong-class', item, {'player_class': 'Druid'}, False, 'negative'),
            ('unknown-class', item, {}, False, 'unknown'),
            ('unidentified', replace(item, identified=False), context, False, 'unknown'),
            (
                'uncaptured-mdr',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 35)),
                context,
                True,
                'unknown',
            ),
        ):
            expected = {}
            if supported:
                keys = ('127:0', '153:0', '74:0') + (() if label == 'uncaptured-mdr' else ('35:0',))
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    *(
                                        IsPartialDict(
                                            configuration_id=config,
                                            desirability='desirable' if key == '127:0' else 'supporting',
                                        )
                                        for config in CONFIGS
                                    )
                                )
                            )
                            for key in keys
                        }
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if label in ('minimum', 'maximum'):
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(memory_stat=IsPartialDict(id=35), roll_range=IsPartialDict(min=7, max=11))
                    )
                )
            yield Case(
                id=f'spirit-shroud/{base}/{label}',
                item=candidate,
                context=loadout,
                covers=ROLES,
                scenario=scenario,
                expected=result,
                absent_configurations=() if supported else CONFIGS,
                absent_stat_configurations={
                    '105:0': CONFIGS,
                    **({'35:0': CONFIGS} if label == 'uncaptured-mdr' else {}),
                },
                report_contains=('The Spirit Shroud', 'Trade tier:', 'Cannot Be Frozen', 'Replenish Life')
                if label == 'minimum'
                else (),
                report_absent=('Leveling: high',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/209',
                    'pricing/data/wp-a-builds.json:/summoner-necromancer-guide/slots/Body Armor/5',
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__summoner-necromancer-guide.html/sections/33',
                ),
            )


CASES = tuple(cases())
