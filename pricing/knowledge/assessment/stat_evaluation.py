"""Pure reviewed stat-combination contracts; roll quality and rendering are separate.

No implicit conversion from important_stats: priorities require an explicit review.
This component has no file access and reuses the shared typed predicate evaluator.
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields

from pricing.knowledge.assessment.domain.facts import freeze, thaw
from pricing.knowledge.assessment.domain.roles import RoleAssessment
from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from pricing.knowledge.assessment.stat_targets import target_keys, validate_target


@dataclass(frozen=True)
class StatPriority:
    key: str
    desirability: str
    activation: Mapping
    explanation: str

    def __post_init__(self):
        if self.desirability not in {'desirable', 'supporting'} or not self.explanation.strip():
            raise ValueError('Stat priority requires a reviewed positive meaning and explanation')
        validate_target(self.key)
        validate(thaw(self.activation))
        object.__setattr__(self, 'activation', freeze(self.activation))


@dataclass(frozen=True)
class StatConfiguration:
    id: str
    version: int
    role_id: str
    qualities: tuple[str, ...]
    types: tuple[str, ...]
    required: Mapping
    priorities: tuple[StatPriority, ...]
    source: Mapping
    review_state: str
    rationale: str
    advisory_conditions: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.id or not self.role_id or type(self.version) is not int or self.version < 1:
            raise ValueError('Stat configuration requires versioned identity and role linkage')
        if not self.qualities or not self.types or not self.priorities:
            raise ValueError('Stat configuration requires explicit applicability and priorities')
        if self.review_state not in {'reviewed', 'pending'} or not self.rationale.strip():
            raise ValueError('Stat configuration requires review state and rationale')
        if any(not self.source.get(key) for key in ('path', 'sha256', 'locator')):
            raise ValueError('Stat configuration requires source provenance')
        if isinstance(self.advisory_conditions, str) or any(
            not isinstance(v, str) or not v.strip() for v in self.advisory_conditions
        ):
            raise ValueError('Invalid advisory conditions')
        object.__setattr__(self, 'advisory_conditions', tuple(self.advisory_conditions))
        validate(thaw(self.required))
        for name in ('qualities', 'types', 'required', 'priorities', 'source'):
            object.__setattr__(self, name, freeze(getattr(self, name)))


@dataclass(frozen=True)
class StatEvaluation:
    configurations: tuple[Mapping, ...]
    annotations: Mapping

    def __post_init__(self):
        object.__setattr__(self, 'configurations', freeze(self.configurations))
        object.__setattr__(self, 'annotations', freeze(self.annotations))


class StatsEvaluator:
    def evaluate(self, item, configurations, context=None, *, role_outcomes=()):
        roles = {}
        for original in role_outcomes:
            role = (
                {field.name: getattr(original, field.name) for field in fields(original)}
                if isinstance(original, RoleAssessment)
                else original
            )
            if role['id'] in roles and roles[role['id']] != role:
                raise ValueError(f'Conflicting role outcome: {role["id"]}')
            roles[role['id']] = role
        unique = {}
        for config in configurations:
            if config.id in unique and unique[config.id] != config:
                raise ValueError(f'Conflicting stat configuration: {config.id}')
            unique[config.id] = config
        outcomes, contributions = [], {}
        for config in sorted(unique.values(), key=lambda c: c.id):
            if item.rarity not in config.qualities or item.item_type not in config.types:
                continue
            required = evaluate(thaw(config.required), item, context)
            status = {'true': 'matched', 'false': 'failed', 'unknown': 'unknown', 'not_applicable': 'not_applicable'}[
                required.truth
            ]
            role = roles.get(config.role_id)
            if status == 'matched':
                status = {'matched': 'matched', 'partial': 'conditional', 'failed': 'failed'}.get(
                    role.get('status') if role else None, 'unknown'
                )
            if status == 'conditional' and _only_reviewed_advice(role, config):
                status = 'matched'
            if item.identified is not True or config.review_state != 'reviewed':
                status = 'unknown'
            activations = []
            for priority in config.priorities:
                activation = evaluate(thaw(priority.activation), item, context)
                activations.append(
                    {'key': priority.key, 'trace': activation.to_dict(), 'explanation': priority.explanation}
                )
                for native_key in target_keys(priority.key, item):
                    observed = item.stats.get(native_key)
                    if (
                        status != 'matched'
                        or activation.truth != 'true'
                        or not observed
                        or observed.get('status') != 'decoded'
                    ):
                        continue
                    contributions.setdefault(native_key, []).append(
                        {
                            'configuration_id': config.id,
                            'role_id': config.role_id,
                            'desirability': priority.desirability,
                            'explanation': priority.explanation,
                            'source': config.source,
                        }
                    )
            outcomes.append(
                {
                    'id': config.id,
                    'version': config.version,
                    'role_id': config.role_id,
                    'role': role,
                    'status': status,
                    'required': required.to_dict(),
                    'activations': activations,
                    'source': config.source,
                    'review_state': config.review_state,
                }
            )
        annotations = {
            key: {
                'desirability': 'desirable' if any(c['desirability'] == 'desirable' for c in uses) else 'supporting',
                'configuration_ids': sorted({c['configuration_id'] for c in uses}),
                'contributions': uses,
                'roll_quality': 'unassessed',
            }
            for key, uses in sorted(contributions.items())
        }
        return StatEvaluation(tuple(outcomes), annotations)


def _only_reviewed_advice(role, config):
    """Local combination may pass while explicitly advisory build checks remain."""
    return bool(
        role
        and role.get('missing')
        and config.advisory_conditions
        and set(role['missing']) <= set(config.advisory_conditions)
        and not role.get('failed')
        and (role.get('rule_trace') or {}).get('truth') == 'true'
        and (role.get('skill_trace') is None or role['skill_trace'].get('truth') == 'true')
        and all(d.get('status') == 'true' for d in role.get('dependencies', ()))
        and (role.get('equipment') is None or role['equipment'].get('status') == 'met')
    )
