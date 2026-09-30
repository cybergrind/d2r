"""The player casts Demon Limb's Enchant on the Ubers mercenary."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'echoing-ubers-mercenary-enchant-prebuff'
CLUB = Item('Tyrant Club', 'unique', 'Demon Limb', ((204, 3351, 1 | (20 << 8)),))
CONTEXT = {'player_class': 'Warlock', 'mercenary_type': 'Act 5 Frenzy'}


def cases():
    scenarios = (
        ('charged', CLUB, CONTEXT, 'true', True),
        ('ethereal', replace(CLUB, ethereal=True), CONTEXT, 'true', True),
        ('wrong-class', CLUB, {**CONTEXT, 'player_class': 'Paladin'}, 'false', False),
        ('unknown-class', CLUB, {**CONTEXT, 'player_class': None}, 'unknown', False),
        ('wrong-mercenary', CLUB, {**CONTEXT, 'mercenary_type': 'Act 2 Might'}, 'false', False),
        ('unknown-mercenary', CLUB, {**CONTEXT, 'mercenary_type': None}, 'unknown', False),
        ('unidentified', replace(CLUB, identified=False), CONTEXT, 'false', False),
        ('empty-charges', replace(CLUB, raw_stats=((204, 3351, 20 << 8),)), CONTEXT, 'true', False),
        ('unread-charges', replace(CLUB, raw_stats=()), CONTEXT, 'true', False),
    )
    for label, item, context, truth, usable in scenarios:
        assessment = {
            'roles': Contains(
                IsPartialDict(id=ROLE, side='player', slot='Prebuff', rule_trace=IsPartialDict(truth=truth))
            )
        }
        if usable:
            assessment['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict({'204:3351': IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))})
            )
        yield Case(
            id='echoing/merc-enchant/' + label,
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**assessment)},
            covers=(ROLE,),
            scenario='unknown' if label.startswith(('unknown', 'unread')) else 'positive' if usable else 'negative',
            absent_configurations=() if usable else (ROLE + '-stats',),
            report_contains=('Enchant for the Act 5 Frenzy mercenary',) if usable else (),
            evidence=(
                'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/25',
                'third-parties/d2data/json/uniqueitems.json:/296',
            ),
        )


CASES = tuple(cases())
