"""Shadow Dancer utility skills, kick-base role and independent native rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'dragon-talon-assassin-shadow-dancer-specialist-equipment-alternative'
CONFIG = ROLE + '-stats'


def dancer(skills=1, dexterity=15, defense=70):
    # Modifier-only native capture: do not invent total armor or numeric pricing.
    return Item(
        'Myrmidon Greaves',
        'unique',
        'Shadow Dancer',
        ((188, 49, skills), (2, 0, dexterity), (16, 0, defense), (96, 0, 30), (99, 0, 30), (91, 0, -20)),
        named_table_id=309,
    )


def cases():
    context = {'player_class': 'Assassin'}
    examples = [
        (f'rolls/{skills}-{dex}-{ed}', dancer(skills, dex, ed), context, 'true')
        for skills in (1, 2)
        for dex in (15, 25)
        for ed in (70, 100)
    ]
    examples += [
        ('wrong-class', dancer(), {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', dancer(), {}, 'unknown'),
        ('ethereal', replace(dancer(), ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(dancer(), ethereal=None), context, 'unknown'),
        ('impossible-socket', replace(dancer(), sockets=1), context, 'false'),
        ('unknown-sockets', replace(dancer(), sockets=None, socket_contents='unknown'), context, 'unknown'),
    ]
    for label, item, loadout, truth in examples:
        active = truth == 'true'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(CONFIG), desirability=grade)
                        for key, grade in (
                            ('188:49', 'desirable'),
                            ('2:0', 'desirable'),
                            ('99:0', 'desirable'),
                            ('96:0', 'supporting'),
                            ('16:0', 'supporting'),
                        )
                    }
                )
            )
        yield Case(
            id=f'shadow-dancer/{label}',
            item=item,
            context=loadout,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if active else (CONFIG,),
            absent_annotations=('188:48', '93:0'),
            report_contains=(
                'Shadow Dancer',
                'Trade tier:',
                '(1-2)',
                'Shadow Disciplines',
                '(15-25)',
                '(70-100%)',
                '30% Faster Hit Recovery',
                '30% Faster Run/Walk',
                'Requirements -20%',
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/dragon-talon-assassin/slots/Boots 4/2',
                'third-parties/d2data/json/uniqueitems.json:/309',
            ),
        )


CASES = tuple(cases())
