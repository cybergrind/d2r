"""Reviewed caster/prebuff base families; recipe legality remains a separate gate.

Membership is explicit, not a type-wide recommendation. Utility KB recommendation
edges still decide preferred versus alternative; these templates do not add votes,
prices, or infer the wearer's build. Exceptions add verification requirements only.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class CasterBaseTemplate:
    id: str
    version: int
    runeword: str
    members: tuple[str, ...]
    role: str
    strength: str
    requirement: str
    tradeoff: str
    ethereal_caveat: str
    ethereal_reason: str
    source_locators: tuple[str, ...]
    exceptions: Mapping[str, tuple[str, ...]]


def compile_templates(templates):
    index = {}
    ids = set()
    for template in templates:
        if not template.source_locators:
            raise ValueError('Template requires reviewed source locators')
        if template.id in ids or template.version < 1 or not template.members:
            raise ValueError('Invalid template identity/version/membership')
        ids.add(template.id)
        if set(template.exceptions) - set(template.members):
            raise ValueError('Template exception has no assigned member')
        for base in template.members:
            key = template.runeword, base
            if key in index:
                raise ValueError(f'Conflicting template membership: {key}')
            index[key] = template
    return MappingProxyType(index)


TEMPLATES = (
    *(
        CasterBaseTemplate(
            id=identity,
            version=1,
            runeword=word,
            members=(base,),
            role=role,
            strength=f'Reviewed {base} base for {word} caster utility.',
            requirement=requirement,
            tradeoff=tradeoff,
            ethereal_caveat='An ethereal weapon cannot be repaired if used for melee attacks.',
            ethereal_reason='Spell casting does not consume weapon durability; melee use does.',
            source_locators=(f'appraisal-utility.json:{base}/sockets_by_runeword/{word}',),
            exceptions=MappingProxyType({}),
        )
        for identity, word, base, role, requirement, tradeoff in (
            (
                'leaf-short-staff',
                'Leaf',
                'Short Staff',
                'Leaf player caster',
                'Check desired fire-skill staffmods and wearer requirements against the intended setup.',
                'A two-handed staff replaces weapon and shield; compare total caster utility, not physical ED.',
            ),
            (
                'memory-battle-staff',
                'Memory',
                'Battle Staff',
                'Memory player caster',
                'Check desired Sorceress staffmods and wearer requirements for the intended casting or prebuff setup.',
                'A two-handed staff replaces weapon and shield; prebuff skill targets depend on the intended setup.',
            ),
            (
                'white-bone-wand',
                'White',
                'Bone Wand',
                'White player caster',
                'Check Necromancer skill needs, desired staffmods and wearer requirements before investing runes.',
                'One-handed wand leaves room for a shield; base identity alone does not prove useful skill bonuses.',
            ),
        )
    ),
    CasterBaseTemplate(
        id='heart-of-the-oak-caster-flail',
        version=1,
        runeword='Heart of the Oak',
        members=('Flail',),
        role='Heart of the Oak player caster',
        strength='One-handed caster base, leaving the other hand available for a shield.',
        requirement='Confirm wearer requirements and whether the setup needs rechargeable summon charges.',
        tradeoff='Caster use values completed skill bonuses, cast rate and resistance rolls; '
        'superior physical damage does not improve spells. '
        'Oak Sage and Raven charges favor a repairable non-ethereal base when used repeatedly.',
        ethereal_caveat='An ethereal weapon cannot be repaired, and its skill charges cannot be recharged.',
        ethereal_reason='Spell casting does not consume durability; ethereal summon charges cannot be recharged.',
        source_locators=(
            'appraisal-utility.json:Flail/sockets_by_runeword/Heart of the Oak',
            'third-parties/d2data/json/runes.json:Heart of the Oak',
            'third-parties/d2data/json/cubemain.json:139',
            'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_IsRepairable',
        ),
        exceptions=MappingProxyType({}),
    ),
    CasterBaseTemplate(
        id='spirit-caster-swords',
        version=1,
        runeword='Spirit',
        members=('Crystal Sword', 'Broad Sword', 'Long Sword'),
        role='Spirit player caster',
        strength='One-handed four-socket sword for Spirit caster utility.',
        requirement='Confirm wearer requirements and intended caster use before investing runes.',
        tradeoff='Caster utility depends on completed Spirit skill, FCR and resource rolls; '
        'superior physical damage and Attack Rating do not improve spells.',
        ethereal_caveat='An ethereal sword cannot be repaired if used for melee attacks.',
        ethereal_reason='Spell casting does not consume sword durability; melee use does.',
        source_locators=(
            'appraisal-utility.json:Crystal Sword/sockets_by_runeword/Spirit',
            'appraisal-utility.json:runes/Spirit',
        ),
        exceptions=MappingProxyType({}),
    ),
    CasterBaseTemplate(
        id='call-to-arms-prebuff',
        version=1,
        runeword='Call to Arms',
        members=('Crystal Sword', 'Flail', 'War Scepter'),
        role='player prebuff',
        strength='One-handed Call to Arms base; leaves the other hand available for a prebuff shield.',
        requirement='Confirm wearer requirements and the intended prebuff setup before investing runes.',
        tradeoff='Prebuff use values completed Call to Arms skill rolls; superior physical damage '
        'and Attack Rating do not improve warcries. Ethereal appearance does not establish a price premium.',
        ethereal_caveat='An ethereal weapon cannot be repaired if used for melee attacks.',
        ethereal_reason='Prebuff warcries do not consume weapon durability; melee use does.',
        source_locators=tuple(
            f'appraisal-utility.json:{base}/sockets_by_runeword/Call to Arms'
            for base in ('Crystal Sword', 'Flail', 'War Scepter')
        ),
        exceptions=MappingProxyType(
            {
                'War Scepter': (
                    'Verify desired Paladin staffmods against the intended setup; base identity alone is insufficient.',
                )
            }
        ),
    ),
)
INDEX = compile_templates(TEMPLATES)


def evaluate_caster_base(facts, runeword):
    template = INDEX.get((runeword, facts.base_name))
    if template is None:
        return None
    missing = [template.requirement, *template.exceptions.get(facts.base_name, ())]
    tradeoff = template.tradeoff
    if facts.ethereal is None:
        missing.append('Ethereal status has not been read.')
    elif facts.ethereal:
        tradeoff += ' ' + template.ethereal_caveat
    return template.role, [template.strength], missing, tradeoff


def caster_ethereal_preference(role, base_name):
    for template in TEMPLATES:
        if template.role == role and base_name in template.members:
            return {'preference': 'neutral', 'reason': template.ethereal_reason}
    return None
