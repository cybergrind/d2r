"""Zeal's linked Duress armor examples preserve base and endgame ethereal scope."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.duress_endgame_merc import duress
from tests.pricing.knowledge.assessment.item_bank.models import Case


KEYS = ('17:0', '18:0', '16:0', '99:0', '135:0', '136:0', '54:0', '55:0', '39:0', '41:0', '43:0', '45:0')


def cases():
    for stage, span in (('mid', 220), ('end', 227)):
        role = f'zeal-paladin-merc-word-duress-{stage}'
        config = role + '-stats'
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(duress(quality), base='Great Hauberk', ethereal=stage == 'end')
            context = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}
            variants = [
                ('native-minimum', item, context, 'true'),
                (
                    'native-maximum',
                    replace(duress(quality, 20, 200), base='Great Hauberk', ethereal=stage == 'end'),
                    context,
                    'true',
                ),
                ('nonethereal', replace(item, ethereal=False), context, 'true' if stage == 'mid' else 'false'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true' if stage == 'mid' else 'unknown'),
                ('other-legal-base', replace(item, base='Dusk Shroud'), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('wrong-bearer', item, {**context, 'mercenary_type': 'Act 3 Fire'}, 'false'),
                ('unknown-bearer', item, {'player_class': 'Paladin'}, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ]
            for label, candidate, loadout, truth in variants:
                active = truth == 'true'
                expected = {}
                if label != 'other-legal-base':
                    expected['roles'] = Contains(
                        IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth))
                    )
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in KEYS}
                        )
                    )
                yield Case(
                    id=f'zeal-duress-examples/{stage}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(('60:0', '1:0', '3:0'), (config,)),
                    report_contains=('Duress', 'Great Hauberk', 'Shael, Um, Thul') if active else (),
                    report_absent=('Life stolen per hit',),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        'third-parties/d2data/json/runes.json:/Duress',
                    ),
                )


CASES = tuple(cases())
