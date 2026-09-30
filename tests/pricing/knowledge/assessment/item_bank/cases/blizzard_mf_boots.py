"""War Traveler in the three-piece Tal MF setup requires wearer gear and 105 FCR."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_boots import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.cases.sorceress_mf_gloves import TAL
from tests.pricing.knowledge.assessment.item_bank.models import Case


ROLE = 'blizzard-mf-war-traveler'


def cases():
    original = next(item for slug, _, item, _, _, _ in EXAMPLES if slug == 'traveler')
    full = {'player_class': 'Sorceress', 'player_total_fcr': 105, 'player_items': list(TAL)}
    rows = [
        ('minimum-mf', original, full, 'true', 'true'),
        (
            'maximum-mf',
            replace(original, raw_stats=tuple((s, p, 50 if s == 80 else v) for s, p, v in original.raw_stats)),
            full,
            'true',
            'true',
        ),
        ('upgraded', replace(original, base='Mirrored Boots'), full, 'true', 'true'),
        ('fcr-short', original, {**full, 'player_total_fcr': 104}, 'false', 'true'),
        ('fcr-above', original, {**full, 'player_total_fcr': 106}, 'true', 'true'),
        ('fcr-unknown', original, {k: v for k, v in full.items() if k != 'player_total_fcr'}, 'unknown', 'true'),
        ('wrong-class', original, {**full, 'player_class': 'Paladin'}, 'false', 'true'),
        ('unidentified', replace(original, identified=False), full, 'false', 'true'),
        ('companions-unknown', original, {k: v for k, v in full.items() if k != 'player_items'}, 'true', 'unknown'),
        ('merc-not-player-set', original, {**full, 'player_items': [], 'mercenary_items': list(TAL)}, 'true', 'false'),
    ]
    rows += [
        (f'missing-{name}', original, {**full, 'player_items': [n for n in TAL if n != name]}, 'true', 'false')
        for name in TAL
    ]
    for label, item, context, truth, dependency in rows:
        config = ROLE + '-stats'
        annotated = truth == dependency == 'true'
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    rule_trace=IsPartialDict(truth=truth),
                    dependencies=Contains(IsPartialDict(status=dependency)),
                )
            )
        }
        if annotated:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('80:0', '96:0', '0:0', '3:0')}
                )
            )
        yield Case(
            id=f'blizzard/mf-boots/{label}',
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario='positive' if annotated else 'unknown' if 'unknown' in (truth, dependency) else 'negative',
            absent_configurations=() if annotated else (config,),
            absent_stat_configurations=dict.fromkeys(('21:0', '22:0', '16:0'), (config,)),
            report_contains=('War Traveler', 'Trade tier:') if item.identified else ('War Traveler',),
            report_absent=() if item.identified else ('Trade tier:',),
            evidence=(
                'pricing/data/wp-a-builds.json:/blizzard-sorceress/variants/2',
                'third-parties/d2data/json/uniqueitems.json',
            ),
        )


CASES = tuple(cases())
