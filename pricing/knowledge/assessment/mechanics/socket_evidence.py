"""Reviewed native snapshot for removable socket contents and armor contributions."""

import hashlib


NATIVE_HASHES = {
    'armor': 'ad8d490abd48b336ac22f605904202fe5132460f91e3b307d9006753b9cb0271',
    'magicprefix': '9e7c42d608768e7f1dd1332345a258e4d5e4347ff48a16e8f9d1e974db39787d',
    'magicsuffix': 'd7060a8a19c2772747f0cd5d82b1571a774f953789d3ade1f7cac426df97e415',
    'gems': '8471e44185164052f2fe3564ad00519055450641c84e4a7830894d82be945670',
    'uniqueitems': 'e6f28489942a6145d99190728071c0e7557313239517bb03c627d3d41bbad8e7',
    'cubemain': '0b3deb18f4b1605e72a11a8d72e8ce73f1fbd662546d2a875d182be9b70b53e8',
    'itemtypes': 'cbfc6d0abdddb20ae0fa9f50e07a072fd075967c5fff5e6455bcf93be922d3ae',
    'properties': '49fa7e80b7c889bb4fec0a4d75a165200b3812f77806e4f66c14e5ee4b8b6c34',
}


def reviewed_native(root, read=None):
    read = read or (lambda path: path.read_bytes())
    try:
        return all(
            hashlib.sha256(read(root / 'third-parties/d2data/json' / f'{name}.json')).hexdigest() == digest
            for name, digest in NATIVE_HASHES.items()
        )
    except OSError:
        return False
