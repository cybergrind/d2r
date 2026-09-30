"""Generic caster CoH recommendations allow legal bases without attack bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.coh_variant_roles import RUNES
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_coh import KEYS, STATS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('Warlock', (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        (
            ('fire-wall-sorceress-guide', 30),
            ('frozen-orb-meteor-sorceress', 29),
            ('frozen-orb-sorceress', 29),
            ('hydra-sorceress', 29),
        ),
    ),
)


def cases():
    for klass, sources in USES:
        roles = tuple(guide + '-chains-of-honor-caster-armor-gear' for guide, _ in sources)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Archon Plate',
                quality,
                'Chains of Honor',
                (*STATS, (194, 0, 4)),
                sockets=4,
                socket_contents='filled',
                socket_items=RUNES,
                runeword='Chains of Honor',
            )
            examples = [
                ('native', item, context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        ('dusk', replace(item, base='Dusk Shroud'), context, 'true'),
                        ('sacred', replace(item, base='Sacred Armor'), context, 'true'),
                        ('illegal-mage-plate', replace(item, base='Mage Plate'), context, 'false'),
                        ('shield', replace(item, base='Monarch'), context, 'false'),
                        ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                        (
                            'unknown-contents',
                            replace(item, socket_contents='unknown', socket_items=()),
                            context,
                            'unknown',
                        ),
                        ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                        ('unknown-class', item, {}, 'unknown'),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
                }
                if label == 'shield':
                    # Type filtering removes armor roles entirely; the absence
                    # assertions below still forbid their stat recommendations.
                    expected = {}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(*configs)) for k in KEYS}
                        )
                    )
                yield Case(
                    id=f'coh-caster/{klass}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations=dict.fromkeys(('60:0', '121:0', '122:0'), configs),
                    report_contains=('Chains of Honor', 'Sockets: 4 — Dol, Um, Ber, Ist') if label == 'native' else (),
                    evidence=tuple(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                        for guide, section in sources
                    ),
                )


CASES = tuple(cases())
