"""Echoing Ubers ring pairing, independent of generic caster ring demand."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'echoing-ubers-sling-magic-pierce'
RING = Item(
    'Ring',
    'unique',
    'Sling',
    ((358, 0, 3), (105, 0, 10), (1, 0, 10), (80, 0, 10), (97, 411, 1), (150, 0, 15)),
    complete=True,
)
CONTEXT = {'player_class': 'Warlock', 'player_items': ["Hellwarden's Will", 'Renewed Black Cleft']}


def cases():
    scenarios = [
        ('low-pierce', RING, CONTEXT, 'true', True),
        (
            'high-pierce',
            replace(RING, raw_stats=tuple((i, p, 5 if i == 358 else v) for i, p, v in RING.raw_stats)),
            CONTEXT,
            'true',
            True,
        ),
        ('wrong-class', RING, {**CONTEXT, 'player_class': 'Paladin'}, 'false', False),
        ('unknown-class', RING, {**CONTEXT, 'player_class': None}, 'unknown', False),
        ('missing-helmet', RING, {**CONTEXT, 'player_items': ['Renewed Black Cleft']}, 'true', False),
        ('missing-sunder', RING, {**CONTEXT, 'player_items': ["Hellwarden's Will"]}, 'true', False),
        ('unknown-companions', RING, {'player_class': 'Warlock'}, 'true', False),
        (
            'mercenary-companions',
            RING,
            {'player_class': 'Warlock', 'player_items': [], 'mercenary_items': CONTEXT['player_items']},
            'true',
            False,
        ),
        ('unidentified', replace(RING, identified=False), CONTEXT, 'false', False),
        ('impossible-ethereal', replace(RING, ethereal=True), CONTEXT, 'false', False),
        ('unknown-ethereal', replace(RING, ethereal=None), CONTEXT, 'unknown', False),
        (
            'impossible-sockets',
            replace(RING, sockets=1, raw_stats=(*RING.raw_stats, (194, 0, 1))),
            CONTEXT,
            'false',
            False,
        ),
    ]
    for label, item, context, truth, usable in scenarios:
        expected = {
            'roles': Contains(IsPartialDict(id=ROLE, side='player', slot='Ring', rule_trace=IsPartialDict(truth=truth)))
        }
        if usable:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for key in ('358:0', '105:0')}
                )
            )
        if usable:
            expected['price_gaps'] = []
        yield Case(
            id='echoing/sling/' + label,
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario='unknown' if label.startswith('unknown') else 'positive' if usable else 'negative',
            absent_configurations=() if usable else (ROLE + '-stats',),
            report_contains=("Setup: Hellwarden's Will in the player setup; Renewed Black Cleft in the player setup",)
            if usable
            else (),
            evidence=(
                'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/24',
                'third-parties/d2data/json/uniqueitems.json:/415',
            ),
        )
    for missing in (358, 105):
        retained = '105:0' if missing == 358 else '358:0'
        yield Case(
            id=f'echoing/sling/unread-{missing}',
            item=replace(RING, complete=False, raw_stats=tuple(s for s in RING.raw_stats if s[0] != missing)),
            context=CONTEXT,
            expected={
                'assessment': IsPartialDict(
                    stat_evaluation=IsPartialDict(
                        annotations=IsPartialDict(
                            {retained: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))}
                        )
                    )
                )
            },
            covers=(ROLE,),
            scenario='unknown',
            absent_stat_configurations={f'{missing}:0': (ROLE + '-stats',)},
            evidence=('pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/24',),
        )


CASES = tuple(cases())
