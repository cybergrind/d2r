"""Lidless Wall casting/swap alternatives, upgrade rolls and optional socket payloads."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = {
    'Warlock': (
        ('echoing-strike-warlock-guide', 'Off-Hand', 1),
        ('echoing-strike-warlock-guide', 'Off-Hand-Swap', 1),
        ('fire-warlock-guide', 'Off-Hand', 2),
        ('fire-warlock-guide', 'Off-Hand-Swap', 1),
        ('mirrored-blades-warlock-guide', 'Off-Hand-Swap', 1),
    ),
    'Sorceress': (
        ('enchant-sorceress', 'Off-Hand-Swap', 1),
        ('lightning-sorceress', 'Off-Hand Swap', 2),
        ('nova-sorceress-guide', 'Off-Hand', 0),
    ),
    'Druid': (('fissure-druid', 'Off-Hand-Swap', 1),),
    'Paladin': (('fist-of-the-heavens-paladin', 'Off-Hand-Swap', 3),),
    'Amazon': (('lightning-fury-amazon-guide', 'Off-Hand Swap', 2),),
    'Assassin': (('lightning-sentry-assassin', 'Off-Hand', 8), ('wake-of-fire-assassin', 'Off-Hand', 5)),
    'Necromancer': (('poison-nova-necromancer', 'Off-Hand-Swap', 1),),
}
BASES = (('Grim Shield', 151), ('Troll Nest', 173))


def shield(base, defense, ed=80, mana_kill=3):
    return Item(
        base,
        'unique',
        'Lidless Wall',
        (
            (127, 0, 1),
            (105, 0, 20),
            (138, 0, mana_kill),
            (1, 0, 10),
            (77, 0, 10),
            (16, 0, ed),
            (31, 0, defense * (100 + ed) // 100),
            (89, 0, 1),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(
            g + '-lidless-wall-' + slot.lower().replace(' ', '-') + '-shield-utility-alternative' for g, slot, _ in uses
        )
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        examples = [
            (base + '/' + label, shield(base, defense, ed, mana), context, 'true')
            for base, defense in BASES
            for label, ed, mana in (
                ('minimum', 80, 3),
                ('perfect', 130, 5),
                ('defense-perfect', 130, 3),
                ('mana-perfect', 80, 5),
            )
        ]
        item = shield('Grim Shield', 151)
        opened = replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1)))
        diamond = replace(
            opened,
            socket_contents='filled',
            socket_items=(SocketItem('Perfect Diamond'),),
            raw_stats=(*opened.raw_stats, *((stat, 0, 19) for stat in (39, 41, 43, 45))),
        )
        examples.extend(
            (
                ('open-socket', opened, context, 'true'),
                ('diamond', diamond, context, 'true'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Other'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('impossible-sockets', replace(item, sockets=2), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            )
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*configs))
                            for key in ('127:0', '105:0', '77:0', '1:0', '138:0')
                        }
                    )
                )
                if label == 'diamond':
                    expected['facts'] = IsPartialDict(
                        stats=IsPartialDict({f'{stat}:0': IsPartialDict(value=19) for stat in (39, 41, 43, 45)})
                    )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=80 if stat == 16 else 3, max=130 if stat == 16 else 5),
                                roll_quality='perfect' if value == (130 if stat == 16 else 5) else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in (16, 138)
                        )
                    )
                )
            report = ('Lidless Wall', 'Trade tier:') if truth == 'true' else (candidate.base,)
            if label == 'open-socket':
                report += ('Sockets: 1',)
            if label == 'diamond':
                report += ('Sockets: 1 — Perfect Diamond',)
            yield Case(
                id=f'lidless-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=dict.fromkeys(('16:0', '31:0', '89:0'), configs),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=report,
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/230',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/{slot}/{i}' for g, slot, i in uses),
                ),
            )


CASES = tuple(cases())
