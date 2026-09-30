"""Loot utility across Ali Baba upgrades; weapon damage is not loot priority."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = {
    'Warlock': (
        ('abyss-warlock-build-guide', 'Weapon-Swap', 1),
        ('echoing-strike-warlock-guide', 'Weapon-Swap', 1),
        ('fire-warlock-guide', 'Weapon-Swap', 1),
        ('mirrored-blades-warlock-guide', 'Weapon-Swap', 1),
    ),
    'Paladin': (('blessed-hammer-paladin', 'Weapon-Swap', 1), ('fist-of-the-heavens-paladin', 'Weapon-Swap', 1)),
    'Sorceress': (
        ('blizzard-sorceress', 'Weapon-Swap', 3),
        ('lightning-sorceress', 'Weapon-Swap', 2),
        ('meteor-sorceress', 'Weapon-Swap', 3),
    ),
    'Barbarian': tuple(
        ('gold-find-barbarian', slot, index)
        for slot, index in (('Weapon', 4), ('Off-Hand', 1), ('Weapon-Swap', 2), ('Off-Hand-Swap', 2))
    ),
}


def cases():
    for player_class, uses in USES.items():
        roles = tuple(f'{g}-blade-of-ali-baba-{slot.lower()}-find-weapon-alternative' for g, slot, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        for base in ('Tulwar', 'Hydra Edge'):
            item = Item(
                base,
                'unique',
                'Blade of Ali Baba',
                ((240, 0, 8), (239, 0, 20), (17, 0, 60), (18, 0, 60), (2, 0, 5), (9, 0, 15 << 8)),
                sockets=2,
            )
            context = {'player_class': player_class}
            examples = (
                ('open', item, context, 'true'),
                ('level-35', replace(item, viewer_level=35), context, 'true'),
                ('level-99', replace(item, viewer_level=99), context, 'true'),
                (
                    'perfect-combat-rolls',
                    replace(
                        item,
                        raw_stats=((240, 0, 8), (239, 0, 20), (17, 0, 120), (18, 0, 120), (2, 0, 15), (9, 0, 15 << 8)),
                    ),
                    context,
                    'true',
                ),
                (
                    'one-ist',
                    replace(
                        item,
                        socket_contents='filled',
                        socket_items=(SocketItem('Ist Rune'),),
                        raw_stats=(*item.raw_stats, (80, 0, 30)),
                    ),
                    context,
                    'true',
                ),
                ('unknown-payload', replace(item, socket_contents='unknown'), context, 'true'),
                ('ethereal-passive', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('wrong-one-socket', replace(item, sockets=1), context, 'false'),
                ('illegal-three-sockets', replace(item, sockets=3), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in examples:
                if candidate.sockets is not None:
                    candidate = replace(candidate, raw_stats=(*candidate.raw_stats, (194, 0, candidate.sockets)))
                expected = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if truth == 'true':
                    keys = ('240:0', '239:0') if player_class == 'Barbarian' else ('240:0',)
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                        )
                    )
                    expected['facts'] = IsPartialDict(
                        stats=IsPartialDict(
                            {
                                '240:0': IsPartialDict(value=candidate.viewer_level),
                                '239:0': IsPartialDict(value=candidate.viewer_level * 20 // 8),
                            }
                        )
                    )
                irrelevant = ('17:0', '18:0', '2:0', '9:0')
                if player_class != 'Barbarian':
                    irrelevant += ('239:0',)
                yield Case(
                    id=f'ali-baba-loot/{player_class}/{base}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    covers=roles,
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations=dict.fromkeys(irrelevant, configs),
                    report_contains=(
                        'Blade of Ali Baba',
                        'Trade tier:',
                        'Sockets: 2 — Ist (1 contents captured)'
                        if label == 'one-ist'
                        else 'Sockets: 2 — contents not captured'
                        if label == 'unknown-payload'
                        else 'Sockets: 2 — 2 empty',
                    )
                    if truth == 'true'
                    else (base,),
                    evidence=(
                        'third-parties/d2data/json/uniqueitems.json:/157',
                        *(f'pricing/data/wp-a-builds.json:/{g}/slots/{slot}/{i}' for g, slot, i in uses),
                    ),
                )


CASES = tuple(cases())
