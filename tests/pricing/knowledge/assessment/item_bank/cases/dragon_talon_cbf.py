"""Explicit Uber alternatives: immunity/resistances are not full-loadout readiness."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def kira(high=False):
    resistance = 70 if high else 50
    return Item(
        'Tiara',
        'unique',
        "Kira's Guardian",
        ((153, 0, 1), (99, 0, 20), *((stat, 0, resistance) for stat in (39, 41, 43, 45))),
        named_table_id=357,
    )


def duriel(high=False):
    return Item(
        'Cuirass',
        'unique',
        "Duriel's Shell",
        (
            (153, 0, 1),
            (0, 0, 15),
            (16, 0, 200 if high else 160),
            (39, 0, 20),
            (41, 0, 20),
            (43, 0, 50),
            (45, 0, 20),
        ),
        named_table_id=216,
    )


def cases():
    context = {'player_class': 'Assassin'}
    for slug, build_item, native, roll_text in (
        ('kira', kira, 357, '(50-70%)'),
        ('duriel', duriel, 216, '(160-200%)'),
    ):
        role = f'dragon-talon-budget-cbf-{slug}'
        config = role + '-stats'
        item = build_item()
        examples = [
            ('minimum-roll', item, context, 'true'),
            ('maximum-roll', build_item(True), context, 'true'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal-player', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        # A damaged/incomplete capture must not acquire a fixed modifier from the
        # item's name. Independently omit each required property, keeping the rest.
        examples += [
            (
                f'uncaptured-{stat}',
                replace(item, raw_stats=tuple(row for row in item.raw_stats if row[0] != stat)),
                context,
                'unknown',
            )
            for stat in (153, 39, 41, 43, 45)
        ]
        for label, candidate, loadout, truth in examples:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config), desirability=grade)
                            for key, grade in (
                                ('153:0', 'desirable'),
                                ('39:0', 'supporting'),
                                ('41:0', 'supporting'),
                                ('43:0', 'supporting'),
                                ('45:0', 'supporting'),
                            )
                        }
                    )
                )
            yield Case(
                id=f'dragon-talon-cbf/{slug}/{label}',
                item=candidate,
                context=loadout,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={
                    'assessment': IsPartialDict(**expected),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(('31:0', '16:0', '7:0', '99:0'), (config,)),
                report_contains=(candidate.name, 'Trade tier:', 'Cannot Be Frozen', roll_text) if active else (),
                evidence=(
                    'pricing/data/wp-a-variants/dragon-talon-assassin.json:/variants/0/quotes/1',
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                ),
            )


CASES = tuple(cases())
