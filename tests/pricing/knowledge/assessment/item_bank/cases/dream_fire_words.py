"""Dream's supplemental Holy Fire words: individual auras are not a full hybrid."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


DRAGON = 'dream-paladin-dragon-body-armor-aura-recipe'
JUSTICE = (
    'dream-paladin-hand-of-justice-main-alternatives-source-recipe',
    'dream-paladin-hand-of-justice-hybrid-source-recipe',
)
DRAGON_STATS = (
    (151, 102, 14),
    (31, 0, 360),
    (32, 0, 230),
    (220, 0, 3),
    (0, 0, 3),
    (1, 0, 3),
    (2, 0, 3),
    (3, 0, 3),
    (77, 0, 5),
    (42, 0, 5),
    (34, 0, 7),
    (198, 62 * 64 + 15, 12),
    (201, 278 * 64 + 18, 20),
    (194, 0, 3),
)
JUSTICE_STATS = (
    (151, 102, 16),
    (93, 0, 33),
    (17, 0, 280),
    (18, 0, 280),
    (333, 0, 20),
    (115, 0, 1),
    (141, 0, 20),
    (60, 0, 7),
    (113, 0, 1),
    (134, 0, 3),
    (199, 46 * 64 + 36, 100),
    (197, 56 * 64 + 48, 100),
    (194, 0, 4),
)


def cases():
    context = {'player_class': 'Paladin'}
    for name, base, roles, stats, runes, locators in (
        ('Dragon', 'Mage Plate', (DRAGON,), DRAGON_STATS, ('Sur', 'Lo', 'Sol'), ('/dream-paladin/slots/Body Armor/5',)),
        (
            'Hand of Justice',
            'Phase Blade',
            JUSTICE,
            JUSTICE_STATS,
            ('Sur', 'Cham', 'Amn', 'Lo'),
            ('/dream-paladin/slots/Weapon/4', '/dream-paladin/variants/1/player/Weapon/0'),
        ),
    ):
        armor = name == 'Dragon'
        configs = tuple(role + '-stats' for role in roles)
        keys = (
            ('151:102', '31:0', '32:0', '220:0', '0:0', '1:0', '2:0', '3:0', '77:0', '42:0', '34:0')
            if armor
            else (
                '151:102',
                '93:0',
                '17:0',
                '18:0',
                '333:0',
                '115:0',
                '141:0',
                '60:0',
            )
        )
        forbidden = ('9:0', '198:3983', '201:17810') if armor else ('199:2980', '197:3632')
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                name,
                stats,
                sockets=len(runes),
                socket_contents='filled',
                runeword=name,
                socket_items=tuple(SocketItem(rune + ' Rune') for rune in runes),
                complete=True,
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple(
                (sid, layer, ({0: 5, 1: 5, 2: 5, 3: 5} if armor else {17: 330, 18: 330}).get(sid, value))
                for sid, layer, value in stats
            )
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('ethereal', replace(native, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
                ('wrong-class', native, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                assessment = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'dream-fire-words/{name}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**assessment),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations=dict.fromkeys(forbidden, configs),
                    report_contains=(
                        name,
                        'Level 14 Holy Fire' if armor else 'Level 16 Holy Fire',
                        *(
                            (
                                f'Sockets: {len(runes)} — ' + ', '.join(runes),
                                '(3-5)' if armor else '(280-345%)' if quality == 'superior' else '(280-330%)',
                            )
                            if truth == 'true' and isinstance(candidate, NativeRunewordItem)
                            else ()
                        ),
                    ),
                    report_absent=('Level 30 Holy Fire', 'Level 30 Holy Shock'),
                    evidence=(
                        *(f'pricing/data/wp-a-builds.json:{loc}' for loc in locators),
                        f'third-parties/d2data/json/runes.json:/{name}',
                    ),
                )
            for label, candidate, omitted in (
                ('wrong-rune-order', replace(native, socket_items=tuple(reversed(native.socket_items))), True),
                ('wrong-recipient-base', replace(native, base='Kite Shield' if armor else 'Crystal Sword'), armor),
            ):
                yield Case(
                    id=f'dream-fire-words/{name}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={
                        'price_estimate': IsPartialDict(estimate_ist=None),
                        **(
                            {}
                            if omitted
                            else {
                                'assessment': IsPartialDict(
                                    roles=Contains(
                                        *(
                                            IsPartialDict(id=role, rule_trace=IsPartialDict(truth='false'))
                                            for role in roles
                                        )
                                    )
                                )
                            }
                        ),
                    },
                    covers=roles,
                    scenario='negative',
                    absent_roles=roles if omitted else (),
                    absent_configurations=configs,
                    evidence=(f'third-parties/d2data/json/runes.json:/{name}',),
                )


CASES = tuple(cases())
