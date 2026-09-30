"""Manual Uber curses distinguish item utility, charges and alternative equipment."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('smite', 'Paladin', 82, 'smite-paladin-starter-charges-82', {}),
    ('dragon-talon', 'Assassin', 82, 'dragon-talon-assassin-budget-charges-82', {}),
    ('dream', 'Paladin', 82, 'dream-paladin-ubers-charges-82', {'player_items': []}),
    ('lightning', 'Sorceress', 91, 'lightning-sorceress-ubers-charges-91', {'mercenary_items': ['Infinity']}),
    ('lightning-strike', 'Amazon', 91, 'lightning-strike-amazon-ubers-charges-91', {}),
)


def cases():
    for slug, player_class, skill, role, extra in SPECS:
        context = {'player_class': player_class, **extra}
        layer = skill * 64 + 3
        other_layer = (91 if skill == 82 else 82) * 64 + 3
        for quality in ('magic', 'rare'):
            item = Item('Bone Wand', quality, raw_stats=((204, layer, (82 << 8) | 1),), complete=True)
            rows = [
                ('one-charge', item, context, 'true', 'true'),
                ('ethereal-one-charge', replace(item, ethereal=True), context, 'true', 'true'),
                ('empty-repairable', replace(item, raw_stats=((204, layer, 82 << 8),)), context, 'true', 'false'),
                (
                    'empty-ethereal',
                    replace(item, ethereal=True, raw_stats=((204, layer, 82 << 8),)),
                    context,
                    'true',
                    'false',
                ),
                (
                    'wrong-curse',
                    replace(item, raw_stats=((204, other_layer, (82 << 8) | 1),)),
                    context,
                    'false',
                    'false',
                ),
                ('unread-curse', replace(item, raw_stats=(), complete=False), context, 'unknown', 'unknown'),
                ('missing-curse', replace(item, raw_stats=()), context, 'false', 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Barbarian'}, 'false', 'true'),
            ]
            for label, candidate, loadout, truth, charge_truth in rows:
                yield Case(
                    id=f'uber-charged-wands/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(
                                IsPartialDict(
                                    id=role,
                                    rule_trace=IsPartialDict(truth=truth),
                                    dependencies=Contains(
                                        IsPartialDict(status=charge_truth, trace=IsPartialDict(expected=1))
                                    ),
                                )
                            )
                        )
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    report_contains=('Bone Wand',),
                    evidence=(
                        'pricing/data/wp-a-builds.json',
                        f'third-parties/d2data/json/skills.json:/{skill}',
                        'third-parties/d2data/json/magicsuffix.json:/578'
                        if skill == 82
                        else 'third-parties/d2data/json/magicsuffix.json:/594',
                    ),
                )


def setup_cases():
    for slug, player_class, skill, role, _ in SPECS:
        if slug not in ('dream', 'lightning'):
            continue
        if slug == 'dream':
            label = "Use the wand when neither Last Wish nor Dracul's Grasp supplies Life Tap."
            setups = (
                ('no-alternative', {'player_items': []}, 'true'),
                ('last-wish', {'player_items': ['Last Wish']}, 'false'),
                ('draculs', {'player_items': ["Dracul's Grasp"]}, 'false'),
                ('unread-equipment', {}, 'unknown'),
            )
        else:
            label = 'This curse setup uses an Infinity mercenary.'
            setups = (
                ('infinity', {'mercenary_items': ['Infinity']}, 'true'),
                ('other-weapon', {'mercenary_items': ['Insight']}, 'false'),
                ('unread-equipment', {}, 'unknown'),
            )
        for quality in ('magic', 'rare'):
            for name, context, truth in setups:
                yield Case(
                    id=f'uber-charged-wands/{slug}/{quality}/setup-{name}',
                    item=Item('Bone Wand', quality, raw_stats=((204, skill * 64 + 3, (82 << 8) | 1),), complete=True),
                    context={'player_class': player_class, **context},
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(
                                IsPartialDict(
                                    id=role,
                                    rule_trace=IsPartialDict(truth='true'),
                                    dependencies=Contains(IsPartialDict(label=label, status=truth)),
                                )
                            )
                        )
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    report_contains=('Bone Wand',),
                    evidence=('pricing/data/wp-a-builds.json',),
                )


CASES = (*cases(), *setup_cases())
