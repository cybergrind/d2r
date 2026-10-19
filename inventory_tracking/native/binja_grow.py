"""Bring an open Binary Ninja database of D2R-decrypted.exe up to the file as `make grow` left it.

A .bndb keeps its own copy of the file's bytes, so reopening it does not show the code pages that
grow.py has decrypted since. This writes those pages into the open view: the names, types, comments
and prototypes already in the database stay, and only what lies on the changed pages is analysed again.

In Binary Ninja, with the D2R view in front, in the Python console:

    exec(open('/mnt/extra/1000/games/d2r/inventory_tracking/native/binja_grow.py').read())

It only reads the file on disk and writes to the view in front (`bv`). Save the database afterwards
(a copy of the .bndb beforehand costs nothing but disk). Run it again after every `make grow`.
"""

from pathlib import Path


GROWN = Path('/mnt/extra/1000/games/d2r/pricing/raw/re/D2R-decrypted.exe')
BASE = 0x140000000
TEXT_FILE, TEXT_SIZE, TEXT_RVA = 0x400, 0x15CB800, 0x1000  # as native/grow.py has them
PAGE = 0x1000
DONE = 'ai_d2_grown_pages'  # the database's own note of the pages analysed again


def grow(view, grown: bytes) -> list[int]:
    """Write every code page that differs from `grown` into `view`; the addresses of the pages written."""
    changed = []
    for offset in range(0, TEXT_SIZE, PAGE):
        address = BASE + TEXT_RVA + offset
        page = grown[TEXT_FILE + offset : TEXT_FILE + offset + min(PAGE, TEXT_SIZE - offset)]
        held = view.read(address, len(page))
        # The section's last page is shorter in memory than in the file (the file pads it): only what the
        # view holds there is compared and written (0x1415cc000, 2026-10-13).
        page = page[: len(held)]
        if page and held != page:
            if view.write(address, page) != len(page):
                raise OSError(f'{address:#x}: the page could not be written')
            changed.append(address)
    return changed


def written(view) -> list[int]:
    """The code pages whose bytes the database holds changed from the file it was made of: every page
    this script ever wrote, whether or not the run that wrote it came to its end."""
    found = []
    for offset in range(0, TEXT_SIZE, PAGE):
        address = BASE + TEXT_RVA + offset
        if any(int(status) != 0 for status in view.get_modification(address, PAGE)):
            found.append(address)
    return found


def done(view) -> set[int]:
    """The pages already analysed again by an earlier run (kept in the database)."""
    try:
        return set(view.query_metadata(DONE))
    except KeyError:
        return set()


def runs(pages: list[int]) -> list[tuple[int, int]]:
    """The pages as address ranges, for the eye."""
    found: list[tuple[int, int]] = []
    for page in pages:
        if found and found[-1][1] == page:
            found[-1] = (found[-1][0], page + PAGE)
        else:
            found.append((page, page + PAGE))
    return found


def again(view, pages: list[int]) -> tuple[int, int]:
    """Analyse again what lies on the pages: the functions that begin there, and a function at every
    named address there that has none yet (a routine named while its page was still encrypted).
    (functions asked again, functions made)."""
    held = set(pages)
    asked = made = 0
    for function in list(view.functions):
        if function.start & ~(PAGE - 1) in held:
            function.reanalyze()
            asked += 1
    for symbol in view.get_symbols():
        address = symbol.address
        named = symbol.name.startswith('ai_d2_') and 'Function' in str(symbol.type)
        on_page = address & ~(PAGE - 1) in held and view.is_offset_executable(address)
        if named and on_page and view.get_function_at(address) is None:
            view.add_function(address)
            made += 1
    view.update_analysis()
    return asked, made


def main(view) -> None:
    if not GROWN.exists():
        print(f'{GROWN} is not there')
        return
    grown = GROWN.read_bytes()
    if view.read(BASE, 2) != b'MZ' or view.start != BASE:
        print('The view in front is not D2R-decrypted.exe mapped at 0x140000000: nothing done')
        return
    fresh = grow(view, grown)
    before = done(view)
    pages = [page for page in written(view) if page not in before]  # also those of a run that broke off
    if not pages:
        print('The database already holds every page of the file, each analysed again: nothing to do')
        return
    asked, made = again(view, pages)
    view.store_metadata(DONE, sorted(before | set(pages)))
    print(
        f'{len(fresh)} pages written now, {len(pages)} to analyse again: '
        f'{asked} functions analysed again, {made} functions made at named addresses'
    )
    for start, end in runs(pages):
        print(f'  {start:#x}-{end:#x}')
    print('Analysis is running; save the database when it has settled.')


main(bv)  # ruff: ignore[undefined-name]  # pyrefly: ignore[unknown-name]  (the console's view in front)
