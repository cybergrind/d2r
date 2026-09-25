"""Evaluate reviewed profiles; guide mentions alone never become executable rules."""

from pricing.knowledge.assessment.adapters.roles import legacy_roles
from pricing.knowledge.assessment.build_profiles import OUTPUT
from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.domain.roles import RoleAssessment
from pricing.knowledge.assessment.mechanics.equipment import assess_requirements
from pricing.knowledge.assessment.mechanics.upgrades import upgrade_paths
from pricing.knowledge.assessment.repository import ProfileRepository
from pricing.knowledge.assessment.roles.predicates import Truth, evaluate, native_keys, validate
from pricing.knowledge.assessment.roles.preparation import dependency_upgrade, describe_upgrade
from pricing.knowledge.assessment.roles.socket_payload import has_verified_socket_item


_repository = ProfileRepository(OUTPUT)


def profile_snapshot():
    return _repository.snapshot()


def load_profiles():
    loaded = _repository.load()
    if loaded.bundle is None:
        return [], list(loaded.issues)
    return thaw(loaded.bundle.profiles), [loaded.bundle.scope, *loaded.issues]


def load_candidates(facts):
    loaded = _repository.load()
    if loaded.bundle is None:
        return [], list(loaded.issues)
    return loaded.bundle.candidates.select(facts), [loaded.bundle.scope, *loaded.issues]


def load_stat_candidates(facts):
    from pricing.knowledge.assessment.stat_bundle import configuration_from_row

    loaded = _repository.load()
    if loaded.bundle is None:
        return ()
    return tuple(configuration_from_row(row) for row in loaded.bundle.stat_candidates.select(facts))


def validate_profiles(profiles):
    from inventory_tracking.items.metadata import metadata

    catalog = metadata()
    types = {b['type'] for b in catalog['bases'].values()}
    ids = set()
    for profile in profiles:
        if profile['id'] in ids or (not profile.get('names') and not profile.get('types')):
            raise ValueError('Duplicate or unscoped build profile')
        ids.add(profile['id'])
        socket_keys = [key for key in ('required_rune', 'required_socket_item') if key in profile]
        if len(socket_keys) > 1 or any(
            not isinstance(profile[key], str) or not profile[key].strip() for key in socket_keys
        ):
            raise ValueError('Profile requires one nonempty socket item name')
        equipment = profile.get('equipment')
        if equipment is not None:
            if not isinstance(equipment, dict) or set(equipment) != {'requirements', 'applies_if'}:
                raise ValueError('Equipment policy requires requirements and applicability')
            requirements = equipment['requirements']
            if (
                not isinstance(requirements, dict)
                or set(requirements) != {'level', 'strength', 'dexterity'}
                or any(type(value) is not int or value < 0 for value in requirements.values())
            ):
                raise ValueError('Invalid equipment requirements')
            validate(equipment['applies_if'])
        if profile.get('must') is not None:
            validate(profile['must'])
        for preference in [*profile.get('preferences', []), *profile.get('depends_on', [])]:
            if not isinstance(preference.get('label'), str) or not preference['label']:
                raise ValueError('Preference or dependency requires a readable label')
            validate(preference['when'])
        if profile.get('review_status') not in ('reviewed_candidate_rule', 'reviewed_setup'):
            raise ValueError('Profile is not reviewed for execution')
        if set(profile.get('types', [])) - types:
            raise ValueError('Unknown item type in build profile')
        if not profile['source'].get('locator') or not profile['source'].get('sha256'):
            raise ValueError('Profile source provenance missing')
        for key in [
            *profile.get('required_any_stats', []),
            *profile.get('important_stats', []),
            *native_keys(profile.get('must', {})),
            *native_keys(profile.get('equipment', {}).get('applies_if', {})),
            *(
                key
                for pref in [*profile.get('preferences', []), *profile.get('depends_on', [])]
                for key in native_keys(pref['when'])
            ),
        ]:
            stat, parameter = key.split(':')
            if stat not in catalog['stats'] or int(parameter) < 0:
                raise ValueError('Unknown native stat in profile')
            if int(parameter) and not catalog['stats'][stat].get('parameter_bits'):
                raise ValueError('Unexpected native stat parameter')
            if stat == '204' and str(int(parameter) >> 6) not in catalog['skills']:
                raise ValueError('Unknown charged skill in profile')
            if stat in ('97', '107', '151') and parameter not in catalog['skills']:
                raise ValueError('Unknown skill in profile')


def assess_roles(facts, profiles, loadout=None, *, upgrades=None):
    return legacy_roles(assess_role_results(facts, profiles, loadout, upgrades=upgrades))


def assess_role_results(facts, profiles, loadout=None, *, upgrades=None):
    loadout = AssessmentContext.from_input(loadout)
    upgrades = upgrade_paths(facts) if upgrades is None else upgrades
    roles = []
    for p in profiles:
        if facts.rarity is not None and facts.rarity not in p['qualities']:
            continue
        if p.get('types') and facts.item_type is not None and facts.item_type not in p['types']:
            continue
        if p.get('names') and facts.name is not None and facts.name not in p['names']:
            continue
        matched, missing, failed = [], [], []
        for selector, value in [('qualities', facts.rarity), ('types', facts.item_type), ('names', facts.name)]:
            if p.get(selector) and value is None:
                missing.append(f'Role selector {selector} is unknown.')
        keys = p.get('required_any_stats', [])
        skill_requirement = (
            {'any': [{'op': 'stat_at_least', 'key': key, 'value': 1, 'absent_is_zero': True} for key in keys]}
            if keys
            else None
        )
        trace = evaluate(p['must'], facts, loadout) if p.get('must') is not None else None
        if trace and p['must'] != skill_requirement:
            if trace.truth == Truth.FALSE:
                failed.append('Required role properties are not satisfied.')
            elif trace.truth != Truth.TRUE:
                missing.append('Required role properties are not fully known.')
            else:
                matched.append('Required role properties are satisfied.')
        skill_trace = (
            trace
            if trace is not None and p['must'] == skill_requirement
            else evaluate(skill_requirement, facts, loadout)
            if skill_requirement
            else None
        )
        if skill_trace:
            if skill_trace.truth == Truth.TRUE:
                labels = [
                    facts.stats[key].get('text') or f'Native skill bonus {key}'
                    for key, child in zip(keys, skill_trace.children, strict=True)
                    if child.truth == Truth.TRUE
                ]
                matched.append('Relevant skill bonus: ' + ', '.join(labels))
            elif skill_trace.truth == Truth.FALSE:
                failed.append('No captured bonus to the skills used by this role.')
            else:
                missing.append('Relevant skill bonuses are not fully known.')
        can_prepare = facts.identified is True and not failed and not missing
        if p.get('names') and facts.name:
            matched.append('Named setup component: ' + facts.name)
        socket_item = p.get('required_socket_item', p.get('required_rune'))
        if socket_item:
            if has_verified_socket_item(facts, socket_item):
                matched.append('Setup socket: ' + socket_item)
            else:
                missing.append('Setup socket requires ' + socket_item + '; not confirmed on this item.')
        if p.get('companions'):
            needed = set(p['companions']) - set(loadout.mercenary_items or ())
            if needed:
                missing.append('Set companions not confirmed: ' + ', '.join(sorted(needed)))
            if loadout.mercenary_type != p['mercenary_type']:
                missing.append('Mercenary type not confirmed: ' + p['mercenary_type'])
        dependencies = []
        for dependency in p.get('depends_on', []):
            result = evaluate(dependency['when'], facts, loadout)
            dependencies.append(
                {
                    'label': dependency['label'],
                    'status': result.truth,
                    'trace': result.to_dict(),
                }
            )
            if result.truth == Truth.TRUE:
                matched.append(dependency['label'])
            elif result.truth == Truth.FALSE:
                preparation = dependency_upgrade(dependency['when'], upgrades) if can_prepare else None
                if preparation:
                    dependencies[-1]['preparation'] = preparation.to_dict()
                    missing.append(describe_upgrade(preparation))
                else:
                    missing.append('Setup requires: ' + dependency['label'])
            else:
                missing.append('Not confirmed: ' + dependency['label'])
        equipment = None
        if p.get('equipment'):
            applies = evaluate(p['equipment']['applies_if'], facts, loadout)
            requirements = p['equipment']['requirements'] if applies.truth == Truth.TRUE else {}
            equipment = assess_requirements(requirements, p['side'], loadout)
            equipment['applicability'] = applies.to_dict()
            if equipment['status'] == 'met':
                matched.append('Known equipment requirements are met.')
            elif equipment['status'] == 'unmet':
                missing.extend(equipment['shortfalls'])
            else:
                missing.append('Equipment requirements or wearer attributes need verification.')
        missing.extend(p.get('conditions', []))
        roles.append(
            RoleAssessment(
                **{
                    **{k: p[k] for k in ('id', 'build', 'variant', 'side', 'slot', 'role', 'review_status', 'source')},
                    'status': 'unknown'
                    if facts.identified is not True
                    else 'failed'
                    if failed
                    else 'partial'
                    if missing
                    else 'matched',
                    'rule_trace': trace.to_dict() if trace else None,
                    'skill_trace': skill_trace.to_dict() if skill_trace else None,
                    'dependencies': dependencies,
                    'equipment': equipment,
                    'ethereal_preference': p.get('ethereal_preference'),
                    'preferences': [
                        {'label': pref['label'], 'status': evaluate(pref['when'], facts, loadout).truth}
                        for pref in p.get('preferences', [])
                    ],
                    'matched': matched,
                    'missing': missing,
                    'failed': failed,
                    'important_rolls': [facts.stats[k] for k in p.get('important_stats', []) if k in facts.stats],
                    'alternatives': p.get('alternatives', []),
                }
            )
        )
    return tuple(roles)
