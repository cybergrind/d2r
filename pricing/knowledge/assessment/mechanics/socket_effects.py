"""Verified fixed socket effects shared by utility and comparison policies."""

# Pinned gems.json helm/shield effects; names resolve to codes through metadata.
RESIST_RUNES = {'Ral Rune': 39, 'Ort Rune': 41, 'Thul Rune': 43, 'Tal Rune': 45}
DIAMONDS = dict(
    zip(
        ('Chipped Diamond', 'Flawed Diamond', 'Diamond', 'Flawless Diamond', 'Perfect Diamond'),
        (6, 8, 11, 14, 19),
        strict=True,
    )
)
RUBIES = dict(
    zip(('Chipped Ruby', 'Flawed Ruby', 'Ruby', 'Flawless Ruby', 'Perfect Ruby'), (10, 17, 24, 31, 38), strict=True)
)
BOOLEAN_SOCKET_STATS = frozenset({152, 153})
