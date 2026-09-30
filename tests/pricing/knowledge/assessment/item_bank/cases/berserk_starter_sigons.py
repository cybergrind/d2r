"""Starter Sigon trio requires the other two pieces on the player, not the mercenary."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEMS = (
    Item('Gauntlets', 'set', "Sigon's Gage", ((0, 0, 10), (19, 0, 20))),
    Item('Plated Belt', 'set', "Sigon's Wrap", ((39, 0, 20), (7, 0, 20 * 256))),
    Item('Greaves', 'set', "Sigon's Sabot", ((96, 0, 20), (43, 0, 40))),
)


def cases():
    for item in ITEMS:
        role = 'berserk-barbarian-starter-set-' + item.name
        companions = [other.name for other in ITEMS if other != item]
        base_context = {'player_class': 'Barbarian'}
        for label, context, truth, dependency_truths, scenario in (
            ('trio', {**base_context, 'player_items': companions}, 'true', ('true', 'true'), 'positive'),
            ('alone', {**base_context, 'player_items': []}, 'true', ('false', 'false'), 'negative'),
            ('one-companion', {**base_context, 'player_items': companions[:1]}, 'true', ('true', 'false'), 'negative'),
            (
                'duplicates-not-trio',
                {**base_context, 'player_items': [companions[0], companions[0]]},
                'true',
                ('true', 'false'),
                'negative',
            ),
            (
                'mercenary-companions',
                {**base_context, 'player_items': [], 'mercenary_items': companions},
                'true',
                ('false', 'false'),
                'negative',
            ),
            ('unknown-companions', base_context, 'true', ('unknown', 'unknown'), 'unknown'),
            (
                'wrong-class',
                {'player_class': 'Sorceress', 'player_items': companions},
                'false',
                ('true', 'true'),
                'negative',
            ),
        ):
            expected_role = {
                'id': role,
                'rule_trace': IsPartialDict(truth=truth),
            }
            if truth == 'true':
                expected_role['dependencies'] = Contains(
                    *[
                        IsPartialDict(label=f'Wear {name} on the player.', status=state)
                        for name, state in zip(companions, dependency_truths, strict=True)
                    ]
                )
            yield Case(
                id=f'berserk/starter-sigons/{item.name}/{label}',
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(roles=Contains(IsPartialDict(**expected_role)))},
                covers=(role,),
                scenario=scenario,
                report_contains=('Trade tier:',),
                evidence=(
                    'pricing/data/wp-a-variants/berserk-barbarian.json:/variants/0',
                    'third-parties/d2data/json/setitems.json',
                ),
            )


CASES = tuple(cases())
