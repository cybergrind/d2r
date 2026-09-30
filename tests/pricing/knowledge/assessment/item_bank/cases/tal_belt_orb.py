"""Tal MF and element-specific mastery alternatives, including upgraded bases."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BELTS = (('blizzard-sorceress', 4), ('meteor-sorceress', 3), ('nova-sorceress-guide', 2))
ORBS = (('blizzard-sorceress', 7, 65), ('lightning-sorceress', 7, 63), ('meteor-sorceress', 6, 61))


def cases():
    for kind, bases in (('belt', ('Mesh Belt', 'Mithril Coil')), ('orb', ('Swirling Crystal', 'Dimensional Shard'))):
        uses = BELTS if kind == 'belt' else ORBS
        suffix = (
            '-tal-rasha-s-fine-spun-cloth-tal-player-alternative'
            if kind == 'belt'
            else '-tal-rasha-s-lidless-eye-tal-player-alternative'
        )
        roles = tuple(row[0] + suffix for row in uses)
        configs = tuple(r + '-stats' for r in roles)
        for base in bases:
            item = Item(
                base,
                'set',
                "Tal Rasha's Fine-Spun Cloth" if kind == 'belt' else "Tal Rasha's Lidless Eye",
                ((80, 0, 10), (9, 0, 30 << 8), (2, 0, 20), (114, 0, 37), (91, 0, -20))
                if kind == 'belt'
                else (
                    (105, 0, 20),
                    (7, 0, 57 << 8),
                    (9, 0, 77 << 8),
                    (1, 0, 10),
                    (107, 61, 1),
                    (107, 63, 1),
                    (107, 65, 1),
                ),
                complete=True,
            )
            context = {'player_class': 'Sorceress', 'player_items': []}
            examples = [
                ('minimum', item, context, 'true'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal-impossible', replace(item, ethereal=True), context, 'false'),
                ('ethereal-unknown', replace(item, ethereal=None), context, 'unknown'),
            ]
            if kind == 'belt':
                examples.extend(
                    (
                        ('perfect-mf', replace(item, raw_stats=((80, 0, 15), *item.raw_stats[1:])), context, 'true'),
                        ('socket-impossible', replace(item, sockets=1), context, 'false'),
                        ('socket-unknown', replace(item, sockets=None), context, 'unknown'),
                    )
                )
            else:
                for mastery in (61, 63, 65):
                    examples.append(
                        (
                            f'perfect-mastery-{mastery}',
                            replace(
                                item,
                                raw_stats=tuple(
                                    (s, layer, 2 if s == 107 and layer == mastery else value)
                                    for s, layer, value in item.raw_stats
                                ),
                            ),
                            context,
                            'true',
                        )
                    )
                examples.extend(
                    (
                        (
                            'open-socket',
                            replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))),
                            context,
                            'true',
                        ),
                        (
                            'unknown-payload',
                            replace(
                                item, sockets=1, socket_contents='unknown', raw_stats=(*item.raw_stats, (194, 0, 1))
                            ),
                            context,
                            'true',
                        ),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if truth == 'true':
                    common = ('80:0', '9:0', '2:0', '114:0') if kind == 'belt' else ('105:0', '7:0', '9:0', '1:0')
                    annotations = {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in common}
                    if kind == 'orb':
                        annotations.update(
                            {
                                f'107:{mastery}': IsPartialDict(configuration_ids=Contains(g + suffix + '-stats'))
                                for g, _, mastery in ORBS
                            }
                        )
                    expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
                result = {'assessment': IsPartialDict(**expected)}
                if truth == 'true' and label != 'unknown-payload':
                    result['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=stat, layer=layer),
                                    roll_range=IsPartialDict(min=10 if stat == 80 else 1, max=15 if stat == 80 else 2),
                                    roll_quality='perfect' if value == (15 if stat == 80 else 2) else 'low',
                                )
                                for stat, layer, value in candidate.raw_stats
                                if stat == (80 if kind == 'belt' else 107)
                            )
                        )
                    )
                absent = (
                    dict.fromkeys(('105:0', '31:0', '91:0'), configs)
                    if kind == 'belt'
                    else {
                        f'107:{mastery}': tuple(g + suffix + '-stats' for g, _, other in ORBS if other != mastery)
                        for mastery in (61, 63, 65)
                    }
                )
                yield Case(
                    id=f'tal-belt-orb/{kind}/{base}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    covers=roles,
                    expected=result,
                    absent_stat_configurations=absent,
                    absent_configurations=() if truth == 'true' else configs,
                    report_contains=(item.name, 'Trade tier:') if truth == 'true' else (base,),
                    report_absent=('10% Faster Cast Rate', '+1 to Sorceress Skill Levels'),
                    evidence=(
                        "third-parties/d2data/json/setitems.json:/Tal Rasha's "
                        + ('Fire-Spun Cloth' if kind == 'belt' else 'Lidless Eye'),
                        *(
                            f'pricing/data/wp-a-builds.json:/{row[0]}/slots/'
                            f'{"Belts" if kind == "belt" else "Weapon"}/{row[1]}'
                            for row in uses
                        ),
                    ),
                )


CASES = tuple(cases())
