"""Named and generic Teleport swaps require charges; named equipment fits the wearer."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def emit(role, label, item, context, truth, scenario, key):
    expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
    if scenario == 'positive':
        expected['stat_evaluation'] = IsPartialDict(
            annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(role + '-stats'))})
        )
    return Case(
        id=f'abyss/teleport-alternatives/{item.rarity}/{label}',
        item=item,
        context=context,
        expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
        covers=(role,),
        scenario=scenario,
        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
        absent_stat_configurations=dict.fromkeys(('127:0', '105:0', '17:0', '18:0'), (role + '-stats',)),
        report_contains=('Teleport',) if scenario == 'positive' else (),
        evidence=(
            'pricing/data/wp-a-builds.json',
            'third-parties/d2data/json/uniqueitems.json',
            'third-parties/d2data/json/setitems.json',
            'third-parties/d2data/json/magicsuffix.json',
        ),
    )


def cases():
    role = 'abyss-warlock-build-guide-naj-teleport-swap'
    item = Item('Elder Staff', 'set', "Naj's Puzzler", ((204, 3467, (69 << 8) | 1), (105, 0, 30), (127, 0, 1)))
    context = {'player_class': 'Warlock', 'player_level': 78, 'player_strength': 44, 'player_dexterity': 37}
    rows = [
        ('one-charge', item, context, 'true', 'positive'),
        ('full-charges', replace(item, raw_stats=((204, 3467, (69 << 8) | 69),)), context, 'true', 'positive'),
        ('depleted', replace(item, raw_stats=((204, 3467, 69 << 8),)), context, 'true', 'negative'),
        ('unread-charges', replace(item, raw_stats=()), context, 'true', 'unknown'),
        ('unknown-equipment', item, {'player_class': 'Warlock'}, 'true', 'unknown'),
        ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false', 'negative'),
        ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown', 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
    ]
    for attr in ('player_level', 'player_strength', 'player_dexterity'):
        rows.append(('below-' + attr, item, {**context, attr: context[attr] - 1}, 'true', 'negative'))
    for label, candidate, loadout, truth, scenario in rows:
        yield emit(role, label, candidate, loadout, truth, scenario, '204:3467')
    role = 'abyss-warlock-build-guide-charge-alternative-weapon-swap-4'
    for quality in ('magic', 'rare'):
        item = Item('Long Staff', quality, raw_stats=((204, 3462, (33 << 8) | 1),))
        context = {'player_class': 'Warlock'}
        for label, candidate, loadout, truth, scenario in (
            ('one-charge', item, context, 'true', 'positive'),
            ('ethereal-charge', replace(item, ethereal=True), context, 'true', 'positive'),
            ('depleted', replace(item, raw_stats=((204, 3462, 33 << 8),)), context, 'true', 'negative'),
            (
                'ethereal-depleted',
                replace(item, ethereal=True, raw_stats=((204, 3462, 33 << 8),)),
                context,
                'true',
                'negative',
            ),
            ('unread-charges', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', 'negative'),
            ('unknown-class', item, {}, 'unknown', 'unknown'),
        ):
            yield emit(role, label, candidate, loadout, truth, scenario, '204:3462')


CASES = tuple(cases())
