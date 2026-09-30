"""Berserk Starter/Standard native mercenary components, not whole-loadout claims.

Source: wp-a-builds Starter Death Mask Bulwark and Standard ethereal Archon Plate
Treachery, both Act 2 Might. Native Non-Ladder Bulwark rolls differ from revisions.
"""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_words import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


def cases():
    for slug, variant, base, keys in (
        ('bulwark', 0, 'Death Mask', ('60:0', '36:0', '76:0', '99:0')),
        ('treachery', 1, 'Archon Plate', ('93:0', '201:17103', '99:0', '43:0')),
    ):
        original = next(item for name, _, item, _ in EXAMPLES if name == slug)
        role = f'berserk-barbarian-{variant}-merc-{slug}-native'
        context = {'player_class': 'Barbarian', 'mercenary_type': 'Act 2 Might'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(original, base=base, rarity=quality, ethereal=True)
            rows = [
                ('native', item, context, 'true'),
                ('nonethereal', replace(item, ethereal=False), context, 'true' if slug == 'bulwark' else 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('two-sockets', replace(item, sockets=2), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                (
                    'different-base',
                    replace(item, base='Bone Visage' if slug == 'bulwark' else 'Mage Plate'),
                    context,
                    'false',
                ),
                ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('wrong-merc', item, {**context, 'mercenary_type': 'Act 2 Holy Freeze'}, 'false'),
                ('unknown-merc', item, {'player_class': 'Barbarian'}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ]
            if slug == 'bulwark':
                rows.append(
                    (
                        'maximum-leech-reduction',
                        replace(
                            item,
                            raw_stats=tuple(
                                (stat, layer, {60: 6, 36: 15}.get(stat, value)) for stat, layer, value in item.raw_stats
                            ),
                        ),
                        context,
                        'true',
                    )
                )
            for label, candidate, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'berserk/native-merc/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations={'3:0' if slug == 'bulwark' else '83:6': (role + '-stats',)},
                    evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
                )


CASES = tuple(cases())
