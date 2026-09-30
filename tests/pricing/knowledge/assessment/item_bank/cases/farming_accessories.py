"""Specialist farming combinations with separately authored item/loadout limits."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def meteor_cases():
    role = 'meteor-standard-volcanic-luck-amulet'
    core = ((188, 8, 3), (80, 0, 35))
    context = {'player_class': 'Sorceress', 'player_total_fcr': 63, 'player_total_fhr': 60}
    examples = [
        ('source-rolls', core, True, context, 'positive'),
        ('minimum-luck', ((188, 8, 3), (80, 0, 26)), True, context, 'positive'),
        ('lower-mf-suffix', ((188, 8, 3), (80, 0, 25)), True, context, 'negative'),
        ('two-fire-skills', ((188, 8, 2), (80, 0, 35)), True, context, 'negative'),
        ('cold-skills', ((188, 10, 3), (80, 0, 35)), True, context, 'negative'),
        ('higher-cast-breakpoint', core, True, {**context, 'player_total_fcr': 105}, 'positive'),
        ('wrong-class', core, True, {**context, 'player_class': 'Necromancer'}, 'negative'),
        ('insufficient-cast-rate', core, True, {**context, 'player_total_fcr': 62}, 'negative'),
        ('insufficient-recovery', core, True, {**context, 'player_total_fhr': 59}, 'negative'),
    ]
    for key in context:
        examples.append((f'unread-{key}', core, True, {k: v for k, v in context.items() if k != key}, 'unknown'))
    for stat, label in ((188, 'skills'), (80, 'magic-find')):
        remaining = tuple(row for row in core if row[0] != stat)
        examples.extend(
            (
                (f'missing-{label}', remaining, True, context, 'negative'),
                (f'unread-{label}', remaining, False, context, 'unknown'),
            )
        )
    for label, stats, complete, loadout, scenario in examples:
        yield make_case(
            role,
            label,
            'Amulet',
            'magic',
            stats,
            complete,
            loadout,
            scenario,
            'pricing/data/wp-a-builds.json:/meteor-sorceress/variants/1',
        )


def belt_cases():
    role = 'goldfind-budget-belt'
    core = ((99, 0, 24), (43, 0, 25), (41, 0, 25), (79, 0, 80))
    examples = [
        ('source-rolls', core, True, 'positive'),
        ('lower-rolls', ((99, 0, 10), (43, 0, 10), (41, 0, 10), (79, 0, 40)), True, 'positive'),
        ('mf-not-gold', (*core[:-1], (80, 0, 25)), True, 'negative'),
    ]
    for stat, label in ((99, 'recovery'), (43, 'cold'), (41, 'lightning'), (79, 'gold')):
        remaining = tuple(row for row in core if row[0] != stat)
        examples.extend(
            (
                (f'missing-{label}', remaining, True, 'negative'),
                (f'unread-{label}', remaining, False, 'unknown'),
            )
        )
    for label, stats, complete, scenario in examples:
        yield make_case(
            role,
            label,
            'Plated Belt',
            'rare',
            stats,
            complete,
            {},
            scenario,
            'pricing/data/wp-a-variants/gold-find-barbarian.json:/variants/0/player/Belt/0',
        )


def make_case(role, label, base, quality, stats, complete, context, scenario, source):
    truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
    return Case(
        id=f'farming-accessory/{role}/{label}',
        item=Item(base, quality, raw_stats=stats, complete=complete),
        context=context,
        scenario=scenario,
        covers=(role,),
        expected={
            'assessment': IsPartialDict(roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth))))
        },
        report_contains=(base,),
        evidence=(source,),
    )


CASES = (*meteor_cases(), *belt_cases())
