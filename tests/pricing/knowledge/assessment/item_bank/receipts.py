"""Evidence of executed scenarios, separate from authored-case coverage claims."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class RunReceipt:
    cases: dict
    inputs: dict
    outcomes: dict = field(default_factory=dict)
    generations: set = field(default_factory=set)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def record(self, case_id, phase, outcome, generation):
        if case_id not in self.cases:
            raise ValueError(f'Unknown item-bank case: {case_id}')
        phases = self.outcomes.setdefault(case_id, {})
        if phases.get(phase, 'passed') == 'passed':
            phases[phase] = outcome
        self.generations.add(generation)

    def finish(self, exitstatus, current_inputs):
        passed = sorted(
            case
            for case, phases in self.outcomes.items()
            if all(phases.get(phase) == 'passed' for phase in ('setup', 'call', 'teardown'))
        )
        generation = next(iter(self.generations)) if len(self.generations) == 1 else None
        unchanged = current_inputs == self.inputs
        return {
            'schema_version': 1,
            'started_at': self.started_at,
            'finished_at': datetime.now(UTC).isoformat(),
            'generation': generation,
            'exitstatus': int(exitstatus),
            'sources_unchanged': unchanged,
            'inputs': self.inputs,
            'finished_inputs': current_inputs,
            'cases': {key: {**self.cases[key], 'phases': phases} for key, phases in sorted(self.outcomes.items())},
            'passed_cases': passed,
            'full_bank_passed': bool(self.cases)
            and bool(generation)
            and unchanged
            and exitstatus == 0
            and set(passed) == set(self.cases),
            'unexecuted_cases': sorted(set(self.cases) - self.outcomes.keys()),
            'coverage_note': (
                'Execution evidence only; report/stat completeness and target coverage require separate review.'
            ),
        }
