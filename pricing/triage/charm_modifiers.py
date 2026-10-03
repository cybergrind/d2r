"""Comparable skiller suffixes: omitted numeric affixes differ from present rolls."""

# Tree IDs verified against WP-H bucket_def and cached Traderie property labels.
TREES = frozenset(
    [
        '443',
        '444',
        '445',
        '516',
        '517',
        '515',
        '408',
        '410',
        '409',
        '456',
        '454',
        '500',
        '499',
        '501',
        '406',
        '405',
        '404',
        '487',
        '485',
        '486',
        '1547',
        '1548',
        '1546',
    ]
)
# Scope, quality, required level, ethereal/socket metadata are not charm suffixes.
METADATA = frozenset(['799', '800', '798', '1854', '797', '796', '738', '402', '934'])


def suffix(name, properties):
    if name != 'Grand Charm':
        return None
    return {
        key: value
        for key, value in sorted(properties.items())
        if key not in TREES | METADATA and type(value) in (int, float) and value != 0
    }
