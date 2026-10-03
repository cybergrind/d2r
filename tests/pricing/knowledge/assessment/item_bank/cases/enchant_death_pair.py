"""Enchant's Death pair: actual player companions and captured piece-owned bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    for name, base, table_id, other, raw, key in (
        ("Death's Hand", 'Leather Gloves', 47, "Death's Guard", ((45, 0, 50), (110, 0, 75), (93, 0, 30)), '93:0'),
        ("Death's Guard", 'Sash', 48, "Death's Hand", ((31, 0, 22), (153, 0, 1)), '153:0'),
    ):
        role = 'enchant-sorceress-starter-set-' + name
        config = role + '-stats'
        item = Item(base, 'set', name, raw, named_table_id=table_id)
        paired = {'player_class': 'Sorceress', 'player_items': [other]}
        for label, candidate, context, dependency, active, scenario in (
            ('paired', item, paired, 'true', True, 'positive'),
            ('no-companion', item, {**paired, 'player_items': []}, 'false', False, 'negative'),
            ('duplicate-self', item, {**paired, 'player_items': [name, name]}, 'false', False, 'negative'),
            ('unknown-companion', item, {'player_class': 'Sorceress'}, 'unknown', False, 'unknown'),
            ('merc-companion', item, {**paired, 'player_items': [], 'merc_items': [other]}, 'false', False, 'negative'),
            ('wrong-class', item, {**paired, 'player_class': 'Paladin'}, 'true', False, 'negative'),
            ('unknown-class', item, {'player_items': [other]}, 'true', False, 'unknown'),
            ('unidentified', replace(item, identified=False), paired, None, False, 'unknown'),
            (
                'uncaptured-modifier',
                replace(item, raw_stats=tuple(row for row in raw if f'{row[0]}:{row[1]}' != key)),
                paired,
                'true',
                False,
                'unknown',
            ),
        ):
            outcome = {'id': role, 'build': 'enchant-sorceress', 'variant': 'Budget'}
            if dependency is not None:
                outcome['dependencies'] = Contains(IsPartialDict(status=dependency))
            expected = {'roles': Contains(IsPartialDict(**outcome))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config))})
                )
            yield Case(
                id=f'enchant-death-pair/{name}/{label}',
                item=candidate,
                context=context,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                # The companion piece's bonus is never credited to the hovered piece.
                absent_stat_configurations={'153:0' if key == '93:0' else '93:0': (config,)},
                report_contains=(
                    name,
                    'Trade tier:',
                    'Leveling: high',
                    *((('30% Increased Attack Speed',) if key == '93:0' else ('Cannot Be Frozen',)) if active else ()),
                )
                if candidate.identified
                else (),
                # Set ownership is not a substitute for capturing its stat values.
                report_absent=('30% Increased Attack Speed',)
                if key == '93:0' and label == 'uncaptured-modifier'
                else ('Fire Resist +15%', 'Cold Resist +15%', 'Lightning Resist +15%')
                if key == '153:0'
                else (),
                evidence=(
                    'pricing/data/wp-a-variants/enchant-sorceress.json:/variants/0',
                    'third-parties/d2data/json/setitems.json:/' + name,
                ),
            )


CASES = tuple(cases())
