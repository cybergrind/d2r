"""Semantic checks for bundled runtime inputs before use or pointer promotion."""

import hashlib
import json

from inventory_tracking.items.metadata import metadata
from pricing.knowledge import definition_store
from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment import base_use
from pricing.knowledge.assessment.adapters import market_projection
from pricing.knowledge.assessment.build_profiles import OUTPUT
from pricing.knowledge.assessment.mechanics import base_tiers
from pricing.knowledge.assessment.policies import generic_leveling, leveling, named_tiers
from pricing.knowledge.assessment.policies.sources import source_error
from pricing.knowledge.assessment.profile_sources import validate_profile_sources
from pricing.knowledge.assessment.repository import ProfileRepository
from pricing.knowledge.assessment.roles.predicates import native_keys
from pricing.knowledge.named_upgrades import named_upgrade_variants


def validate_definition_metadata(definitions, item_metadata, base_catalog):
    if definitions.get('inputs') != item_metadata.get('provenance', {}).get('identities'):
        raise ValueError('Definition/metadata source generations differ')
    expected_identities = {kind: {} for kind in ('set', 'unique', 'runeword')}
    expected_affixes = {kind: {} for kind in ('prefix', 'suffix', 'auto')}
    for row in definitions['rows']:
        if row.get('affix_table'):
            expected_affixes[row['affix_table']][str(row['table_id'])] = row
        elif row.get('table_id') is not None:
            expected_identities[row['rarity']][str(row['table_id'])] = row
    actual = {
        kind: {key: {k: v for k, v in row.items() if k != 'upgrade_variants'} for key, row in entries.items()}
        for kind, entries in item_metadata.get('identities', {}).items()
    }
    if actual != expected_identities:
        raise ValueError('Compiled metadata identity content differs from definitions')
    bases = {}
    for row in base_catalog['rows']:
        if not row.get('base_code'):
            continue
        details = row.get('details', {})
        defense = details.get('base_defense', [None, None])
        base = {
            'normcode': details.get('normal_code'),
            'ubercode': details.get('exceptional_code'),
            'ultracode': details.get('elite_code'),
            'minac': defense[0],
            'maxac': defense[1],
        }
        code = row['base_code']
        if code in bases and bases[code] != base:
            raise ValueError(f'Conflicting upgrade base catalog entry: {code}')
        bases[code] = base
    for quality in ('unique', 'set'):
        for identifier, row in expected_identities[quality].items():
            actual_variants = item_metadata['identities'][quality][identifier].get('upgrade_variants')
            if actual_variants != named_upgrade_variants(row, bases):
                raise ValueError(f'Compiled upgrade metadata differs from base catalog: {row["name"]}')
    if item_metadata.get('affixes') != expected_affixes:
        raise ValueError('Compiled metadata affixes differ from definitions')
    for field in ('affix_pools', 'staffmods', 'rare_names'):
        if item_metadata.get(field) != definitions.get(field):
            raise ValueError(f'Compiled metadata {field} differs from definitions')
    superior = {r['category']: r for r in definitions['rows'] if r['kind'] == 'quality_definition'}
    if item_metadata.get('superior') != superior:
        raise ValueError('Compiled superior metadata differs from definitions')
    for field in (
        'crafting_bases',
        'crafting_nonethereal',
        'crafting_triggers',
        'crafting_affix_only_cold',
        'crafting_affix_only_poison',
    ):
        if item_metadata.get(field) != definitions.get(field):
            raise ValueError(f'Compiled {field} metadata differs from definitions')


def validate_runtime_inputs():
    """Run inside a supplied artifact/definition/metadata snapshot; no live reads."""
    definitions = json.loads(read_artifact(definition_store.STORE.path))
    item_metadata = metadata()
    validate_definition_metadata(definitions, item_metadata, json.loads(read_artifact(base_tiers.CATALOG)))
    profiles = ProfileRepository(OUTPUT).load()
    if profiles.bundle is None or profiles.issues:
        raise ValueError(f'Invalid published profiles: {profiles.issues}')
    validate_profile_sources(json.loads(read_artifact(OUTPUT)), named_tiers.ROOT, read_artifact)
    from pricing.knowledge.assessment.guide_demand import validate_demand

    validate_demand(json.loads(read_artifact(OUTPUT)))
    from pricing.knowledge.assessment.stat_bundle import validate_stat_bundle

    validate_stat_bundle(json.loads(read_artifact(OUTPUT)))
    # Publication checks must not inherit an earlier generation's validation cache.
    policies = named_tiers._policies.__wrapped__(read_artifact(named_tiers.RULES))
    for identity, policy in policies.items():
        if error := source_error(policy['source'], identity, named_tiers.ROOT):
            raise ValueError(f'Invalid named tier source {identity}: {error}')
        predicates = [policy['valid_if'], *(r['when'] for r in policy['overrides'])]
        for predicate in predicates:
            for key in native_keys(predicate):
                stat, parameter = key.split(':')
                spec = item_metadata['stats'].get(stat)
                if spec is None or (int(parameter) and not spec.get('parameter_bits')):
                    raise ValueError(f'Invalid named tier native stat: {key}')
    market_projection.compiled_properties.__wrapped__(read_artifact(market_projection.CATALOG))
    base_use._recipes.__wrapped__(read_artifact(base_use.UTILITY))
    base_tiers._tiers.__wrapped__(read_artifact(base_tiers.CATALOG))
    leveling._load.__wrapped__(
        read_artifact(leveling.DATA / 'appraisal-recommendations.json'),
        read_artifact(leveling.DATA / 'appraisal-item-facts.json'),
    )
    if hashlib.sha256(read_artifact(generic_leveling.SOURCE)).hexdigest() != generic_leveling.SOURCE_SHA256:
        raise ValueError('Generic leveling evidence requires review')
    return {'profiles': len(profiles.bundle.profiles), 'named_policies': len(policies)}
