"""Farming attention policy, separate from the full assessment of possible uses."""

from inventory_tracking.appraisal.sections import build_name


# Reviewed progression labels used by the role corpus. Match whole labels, not
# words in a role name or guide prose (a Budget role may mention Starter).
STARTER_PROGRESSIONS = frozenset(
    {'before spirit', 'starter', 'starter alternative', 'early', 'foh starter', 'holy bolt starter'}
)


def progression_for(role, result):
    presentation = (result.get('guide_demand') or {}).get('role_presentation', {})
    return presentation.get(role['id'], {}).get('progression') or role.get('variant', '')


def starter_only(role, result):
    return progression_for(role, result).strip().casefold() in STARTER_PROGRESSIONS


def actionable_roles(result):
    """Starter use alone is quiet; conditional use also needs positive evidence.

    Keep the original roles intact for Alt+D. Price, value-watch and reviewed
    leveling evidence are independent reasons handled by the caller.
    """
    return [
        role
        for role in result.get('assessment', {}).get('roles', [])
        if not starter_only(role, result)
        and (
            role['status'] == 'matched' or (role['status'] == 'partial' and role.get('matched') and role.get('missing'))
        )
    ]


def role_reason(roles, result, *, conditional=False):
    role = roles[0]
    more = f' +{len(roles) - 1}' if len(roles) > 1 else ''
    stage = progression_for(role, result)
    context = f' [{stage}]' if stage else ''
    label = 'possible' if conditional else 'build use'
    reason = f'{label}: {build_name(role["build"])} {role["side"]} {role["role"]}{context}{more}'
    if conditional:
        reason += '; needs review: ' + '; '.join(dict.fromkeys(role['missing']))
    return reason
