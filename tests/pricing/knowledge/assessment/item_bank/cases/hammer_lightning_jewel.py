"""Uber Hammerdin's magic IAS/lightning-resist jewel and recipient conditions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'hammer-ubers-ias-lightning-jewel'
CONFIG = ROLE + '-stats'
RECIPIENT = "Guillaume's Face"


def jewel(resistance):
    return Item(
        'Jewel',
        'magic',
        raw_stats=((93, 0, 15), (41, 0, resistance)),
        complete=True,
        affix_records=(('prefix', 395 if resistance <= 15 else 396), ('suffix', 171)),
    )


def cases():
    item = jewel(30)
    context = {'player_class': 'Paladin', 'player_items': [RECIPIENT]}
    rows = [
        ('perfect', item, context, 'true', 'true'),
        ('minimum-ambergris', jewel(16), context, 'true', 'true'),
        ('minimum-camphor', jewel(5), context, 'true', 'true'),
        ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false', 'true'),
        ('unknown-class', item, {'player_items': [RECIPIENT]}, 'unknown', 'true'),
        ('wrong-helmet', item, {**context, 'player_items': ['Harlequin Crest']}, 'true', 'false'),
        (
            'mercenary-helmet',
            item,
            {'player_class': 'Paladin', 'player_items': [], 'mercenary_items': [RECIPIENT]},
            'true',
            'false',
        ),
        ('unknown-helmet', item, {'player_class': 'Paladin'}, 'true', 'unknown'),
        (
            'wrong-element',
            replace(item, raw_stats=((93, 0, 15), (39, 0, 30)), affix_records=(('prefix', 376), ('suffix', 171))),
            context,
            'false',
            'true',
        ),
        ('impossible-ias', replace(item, raw_stats=((93, 0, 16), (41, 0, 30))), context, 'false', 'true'),
    ]
    for sid, label in ((93, 'ias'), (41, 'lightning-resistance')):
        for complete, truth in ((True, 'false'), (False, 'unknown')):
            rows.append(
                (
                    ('missing-' if complete else 'unread-') + label,
                    replace(
                        item,
                        raw_stats=tuple(s for s in item.raw_stats if s[0] != sid),
                        complete=complete,
                        affix_records=None,
                    ),
                    context,
                    truth,
                    'true',
                )
            )
    for label, candidate, loadout, truth, dependency in rows:
        active = truth == dependency == 'true'
        assessment = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    side='player',
                    rule_trace=IsPartialDict(truth=truth),
                    dependencies=Contains(IsPartialDict(status=dependency)),
                )
            )
        }
        if active:
            assessment['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in ('93:0', '41:0')}
                )
            )
        expected = {'assessment': IsPartialDict(**assessment)}
        if label in ('perfect', 'minimum-ambergris', 'minimum-camphor'):
            lower = label == 'minimum-camphor'
            expected['extraction'] = IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat=IsPartialDict(id=41),
                        roll_range=IsPartialDict(min=5 if lower else 16, max=15 if lower else 30),
                        roll_quality_range=IsPartialDict(min=5, max=30),
                        roll_tier=2 if lower else 1,
                        roll_quality={'perfect': 'perfect', 'minimum-ambergris': 'normal', 'minimum-camphor': 'low'}[
                            label
                        ],
                    )
                )
            )
        yield Case(
            id='hammer-lightning-jewel/' + label,
            item=candidate,
            context=loadout,
            expected=expected,
            covers=(ROLE,),
            scenario='positive' if active else ('negative' if 'false' in (truth, dependency) else 'unknown'),
            absent_configurations=() if active else (CONFIG,),
            report_contains=('Jewel', 'Increased Attack Speed', 'Lightning Resist') if active else ('Jewel',),
            evidence=(
                'pricing/data/wp-a-variants/blessed-hammer-paladin.json:/variants/3/player/Helmet/0',
                'third-parties/d2data/json/magicprefix.json:/395',
                'third-parties/d2data/json/magicprefix.json:/396',
                'third-parties/d2data/json/magicsuffix.json:/171',
            ),
        )
    yield Case(
        id='hammer-lightning-jewel/rare-cannot-have-fervor',
        item=replace(item, rarity='rare'),
        context=context,
        expected={},
        covers=(f'role:{ROLE}:magic',),
        scenario='negative',
        absent_roles=(ROLE,),
        absent_configurations=(CONFIG,),
        evidence=('third-parties/d2data/json/magicsuffix.json:/171',),
    )


CASES = tuple(cases())
