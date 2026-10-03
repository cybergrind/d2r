"""Trade-qualification coverage backed by published rules and executed reports.

Named jewelry, charms and Colossal Jewels have separate native base scopes.
Scalar scopes share integer boundary proofs. Compound scopes explicitly opt into
verified shared rolls; Small Charms can carry independent attribute/resistance axes.
"""

from datetime import date
from math import isfinite
from pathlib import PurePosixPath

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import (
    trade_arachnid,
    trade_arachnid_evidence,
    trade_choice_evidence,
    trade_crown,
    trade_draculs,
    trade_draculs_evidence,
    trade_equipment_evidence,
    trade_facets,
    trade_fixed_armor,
    trade_gore_rider,
    trade_gore_rider_evidence,
    trade_ik_components,
    trade_normal_belt,
    trade_opalvein,
    trade_partial_evidence,
    trade_scalar_jewelry,
    trade_shako,
    trade_stormshield,
    trade_tal_belt,
    trade_titan,
    trade_titan_evidence,
    trade_torch,
    trade_torch_evidence,
    trade_trek,
    trade_war_traveler,
    trade_war_traveler_evidence,
    trade_waterwalk,
    trade_waterwalk_evidence,
)
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.trade_review_cases import (
    LEGAL,
    REQUIRED,
    executed_cases,
    variant_predicate,
)


RECEIPT_ROOT = PurePosixPath('pricing/data/report-receipts')
ARMOR_SCOPES = {'fixed_set_armor': trade_fixed_armor, 'original_set_mf': trade_tal_belt}
CHOICE_SCOPES = {'choice_named_jewelry'}
EQUIPMENT_SCOPES = {'ethereal_unique_boots'}
TITAN_SCOPES = {'ethereal_unique_javelin'}
TORCH_SCOPES = {'native_torch_classes'}
ARACHNID_SCOPES = {'native_unique_caster_belt'}
WAR_TRAVELER_SCOPES = {'native_unique_mf_boots'}
GORE_RIDER_SCOPES = {'native_unique_combat_boots'}
WATERWALK_SCOPES = {'native_unique_waterwalk'}
DRACULS_SCOPES = {'native_unique_lifetap_gloves'}
NATIVE_SCOPES = {
    'native_unique_waterwalk': trade_waterwalk,
    'native_unique_crown_shell': trade_crown,
    **ARMOR_SCOPES,
    'native_fixed_ik_component': trade_ik_components,
    'native_fixed_normal_belt': trade_normal_belt,
    'choice_named_jewelry': trade_opalvein,
    'ethereal_unique_boots': trade_trek,
    'ethereal_unique_javelin': trade_titan,
    'native_unique_caster_belt': trade_arachnid,
    'native_unique_mf_boots': trade_war_traveler,
    'native_unique_combat_boots': trade_gore_rider,
    'native_unique_lifetap_gloves': trade_draculs,
    'native_unique_underlying_shako': trade_shako,
    'native_unique_underlying_stormshield': trade_stormshield,
    'native_facet_variants': trade_facets,
    'native_torch_classes': trade_torch,
}
SCALAR_SCOPES = {
    'scalar_named_jewelry': ('Ring', 'Amulet'),
    'scalar_colossal_jewel': ('Colossal Jewel',),
    'scalar_named_charm': ('Grand Charm',),
}
PARTIAL_SCOPES = {'partial_scalar_named_jewelry', 'partial_compound_named_jewelry'}
INTEGER_SCOPES = {
    'partial_scalar_named_jewelry': ('Ring', 'Amulet'),
    'partial_compound_named_jewelry': ('Ring', 'Amulet'),
    **SCALAR_SCOPES,
    'compound_colossal_jewel': ('Colossal Jewel',),
    'compound_named_jewelry': ('Ring', 'Amulet'),
    'compound_named_charm': ('Small Charm',),
    'base_defense_set_boots': ('Mirrored Boots',),
    'total_defense_set_belt': ('Troll Belt',),
}


def fixed_definition(variants):
    if len(variants) != 1:
        return None
    definition = variants[0]
    if (
        definition.get('base_name') not in {'Ring', 'Amulet'}
        or not definition.get('roll_ranges')
        or any(
            type(r.get('min')) not in (int, float) or not isfinite(r['min']) or r['min'] != r.get('max')
            for r in definition['roll_ranges'].values()
        )
        or any(
            definition.get(k)
            for k in (
                'base_defense_range',
                'native_socket_range',
                'variable_per_level_effects',
                'property_groups',
            )
        )
    ):
        return None
    return definition


def _fixed_case_gap(cases, policy):
    seen = set()
    trade = policy['trade_qualification']
    for _item, checks, signature in cases:
        seen.add(signature)
        status = 'candidate' if signature == LEGAL else 'unresolved'
        expected = {'status': status, **({'material_stats': []} if status == 'candidate' else {})}
        lines = []
        if status == 'candidate':
            lines = [
                {'text': 'Trade: candidate — ' + trade['default_reason'], 'tone': 'tier_' + policy['default_tier']}
            ]
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Trade verdict and rendered text/color are not explicitly asserted.'
    if not seen >= REQUIRED:
        return 'Legal, impossible and unknown variant boundaries are not all executed.'
    return None


def _gap(review, policy, variants, receipt, generation, inputs, stat_specs, partial_evidence):
    if policy is None or review['policy_fingerprint'] != fingerprint(policy):
        return 'Missing or changed published trade policy.'
    if review['definition_fingerprint'] != fingerprint(thaw(variants)):
        return 'Changed published native definition.'
    trade = policy.get('trade_qualification', {})
    native_reviewer = NATIVE_SCOPES.get(review['scope'])
    native_spec = native_reviewer.specification(policy, variants, stat_specs or {}) if native_reviewer else None
    integer_rolls = review['scope'] in INTEGER_SCOPES
    spec = (
        trade_scalar_jewelry.specification(
            policy,
            variants,
            stat_specs,
            allowed_bases=INTEGER_SCOPES[review['scope']],
            compounds={
                'compound_colossal_jewel': ('enhanced_damage',),
                'compound_named_jewelry': ('all_resistances',),
                'partial_compound_named_jewelry': ('all_resistances',),
                'compound_named_charm': ('all_attributes', 'all_resistances'),
            }.get(review['scope'], ()),
            base_defense=review['scope'] == 'base_defense_set_boots',
            total_defense=review['scope'] == 'total_defense_set_belt',
            allow_unknown_default=review['scope'] in PARTIAL_SCOPES,
        )
        if integer_rolls
        else None
    )
    definition = (
        (native_spec['definition'] if native_spec else None)
        if native_reviewer
        else (spec[0] if spec else fixed_definition(variants) if not integer_rolls else None)
    )
    if definition is None or (
        not integer_rolls
        and not native_spec
        and (
            trade.get('material_stats') != []
            or trade.get('bands') != []
            or trade.get('default_status') != 'candidate'
            or policy.get('overrides')
            or policy.get('variant_rules')
            or not variant_predicate(policy['valid_if'])
            or not variant_predicate(trade['valid_if'])
        )
    ):
        return 'This review cannot establish coverage for these roll or conditional trade rules.'
    if review['scope'] in CHOICE_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_choice_evidence.reviewed_choices(evidence, tuple(trade.get('choice_keys', ())))
        ):
            return 'Unreviewed native choices lack current source-bound independent-seller evidence.'
    if review['scope'] in EQUIPMENT_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_equipment_evidence.reviewed_variants(evidence)
        ):
            return 'Equipment variants lack current source-bound independent-seller evidence.'
    if review['scope'] in TITAN_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_titan_evidence.reviewed_variants(evidence)
        ):
            return 'Javelin base variants lack current source-bound independent-seller evidence.'
    if review['scope'] in ARACHNID_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_arachnid_evidence.reviewed_variants(evidence)
        ):
            return 'Arachnid roll regions lack current source-bound independent-seller evidence.'
    if review['scope'] in WAR_TRAVELER_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_war_traveler_evidence.reviewed(evidence)
        ):
            return 'War Traveler roll regions lack current source-bound asking evidence.'
    if review['scope'] in GORE_RIDER_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_gore_rider_evidence.reviewed(evidence)
        ):
            return 'Gore Rider original and upgraded cohorts lack current source-bound asking evidence.'
    if review['scope'] in WATERWALK_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_waterwalk_evidence.reviewed(evidence)
        ):
            return 'Waterwalk cohorts lack current source-bound asking evidence or contain an unreviewed dense cohort.'
    if review['scope'] in DRACULS_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_draculs_evidence.reviewed(evidence)
        ):
            return 'Dracul leech cohorts lack current source-bound asking evidence.'
    if review['scope'] in TORCH_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not trade_torch_evidence.reviewed_classes(evidence, native_spec['classes'])
        ):
            return 'Torch classes lack current source-bound independent-seller evidence.'
    reviewed_unknowns = frozenset()
    if review['scope'] in PARTIAL_SCOPES:
        evidence = partial_evidence.get((review['quality'], review['name']), {})
        if (
            review.get('unresolved_evidence_fingerprint') != fingerprint(evidence)
            or evidence.get('market_snapshot') != trade.get('market_snapshot')
            or not (
                reviewed_unknowns := trade_partial_evidence.reviewed_vectors(
                    evidence, spec[1], tuple(trade.get('compound_stats', ()))
                )
            )
        ):
            return 'Unknown roll regions lack current, thin, source-bound market evidence.'
    if not receipt or receipt.get('schema_version') != 1:
        return 'Missing trade execution receipt.'
    if not generation or receipt.get('generation') != generation:
        return 'Trade receipt does not verify the selected generation.'
    if (
        receipt.get('exitstatus') != 0
        or receipt.get('sources_unchanged') is not True
        or receipt.get('inputs') != inputs
        or receipt.get('finished_inputs') != inputs
    ):
        return 'Trade execution failed or verification sources changed.'
    cases, gap = executed_cases(
        review,
        receipt,
        definition,
        additional_bases=(
            native_spec.get(
                'additional_bases', (native_spec['upgraded_base'],) if 'upgraded_base' in native_spec else ()
            )
            if native_spec
            else ()
        ),
        allowed_variants=native_spec.get('variants', REQUIRED) if native_spec else REQUIRED,
    )
    if gap:
        return gap
    if native_spec:
        return native_reviewer.case_gap(cases, policy, native_spec)
    return (
        trade_scalar_jewelry.case_gap(cases, policy, spec, reviewed_unknowns=reviewed_unknowns)
        if integer_rolls
        else _fixed_case_gap(cases, policy)
    )


def review_dimensions(
    document, policies, definitions, receipts, generation, inputs, stat_specs=None, partial_evidence=None
):
    """Use policies/definitions validated within the selected published snapshot."""
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported trade review schema')
    rows, accepted = {}, set()
    for index, review in enumerate(document['rows']):
        identity = (review['quality'], review['name'])
        if identity in rows or review.get('scope') not in {'fixed_named_jewelry', *NATIVE_SCOPES, *INTEGER_SCOPES}:
            raise ValueError('Duplicate or unsupported trade review scope')
        path = PurePosixPath(review['receipt'])
        if path.is_absolute() or '..' in path.parts or not path.is_relative_to(RECEIPT_ROOT):
            raise ValueError('Trade receipt escapes the report receipt directory')
        date.fromisoformat(review['review_date'])
        if not review.get('reason') or not isinstance(review.get('cases'), dict) or not review['cases']:
            raise ValueError('Trade review requires a rationale and explicit cases')
        gap = _gap(
            review,
            policies.get(identity),
            definitions.get(identity, ()),
            receipts.get(str(path)),
            generation,
            inputs,
            stat_specs,
            partial_evidence or {},
        )
        source = {'artifact': 'trade_reviews', 'locator': f'/rows/{index}'}
        if gap is None:
            accepted.add(str(path))
            source.update(receipt=str(path), generation=generation)
        rows[identity] = {
            'state': 'pending' if gap else 'reviewed',
            'reason': gap or review['reason'],
            'sources': [source],
        }
    return rows, accepted


def apply_trade_reviews(rows, document, **context):
    dimensions, accepted = review_dimensions(document, **context)
    targets = {}
    for row in rows:
        if row['kind'] == 'identity':
            key = (row['category'], row['name'])
            if key in targets:
                raise ValueError('Ambiguous trade-review identity row')
            targets[key] = row
    if dimensions.keys() - targets.keys():
        raise ValueError('Trade review addresses a missing coverage identity')
    for identity, dimension in dimensions.items():
        targets[identity]['dimensions']['trade_qualification'] = dimension
    return accepted


def load_context(root, document):
    """Read rule/definition inputs from one immutable published generation."""
    import json

    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.maintenance.verification_scope import verification_inputs
    from pricing.knowledge.assessment.policies.named_tiers import _policies
    from pricing.knowledge.assessment.policies.sources import source_error
    from pricing.knowledge.definition_store import catalog
    from pricing.knowledge.publication import current_generation
    from pricing.knowledge.published_runtime import load_runtime, published_snapshot

    selected = current_generation(root / 'pricing/data/generations')
    with published_snapshot(load_runtime(selected)):
        raw = selected.artifact('pricing/knowledge/assessment/rules/named_tiers.json').read_bytes()
        policies = dict(_policies(raw))
        definitions = {key: thaw(value) for key, value in catalog().named_variants.items()}
        stat_specs = thaw(metadata()['stats'])
        for review in document['rows']:
            identity = (review['quality'], review['name'])
            policy = policies.get(identity)
            if policy and source_error(policy['source'], identity, root):
                policies.pop(identity)
            elif policy and review['scope'] == 'native_unique_underlying_shako':
                policies[identity] = trade_shako.bind_policy(policy)
            elif policy and review['scope'] == 'native_unique_underlying_stormshield':
                policies[identity] = trade_stormshield.bind_policy(policy)
            elif policy and review['scope'] == 'native_unique_crown_shell':
                policies[identity] = trade_crown.bind_policy(policy)
    receipts = {}
    for review in document['rows']:
        path = (root / review['receipt']).resolve()
        if not path.is_relative_to((root / str(RECEIPT_ROOT)).resolve()):
            raise ValueError('Trade receipt escapes the report receipt directory')
        if path.is_file():
            receipts[review['receipt']] = json.loads(path.read_bytes())
    return {
        'policies': policies,
        'definitions': definitions,
        'stat_specs': stat_specs,
        'partial_evidence': {
            **trade_waterwalk_evidence.load_evidence(root, document, policies, WATERWALK_SCOPES),
            **trade_partial_evidence.load_evidence(root, document, policies, PARTIAL_SCOPES),
            **trade_choice_evidence.load_evidence(root, document, policies, CHOICE_SCOPES),
            **trade_equipment_evidence.load_evidence(root, document, policies, EQUIPMENT_SCOPES),
            **trade_titan_evidence.load_evidence(root, document, policies, TITAN_SCOPES),
            **trade_torch_evidence.load_evidence(root, document, policies, TORCH_SCOPES),
            **trade_arachnid_evidence.load_evidence(root, document, policies, ARACHNID_SCOPES, definitions),
            **trade_war_traveler_evidence.load_evidence(root, document, policies, WAR_TRAVELER_SCOPES),
            **trade_gore_rider_evidence.load_evidence(root, document, policies, GORE_RIDER_SCOPES),
            **trade_draculs_evidence.load_evidence(root, document, policies, DRACULS_SCOPES),
        },
        'receipts': receipts,
        'generation': selected.generation,
        'inputs': verification_inputs(root),
    }


def validate_published_reviews(matrix, source_documents, generation, inputs, root):
    reviewed_rows = [
        r for r in matrix['rows'] if r['dimensions'].get('trade_qualification', {}).get('state') == 'reviewed'
    ]
    document = source_documents.get('trade_reviews')
    if document is None:
        if reviewed_rows:
            raise ValueError('Unattested trade qualification coverage')
        if matrix.get('trade_receipts'):
            raise ValueError('Missing trade-review source')
        return
    context = load_context(root, document)
    if context['generation'] != generation or context['inputs'] != inputs:
        raise ValueError('Trade verification snapshot changed during completion')
    context['receipts'] = {path: source_documents.get('receipt:' + path) for path in matrix.get('trade_receipts', [])}
    dimensions, accepted = review_dimensions(document, **context)
    if any(r['kind'] != 'identity' or (r['category'], r['name']) not in dimensions for r in reviewed_rows):
        raise ValueError('Unattested trade qualification coverage')
    if accepted != set(matrix.get('trade_receipts', [])):
        raise ValueError('Stale trade execution evidence; rebuild the coverage matrix')
    targets = {(r['category'], r['name']): r['dimensions'] for r in matrix['rows'] if r['kind'] == 'identity'}
    for identity, dimension in dimensions.items():
        actual = targets.get(identity, {}).get('trade_qualification')
        if (dimension['state'] == 'reviewed' or (actual or {}).get('state') == 'reviewed') and actual != dimension:
            raise ValueError('Changed trade qualification dimension; rebuild the coverage matrix')
