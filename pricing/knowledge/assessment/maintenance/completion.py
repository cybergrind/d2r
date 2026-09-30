"""Fail-closed completion ledger; checkpoints are never completion evidence."""

import hashlib
import json
from collections import Counter, defaultdict

from pricing.knowledge.assessment.maintenance.coverage_matrix import DIMENSIONS
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.source_matching import (
    occurrence_name_matches,
    occurrence_quality_matches as _occurrence_quality_matches,
)
from pricing.knowledge.refresh import atomic_json


def _indexed(rows):
    result = {row['id']: row for row in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate completion identity')
    return result


def policy_fingerprint():
    """Final attestations cannot survive changed completion or exclusion logic."""
    paths = (
        'completion.py',
        'completion_evidence.py',
        'occurrence_scope.py',
        'non_item_scope.py',
        'carried_cube_reviews.py',
        'cube_narrative_reviews.py',
        'planner_occurrence_links.py',
        'embedded_planner_links.py',
        'armor_planner_links.py',
        'planner_equipment_branch.py',
        'planner_endorsement.py',
        'planner_runeword_endorsement.py',
        'planner_tab_endorsement.py',
        'planner_set_endorsement.py',
        'planner_jewel_endorsement.py',
        'planner_socket_endorsement.py',
        'shared_armor_endorsement.py',
        'cta_swap_endorsement.py',
        'swap_planner_links.py',
        'planner_equipment_quote.py',
        'weapon_component_endorsement.py',
        'weapon_planner_links.py',
        'spirit_planner_links.py',
        'sazabi_loadout_endorsement.py',
        'sazabi_planner_links.py',
        'named_socket_endorsement.py',
        'named_planner_links.py',
        'planner_fcr.py',
        'spirit_loadout_endorsement.py',
        'value_scope.py',
        'evidence_scope.py',
        'value_scope_manifest.py',
        'seasonal_named_audit.py',
        'coverage_matrix.py',
        'pattern_collections.py',
        'named_matrix.py',
        'recipe_applicability.py',
        'base_matrix.py',
        'recipe_eligibility.py',
        'source_context_reviews.py',
        'variant_prose_context.py',
        'variant_mercenary_choices.py',
        'charm_source_context.py',
        'embedded_reviews.py',
        'embedded_dream.py',
        'embedded_dream_prose.py',
        'embedded_hardcore.py',
        'embedded_negative.py',
        'embedded_abyss_recipes.py',
        'embedded_echoing_fade.py',
        'embedded_echoing_malice.py',
        'embedded_echoing_insight.py',
        'merc_survival_templates.py',
        'embedded_echoing_starter.py',
        'embedded_echoing_cure.py',
        'embedded_echoing_enigma.py',
        'embedded_echoing_enchant.py',
        'embedded_echoing_pairing.py',
        'embedded_occurrences.py',
        'hardcore_bounds.py',
        'table_equivalence.py',
        'prose_socket_links.py',
        'structured_variant_mirrors.py',
        'structured_named_variants.py',
        'resistance_armor_links.py',
        'resistance_armor_templates.py',
        'table_cells.py',
        'player_table_context.py',
        'qualified_table_context.py',
        'socketed_table_pattern.py',
        'qualified_equipment_templates.py',
        'named_shield_templates.py',
        'embedded_evidence.py',
        'embedded_items.py',
        'guide_sections.py',
        'mercenary_source_context.py',
        'mercenary_table_context.py',
        'player_utility_context.py',
        'socket_component_context.py',
        'named_prose_context.py',
        'context_values.py',
        'reward_mentions.py',
        'hardcore_mentions.py',
        'utility_source_reviews.py',
        'guide_positions.py',
        '../policies/consumables.py',
        'source_matching.py',
        'guide_demand.py',
        'guide_spans.py',
        'guide_inventory.py',
        'planner_source_audit.py',
        'planner_reachability.py',
        'planner_context_reviews.py',
        'planner_resource_notes.py',
        'inventory.py',
        'review_dossiers.py',
    )
    digest = hashlib.sha256()
    for name in paths:
        digest.update(name.encode())
        digest.update((ROOT / 'pricing/knowledge/assessment/maintenance' / name).read_bytes())
    for name in ('builds.py', 'negative_mentions.py', 'definitions.py'):
        digest.update(('pricing/knowledge/' + name).encode())
        digest.update((ROOT / 'pricing/knowledge' / name).read_bytes())
    return digest.hexdigest()


def scope_fingerprint(
    matrix,
    inventory,
    named_gate,
    profiles,
    uses,
    bases=None,
    bank_coverage=None,
    source_context_reviews=None,
    reward_reviews=None,
    hardcore_reviews=None,
    utility_reviews=None,
    planner_audit=None,
    embedded_reviews=None,
    table_reviews=None,
    value_scope=None,
    carried_cube_reviews=None,
    cube_narrative_reviews=None,
    planner_occurrence_reviews=None,
    embedded_planner_reviews=None,
    armor_planner_reviews=None,
    swap_planner_reviews=None,
    weapon_planner_reviews=None,
    spirit_planner_reviews=None,
    sazabi_planner_reviews=None,
    named_planner_reviews=None,
    value_manifest=None,
    seasonal_audit=None,
):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.verification_scope import verification_inputs

    return fingerprint(
        {
            'completion_policy': policy_fingerprint(),
            'verification_inputs': verification_inputs(ROOT),
            'matrix': matrix,
            'inventory': inventory,
            'named_gate': named_gate,
            'profiles': profiles,
            'uses': uses,
            'bases': bases,
            'bank_coverage': bank_coverage,
            'source_context_reviews': source_context_reviews,
            'reward_reviews': reward_reviews,
            'hardcore_reviews': hardcore_reviews,
            'utility_reviews': utility_reviews,
            'planner_audit': planner_audit,
            'embedded_reviews': embedded_reviews,
            'table_reviews': table_reviews,
            'value_scope': value_scope,
            'carried_cube_reviews': carried_cube_reviews,
            'cube_narrative_reviews': cube_narrative_reviews,
            'planner_occurrence_reviews': planner_occurrence_reviews,
            'embedded_planner_reviews': embedded_planner_reviews,
            'armor_planner_reviews': armor_planner_reviews,
            'swap_planner_reviews': swap_planner_reviews,
            'weapon_planner_reviews': weapon_planner_reviews,
            'spirit_planner_reviews': spirit_planner_reviews,
            'sazabi_planner_reviews': sazabi_planner_reviews,
            'named_planner_reviews': named_planner_reviews,
            'value_manifest': value_manifest,
            'seasonal_audit': seasonal_audit,
        }
    )


def compile_completion(
    matrix,
    inventory,
    named_gate,
    *,
    profiles=None,
    uses=(),
    bases=None,
    bank_coverage=None,
    final_checks=None,
    generation=None,
    source_documents=None,
    source_context_reviews=None,
    source_root=ROOT,
    reward_reviews=None,
    hardcore_reviews=None,
    utility_reviews=None,
    planner_audit=None,
    embedded_reviews=None,
    table_reviews=None,
    value_scope=None,
    carried_cube_reviews=None,
    cube_narrative_reviews=None,
    planner_occurrence_reviews=None,
    embedded_planner_reviews=None,
    armor_planner_reviews=None,
    swap_planner_reviews=None,
    weapon_planner_reviews=None,
    spirit_planner_reviews=None,
    sazabi_planner_reviews=None,
    named_planner_reviews=None,
    value_manifest=None,
    seasonal_audit=None,
):
    """Derive work from evidence, never trust aggregate complete/count fields."""
    identities = _indexed(inventory['identities'])
    rows = _indexed(matrix['rows'])
    occurrences = _indexed(inventory['occurrences'])
    from pricing.knowledge.assessment.maintenance.evidence_scope import evidence_exclusions
    from pricing.knowledge.assessment.maintenance.occurrence_scope import softcore_exclusions
    from pricing.knowledge.assessment.maintenance.value_scope import (
        dimension_exclusions,
        occurrence_exclusions,
        use_exclusions,
    )

    excluded_evidence = evidence_exclusions(matrix['rows'], value_scope, source_root)
    excluded_uses = use_exclusions(profiles or [], value_scope, source_root)
    excluded_dimensions = dimension_exclusions(profiles or [], value_scope, source_root)
    excluded_occurrences = softcore_exclusions(inventory)
    for key, value in occurrence_exclusions(profiles or [], excluded_uses, occurrences.values()).items():
        excluded_occurrences.setdefault(key, value)
    documents = {'inventory': inventory, 'bases': bases or {}, 'profiles': {'profiles': profiles or []}}
    documents.update(source_documents or {})
    if source_context_reviews is not None:
        documents['source_context_reviews'] = source_context_reviews
    if reward_reviews is not None:
        documents['reward_reviews'] = reward_reviews
    if hardcore_reviews is not None:
        documents['hardcore_reviews'] = hardcore_reviews
    if utility_reviews is not None:
        documents['utility_reviews'] = utility_reviews
    if not identities:
        raise ValueError('Empty scope cannot establish completion')
    reviewed_occurrences = set()
    exact_reviewed_occurrences = set()
    partial_patterns = defaultdict(list)
    if profiles is not None:
        from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source
        from pricing.knowledge.assessment.maintenance.review_dossiers import _review_leads, compile_dossiers

        dossiers = compile_dossiers(inventory, profiles, uses)
        for identity in dossiers['identities']:
            for partial in identity.get('partial_pattern_reviews', []):
                for oid in partial['occurrence_ids']:
                    partial_patterns[oid].extend(partial['remaining_branches'])
        reviewed_occurrences = {oid for row in dossiers['identities'] for oid in row['reviewed_pattern_occurrence_ids']}
        by_profile = {row['id']: row for row in profiles}
        eligible = set(_review_leads(list(occurrences.values()))['occurrence_ids'])
        exact_sources = defaultdict(list)
        for row in occurrences.values():
            exact_sources[(row.get('source_id'), row.get('source_locator'))].append(row)
        for use in uses:
            if 'item' not in use or use.get('pattern_component'):
                continue
            role = by_profile[use['profile_id']]
            for row in exact_sources[occurrence_source(use['source'])]:
                if (
                    row['id'] in eligible
                    and row.get('identity_status') == 'resolved'
                    and occurrence_name_matches(row, role, use['item'])
                    and _occurrence_quality_matches(row, role)
                    and role['id'] in row['source_rule_ids']
                    and all(row.get(key) == role.get(key) for key in ('build', 'variant', 'side', 'slot'))
                ):
                    reviewed_occurrences.add(row['id'])
                    exact_reviewed_occurrences.add(row['id'])
    from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews

    context_dispositions = compile_source_context_reviews(
        source_context_reviews, list(occurrences.values()), profiles or [], uses, source_root
    )
    from pricing.knowledge.assessment.maintenance.reward_mentions import compile_reward_mentions

    reward_dispositions = compile_reward_mentions(reward_reviews, list(occurrences.values()), source_root)
    context_ids = {row['occurrence_id'] for row in context_dispositions}
    from pricing.knowledge.assessment.maintenance.hardcore_mentions import compile_hardcore_mentions

    hardcore_dispositions = compile_hardcore_mentions(hardcore_reviews, list(occurrences.values()), source_root)
    for row in [*reward_dispositions, *hardcore_dispositions]:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting source exclusion disposition')
        excluded_occurrences[oid] = row
    pending_contexts = {row['occurrence_id']: row for row in context_dispositions if row['state'] == 'pending'}
    reviewed_occurrences.difference_update(pending_contexts)
    reviewed_occurrences.update(row['occurrence_id'] for row in context_dispositions if row['state'] == 'reviewed')
    from pricing.knowledge.assessment.maintenance.utility_source_reviews import compile_utility_source_reviews

    utility_dispositions = compile_utility_source_reviews(utility_reviews, list(occurrences.values()), source_root)
    for row in utility_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting utility occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    table_dispositions = compile_table_equivalence(
        table_reviews, list(occurrences.values()), profiles or [], uses, source_root
    )
    for row in table_dispositions:
        oid = row['occurrence_id']
        # An independently validated configuration can corroborate an exact
        # named source link. It does not create a second occurrence or override
        # a context, exclusion, utility or pattern disposition.
        if (
            oid in context_ids
            or oid in excluded_occurrences
            or (oid in reviewed_occurrences and oid not in exact_reviewed_occurrences)
        ):
            raise ValueError('Conflicting table equivalence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews, embedded_identity

    embedded_dispositions = compile_embedded_reviews(
        embedded_reviews, inventory.get('embedded_item_links', []), profiles or [], uses, source_root
    )
    from pricing.knowledge.assessment.maintenance.embedded_occurrences import compile_embedded_occurrence_links

    embedded_occurrence_dispositions = compile_embedded_occurrence_links(
        embedded_reviews, embedded_dispositions, list(occurrences.values()), profiles or []
    )
    for row in embedded_occurrence_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting embedded occurrence disposition')
        if row['state'] == 'excluded':
            excluded_occurrences[oid] = row
        else:
            reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.non_item_scope import empty_slot_exclusions

    empty_occurrences, non_item_identities = empty_slot_exclusions(inventory, source_root)
    for key, disposition in empty_occurrences.items():
        if key in context_ids or key in reviewed_occurrences or key in excluded_occurrences:
            raise ValueError('Conflicting empty-slot disposition')
        excluded_occurrences[key] = disposition
    from pricing.knowledge.assessment.maintenance.carried_cube_reviews import compile_carried_cube_reviews

    carried_cube_dispositions = compile_carried_cube_reviews(carried_cube_reviews, inventory, source_root)
    for row in carried_cube_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting carried Cube occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.cube_narrative_reviews import compile_cube_narrative_reviews

    cube_narrative_dispositions = compile_cube_narrative_reviews(cube_narrative_reviews, inventory, source_root)
    for row in cube_narrative_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting Cube narrative occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_planner_occurrence_links

    planner_occurrence_dispositions = compile_planner_occurrence_links(
        planner_occurrence_reviews, table_reviews, table_dispositions, inventory, source_root
    )
    for row in planner_occurrence_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.embedded_planner_links import compile_embedded_planner_links

    embedded_planner_dispositions = compile_embedded_planner_links(
        embedded_planner_reviews, embedded_reviews, embedded_dispositions, inventory, profiles or [], source_root
    )
    for row in embedded_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting embedded planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.armor_planner_links import compile_armor_planner_links

    armor_planner_dispositions = compile_armor_planner_links(
        armor_planner_reviews, inventory, profiles or [], uses, source_root
    )
    for row in armor_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting armor planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.swap_planner_links import compile_swap_planner_links

    swap_planner_dispositions = compile_swap_planner_links(
        swap_planner_reviews, inventory, profiles or [], uses, source_root
    )
    for row in swap_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting swap planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.weapon_planner_links import compile_weapon_planner_links

    weapon_planner_dispositions = compile_weapon_planner_links(
        weapon_planner_reviews, inventory, profiles or [], uses, source_root
    )
    for row in weapon_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting weapon planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.spirit_planner_links import compile_spirit_planner_links

    spirit_planner_dispositions = compile_spirit_planner_links(
        spirit_planner_reviews, inventory, profiles or [], uses, source_root
    )
    for row in spirit_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting Spirit planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.sazabi_planner_links import compile_sazabi_planner_links

    sazabi_planner_dispositions = compile_sazabi_planner_links(
        sazabi_planner_reviews, inventory, profiles or [], uses, source_root
    )
    for row in sazabi_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting Sazabi planner occurrence disposition')
        reviewed_occurrences.add(oid)
    from pricing.knowledge.assessment.maintenance.named_planner_links import compile_named_planner_links

    named_planner_dispositions = compile_named_planner_links(
        named_planner_reviews, inventory, profiles or [], uses, source_root
    )
    for row in named_planner_dispositions:
        oid = row['occurrence_id']
        if oid in context_ids or oid in reviewed_occurrences or oid in excluded_occurrences:
            raise ValueError('Conflicting named planner occurrence disposition')
        reviewed_occurrences.add(oid)
    reviewed_occurrences.difference_update(excluded_occurrences)
    queue = []

    def add(key, dimension, reason, state='pending'):
        queue.append({'id': key, 'dimension': dimension, 'state': state, 'reason': reason})

    if seasonal_audit is not None:
        from pricing.knowledge.assessment.maintenance.seasonal_named_audit import completion_tasks

        queue.extend(completion_tasks(seasonal_audit, source_root))
    elif any(
        source.get('path') == 'pricing/data/appraisal-definitions.json' for source in inventory.get('sources', [])
    ):
        add('seasonal_definition:missing', 'source_review', 'Native seasonal definition audit is missing.', 'blocked')

    expected_manifest = None
    if value_scope is not None:
        from pricing.knowledge.assessment.maintenance.value_scope_manifest import build_manifest

        expected_manifest = build_manifest(
            inventory,
            profiles or [],
            bases,
            value_scope,
            excluded_evidence=excluded_evidence,
            excluded_uses=excluded_uses,
            excluded_occurrences=excluded_occurrences,
            non_item_identities=non_item_identities,
            matrix=matrix,
            seasonal_audit=seasonal_audit,
        )
    manifest_matches = value_manifest is not None and value_manifest == expected_manifest
    if value_scope is not None and (value_scope.get('migration_status') != 'complete' or not manifest_matches):
        add('scope:value-migration', 'scope', 'Value-focused occurrence and item-bank scope migration is incomplete.')

    for identity in identities:
        if 'identity:' + identity not in rows:
            add('identity:' + identity, 'scope', 'Identity missing from coverage matrix.', 'blocked')
    expected = {'base:' + row['id'] for row in _indexed((bases or {}).get('rows', [])).values()}
    expected.update(f'use:{role["id"]}:{quality}' for role in (profiles or []) for quality in role['qualities'])
    for key in sorted(expected - rows.keys()):
        add(key, 'scope', 'Expected base/use quality missing from coverage matrix.', 'blocked')
    for key, row in rows.items():
        if key in excluded_evidence:
            continue
        if key.startswith('identity:') and key.removeprefix('identity:') in non_item_identities:
            if (
                row.get('kind') != 'identity'
                or row.get('category') != 'unresolved'
                or row.get('catalog_ids') != []
                or row.get('name') != 'N/A'
            ):
                raise ValueError('Empty-slot exclusion targets a conflicting coverage row')
            continue
        if key in excluded_uses:
            if row.get('kind') != 'use_quality' or key != f'use:{row.get("profile_id")}:{row.get("quality")}':
                raise ValueError('Scope exclusion targets a conflicting coverage row')
            continue
        dimensions = row.get('dimensions', {})
        for dimension in sorted(set(DIMENSIONS) | set(dimensions)):
            if f'{key}/{dimension}' in excluded_dimensions:
                if row.get('kind') != 'use_quality' or key != f'use:{row.get("profile_id")}:{row.get("quality")}':
                    raise ValueError('Dimension exclusion targets a conflicting coverage row')
                continue
            evidence = dimensions.get(dimension, {})
            state = evidence.get('state', 'pending')
            if state not in {'pending', 'blocked', 'reviewed', 'excluded'}:
                raise ValueError(f'Unknown completion state: {state}')
            if state in {'reviewed', 'excluded'} and evidence.get('sources'):
                from pricing.knowledge.assessment.maintenance.completion_evidence import invalid_reference

                errors = [error for source in evidence['sources'] if (error := invalid_reference(source, documents))]
                if errors:
                    add(f'{key}/{dimension}', dimension, '; '.join(errors), 'blocked')
                    continue
            if state in {'pending', 'blocked'} or not evidence.get('sources') or not evidence.get('reason'):
                add(
                    f'{key}/{dimension}',
                    dimension,
                    evidence.get('reason') or 'Missing reviewed dimension evidence.',
                    state if state in {'pending', 'blocked'} else 'pending',
                )
    for key, occurrence in occurrences.items():
        if occurrence['identity_id'] not in identities:
            raise ValueError('Occurrence references unknown identity')
        # source_rule_ids are candidate provenance links, not semantic reviews.
        # Until an exact occurrence disposition is validated, retain the work.
        if key not in reviewed_occurrences and key not in excluded_occurrences:
            reason = (
                'Remaining source branches: ' + '; '.join(pending_contexts[key]['remaining_branches'])
                if key in pending_contexts
                else 'Remaining preparation branches: ' + '; '.join(sorted(set(partial_patterns[key])))
                if key in partial_patterns
                else 'Exact occurrence disposition needs validation.'
            )
            add('occurrence:' + key, 'source_review', reason)
    reviewed_embedded = {row['id'] for row in embedded_dispositions}
    for link in inventory.get('embedded_item_links', []):
        # Resolution only proves which definition was referenced. Inventory-set
        # membership and a caller-supplied review_state do not prove guide use.
        identity = embedded_identity(link)
        if identity in reviewed_embedded:
            continue
        add(
            'embedded_reference:' + identity,
            'source_review',
            'Exact embedded guide use needs a validated semantic review; planner linkage is discovery evidence.',
        )
    for field, prefix in [('source_conflicts', 'source_conflict'), ('planner_source_gaps', 'planner_gap')]:
        for index, _ in enumerate(inventory.get(field, [])):
            add(f'{prefix}:{index}', 'source_review', 'Required source issue remains unresolved.', 'blocked')
    if planner_audit is not None:
        from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

        if planner_audit.get('schema_version') != 1 or planner_audit.get('inventory_fingerprint') != fingerprint(
            inventory
        ):
            raise ValueError('Stale planner reachability audit')
        for path, expected_hash in planner_audit['source_hashes'].items():
            source = (source_root / path).resolve()
            if (
                not source.is_relative_to(source_root.resolve())
                or hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash
            ):
                raise ValueError('Stale planner reachability source')
        for source, report in planner_audit['planner_reports'].items():
            for index, issue in enumerate(report['issues']):
                add(f'planner_audit:{source}:{index}', 'source_review', json.dumps(issue, sort_keys=True))
        accounted = set(planner_audit['planner_reports']) | {
            issue['source'] for field in ('source_issues', 'unsupported_sources') for issue in planner_audit[field]
        }
        for source in inventory.get('sources', []):
            path = source.get('path', '')
            if (
                '/planners/' in path
                and not path.endswith(('/game-data.json', '/game-strings.json'))
                and path not in accounted
            ):
                add(
                    f'planner_audit:omitted:{path}',
                    'source_review',
                    'Scoped planner omitted from reachability audit.',
                    'blocked',
                )
        for field in ('source_issues', 'guide_issues', 'unsupported_sources', 'missing_planners'):
            for index, issue in enumerate(planner_audit[field]):
                add(f'planner_audit:{field}:{index}', 'source_review', json.dumps(issue, sort_keys=True), 'blocked')
    elif any('/planners/' in source.get('path', '') for source in inventory.get('sources', [])):
        add('planner_audit:missing', 'source_review', 'Planner reachability audit has not run.', 'blocked')
    if named_gate.get('complete') is not True:
        add('final:named_tiers', 'named_tiers', 'Universal named-tier gate has not passed.')
    scope = scope_fingerprint(
        matrix,
        inventory,
        named_gate,
        profiles,
        uses,
        bases,
        bank_coverage,
        source_context_reviews,
        reward_reviews,
        hardcore_reviews,
        utility_reviews,
        planner_audit,
        embedded_reviews,
        table_reviews,
        value_scope,
        carried_cube_reviews,
        cube_narrative_reviews,
        planner_occurrence_reviews,
        embedded_planner_reviews,
        armor_planner_reviews,
        swap_planner_reviews,
        weapon_planner_reviews,
        spirit_planner_reviews,
        sazabi_planner_reviews,
        named_planner_reviews,
        value_manifest,
        seasonal_audit,
    )
    for key in ('verification', 'delivery', 'item_bank'):
        check = (final_checks or {}).get(key, {})
        bank_ready = (
            (bank_coverage or {}).get('case_coverage_complete') is True
            and not (bank_coverage or {}).get('missing')
            and not (bank_coverage or {}).get('orphaned_case_targets')
        )
        if not (
            (key != 'item_bank' or bank_ready)
            and generation
            and check.get('status') == 'passed'
            and check.get('scope') == scope
            and check.get('generation') == generation
            and check.get('evidence')
            and all(row.get('path') and row.get('sha256') for row in check['evidence'])
        ):
            add('final:' + key, key, 'Scope-bound, selected-generation verification pending.')
    queue.sort(key=lambda row: row['id'])
    return {
        'schema_version': 1,
        'scope': scope,
        'generation': generation,
        'complete': not queue,
        'counts': {
            'identities': len(identities),
            'occurrences': len(occurrences),
            'reviewed_occurrences': len(reviewed_occurrences),
            'excluded_occurrences': len(excluded_occurrences),
            'coverage_rows': len(rows),
            'remaining_tasks': len(queue),
        },
        'remaining_by_dimension': dict(sorted(Counter(r['dimension'] for r in queue).items())),
        'queue': queue,
        'dimension_scope_dispositions': [{'id': key, **value} for key, value in sorted(excluded_dimensions.items())],
        'evidence_scope_dispositions': [{'id': key, **value} for key, value in sorted(excluded_evidence.items())],
        'use_scope_dispositions': [{'id': key, **value} for key, value in sorted(excluded_uses.items())],
        'scope_policy': value_scope.get('scope') if value_scope else 'legacy_all_uses',
        'scope_manifest': expected_manifest,
        'scope_manifest_status': 'verified' if manifest_matches else 'missing_or_stale',
        'scope_manifest_counts': expected_manifest['counts'] if expected_manifest else None,
        'occurrence_dispositions': [excluded_occurrences[key] for key in sorted(excluded_occurrences)],
        'non_item_identity_dispositions': [non_item_identities[key] for key in sorted(non_item_identities)],
        'source_context_dispositions': context_dispositions,
        'utility_dispositions': utility_dispositions,
        'embedded_dispositions': embedded_dispositions,
        'embedded_occurrence_dispositions': embedded_occurrence_dispositions,
        'table_dispositions': table_dispositions,
        'carried_cube_dispositions': carried_cube_dispositions,
        'cube_narrative_dispositions': cube_narrative_dispositions,
        'planner_occurrence_dispositions': planner_occurrence_dispositions,
        'embedded_planner_dispositions': embedded_planner_dispositions,
        'armor_planner_dispositions': armor_planner_dispositions,
        'swap_planner_dispositions': swap_planner_dispositions,
        'weapon_planner_dispositions': weapon_planner_dispositions,
        'spirit_planner_dispositions': spirit_planner_dispositions,
        'sazabi_planner_dispositions': sazabi_planner_dispositions,
        'named_planner_dispositions': named_planner_dispositions,
    }


def verify_artifact_inputs(documents, root):
    """Reject mixed/stale snapshots before deriving a completion checkpoint."""
    pins = {}
    for document in documents.values():
        if not isinstance(document, dict):
            continue  # Some pinned rule artifacts are lists with no transitive inputs.
        sources = document.get('sources', {})
        sources = sources.values() if isinstance(sources, dict) else sources
        refs = [(row['path'], row['sha256']) for row in sources if 'path' in row and 'sha256' in row]
        refs.extend(document.get('inputs', {}).items())
        refs.extend(document.get('input_hashes', {}).items())
        for name, digest in refs:
            if name in pins and pins[name] != digest:
                raise ValueError(f'Conflicting completion input: {name}')
            pins[name] = digest
    for name, digest in pins.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f'Missing completion input: {name}')
        if not digest or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Stale completion input: {name}')


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--write-scope-manifest', action='store_true', help='Write derived membership; does not approve migration'
    )
    args = parser.parse_args()
    paths = {
        'matrix': 'pricing/data/appraisal-coverage-matrix.json',
        'bases': 'pricing/data/appraisal-base-matrix.json',
        'bank_coverage': 'pricing/data/appraisal-item-bank-coverage.json',
        'inventory': 'pricing/data/appraisal-guide-inventory.json',
        'named_gate': 'pricing/data/appraisal-named-gate.json',
        'seasonal_audit': 'pricing/data/appraisal-seasonal-named-audit.json',
        'profiles': 'pricing/data/appraisal-build-profiles.json',
        'uses': 'pricing/knowledge/assessment/rules/guide_use_reviews.json',
        'source_context_reviews': 'pricing/knowledge/assessment/rules/source_context_reviews.json',
        'reward_reviews': 'pricing/knowledge/assessment/rules/reward_reviews.json',
        'hardcore_reviews': 'pricing/knowledge/assessment/rules/hardcore_reviews.json',
        'utility_reviews': 'pricing/knowledge/assessment/rules/utility_reviews.json',
        'embedded_reviews': 'pricing/knowledge/assessment/rules/embedded_reviews.json',
        'table_reviews': 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json',
        'planner_audit': 'pricing/data/appraisal-planner-reachability.json',
        'value_scope': 'pricing/knowledge/assessment/rules/value_scope_reviews.json',
        'carried_cube_reviews': 'pricing/knowledge/assessment/rules/carried_cube_reviews.json',
        'cube_narrative_reviews': 'pricing/knowledge/assessment/rules/cube_narrative_reviews.json',
        'planner_occurrence_reviews': 'pricing/knowledge/assessment/rules/planner_occurrence_reviews.json',
        'embedded_planner_reviews': 'pricing/knowledge/assessment/rules/embedded_planner_reviews.json',
        'armor_planner_reviews': 'pricing/knowledge/assessment/rules/armor_planner_reviews.json',
        'swap_planner_reviews': 'pricing/knowledge/assessment/rules/swap_planner_reviews.json',
        'weapon_planner_reviews': 'pricing/knowledge/assessment/rules/weapon_planner_reviews.json',
        'spirit_planner_reviews': 'pricing/knowledge/assessment/rules/spirit_planner_reviews.json',
        'sazabi_planner_reviews': 'pricing/knowledge/assessment/rules/sazabi_planner_reviews.json',
        'named_planner_reviews': 'pricing/knowledge/assessment/rules/named_planner_reviews.json',
    }
    manifest_path = 'pricing/data/appraisal-value-scope-manifest.json'
    if (ROOT / manifest_path).exists():
        paths['value_manifest'] = manifest_path
    raw = {key: (ROOT / path).read_bytes() for key, path in paths.items()}
    docs = {key: json.loads(value) for key, value in raw.items()}
    verify_artifact_inputs(docs, ROOT)
    source_documents = {
        key: json.loads((ROOT / source['path']).read_bytes()) for key, source in docs['matrix']['sources'].items()
    }
    verify_artifact_inputs(source_documents, ROOT)
    docs['profiles'] = docs['profiles']['profiles']
    docs['uses'] = docs['uses']['uses']
    checks_path = ROOT / 'pricing/data/appraisal-completion-checks.json'
    checks = json.loads(checks_path.read_bytes()) if checks_path.exists() else {}
    verify_artifact_inputs({key: {'sources': check.get('evidence', [])} for key, check in checks.items()}, ROOT)
    pointer_path = ROOT / 'pricing/data/generations/current.json'
    pointer = json.loads(pointer_path.read_bytes())
    result = compile_completion(
        **docs, final_checks=checks, generation=pointer['generation'], source_documents=source_documents
    )
    expected_manifest = result.pop('scope_manifest')
    if args.write_scope_manifest:
        if expected_manifest is None:
            raise ValueError('No value policy available for scope manifest')
        atomic_json(ROOT / manifest_path, expected_manifest)
    result['inputs'] = {paths[key]: hashlib.sha256(value).hexdigest() for key, value in raw.items()}
    atomic_json(ROOT / 'pricing/data/appraisal-completion.json', result)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in ('queue', 'occurrence_dispositions')}, indent=2
        )
    )


if __name__ == '__main__':
    main()
