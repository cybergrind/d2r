# Local reference repositories

Checked out 2026-09-23. These are shallow Git checkouts of the external repositories
referenced by the inventory-tracking research. `repos.json` records exact origins,
commits and branches. Checkouts are ignored by the parent repository; this guide
and manifest are retained. No external code was installed or executed.

Use local sources first. These repositories describe different game versions;
validate offsets and interpretations against our supported build and captures.
The d2go, Koolo and MapAssist directories use the accessible forks already cited
by the research notes. The original hectorgimenez repositories are unavailable.

| Checkout | Purpose | Commit |
| --- | --- | --- |
| [d2go](d2go/) | D2R memory layouts and stat readers; accessible fork | `1fb1e7a6569f` |
| [D2MOO](D2MOO/) | Reconstructed legacy stat/item algorithms | `5596f5cb6c52` |
| [d2data](d2data/) | D2R static item, stat and skill tables | `fc469993502d` |
| [diablo2utils](diablo2utils/) | Linux memory structures and signatures | `b7dcd531e737` |
| [MapAssist](MapAssist/) | C# item/stat readers and overlay; accessible fork | `c503b29d014d` |
| [D2R-AutoPotion-Go](D2R-AutoPotion-Go/) | Potion watcher and d2go lineage | `e1d1e6e424db` |
| [koolo](koolo/) | Health/belt/recovery policies; accessible fork | `91a04550a546` |
| [d2r-mapview](d2r-mapview/) | AutoHotkey memory and HUD reference | `50131a765183` |
| [botty](botty/) | Visual health-bar cross-check | `22ab86b3877e` |
| [d2bs](d2bs/) | Legacy client APIs and item/stat logic | `f4b99bbe8de6` |
| [d2rmanager-cartographer-wanderer](d2rmanager-cartographer-wanderer/) | HUD documentation reference | `390698dc775f` |
| [D2tools](D2tools/) | Rust ReadMem reference | `ea6939b2fa7c` |
| [niri](niri/) | Compositor IPC, focus and binding contracts | `5f4469b6a992` |

Search ignored checkouts explicitly, for example:

```sh
rg --no-config --no-ignore -n 'getItemStats' third-parties/d2go/pkg/memory
rg --no-config --no-ignore -n 'dwFileIndex' third-parties/D2MOO/source
```

To reproduce a checkout, use the URL and commit from `repos.json`. Existing
checkouts are not updated automatically. When updating deliberately, record the
new commit in the manifest; source evidence may depend on the older revision.
Shallow history can be extended with `git -C third-parties/<name> fetch --unshallow`
when historical source is needed. Runtime appraisal continues to use our bundled
metadata, not a changing external checkout.
