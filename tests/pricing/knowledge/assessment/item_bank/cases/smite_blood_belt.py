"""Blood belt utility for Smite: Open Wounds, recovery and life, not life leech."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'smite-starter-crafted-belt'
CONFIG = ROLE + '-stats'
BELT = Item('Mesh Belt', 'crafted', raw_stats=((99, 0, 24), (60, 0, 3), (135, 0, 10), (7, 0, 20 * 256)))


def cases():
    # These are transferable belt modifiers, not class-restricted skill bonuses.
    # A scanning character of another class does not erase demand from Smite.
    examples = [
        ('reviewed-combination', BELT, 'positive'),
        (
            'below-guide-preferences',
            replace(BELT, raw_stats=((99, 0, 10), (60, 0, 1), (135, 0, 5), (7, 0, 10 * 256))),
            'positive',
        ),
        ('other-character', BELT, 'positive'),
        ('unknown-character', BELT, 'positive'),
        ('ethereal', replace(BELT, ethereal=True), 'negative'),
        ('unknown-ethereal', replace(BELT, ethereal=None), 'unknown'),
        ('unidentified', replace(BELT, identified=False), 'negative'),
        ('wrong-quality', replace(BELT, rarity='rare'), 'negative'),
    ]
    for stat in (99, 60, 135, 7):
        examples.extend(
            [
                (
                    f'zero-{stat}',
                    replace(BELT, raw_stats=tuple((s, p, 0 if s == stat else v) for s, p, v in BELT.raw_stats)),
                    'negative',
                ),
                (
                    f'unread-{stat}',
                    replace(BELT, raw_stats=tuple(row for row in BELT.raw_stats if row[0] != stat)),
                    'unknown',
                ),
            ]
        )
    for label, item, scenario in examples:
        expected = {}
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(
                            contributions=Contains(IsPartialDict(configuration_id=CONFIG, desirability='desirable'))
                        )
                        for key in ('99:0', '135:0', '7:0')
                    }
                )
            )
            expected['roles'] = Contains(
                IsPartialDict(
                    id=ROLE,
                    missing=Contains(
                        'The cited Ubers setup requires Life Tap for sustain, Cannot Be Frozen, Crushing Blow '
                        'and enough resistance for Uber Mephisto; belt Life Leech does not establish Life Tap sustain.',
                    ),
                )
            )
        yield Case(
            id=f'smite-blood-belt/{label}',
            item=item,
            context={}
            if label == 'unknown-character'
            else {'player_class': 'Sorceress' if label == 'other-character' else 'Paladin'},
            covers=('role:' + ROLE + ':crafted',),
            scenario=scenario,
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if scenario == 'positive' else (CONFIG,),
            absent_stat_configurations={'60:0': (CONFIG,)},
            report_contains=('Chance of Open Wounds', 'Faster Hit Recovery', 'to Life')
            if scenario == 'positive'
            else (),
            evidence=('pricing/data/wp-a-variants/smite-paladin.json:/variants/0/player/Belt/0',),
        )


CASES = tuple(cases())
