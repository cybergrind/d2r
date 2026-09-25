"""Precompiled selector postings; predicates still decide actual role fit."""

from pricing.knowledge.assessment.domain.facts import freeze, thaw


class CandidateIndex:
    def __init__(self, profiles):
        self._profiles = freeze(profiles)
        self._all = frozenset(range(len(profiles)))
        postings = {}
        for field in ('qualities', 'types', 'names'):
            entries = {}
            for position, profile in enumerate(profiles):
                for value in profile.get(field) or (None,):
                    entries.setdefault(value, set()).add(position)
            postings[field] = {value: frozenset(ids) for value, ids in entries.items()}
        self._postings = freeze(postings)

    def select(self, facts):
        candidates = self._all
        for field, value in [('qualities', facts.rarity), ('types', facts.item_type), ('names', facts.name)]:
            if value is None:
                continue
            entries = self._postings[field]
            candidates = candidates & (entries.get(value, frozenset()) | entries.get(None, frozenset()))
        return [thaw(self._profiles[position]) for position in sorted(candidates)]
