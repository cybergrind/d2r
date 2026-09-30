"""Lidless caster alternatives: summon kills are not wearer mana-after-kill."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.lidless_alternatives import BASES, shield
from tests.pricing.knowledge.assessment.item_bank.models import Case


GUIDES = ('blood-boil-warlock-guide', 'summoner-warlock-guide')
ROLES = tuple(g + '-lidless-wall-caster-gear-alternative' for g in GUIDES)
CONFIGS = tuple(r + '-stats' for r in ROLES)


def cases():
    context = {'player_class': 'Warlock'}
    examples = [(base, shield(base, defense), context, 'true') for base, defense in BASES]
    item = shield('Grim Shield', 151)
    opened = replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1)))
    examples.extend(
        (
            ('open-socket', opened, context, 'true'),
            ('unread-contents', replace(opened, socket_contents='unknown'), context, 'true'),
            (
                'unread-mana-kill',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 138), complete=False),
                context,
                'true',
            ),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-sockets', replace(item, sockets=2), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
    )
    for label, candidate, loadout, truth in examples:
        expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in ROLES))}
        if truth == 'true':
            annotations = {
                key: IsPartialDict(configuration_ids=Contains(*CONFIGS)) for key in ('127:0', '105:0', '77:0', '1:0')
            }
            if label != 'unread-mana-kill':
                annotations['138:0'] = IsPartialDict(configuration_ids=Contains(CONFIGS[0]))
            expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
        yield Case(
            id='lidless-caster-tables/' + label,
            item=candidate,
            context=loadout,
            scenario='unknown'
            if label in ('unread-mana-kill', 'unread-contents')
            else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            covers=ROLES,
            expected={'assessment': IsPartialDict(**expected)},
            absent_stat_configurations={
                **dict.fromkeys(('16:0', '31:0', '89:0'), CONFIGS),
                '138:0': CONFIGS if label == 'unread-mana-kill' else (CONFIGS[1],),
            },
            absent_configurations=() if truth == 'true' else CONFIGS,
            report_contains=('Lidless Wall', 'Trade tier:') if truth == 'true' else (candidate.base,),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/230',
                *(
                    f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{g}.html/sections/29'
                    for g in GUIDES
                ),
            ),
        )


CASES = tuple(cases())
