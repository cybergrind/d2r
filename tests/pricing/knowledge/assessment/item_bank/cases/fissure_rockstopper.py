"""Rockstopper defenses help hirelings; its Vitality remains a visible inert stat."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'fissure-starter-merc-rockstopper'
KEYS = ('39:0', '41:0', '43:0', '36:0', '99:0')
ITEM = Item(
    'Sallet', 'unique', 'Rockstopper', ((39, 0, 20), (41, 0, 20), (43, 0, 20), (36, 0, 10), (99, 0, 30), (3, 0, 15))
)
CASES = tuple(
    Case(
        id='fissure-rockstopper/' + label,
        item=item,
        context={'player_class': klass, 'mercenary_type': merc},
        covers=(ROLE,),
        scenario='unknown' if label.startswith('unknown') else 'positive' if active else 'negative',
        expected={
            'assessment': IsPartialDict(
                stat_evaluation=IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for k in KEYS}
                    )
                )
            )
        }
        if active
        else {},
        absent_stat_configurations={'3:0': (ROLE + '-stats',)},
        absent_configurations=() if active else (ROLE + '-stats',),
        report_contains=('+15 to Vitality',),
        evidence=(
            'pricing/raw/mr/guides__fissure-druid.html:Starter / Mercenary',
            'third-parties/d2data/json/itemstatcost.json:/vitality/op',
            'third-parties/D2MOO/source/D2Common/src/D2StatList.cpp:op9 UNIT_PLAYER guard',
        ),
    )
    for label, item, klass, merc, active in (
        ('prayer', ITEM, 'Druid', 'Act 2 Prayer', True),
        ('caster', ITEM, 'Druid', 'Act 3 Fire', True),
        ('ethereal', replace(ITEM, ethereal=True), 'Druid', 'Act 2 Prayer', True),
        ('unknown-bearer', ITEM, 'Druid', None, True),
        ('wrong-class', ITEM, 'Barbarian', 'Act 2 Prayer', False),
        ('unknown-class', ITEM, None, 'Act 2 Prayer', False),
    )
)
