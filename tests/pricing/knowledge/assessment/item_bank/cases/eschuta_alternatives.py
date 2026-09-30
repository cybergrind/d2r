"""Eschuta's independent fire/lightning rolls retain build-specific priorities."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


FIRE_ROLES = (
    'enchant-sorceress-eschuta-s-temper-caster-survival-alternative',
    'meteor-sorceress-eschuta-s-temper-caster-survival-alternative',
    'fire-wall-sorceress-guide-eschuta-s-temper-caster-weapon-gear',
    'hydra-sorceress-eschuta-s-temper-caster-weapon-gear',
)
LIGHTNING_ROLE = 'lightning-sorceress-eschuta-s-temper-caster-survival-alternative'
ROLES = (*FIRE_ROLES, LIGHTNING_ROLE)


def cases():
    item = Item(
        'Eldritch Orb',
        'unique',
        "Eschuta's Temper",
        raw_stats=(
            (83, 1, 1),
            (105, 0, 40),
            (329, 0, 10),
            (330, 0, 10),
            (1, 0, 20),
        ),
    )
    context = {'player_class': 'Sorceress'}
    examples = (
        ('minimum-rolls', item, context, 'true'),
        (
            'maximum-rolls',
            replace(item, raw_stats=((83, 1, 3), (105, 0, 40), (329, 0, 20), (330, 0, 20), (1, 0, 30))),
            context,
            'true',
        ),
        (
            'fire-perfect-only',
            replace(item, raw_stats=((83, 1, 3), (105, 0, 40), (329, 0, 20), (330, 0, 10), (1, 0, 20))),
            context,
            'true',
        ),
        (
            'lightning-perfect-only',
            replace(item, raw_stats=((83, 1, 3), (105, 0, 40), (329, 0, 10), (330, 0, 20), (1, 0, 20))),
            context,
            'true',
        ),
        ('open-socket', replace(item, sockets=1), context, 'true'),
        ('unknown-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
        ('ethereal-casting', replace(item, ethereal=True), context, 'true'),
        ('unknown-ethereal-casting', replace(item, ethereal=None), context, 'true'),
        ('illegal-two-sockets', replace(item, sockets=2), context, 'false'),
        ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false'),
        ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
        ('unknown-class', item, {}, 'unknown'),
    )
    for label, candidate, loadout, truth in examples:
        expected = {
            'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
        }
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        **{
                            key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in ROLES)))
                            for key in ('83:1', '105:0', '1:0')
                        },
                        '329:0': IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in FIRE_ROLES))),
                        '330:0': IsPartialDict(configuration_ids=Contains(LIGHTNING_ROLE + '-stats')),
                    }
                )
            )
        result = {'assessment': IsPartialDict(**expected)}
        grades = {
            'minimum-rolls': ('low', 'low'),
            'maximum-rolls': ('perfect', 'perfect'),
            'fire-perfect-only': ('perfect', 'low'),
            'lightning-perfect-only': ('low', 'perfect'),
        }
        if label in grades:
            result['extraction'] = IsPartialDict(
                decoded_stats=Contains(
                    *(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=stat, layer=0),
                            roll_range=IsPartialDict(min=10, max=20),
                            roll_quality=grade,
                        )
                        for stat, grade in zip((329, 330), grades[label], strict=True)
                    )
                )
            )
        yield Case(
            id='eschuta-alternatives/' + label,
            item=candidate,
            context=loadout,
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            covers=ROLES,
            expected=result,
            absent_stat_configurations={
                '329:0': (LIGHTNING_ROLE + '-stats',),
                '330:0': tuple(role + '-stats' for role in FIRE_ROLES),
            },
            report_contains=("Eschuta's Temper", '40% Faster Cast Rate', 'Trade tier:')
            if truth == 'true'
            else ('Eldritch Orb',),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/367',
                *(
                    f'pricing/data/wp-a-builds.json:/{g}/slots/Weapon/{i}'
                    for g, i in (('enchant-sorceress', 4), ('lightning-sorceress', 1), ('meteor-sorceress', 4))
                ),
                *(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__{g}.html/sections/{i}'
                    for g, i in (('fire-wall-sorceress-guide', 30), ('hydra-sorceress', 29))
                ),
            ),
        )


CASES = tuple(cases())
