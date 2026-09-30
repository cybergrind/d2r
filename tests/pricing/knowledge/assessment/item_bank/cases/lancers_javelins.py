"""Valuable 6/40 blue javelins: total skills combine an inherent roll and prefix."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'lightning-fury-starter-lancers-javelin'
CONFIG = ROLE + '-stats'
SOURCE = 'pricing/data/wp-a-variants/lightning-fury-amazon-guide.json:/variants/0/player/Weapon'


def javelin(skills=6, speed=40, *, native=True):
    return Item(
        'Matriarchal Javelin',
        'magic',
        raw_stats=((188, 2, skills), (93, 0, speed)),
        complete=True,
        affix_records=(('prefix', 441), ('suffix', 169), ('auto', skills + 2)) if native else None,
    )


def cases():
    context = {'player_class': 'Amazon'}
    rows = [(f'{skills}-skills-40-ias', javelin(skills), context, 'true') for skills in (4, 5, 6)]
    rows += [
        ('totals-only', javelin(native=False), context, 'true'),
        ('three-skills', javelin(3, native=False), context, 'false'),
        ('seven-skills', javelin(7, native=False), context, 'false'),
        ('30-ias', javelin(speed=30, native=False), context, 'false'),
        ('39-ias', javelin(speed=39, native=False), context, 'false'),
        ('41-ias', javelin(speed=41, native=False), context, 'false'),
        ('wrong-tree', replace(javelin(native=False), raw_stats=((188, 0, 6), (93, 0, 40))), context, 'false'),
        ('ethereal', replace(javelin(), ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(javelin(), ethereal=None), context, 'unknown'),
        ('wrong-class', javelin(), {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', javelin(), {}, 'unknown'),
        ('wrong-base', replace(javelin(), base='Maiden Javelin'), context, 'false'),
    ]
    for sid, label in ((188, 'skills'), (93, 'speed')):
        for complete, truth in ((True, 'false'), (False, 'unknown')):
            rows.append(
                (
                    ('missing-' if complete else 'unread-') + label,
                    replace(
                        javelin(native=False),
                        raw_stats=tuple(s for s in javelin().raw_stats if s[0] != sid),
                        complete=complete,
                    ),
                    context,
                    truth,
                )
            )
    for label, candidate, loadout, truth in rows:
        assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            assessment['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in ('188:2', '93:0')}
                )
            )
        expected = {'assessment': IsPartialDict(**assessment)}
        if label in ('4-skills-40-ias', '5-skills-40-ias', '6-skills-40-ias'):
            expected['extraction'] = IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat=IsPartialDict(id=188, layer=2),
                        roll_quality_range=IsPartialDict(max=6),
                        roll_quality='perfect' if label.startswith('6-') else 'normal',
                    )
                )
            )
        yield Case(
            id='lancers-javelin/' + label,
            item=candidate,
            context=loadout,
            expected=expected,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (CONFIG,),
            report_contains=('Matriarchal Javelin', 'Increased Attack Speed') if truth == 'true' else (),
            evidence=(
                SOURCE,
                'third-parties/d2data/json/magicprefix.json:/441',
                'third-parties/d2data/json/magicsuffix.json:/169',
                'third-parties/d2data/json/automagic.json:/6',
                'third-parties/d2data/json/automagic.json:/7',
                'third-parties/d2data/json/automagic.json:/8',
            ),
        )
    yield Case(
        id='lancers-javelin/rare-cannot-have-three-skill-prefix',
        item=replace(javelin(), rarity='rare'),
        context=context,
        expected={},
        covers=(f'role:{ROLE}:magic',),
        scenario='negative',
        absent_roles=(ROLE,),
        absent_configurations=(CONFIG,),
        evidence=('third-parties/d2data/json/magicprefix.json:/441',),
    )


CASES = tuple(cases())
