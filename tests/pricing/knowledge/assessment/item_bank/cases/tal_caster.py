"""Tal caster alternatives: distinguish observed bonuses from equipped companions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ARMOR = "Tal Rasha's Guardianship"
HELM = "Tal Rasha's Horadric Crest"
BELT = "Tal Rasha's Fine-Spun Cloth"
ORB = "Tal Rasha's Lidless Eye"
AMULET = "Tal Rasha's Adjudication"
SORCERESSES = (
    ('fire-wall-sorceress-guide', True, False, 30),
    ('frozen-orb-meteor-sorceress', True, True, 29),
    ('frozen-orb-sorceress', False, True, 29),
    ('hydra-sorceress', True, False, 29),
)
ITEMS = {
    ARMOR: Item('Lacquered Plate', 'set', ARMOR, ((80, 0, 88), (105, 0, 10))),
    BELT: Item('Mesh Belt', 'set', BELT, ((80, 0, 10), (31, 0, 95), (105, 0, 10))),
    HELM: Item('Death Mask', 'set', HELM, ((7, 0, 60 << 8), (9, 0, 30 << 8), (60, 0, 10), (62, 0, 10))),
    ORB: Item(
        'Swirling Crystal',
        'set',
        ORB,
        ((105, 0, 20), (107, 61, 1), (107, 63, 2), (107, 65, 1), (83, 1, 1), (333, 0, 15), (334, 0, 15), (331, 0, 15)),
    ),
}
NATIVE_NAMES = {
    ARMOR: "Tal Rasha's Howling Wind",
    BELT: "Tal Rasha's Fire-Spun Cloth",
    HELM: HELM,
    ORB: ORB,
}
SLUGS = {ARMOR: 'guardianship', BELT: 'fine-spun-cloth', HELM: 'horadric-crest', ORB: 'lidless-eye'}


def cases():
    result = []
    uses = [(b, 'Sorceress', fire, cold, section, name) for b, fire, cold, section in SORCERESSES for name in ITEMS]
    uses += [(b, 'Warlock', False, False, 29, ARMOR) for b in ('blood-boil-warlock-guide', 'summoner-warlock-guide')]
    for build, klass, fire, cold, section, name in uses:
        role = f'{build}-tal-rasha-s-{SLUGS[name]}-tal-caster-gear'
        config = role + '-stats'
        for scenario in ('positive', 'negative', 'unknown'):
            context = {'player_class': klass}
            required, forbidden = [], []
            truth = 'true'
            if name == HELM:
                forbidden = ['60:0', '62:0']
                if scenario == 'positive':
                    required = ['7:0', '9:0']
                elif scenario == 'negative':
                    context['player_class'] = 'Barbarian'
                    truth = 'false'
                else:
                    context = {}
                    truth = 'unknown'
            else:
                if scenario == 'positive':
                    context['player_items'] = [
                        p for p in (ARMOR, HELM, BELT, ORB, AMULET) if p != name and (klass == 'Sorceress' or p != ORB)
                    ]
                elif scenario == 'negative':
                    context['player_items'] = [ORB] if klass == 'Warlock' else [] if name == ARMOR else [ARMOR] * 4
                if name == ARMOR:
                    required = ['80:0']
                    (required if scenario == 'positive' else forbidden).append('105:0')
                elif name == BELT:
                    required = ['80:0']
                    (required if scenario != 'unknown' else forbidden).append('31:0')
                    (required if scenario == 'positive' else forbidden).append('105:0')
                else:
                    forbidden = ['107:63', '334:0']
                    if not fire:
                        forbidden += ['107:61', '333:0']
                    if not cold:
                        forbidden += ['107:65', '331:0']
                    if scenario != 'unknown':
                        required = ['105:0', '83:1']
                        if fire:
                            required.append('107:61')
                            (required if scenario == 'positive' else forbidden).append('333:0')
                        if cold:
                            required.append('107:65')
                            (required if scenario == 'positive' else forbidden).append('331:0')
            assessment = {
                'roles': Contains(IsPartialDict(id=role, build=build, rule_trace=IsPartialDict(truth=truth))),
            }
            if required:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in required}
                    )
                )
            result.append(
                Case(
                    id=f'tal-caster/{role}/{scenario}',
                    item=ITEMS[name],
                    context=context,
                    expected={'assessment': IsPartialDict(**assessment)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=(config,)
                    if (name == HELM and scenario != 'positive') or (name == ORB and scenario == 'unknown')
                    else (),
                    absent_stat_configurations=dict.fromkeys(forbidden, (config,)),
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{build}.html/sections/{section}',
                        f'third-parties/d2data/json/setitems.json:/{NATIVE_NAMES[name]}',
                    ),
                )
            )
    # A valid combination is not evidence that the individual capture contains
    # its partial bonuses. Keep intrinsic properties while withholding those
    # unavailable values from this configuration's stat annotations.
    for case in tuple(result):
        if case.scenario != 'positive' or case.item.name == HELM:
            continue
        conditional = {
            ARMOR: ('105:0',),
            BELT: ('31:0', '105:0'),
            ORB: ('83:1', '333:0', '331:0'),
        }[case.item.name]
        intrinsic = '105:0' if case.item.name == ORB else '80:0'
        role = case.covers[0]
        config = role + '-stats'
        result.append(
            replace(
                case,
                id=case.id.removesuffix('/positive') + '/uncaptured-bonus',
                scenario='negative',
                item=replace(
                    case.item,
                    raw_stats=tuple(row for row in case.item.raw_stats if f'{row[0]}:{row[1]}' not in conditional),
                ),
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth='true'))),
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    intrinsic: IsPartialDict(configuration_ids=Contains(config)),
                                }
                            )
                        ),
                    )
                },
                absent_stat_configurations={
                    **case.absent_stat_configurations,
                    **dict.fromkeys(conditional, (config,)),
                },
            )
        )
    return tuple(result)


CASES = cases()
