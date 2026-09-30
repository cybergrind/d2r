"""Cold-spell alternatives retain utility at low rolls and distinguish socket evidence."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = (
    'blizzard-sorceress-nightwing-s-veil-equipment-tail-alternative',
    'frozen-orb-sorceress-nightwing-s-veil-caster-defense-gear',
)


def cases():
    item = Item(
        'Spired Helm',
        'unique',
        "Nightwing's Veil",
        raw_stats=(
            (331, 0, 8),
            (16, 0, 90),
            (127, 0, 2),
            (2, 0, 10),
            (149, 0, 5),
            (118, 0, 1),
            (91, 0, -50),
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
                    (331, 0, 15),
                    (16, 0, 120),
                    (127, 0, 2),
                    (2, 0, 20),
                    (149, 0, 9),
                    (118, 0, 1),
                    (91, 0, -50),
                ),
            ),
            context,
            'true',
        ),
        ('open-socket', replace(item, sockets=1), context, 'true'),
        ('unknown-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
        ('illegal-two-sockets', replace(item, sockets=2), context, 'false'),
        ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ('ethereal', replace(item, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false'),
        ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
        ('unknown-class', item, {}, 'unknown'),
    ):
        expected = {
            'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
        }
        report = ("Nightwing's Veil", 'Trade tier:') if truth == 'true' else ('Spired Helm',)
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in ROLES)))
                        for key in ('127:0', '331:0', '2:0', '149:0', '118:0')
                    }
                )
            )
            report += (
                f'+{15 if label == "maximum-rolls" else 8}% (8-15%) to Cold Skill Damage',
                f'+{120 if label == "maximum-rolls" else 90}% (90-120%) Enhanced Defense',
            )
        if label == 'unknown-payload':
            report = (
                "Nightwing's Veil",
                'Trade tier:',
                '+8% to Cold Skill Damage — item range: 8-15',
                '+90% Enhanced Defense — item range: 90-120',
            )
        yield Case(
            id='nightwing-alternatives/' + label,
            item=candidate,
            context=loadout,
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            covers=ROLES,
            expected={'assessment': IsPartialDict(**expected)},
            report_contains=report,
            report_absent=('(8-15%)', '(90-120%)') if label == 'unknown-payload' else (),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/343',
                'pricing/data/wp-a-builds.json:/blizzard-sorceress/slots/Helmets/1',
                'pricing/data/appraisal-guide-sections.json:/sources/'
                'pricing~1raw~1mr~1guides__frozen-orb-sorceress.html/sections/29',
            ),
        )


CASES = tuple(cases())
