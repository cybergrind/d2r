"""Independent material catalog and full-pipeline positive/invalid/unknown examples."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    ('pk1', 'Key of Terror', 'minor Uber portal'),
    ('pk2', 'Key of Hate', 'minor Uber portal'),
    ('pk3', 'Key of Destruction', 'minor Uber portal'),
    ('bey', "Baal's Eye", 'Uber Tristram'),
    ('dhn', "Diablo's Horn", 'Uber Tristram'),
    ('mbr', "Mephisto's Brain", 'Uber Tristram'),
    ('tes', 'Twisted Essence of Suffering', 'Token of Absolution'),
    ('ceh', 'Charged Essense of Hatred', 'Token of Absolution'),
    ('bet', 'Burning Essence of Terror', 'Token of Absolution'),
    ('fed', 'Festering Essence of Destruction', 'Token of Absolution'),
    ('toa', 'Token of Absolution', 'reset Stat/Skill Points'),
    ('ua1', 'Uber Ancient Summon Material Act 1', 'Colossal Summit'),
    ('ua2', 'Uber Ancient Summon Material Act 2', 'Colossal Summit'),
    ('ua3', 'Uber Ancient Summon Material Act 3', 'Colossal Summit'),
    ('ua4', 'Uber Ancient Summon Material Act 4', 'Colossal Summit'),
    ('ua5', 'Uber Ancient Summon Material Act5', 'Colossal Summit'),
    ('xa1', 'Western Worldstone Shard', 'Renewed Rotting Fissure'),
    ('xa2', 'Eastern Worldstone Shard', 'Renewed Cold Rupture'),
    ('xa3', 'Southern Worldstone Shard', 'Renewed Crack of the Heavens'),
    ('xa4', 'Deep Worldstone Shard', 'Renewed Flame Rift'),
    ('xa5', 'Northern Worldstone Shard', 'Renewed Bone Break'),
    ('box', 'Horadric Cube', 'separate storage grid'),
)


def cases():
    result = []
    for code, name, text in EXAMPLES:
        item = Item(name, 'normal', complete=True)
        for scenario, specimen in (
            ('positive', item),
            ('negative', replace(item, sockets=1)),
            ('unknown', replace(item, complete=False)),
        ):
            contract = (
                IsPartialDict(policy='quest_material', base_code=code)
                if scenario == 'positive' and code != 'box'
                else None
            )
            result.append(
                Case(
                    id=f'quest-material-{code}-{scenario}',
                    item=specimen,
                    context={},
                    scenario=scenario,
                    covers=('quest_material:' + code,),
                    expected={
                        'assessment': IsPartialDict(
                            family='quest_material',
                            quality_policy='quest_material',
                            contract=contract,
                            utility=IsPartialDict(
                                status='usable' if scenario == 'positive' else 'review', variable_rolls=False
                            ),
                        )
                    },
                    report_contains=(text,),
                    report_absent=('unsupported comparison policy', 'No supported stats decoded'),
                    evidence=(
                        f'third-parties/d2data/json/misc.json:/{code}',
                        'third-parties/d2data/json/cubemain.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
