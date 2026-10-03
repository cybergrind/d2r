"""RotW stack widget: captured native getter returns widget + 0x608 directly."""

from inventory_tracking.items.metadata import item_base


ITEM_POINTER = 0x608


def material_widget(widget, base):
    return widget.get('vtable') == base + 0x1712F88 and widget.get('methods', {}).get('0xc0') == base + 0x220B60


def validate_material_item(item, widget):
    details = item['details']
    definition = item_base(item['txt_id']) or {}
    code = widget[0x20:0x30].split(b'\0', 1)[0]
    if definition.get('code', '').encode('ascii') != code or details.get('x') != 0 or details.get('y') != 0:
        raise ValueError('Material widget item mismatch')
