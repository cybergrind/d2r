"""Nonethereal Harlequin Crest evidence independent of inserted-item value.

The reviewed native Shako starts at 98 defense and has no intrinsic enhanced,
flat or level-scaled defense. Ethereal base defense therefore starts at 147;
the reviewed rune, gem and jewel effects cannot reduce it. An explicit total
of 98..141 proves nonethereal, even with unknown sockets. It does not prove
the unmodified base roll: a socket addition could be part of that total.
"""

from pricing.knowledge.assessment.mechanics.socket_evidence import reviewed_native


def shell_evidence(row, root, read=None):
    props = row.get('properties', {})
    ethereal, sockets = row.get('ethereal'), row.get('sockets')
    if (
        (row.get('rarity'), row.get('name'), row.get('base_code')) != ('unique', 'Harlequin Crest', 'uap')
        or not (ethereal is None or ethereal is False)
        or not (row.get('base_upgrade') is None or row['base_upgrade'] is False)
        or not (sockets is None or (type(sockets) is int and sockets in (0, 1)))
        or not (props.get('738') is None or props['738'] is False)
        or not (props.get('1216') is None or props['1216'] is False)
        or props.get('930') not in (None, 'Elite')
        or props.get('797') not in (None, 'unique')
        or ('402' in props and (type(props['402']) is not int or props['402'] not in (0, 1)))
        or (sockets is not None and '402' in props and props['402'] != sockets)
        or (row.get('socket_contents') == 'filled' and (sockets == 0 or props.get('402') == 0))
        or type(props.get('1855')) is not int
        or not 98 <= props['1855'] <= 141
        or not reviewed_native(root, read)
    ):
        return None
    return {
        'identity': 'Harlequin Crest',
        'ethereal': False,
        'ethereal_basis': 'explicit_total_defense',
        'sockets': sockets,
        'socket_contents': row.get('socket_contents', 'unknown'),
        'scope': 'underlying_item_only',
        'intrinsic_defense_proved': False,
        'price_eligible': False,
    }
