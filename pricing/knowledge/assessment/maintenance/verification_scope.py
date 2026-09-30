"""Bind final verification to executable sources, test fixtures and dependencies."""

import hashlib


CACHE_DIRECTORIES = frozenset({'__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache'})
RUNTIME_SUFFIXES = frozenset({'.py', '.json', '.html', '.js', '.css', '.sh'})
GENERATED_DIRECTORIES = frozenset({'pricing/data', 'pricing/raw', 'inventory_tracking/runs'})


def verification_inputs(root):
    """Keep generated KB/publication outputs out; their manifests are pinned separately.

    Read current bytes rather than trusting timestamps or an old file inventory, so
    additions and removals invalidate the attestation too.
    """
    files = {}
    for name in ('pricing', 'inventory_tracking', 'tests'):
        directory = root / name
        if not directory.is_dir():
            raise ValueError(f'Missing verification source directory: {name}')
        for parent, directories, names in directory.walk():
            directories[:] = sorted(
                child
                for child in directories
                if child not in CACHE_DIRECTORIES
                and (parent / child).relative_to(root).as_posix() not in GENERATED_DIRECTORIES
            )
            for filename in sorted(names):
                path = parent / filename
                if path.suffix in ('.pyc', '.pyo'):
                    continue
                if name != 'tests' and path.suffix not in RUNTIME_SUFFIXES:
                    continue
                files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('pyproject.toml', 'uv.lock'):
        path = root / name
        if not path.is_file():
            raise ValueError(f'Missing verification dependency input: {name}')
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if (root / 'Makefile').is_file():
        files['Makefile'] = hashlib.sha256((root / 'Makefile').read_bytes()).hexdigest()
    return dict(sorted(files.items()))
