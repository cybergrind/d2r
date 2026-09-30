"""The cited shared Smite armor requires Paladin context and repairability."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'smite-shared-treachery'
ARMOR = Item(
    'Mage Plate',
    'normal',
    'Treachery',
    ((201, 17103, 5), (93, 0, 45), (99, 0, 20), (43, 0, 30), (194, 0, 3)),
    sockets=3,
    socket_contents='filled',
    runeword='Treachery',
    socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Thul Rune', 'Lem Rune')),
)


def cases():
    context = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}
    rows = (
        ('shared-armor', ARMOR, context, 'true', True),
        ('wrong-class', ARMOR, {**context, 'player_class': 'Warlock'}, 'false', False),
        ('unknown-class', ARMOR, {**context, 'player_class': None}, 'unknown', False),
        ('ethereal', replace(ARMOR, ethereal=True), context, 'false', False),
        ('unknown-ethereal', replace(ARMOR, ethereal=None), context, 'unknown', False),
        ('wrong-mercenary', ARMOR, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'true', False),
        ('unknown-mercenary', ARMOR, {**context, 'mercenary_type': None}, 'true', False),
    )
    for quality in ('normal', 'superior'):
        for label, item, loadout, truth, active in rows:
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                            for key in ('201:17103', '93:0', '99:0', '43:0')
                        }
                    )
                )
            yield Case(
                id=f'smite/shared-treachery/{quality}/{label}',
                item=replace(item, rarity=quality),
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario='unknown' if 'unknown' in label else 'positive' if active else 'negative',
                absent_configurations=() if active else (ROLE + '-stats',),
                evidence=(
                    'pricing/data/wp-a-variants/smite-paladin.json:/variants/1',
                    'third-parties/d2data/json/runes.json:/Treachery',
                ),
            )


CASES = tuple(cases())
