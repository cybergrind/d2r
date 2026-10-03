"""Conservative, offline proof of a recoverable JMOD shell in market records.

This is evidence preparation, not an appraisal or an empty-shield price rule.
The reviewed table snapshot has only 0/15/30 intrinsic shield FBR and socket
increments of 20 (Shael); jewels cannot supply FBR. Thus exactly 30 requires
Deflecting. Four magic sockets require Jeweler's, consuming the prefix. With
those affixes established, all possible socket defense contributions are
nonnegative. An ethereal Monarch starts above 148 defense, so an explicit total
in 133..148 proves nonethereal. The proof deliberately does not cover higher
totals, additional block/FBR from inserts, or the ambiguously labeled field 399.

Pin the complete reviewed native tables: a new jewel or affix can invalidate
this arithmetic even if the familiar Jeweler's/Deflecting rows stay unchanged.
"""

from pricing.knowledge.assessment.mechanics.socket_evidence import (
    NATIVE_HASHES as NATIVE_HASHES,
    reviewed_native,
)


def shell_evidence(row, root, read=None):
    """Return variant evidence without mutating a listing or pricing its payload."""
    props = row.get('properties', {})
    ethereal = row.get('ethereal')
    if (
        (row.get('name'), row.get('base_code'), row.get('rarity')) != ('Monarch', 'uit', 'magic')
        or type(row.get('sockets')) is not int
        or row['sockets'] != 4
        or not (ethereal is None or ethereal is False)
        or not (props.get('738') is None or props['738'] is False)
        or props.get('797') not in (None, 'magic')
        or any(type(props.get(k)) is not int or props[k] != v for k, v in {'402': 4, '449': 30, '446': 20}.items())
        or type(props.get('1855')) is not int
        or not 133 <= props['1855'] <= 148
        or not reviewed_native(root, read)
    ):
        return None
    return {
        'identity': "Jeweler's Monarch of Deflecting",
        'ethereal': False,
        'ethereal_basis': 'explicit_total_defense',
        'socket_contents': row.get('socket_contents', 'unknown'),
        'scope': 'recoverable_shell_only',
        'price_eligible': False,
    }
