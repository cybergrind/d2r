"""Fire Warlock grimoire rolls and distinct Standard/MF socket requirements."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


STATS = (
    (188, 58, 2),
    (105, 0, 25),
    (16, 0, 170),
    (329, 0, 15),
    (89, 0, 5),
    (138, 0, 5),
    (39, 0, 20),
    (107, 401, 3),
    (201, 4929, 15),
)


def cases():
    for variant, rune, other, index in (
        ('standard', 'Um Rune', 'Ist Rune', 1),
        ('mf', 'Ist Rune', 'Um Rune', 2),
    ):
        role = f'fire-warlock-{variant}-ars-diabolos'
        item = Item('Blasphemous Grimoire', 'unique', "Ars Al'Diabolos", STATS)
        context = {'player_class': 'Warlock'}
        socketed = replace(item, sockets=1, socket_contents='filled', socket_items=(SocketItem(rune),))
        maximum = replace(
            item, raw_stats=tuple((stat, layer, {329: 25, 107: 5}.get(stat, value)) for stat, layer, value in STATS)
        )
        for label, candidate, loadout, truth, confirmed, applicable, scenario in (
            ('minimum', item, context, 'true', False, True, 'positive'),
            ('maximum', maximum, context, 'true', False, True, 'positive'),
            ('required-rune', socketed, context, 'true', True, True, 'positive'),
            (
                'different-rune',
                replace(socketed, socket_items=(SocketItem(other),)),
                context,
                'true',
                False,
                True,
                'negative',
            ),
            ('empty-socket', replace(item, sockets=1), context, 'true', False, True, 'negative'),
            (
                'unknown-contents',
                replace(socketed, socket_contents='unknown', socket_items=()),
                context,
                'true',
                False,
                True,
                'unknown',
            ),
            ('ethereal', replace(item, ethereal=True), context, 'false', False, False, 'negative'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False, False, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', False, False, 'negative'),
            ('unknown-class', item, {}, 'unknown', False, False, 'unknown'),
            (
                'missing-fire-roll',
                replace(item, raw_stats=tuple(r for r in STATS if r[0] != 329)),
                context,
                'unknown',
                False,
                False,
                'unknown',
            ),
        ):
            expected_role = {
                'id': role,
                'rule_trace': IsPartialDict(truth=truth),
                'socket_requirement': IsPartialDict(item=rune, confirmed=confirmed, applicable=applicable),
            }
            if label in ('minimum', 'maximum'):
                expected_role['preferences'] = [
                    IsPartialDict(status='true' if label == 'maximum' else 'false'),
                    IsPartialDict(status='true' if label == 'maximum' else 'false'),
                ]
            yield Case(
                id=f'fire-ars-diabolos/{variant}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(role,),
                expected={'assessment': IsPartialDict(roles=Contains(IsPartialDict(**expected_role)))},
                report_contains=(
                    'Trade tier:',
                    '25% Faster Cast Rate',
                    *(
                        (
                            'Trade tier: high',
                            'VALUABLE CANDIDATE',
                            f'+{25 if label == "maximum" else 15}% (15-25%) to Fire Skill Damage',
                            f'+{5 if label == "maximum" else 3} (3-5) to Apocalypse',
                        )
                        if label in ('minimum', 'maximum')
                        else ()
                    ),
                ),
                evidence=(
                    'pricing/raw/d2data/uniqueitems.json:/408',
                    f'pricing/data/wp-a-variants/fire-warlock-guide.json:/variants/{index}/player/Off-Hand',
                ),
            )


CASES = tuple(cases())
