"""Compatibility serialization of typed roles; contains no assessment logic."""

from dataclasses import fields

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.domain.roles import RoleAssessment


def legacy_role(result: RoleAssessment):
    return {field.name: thaw(getattr(result, field.name)) for field in fields(result)}


def legacy_roles(results):
    return [legacy_role(result) for result in results]


def ethereal_role_input(result: RoleAssessment):
    """Small policy view; do not serialize traces, rolls or preparation evidence."""
    return {
        name: getattr(result, name)
        for name in ('id', 'build', 'variant', 'side', 'role', 'source', 'status', 'ethereal_preference')
    }
