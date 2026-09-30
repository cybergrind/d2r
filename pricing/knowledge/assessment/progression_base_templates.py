"""Reviewed player progression recipes; legal eligibility alone is not demand.

Membership comes from appraisal-utility.json <base>/sockets_by_runeword/<word>.
Native recipe edges still gate execution. These are use recommendations, not price
bands or a claim that every listed base is suitable at the same character level.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ProgressionBaseTemplate:
    runeword: str
    members: tuple[str, ...]
    strength: str
    tradeoff: str
    version: int = 1
    reviewed_sources: tuple[str, ...] = ()

    @property
    def source_locators(self):
        if self.reviewed_sources:
            return self.reviewed_sources
        return tuple(f'appraisal-utility.json:{base}/sockets_by_runeword/{self.runeword}' for base in self.members)


TEMPLATES = (
    ProgressionBaseTemplate(
        'Lionheart',
        ('Mage Plate',),
        'Light armor base for the reviewed Strafe Amazon Starter Lionheart setup.',
        'Life, attributes, resistances and off-weapon damage support progression; this recipe supplies no '
        'attack speed or life leech. Superior defense is optional, not evidence of a valuable trade base.',
        reviewed_sources=('pricing/data/wp-a-builds.json#/strafe-amazon/variants/0/player/Body Armor',),
    ),
    ProgressionBaseTemplate(
        'Duress',
        ('Dusk Shroud',),
        'Light armor base for the reviewed budget kicker Duress setup.',
        'Compare wearer requirements and the complete Ubers setup; superior defense is not required '
        'and this source does not establish the best possible base or a trade premium.',
        reviewed_sources=('pricing/data/wp-a-builds.json#/dragon-talon-assassin/variants/0/player/Body Armor',),
    ),
    ProgressionBaseTemplate(
        'Stealth',
        ('Quilted Armor', 'Leather Armor', 'Hard Leather Armor', 'Studded Leather'),
        'Light body armor for Stealth mobility and casting utility.',
        'For progression, equipment requirements and utility matter more than superior defense premiums.',
    ),
    ProgressionBaseTemplate(
        'Smoke',
        ('Mage Plate', 'Studded Leather'),
        'Player armor option for Smoke resistance and hit-recovery utility.',
        'Compare the current resistance shortfall and wearer requirements before spending runes; '
        'a recommended base is not a priced premium.',
    ),
    ProgressionBaseTemplate(
        'Rhyme',
        ('Bone Shield', 'Targe', 'Preserved Head'),
        'Two-socket player shield option for Rhyme utility.',
        'Compare class access, shield defenses and the current setup; base-specific bonuses are separate.',
    ),
    ProgressionBaseTemplate(
        'Lore',
        ('Cap', 'Diadem'),
        'Player helm option for Lore skill and resistance utility.',
        'Check the base level requirement as well as rune requirements; legal bases are not equally accessible.',
    ),
)
EXCEPTIONS = MappingProxyType(
    {
        (
            'Duress',
            'Dusk Shroud',
        ): 'For Ubers, the guide recommends level 90; verify boots, Attack Rating, Cannot Be Frozen and resistances.',
        ('Lore', 'Diadem'): 'Diadem requires level 64; this is not an early-leveling base.',
        ('Rhyme', 'Targe'): 'Paladin only: inspect inherent resistance rolls against the intended setup.',
        ('Rhyme', 'Preserved Head'): 'Necromancer only: inspect desired staffmods against the intended setup.',
    }
)


def compile_templates(templates):
    index = {}
    for template in templates:
        for base in template.members:
            key = template.runeword, base
            if key in index:
                raise ValueError(f'Conflicting progression base membership: {key}')
            index[key] = template
    if set(EXCEPTIONS) - set(index):
        raise ValueError('Progression exception has no assigned member')
    return MappingProxyType(index)


INDEX = compile_templates(TEMPLATES)


def evaluate_progression_base(facts, runeword):
    template = INDEX.get((runeword, facts.base_name))
    if template is None:
        return None
    missing = ['Confirm wearer level, strength and class requirements against the intended progression setup.']
    if exception := EXCEPTIONS.get((runeword, facts.base_name)):
        missing.append(exception)
    return 'player progression', [template.strength], missing, template.tradeoff


def reviewed_base_sources(facts, runeword):
    template = INDEX.get((runeword, facts.base_name))
    return template.reviewed_sources if template else ()
