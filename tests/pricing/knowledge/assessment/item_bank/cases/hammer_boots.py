"""Hammerdin footwear alternatives: native rolls, upgrades and observed self-repair.

Guide Boots/1..3 and native item definitions reviewed independently. Waterwalk
raises the fire cap, not fire resistance; Aldur's standalone stats need no set.
"""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_boots import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


MAXIMA = {'waterwalk': {7: 65 * 256}, 'trek': {0: 15, 3: 15, 45: 70}, 'aldur': {39: 50}}


def cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer'):
    context = {'player_class': player_class, 'player_items': []}
    for slug, _, original, bases, keys, incidental in EXAMPLES[:3]:
        role = f'{build}-{slug}-boots-alternative'
        config = role + '-stats'
        for base in bases:
            item = replace(original, base=base)
            rows = [
                ('minimum-alone', item, context, 'true'),
                (
                    'maximum',
                    replace(item, raw_stats=tuple((s, p, MAXIMA[slug].get(s, v)) for s, p, v in item.raw_stats)),
                    context,
                    'true',
                ),
                ('unidentified', replace(item, identified=False), context, 'false'),
                (
                    'wrong-class',
                    item,
                    {'player_class': 'Paladin' if player_class == 'Sorceress' else 'Sorceress'},
                    'false',
                ),
                ('unknown-class', item, {}, 'unknown'),
                ('invalid-sockets', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'true' if slug == 'trek' else 'false'),
            ]
            if slug == 'trek':
                rows += [
                    (
                        'absent-repair',
                        replace(item, ethereal=True, raw_stats=item.raw_stats[:-1], complete=True),
                        context,
                        'false',
                    ),
                    ('unread-repair', replace(item, ethereal=True, raw_stats=item.raw_stats[:-1]), context, 'unknown'),
                ]
            for label, candidate, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'{prefix}/boots/{slug}/{base}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(incidental, (config,)),
                    report_contains=(original.name, 'Trade tier:')
                    if candidate.identified and not (candidate.rarity == 'set' and candidate.ethereal is True)
                    else (base,),
                    report_absent=('Trade tier:',) if candidate.rarity == 'set' and candidate.ethereal is True else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Boots',
                        'third-parties/d2data/json/uniqueitems.json',
                        'third-parties/d2data/json/setitems.json',
                    ),
                )


CASES = tuple(cases())
