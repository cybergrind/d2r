"""Project unconditional set extras for the existing named-effect compilers.

D2MOO ItemMods.cpp PROPMODE_SET applies extra properties as ordinary modifiers
when add func is zero. Modes 1/2 use conditional set states instead. The original
game record remains untouched for provenance and conditional-set assessment.
"""

PROPERTY_SLOTS = 12


def has_partial_enhanced_defense(record):
    """Dormant ac% still fixes original base armor to maxac+1 at creation.

    ItemMods.cpp PROPMODE_SET invokes PropertyFunc02 for partial properties;
    its base-armor mutation does not depend on the property's active state.
    This says nothing about upgraded armor, whose base is rerolled.
    """
    return any(record.get(f'aprop{number}{suffix}') == 'ac%' for number in range(1, 6) for suffix in ('a', 'b'))


def extra_properties_are_unconditional(record):
    mode = record.get('add func', 0)
    return type(mode) is int and mode == 0


def standalone_set_record(record):
    projected = dict(record)
    if not extra_properties_are_unconditional(record):
        return projected
    available = iter(slot for slot in range(1, PROPERTY_SLOTS + 1) if not record.get(f'prop{slot}'))
    for number in range(1, 6):
        for suffix in ('a', 'b'):
            source = f'{number}{suffix}'
            if not record.get('aprop' + source):
                continue
            slot = next(available, None)
            if slot is None:
                raise ValueError('Unconditional set properties exceed named compiler capacity')
            for field in ('prop', 'min', 'max', 'par'):
                target, origin = f'{field}{slot}', 'a' + field + source
                projected.pop(target, None)
                projected.pop(origin, None)
                if origin in record:
                    projected[target] = record[origin]
    return projected
