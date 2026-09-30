"""Cold orb utility includes ethereal spell use without inferring a price premium."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = (
    'blizzard-sorceress-death-s-fathom-caster-shield-alternative',
    'frozen-orb-meteor-sorceress-death-s-fathom-caster-weapon-gear',
    'frozen-orb-sorceress-death-s-fathom-caster-weapon-gear',
)


def cases():
    item = Item(
        'Dimensional Shard',
        'unique',
        "Death's Fathom",
        raw_stats=(
            (83, 1, 3),
            (331, 0, 15),
            (105, 0, 20),
            (39, 0, 25),
            (41, 0, 25),
        ),
    )
    context = {'player_class': 'Sorceress'}
    for label, candidate, loadout, truth in (
        ('minimum-rolls', item, context, 'true'),
        (
            'maximum-rolls',
            replace(
                item,
                raw_stats=(
                    (83, 1, 3),
                    (331, 0, 30),
                    (105, 0, 20),
                    (39, 0, 40),
                    (41, 0, 40),
                ),
            ),
            context,
            'true',
        ),
        ('ethereal-casting', replace(item, ethereal=True), context, 'true'),
        ('unknown-ethereal-casting', replace(item, ethereal=None), context, 'true'),
        ('open-socket', replace(item, sockets=1), context, 'true'),
        ('unknown-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
        ('illegal-two-sockets', replace(item, sockets=2), context, 'false'),
        ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false'),
        ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
        ('unknown-class', item, {}, 'unknown'),
    ):
        expected = {
            'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
        }
        report = ("Death's Fathom", 'Trade tier:') if truth == 'true' else ('Dimensional Shard',)
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in ROLES)))
                        for key in ('83:1', '331:0', '105:0', '39:0', '41:0')
                    }
                )
            )
            if label == 'unknown-payload':
                report += ('+15% to Cold Skill Damage — item range: 15-30',)
            else:
                report += (f'+{30 if label == "maximum-rolls" else 15}% (15-30%) to Cold Skill Damage',)
        yield Case(
            id='fathom-alternatives/' + label,
            item=candidate,
            context=loadout,
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            covers=ROLES,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            report_contains=report,
            report_absent=('(15-30%)',) if label == 'unknown-payload' else (),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/354',
                'pricing/data/wp-a-builds.json:/blizzard-sorceress/slots/Weapon/5',
                *(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__{guide}.html/sections/29'
                    for guide in ('frozen-orb-sorceress', 'frozen-orb-meteor-sorceress')
                ),
            ),
        )


CASES = tuple(cases())
