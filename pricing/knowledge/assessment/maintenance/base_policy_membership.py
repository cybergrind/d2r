"""Runtime-equivalent routing over partial catalog facts; never a keep decision."""

from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.roles.candidates import CandidateIndex
from pricing.knowledge.assessment.roles.predicates import evaluate


class BasePolicyMembership:
    def __init__(self, profiles):
        self.index = CandidateIndex([p for p in profiles if not p.get('names')])

    def assignments(self, code, base, quality):
        facts = catalog_facts(code, base, quality)
        rows = []
        for profile in self.index.select(facts):
            trace = evaluate(profile['must'], facts) if profile.get('must') is not None else None
            rows.append(
                {
                    'profile_id': profile['id'],
                    'profile_fingerprint': fingerprint(profile),
                    'source': profile.get('source'),
                    'guard_truth': trace.truth.value if trace else 'true',
                    'guard_trace': trace.to_dict() if trace else None,
                    'scope': 'Catalog routing only; item rolls, flags, sockets and loadout remain unknown.',
                }
            )
        return sorted(rows, key=lambda row: row['profile_id'])


def catalog_facts(code, base, quality):
    return ItemFacts(
        name=base['name'],
        base_name=base['name'],
        base_code=code,
        item_type=base.get('type'),
        rarity=quality,
        runeword=None,
        identified=None,
        ethereal=None,
        sockets=None,
        socket_contents=None,
        socket_items=[],
        capture_complete=False,
    )
