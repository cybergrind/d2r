"""Bind reviewed asking segments to the same native predicates as captured items."""

from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics import waterwalk_defense
from pricing.knowledge.assessment.mechanics.base_tiers import is_base_upgrade
from pricing.knowledge.assessment.mechanics.wisp import listing_absorb
from pricing.knowledge.assessment.policies import (
    draculs_ethereal,
    gore_rider_defense,
    market_ethereal_inference,
    war_traveler_ethereal,
)
from pricing.knowledge.assessment.policies.market_base_inference import MODE, original_base_code
from pricing.knowledge.assessment.policies.trade_base_defense import valid_base_defense
from pricing.knowledge.assessment.policies.trade_choices import valid_reviewed_choice, validate_cohorts
from pricing.knowledge.assessment.policies.trade_class_skills import validate_class_cohorts
from pricing.knowledge.assessment.policies.trade_facets import listing_provenance, valid_rolls
from pricing.knowledge.assessment.policies.trade_rolls import market_mapping, valid_compounds, valid_market_compounds
from pricing.knowledge.assessment.policies.trade_sunder import project_properties
from pricing.knowledge.assessment.roles.predicates import Truth, evaluate
from pricing.knowledge.definition_store import catalog


def listing_definition(item):
    definition, _ = resolve_named_definition(item, identity_only=True)
    if definition is not None:
        return definition
    # A listed named upgraded base is not a captured native table ID. Accept
    # only an unambiguous definition and a verified legal upgrade relationship.
    variants = catalog().named_variants.get((item.rarity, item.name), ())
    if len(variants) == 1 and any(is_base_upgrade(code, item.base_code) for code in variants[0]['base_codes']):
        return variants[0]
    return None


def validate_segments(review, parent_valid_if):
    validate_cohorts(review)
    validate_class_cohorts(review)
    base_inferences = {
        waterwalk_defense.VARIANT_MODE: waterwalk_defense.variant_code,
        MODE: original_base_code,
        gore_rider_defense.MODE: gore_rider_defense.original_code,
        gore_rider_defense.VARIANT_MODE: gore_rider_defense.variant_code,
    }
    if review.get('base_inference') not in (None, *base_inferences):
        raise ValueError('Unsupported trade evidence base inference')
    inferences = {
        waterwalk_defense.VARIANT_MODE: waterwalk_defense.infer_variant,
        market_ethereal_inference.MODE: market_ethereal_inference.arachnid_ethereal,
        war_traveler_ethereal.MODE: war_traveler_ethereal.infer,
        draculs_ethereal.MODE: draculs_ethereal.infer,
        gore_rider_defense.MODE: gore_rider_defense.infer,
        gore_rider_defense.VARIANT_MODE: gore_rider_defense.infer_variant,
    }
    if review.get('ethereal_inference') not in (None, *inferences):
        raise ValueError('Unsupported trade evidence ethereal inference')
    mapping = market_mapping(review)
    validity = {'all': [parent_valid_if, review['valid_if']]}
    expected = {None: set(review['default_evidence_ids'])}
    expected.update({index: set(band['evidence_ids']) for index, band in enumerate(review['bands'])})
    actual = {key: set() for key in expected}
    for row in review['market_evidence']:
        properties = project_properties(review, row, mapping)
        properties = listing_absorb({'policy': 'named', 'rarity': row['rarity'], 'name': row['name']}, row, properties)
        if not valid_market_compounds(review, properties):
            raise ValueError('Ambiguous compound trade evidence representation')
        item = ItemFacts(
            name=row['name'],
            base_name=None,
            base_code=(
                base_inferences[review['base_inference']](row)
                if review.get('base_inference') in base_inferences
                else row.get('base_code')
            ),
            item_type=None,
            rarity=row['rarity'],
            runeword=None,
            identified=True,
            ethereal=(
                inferences[review['ethereal_inference']](row)
                if review.get('ethereal_inference') in inferences
                else row.get('ethereal')
            ),
            sockets=row.get('sockets'),
            socket_contents=row.get('socket_contents'),
            socket_items=(),
            gaps=(),
            capture_complete=False,
            provenance=listing_provenance(review, row),
            stats={
                key: {'status': 'decoded', 'value': properties[prop]}
                for key, prop in mapping.items()
                if prop in properties
            },
        )
        if (
            listing_definition(item) is None
            or not valid_rolls(review, item)
            or evaluate(validity, item).truth != Truth.TRUE
            or not valid_compounds(review, item, market_properties=properties)
            or not valid_base_defense(review, item, market_properties=properties)
            or not valid_reviewed_choice(review, item, market_properties=properties)
        ):
            raise ValueError('Unverified trade evidence variant or material roll')
        matched = None
        for index, band in enumerate(review['bands']):
            truth = evaluate(band['when'], item).truth
            if truth == Truth.UNKNOWN:
                raise ValueError('Unknown trade evidence band membership')
            if truth == Truth.TRUE:
                matched = index
                break
        actual[matched].add(row['id'])
    if actual != expected:
        raise ValueError('Trade evidence does not match reviewed trade bands')
