"""Bounded qualified labels require the already reviewed equipment dependency."""

from pricing.knowledge.assessment.maintenance.named_shield_templates import shield_setup
from pricing.knowledge.assessment.maintenance.qualified_equipment_templates import setup_condition
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.definition_store import catalog


def require_qualification(role, label):
    name = role['names'][0]
    ethereal_labels = {
        f'Ethereal {weapon}' for weapon in ('Gimmershred', 'Warshrike', 'Lacerator', "Demon's Arch", "Gargoyle's Bite")
    }
    ethereal_labels.update(f'Ethereal {weapon} (Upgraded)' for weapon in ('Deathbit', 'The Scalper'))
    if label in ethereal_labels:
        if not label.startswith('Ethereal ' + name) or not requires_eq(
            role.get('must', {}), 'fact_eq', 'ethereal', True
        ):
            raise ValueError('Table qualification requires an explicitly ethereal item')
        label = label.removeprefix('Ethereal ')
        if label == name:
            return
    if name in ('Deathbit', 'The Scalper') and label == f'{name} (Upgraded)':
        elite = catalog().named['unique', name]['base_definition']['ultracode']
        if not elite or not requires_eq(role.get('must', {}), 'fact_eq', 'base_code', elite):
            raise ValueError(f'Table qualification requires the upgraded {name} base')
        return
    labels = {
        "Trang-Oul's Wing": ("Trang-Oul's Wing (3-Piece Trang-Oul's Set )",),
        'Stormlash': ('Stormlash ( Shael Rune )',),
        'Rune Master': ('Rune Master (5x Ist Rune s )',),
        'Angelic Halo': ('Angelic Halo (2-Piece Set)', 'Angelic Halo (2-Piece Angelic Set )'),
        'Angelic Wings': ('Angelic Wings (2-Piece Set)', 'Angelic Wings (2-Piece Angelic Set )'),
        "Immortal King's Forge": ("Immortal King's Forge (3-Piece Immortal King's Set )",),
        "Immortal King's Pillar": ("Immortal King's Pillar (3-Piece Immortal King's Set )",),
    }
    if label not in labels.get(name, ()):
        raise ValueError('Table qualification is not a reviewed equipment setup')
    expected = shield_setup(name, 'poison-nova-necromancer') if name == "Trang-Oul's Wing" else setup_condition(name)
    if not any(d.get('when') == expected and d.get('required', True) for d in role.get('depends_on', ())):
        raise ValueError('Table qualification requires its exact equipment dependency')
