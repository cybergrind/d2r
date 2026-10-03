"""Trade review identity for the eight element/event facet variants."""

from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey
from pricing.knowledge.assessment.handlers.facet import TRIGGERS
from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_facet_catalog import facet_catalog


def definition_for_review(review):
    table = review.get('facet_table_id')
    if type(table) is not int:
        raise ValueError('Facet trade review requires a native table identity')
    definition = next(
        (d for d in catalog().named_variants.get(('unique', 'Rainbow Facet'), ()) if d['table_id'] == table), None
    )
    if definition is None or facet_catalog(definition) is None:
        raise ValueError('Facet trade review has no verified native catalog')
    if set(review['material_stats']) != {key + ':0' for key in definition['roll_ranges']}:
        raise ValueError('Facet trade review requires both native elemental rolls')
    return definition


def valid_rolls(review, facts):
    if 'facet_table_id' not in review:
        return True
    definition = definition_for_review(review)
    for key, bounds in definition['roll_ranges'].items():
        value = facts.stat(StatKey(int(key)))
        if (
            value.status != FactStatus.KNOWN
            or type(value.value) is not int
            or not bounds['min'] <= value.value <= bounds['max']
        ):
            return False
    return True


def listing_provenance(review, row):
    """Resolve native identity from the verified catalog pair, never from a roll."""
    if 'facet_table_id' not in review:
        return {}
    definition = definition_for_review(review)
    if (row.get('rarity'), row.get('name')) != ('unique', 'Rainbow Facet') or (
        row.get('catalog_id'),
        row.get('catalog_name'),
    ) != facet_catalog(definition):
        raise ValueError('Facet trade evidence belongs to another catalog variant')
    if row.get('mechanics_conflicts'):
        raise ValueError('Conflicting facet trade evidence mechanics')
    expected = TRIGGERS[definition['table_id']][2]
    for _, _, field, _ in TRIGGERS.values():
        if field is not None and field in row['properties']:
            value = row['properties'][field]
            if field != expected or type(value) not in (int, float) or value != 100:
                raise ValueError('Conflicting facet trade evidence trigger')
    return {'capture': {'item_identity': {'table': 'unique', 'table_id': definition['table_id']}}}


def validate_variant_reviews(policy, identity):
    """A multi-variant review is complete and cannot fall back to a pooled review."""
    from pricing.knowledge.assessment.policies.trade_qualification import validate_review

    variants = policy.get('variant_rules', [])
    if not any('trade_qualification' in variant for variant in variants):
        if 'facet_table_id' in policy.get('trade_qualification', {}):
            raise ValueError('Facet trade review must belong to its native variant')
        return
    if identity != ('unique', 'Rainbow Facet') or policy.get('trade_qualification'):
        raise ValueError('Variant trade reviews cannot mix with a pooled trade review')
    for variant in variants:
        review = variant.get('trade_qualification')
        if not review or variant['table_ids'] != [review.get('facet_table_id')]:
            raise ValueError('Facet trade review must cover each native variant exactly')
        definition_for_review(review)
        validate_review(review, identity, {'all': [policy['valid_if'], variant['valid_if']]})
