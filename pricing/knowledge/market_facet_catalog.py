"""Catalog identities for the eight native Rainbow Facet variants."""

from pricing.knowledge.definition_store import catalog


# Verified native uniqueitems records and local Traderie catalog, 2026-10-02.
# The generic Rainbow Facet catalog does not identify an element or trigger.
VARIANTS = (
    (392, '2368934470', 'Lightning Death', 'ltng', 'death-skill', 'Chain Lightning', 47),
    (393, '3308865831', 'Cold Death', 'cold', 'death-skill', 'Blizzard', 37),
    (394, '2991746251', 'Fire Death', 'fire', 'death-skill', 'Meteor', 31),
    (395, '2470315921', 'Poison Death', 'pois', 'death-skill', 'Poison Nova', 51),
    (396, '3699123392', 'Lightning Level-up', 'ltng', 'levelup-skill', 'Nova', 41),
    (397, '3807838496', 'Cold Level-up', 'cold', 'levelup-skill', 'Frost Nova', 43),
    (398, '2722722130', 'Fire Level-up', 'fire', 'levelup-skill', 'Blaze', 29),
    (399, '2188191106', 'Poison Level-up', 'pois', 'levelup-skill', 'Venom', 23),
)


def facet_catalog(definition):
    """Bind a native definition to a catalog only while its discriminator agrees."""
    spec = next((row for row in VARIANTS if row[0] == definition.get('table_id')), None)
    if spec is None or definition.get('base_name') != 'Jewel':
        return None
    _, identity, label, element, event, skill, level = spec
    game = definition.get('game_definition', {})
    expected = {
        'index': 'Rainbow Facet',
        'prop1': 'dmg-' + element,
        'prop2': 'pierce-' + element,
        'prop3': 'extra-' + element,
        'prop4': event,
        'par4': skill,
        'min4': 100,
        'max4': level,
    }
    if any(game.get(key) != value for key, value in expected.items()):
        return None
    return identity, 'Rainbow Facet: ' + label


def canonicalize_facet_catalog(row):
    """Preserve the original label; mismatching and generic catalogs stay unresolved."""
    if row.get('category') not in ('unique', 'uniques'):
        return False
    if not any(
        (row.get('catalog_id'), row.get('name')) == (identity, 'Rainbow Facet: ' + label)
        for _, identity, label, *_ in VARIANTS
    ):
        return False
    try:
        definitions = catalog()
    except OSError, ValueError, KeyError, TypeError:
        return False
    for definition in definitions.named_variants.get(('unique', 'Rainbow Facet'), ()):
        match = facet_catalog(definition)
        if match is None or match != (row.get('catalog_id'), row.get('name')):
            continue
        row['catalog_name'] = row['name']
        row['name'] = 'Rainbow Facet'
        row.setdefault('facet_basis', {})['identity'] = {
            'kind': 'reviewed_facet_catalog_variant',
            'catalog_id': row['catalog_id'],
            'catalog_name': row['catalog_name'],
            'catalog_path': 'pricing/data/appraisal-traderie-catalog.json',
            'definition_name': 'Rainbow Facet',
            'table_id': definition['table_id'],
            'definition_generation': definitions.generation,
            'reviewed_at': '2026-10-02',
        }
        return True
    return False
