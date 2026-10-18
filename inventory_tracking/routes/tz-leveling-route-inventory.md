# Terror Zone route inventory (2026-10-18)

Generated from `terror/zones.py` and the route catalogue. Each row is an eligible group level, not proof that the client currently terrorizes it. The client service's current list must confirm the individual level before selection. `needs-played-check` means its route and waypoint exist in data but its transitions and target have not been verified for this loop. `unavailable` names a missing capability. No row is enabled for unattended travel yet; the first playable slice requires one selected route's played check.

The five TZ levels outside Herald groups (Forgotten Tower, Valley of Snakes, Harem Level 1, Duriel's Lair, Worldstone Chamber) need a separate TZ list audit before an `all` itinerary can include them. A locked player waypoint can make any listed route unavailable at runtime. Target `—` means this area's script has no attached boss or chest; the route may target one farther on.

| TZ group | ID | Level | Route | Entry waypoint ID | Entry | Attached target | Exit | Status |
| --- | ---: | --- | --- | ---: | --- | --- | --- | --- |
| Blood Moor | 2 | Blood Moor | Den of Evil | 1 | route entry needs played check | — | enter Den of Evil | needs-played-check |
| Cold Plains | 3 | Cold Plains | Cave | 3 | waypoint 3 | — | enter Cave | needs-played-check |
| Stony Field and Tristram | 4 | Stony Field | Tristram | 4 | waypoint 4 | — | use Tristram | needs-played-check |
| Dark Wood | 5 | Dark Wood | Underground Passage | 5 | waypoint 5 | — | enter Underground Passage | needs-played-check |
| Black Marsh | 6 | Black Marsh | Countess | 6 | waypoint 6 | — | enter Forgotten Tower | needs-played-check |
| Tamoe Highland and Outer Cloister | 7 | Tamoe Highland | Pit | 27 | enter Tamoe Highland | — | enter Pit | needs-played-check |
| Den of Evil | 8 | Den of Evil | Den of Evil | 1 | enter Den of Evil | boss | leave | needs-played-check |
| Cave levels | 9 | Cave Level 1 | Cave | 3 | enter Cave | boss | enter Next level | needs-played-check |
| Underground Passage levels | 10 | Underground Passage Level 1 | Underground Passage | 5 | enter Underground Passage | — | enter Level 2 | needs-played-check |
| Hole levels | 11 | Hole Level 1 | Hole | 6 | enter Hole 1 | — | enter Next level | needs-played-check |
| Pit levels | 12 | Pit Level 1 | Pit | 27 | enter Pit | — | enter Next level | needs-played-check |
| Cave levels | 13 | Cave Level 2 | Cave | 3 | enter Next level | chest | leave | needs-played-check |
| Underground Passage levels | 14 | Underground Passage Level 2 | Underground Passage | 5 | enter Level 2 | chest | leave | needs-played-check |
| Hole levels | 15 | Hole Level 2 | Hole | 6 | enter Next level | chest | leave | needs-played-check |
| Pit levels | 16 | Pit Level 2 | Pit | 27 | enter Next level | chest | leave | needs-played-check |
| Burial Grounds, Crypt and Mausoleum | 17 | Burial Grounds | Mausoleum | 3 | enter Burial Grounds | boss | enter Mausoleum | needs-played-check |
| Burial Grounds, Crypt and Mausoleum | 18 | Crypt | Crypt | 3 | enter Crypt | boss | leave | needs-played-check |
| Burial Grounds, Crypt and Mausoleum | 19 | Mausoleum | Mausoleum | 3 | enter Mausoleum | chest | leave | needs-played-check |
| Tower Cellar levels | 21 | Tower Cellar Level 1 | Countess | 6 | enter Tower Cellar 1 | — | enter Next level | needs-played-check |
| Tower Cellar levels | 22 | Tower Cellar Level 2 | Countess | 6 | enter Next level | — | enter Next level | needs-played-check |
| Tower Cellar levels | 23 | Tower Cellar Level 3 | Countess | 6 | enter Next level | — | enter Next level | needs-played-check |
| Tower Cellar levels | 24 | Tower Cellar Level 4 | Countess | 6 | enter Next level | — | enter Next level | needs-played-check |
| Tower Cellar levels | 25 | Tower Cellar Level 5 | Countess | 6 | enter Next level | boss | leave | needs-played-check |
| Tamoe Highland and Outer Cloister | 26 | Monastery Gate | Pit | 27 | enter Monastery Gate | — | enter Tamoe Highland | needs-played-check |
| Tamoe Highland and Outer Cloister | 27 | Outer Cloister | Pit | 27 | waypoint 27 | — | enter Monastery Gate | needs-played-check |
| Barracks | 28 | Barracks | Andariel | 27 | enter Barracks | — | enter Next level | needs-played-check |
| Jail levels | 29 | Jail Level 1 | Andariel | 27 | enter Next level | — | enter Next level | needs-played-check |
| Jail levels | 30 | Jail Level 2 | Andariel | 27 | enter Next level | — | enter Next level | needs-played-check |
| Jail levels | 31 | Jail Level 3 | Andariel | 27 | enter Next level | — | enter Inner Cloister | needs-played-check |
| Inner Cloister, Cathedral and Catacombs | 32 | Inner Cloister | Andariel | 27 | enter Inner Cloister | — | enter Cathedral | needs-played-check |
| Inner Cloister, Cathedral and Catacombs | 33 | Cathedral | Andariel | 27 | enter Cathedral | — | enter Catacombs 1 | needs-played-check |
| Inner Cloister, Cathedral and Catacombs | 34 | Catacombs Level 1 | Andariel | 27 | enter Catacombs 1 | — | enter Next level | needs-played-check |
| Inner Cloister, Cathedral and Catacombs | 35 | Catacombs Level 2 | Andariel | 27 | enter Next level | — | enter Next level | needs-played-check |
| Inner Cloister, Cathedral and Catacombs | 36 | Catacombs Level 3 | Andariel | 27 | enter Next level | — | enter Next level | needs-played-check |
| Inner Cloister, Cathedral and Catacombs | 37 | Catacombs Level 4 | Andariel | 27 | enter Next level | boss | leave | needs-played-check |
| Stony Field and Tristram | 38 | Tristram | Tristram | 4 | use Tristram | — | leave | needs-played-check |
| Cow Level | 39 | Moo Moo Farm | Cow Level | 1 | route entry needs played check | — | leave | needs-played-check |
| Rocky Waste | 41 | Rocky Waste | Stony Tomb | 40 | route entry needs played check | — | enter Stony Tomb | needs-played-check |
| Dry Hills | 42 | Dry Hills | Halls of the Dead | 42 | waypoint 42 | — | enter Halls of the Dead | needs-played-check |
| Far Oasis | 43 | Far Oasis | Maggot Lair | 43 | waypoint 43 | — | enter Maggot Lair | needs-played-check |
| Lost City | 44 | Lost City | Ancient Tunnels | 44 | waypoint 44 | — | enter Ancient Tunnels | needs-played-check |
| Canyon of the Magi | 46 | Canyon of the Magi | Tal Rasha's Tombs | 46 | back to Canyon of the Magi | — | leave | needs-played-check |
| Lut Gholein Sewer levels | 47 | Sewers Level 1 | Radament | 40 | route entry needs played check | — | enter Next level | needs-played-check |
| Lut Gholein Sewer levels | 48 | Sewers Level 2 | Radament | 40 | enter Next level | — | enter Next level | needs-played-check |
| Lut Gholein Sewer levels | 49 | Sewers Level 3 | Radament | 40 | enter Next level | boss | leave | needs-played-check |
| Harem Level 2 | 51 | Harem Level 2 | Summoner | 40 | enter Harem 2 | — | enter Palace Cellar 1 | needs-played-check |
| Palace Cellar levels | 52 | Palace Cellar Level 1 | Summoner | 40 | enter Palace Cellar 1 | — | enter Palace Cellar 2 | needs-played-check |
| Palace Cellar levels | 53 | Palace Cellar Level 2 | Summoner | 40 | enter Palace Cellar 2 | — | enter Palace Cellar 3 | needs-played-check |
| Palace Cellar levels | 54 | Palace Cellar Level 3 | Summoner | 40 | enter Palace Cellar 3 | — | use Arcane Sanctuary | needs-played-check |
| Stony Tomb levels | 55 | Stony Tomb Level 1 | Stony Tomb | 40 | enter Stony Tomb | — | enter Next level | needs-played-check |
| Halls of the Dead levels | 56 | Halls of the Dead Level 1 | Halls of the Dead | 42 | enter Halls of the Dead | — | enter Next level | needs-played-check |
| Halls of the Dead levels | 57 | Halls of the Dead Level 2 | Halls of the Dead | 42 | enter Next level | — | enter Next level | needs-played-check |
| Claw Viper Temple levels | 58 | Claw Viper Temple Level 1 | Claw Viper Temple | 44 | enter Claw Viper Temple | — | enter Next level | needs-played-check |
| Stony Tomb levels | 59 | Stony Tomb Level 2 | Stony Tomb | 40 | enter Next level | boss | leave | needs-played-check |
| Halls of the Dead levels | 60 | Halls of the Dead Level 3 | Halls of the Dead | 42 | enter Next level | boss | leave | needs-played-check |
| Claw Viper Temple levels | 61 | Claw Viper Temple Level 2 | Claw Viper Temple | 44 | enter Next level | boss | leave | needs-played-check |
| Maggot Lair Level 1 | 62 | Maggot Lair Level 1 | Maggot Lair | 43 | enter Maggot Lair | — | enter Next level | needs-played-check |
| Maggot Lair Level 2 | 63 | Maggot Lair Level 2 | Maggot Lair | 43 | enter Next level | — | enter Next level | needs-played-check |
| Maggot Lair Level 3 | 64 | Maggot Lair Level 3 | Maggot Lair | 43 | enter Next level | boss | leave | needs-played-check |
| Ancient Tunnels | 65 | Ancient Tunnels | Ancient Tunnels | 44 | enter Ancient Tunnels | chest | leave | needs-played-check |
| Tal Rasha's Tomb 1 | 66 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Tal Rasha's Tomb 2 | 67 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Tal Rasha's Tomb 3 | 68 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Tal Rasha's Tomb 4 | 69 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Tal Rasha's Tomb 5 | 70 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Tal Rasha's Tomb 6 | 71 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Tal Rasha's Tomb 7 | 72 | Tal Rasha's Tomb | Tal Rasha's Tombs | 46 | tour Tomb | — | back to Canyon of the Magi | needs-played-check |
| Arcane Sanctuary | 74 | Arcane Sanctuary | Summoner | 40 | use Arcane Sanctuary | boss | leave | needs-played-check |
| Spider Forest | 76 | Spider Forest | Spider Cavern | 76 | waypoint 76 | — | enter Spider Cavern | needs-played-check |
| Great Marsh | 77 | Great Marsh | Great Marsh | 77 | waypoint 77 | — | leave | needs-played-check |
| Flayer Jungle | 78 | Flayer Jungle | Swampy Pit | 78 | waypoint 78 | — | enter Swampy Pit 1 | needs-played-check |
| Lower Kurast | 79 | Lower Kurast | Lower Kurast | 79 | waypoint 79 | chest | leave | needs-played-check |
| Kurast Bazaar | 80 | Kurast Bazaar | Kurast Sewers | 80 | waypoint 80 | — | enter Sewers | needs-played-check |
| Upper Kurast and Kurast Causeway | 81 | Upper Kurast | Forgotten Reliquary | 81 | waypoint 81 | — | enter Forgotten Reliquary | needs-played-check |
| Upper Kurast and Kurast Causeway | 82 | Kurast Causeway | Ruined Fane | 81 | enter Kurast Causeway | — | enter Ruined Fane | needs-played-check |
| Travincal | 83 | Travincal | Mephisto | 81 | enter Travincal | boss | enter Durance of Hate | needs-played-check |
| Arachnid Lair | 84 | Spider Cave | Arachnid Lair | 76 | enter Arachnid Lair | chest | leave | needs-played-check |
| Spider Cavern | 85 | Spider Cavern | Spider Cavern | 76 | enter Spider Cavern | boss | leave | needs-played-check |
| Swampy Pit levels | 86 | Swampy Pit Level 1 | Swampy Pit | 78 | enter Swampy Pit 1 | — | enter Next level | needs-played-check |
| Swampy Pit levels | 87 | Swampy Pit Level 2 | Swampy Pit | 78 | enter Next level | — | enter Next level | needs-played-check |
| Flayer Dungeon levels | 88 | Flayer Dungeon Level 1 | Flayer Dungeon | 78 | enter Flayer Dungeon 1 | — | enter Next level | needs-played-check |
| Flayer Dungeon levels | 89 | Flayer Dungeon Level 2 | Flayer Dungeon | 78 | enter Next level | — | enter Next level | needs-played-check |
| Swampy Pit levels | 90 | Swampy Pit Level 3 | Swampy Pit | 78 | enter Next level | chest | leave | needs-played-check |
| Flayer Dungeon levels | 91 | Flayer Dungeon Level 3 | Flayer Dungeon | 78 | enter Next level | boss | leave | needs-played-check |
| Kurast Sewer levels | 92 | Sewers Level 1 | Kurast Sewers | 80 | enter Sewers | chest | enter Sewers 2 | needs-played-check |
| Kurast Sewer levels | 93 | Sewers Level 2 | Kurast Sewers | 80 | enter Sewers 2 | — | leave | needs-played-check |
| All Kurast temple levels | 94 | Ruined Temple | Ruined Temple | 80 | enter Ruined Temple | boss | leave | needs-played-check |
| All Kurast temple levels | 95 | Disused Fane | Disused Fane | 80 | enter Disused Fane | — | leave | needs-played-check |
| All Kurast temple levels | 96 | Forgotten Reliquary | Forgotten Reliquary | 81 | enter Forgotten Reliquary | — | leave | needs-played-check |
| All Kurast temple levels | 97 | Forgotten Temple | Forgotten Temple | 81 | enter Forgotten Temple | — | leave | needs-played-check |
| All Kurast temple levels | 98 | Ruined Fane | Ruined Fane | 81 | enter Ruined Fane | — | leave | needs-played-check |
| All Kurast temple levels | 99 | Disused Reliquary | Disused Reliquary | 81 | enter Disused Reliquary | — | leave | needs-played-check |
| Durance of Hate levels | 100 | Durance of Hate Level 1 | Mephisto | 81 | enter Durance of Hate | — | enter Next level | needs-played-check |
| Durance of Hate levels | 101 | Durance of Hate Level 2 | Mephisto | 81 | enter Next level | — | enter Next level | needs-played-check |
| Durance of Hate levels | 102 | Durance of Hate Level 3 | Mephisto | 81 | enter Next level | boss | use Red portal | needs-played-check |
| Outer Steppes | 104 | Outer Steppes | Izual | 103 | route entry needs played check | — | enter Plains of Despair | needs-played-check |
| Plains of Despair | 105 | Plains of Despair | Izual | 103 | enter Plains of Despair | boss | leave | needs-played-check |
| City of the Damned | 106 | City of the Damned | Diablo | 106 | waypoint 106 | — | enter River of Flame | needs-played-check |
| River of Flame | 107 | River of Flame | Diablo | 106 | enter River of Flame | — | enter Chaos Sanctum | needs-played-check |
| Chaos Sanctuary | 108 | Chaos Sanctum | Diablo | 106 | enter Chaos Sanctum | boss | leave | needs-played-check |
| Bloody Foothills | 110 | Bloody Foothills | Abaddon | 111 | route entry needs played check | — | enter Frigid Highlands | needs-played-check |
| Frigid Highlands | 111 | Rigid Highlands | Abaddon | 111 | enter Frigid Highlands | — | use Abaddon (pending) | unavailable: the red portal is not in the map files: its object is not read yet |
| Arreat Plateau | 112 | Arreat Plateau | Pit of Acheron | 112 | waypoint 112 | — | use Pit of Acheron (pending) | unavailable: the red portal is not in the map files: its object is not read yet |
| Crystalline Passage | 113 | Crystalized Cavern Level 1 | Frozen River | 113 | waypoint 113 | — | enter Frozen River | needs-played-check |
| Frozen River | 114 | Cellar of Pity | Frozen River | 113 | enter Frozen River | boss | leave | needs-played-check |
| Glacial Trail and Drifter Cavern | 115 | Crystalized Cavern Level 2 | Drifter Cavern | 115 | waypoint 115 | — | enter Drifter Cavern | needs-played-check |
| Glacial Trail and Drifter Cavern | 116 | Echo Chamber | Drifter Cavern | 115 | enter Drifter Cavern | chest | leave | needs-played-check |
| Frozen Tundra | 117 | Tundra Wastelands | Infernal Pit | 117 | waypoint 117 | — | use Infernal Pit (pending) | unavailable: the red portal is not in the map files: its object is not read yet |
| Ancients' Way and Icy Cellar | 118 | Glacial Caves Level 1 | Icy Cellar | 118 | waypoint 118 | — | enter Icy Cellar | needs-played-check |
| Ancients' Way and Icy Cellar | 119 | Glacial Caves Level 2 | Icy Cellar | 118 | enter Icy Cellar | boss | leave | needs-played-check |
| Nihlathak's Temple and Halls of Anguish | 121 | Nihlathaks Temple | Nihlathak | 123 | route entry needs played check | — | enter Halls of Anguish | needs-played-check |
| Nihlathak's Temple and Halls of Anguish | 122 | Halls of Anguish | Nihlathak | 123 | enter Halls of Anguish | — | enter Next level | needs-played-check |
| Halls of Pain | 123 | Halls of Death's Calling | Nihlathak | 123 | enter Next level | — | enter Next level | needs-played-check |
| Halls of Vaught | 124 | Halls of Vaught | Nihlathak | 123 | enter Next level | boss | leave | needs-played-check |
| Abaddon | 125 | Hell1 | Abaddon | 111 | use Abaddon (pending) | chest | leave | needs-played-check |
| Pit of Acheron | 126 | Hell2 | Pit of Acheron | 112 | use Pit of Acheron (pending) | chest | leave | needs-played-check |
| Infernal Pit | 127 | Hell3 | Infernal Pit | 117 | use Infernal Pit (pending) | chest | leave | needs-played-check |
| Worldstone Keep and Throne | 128 | The Worldstone Keep Level 1 | Baal | 129 | enter The Worldstone Keep 1 | — | enter Next level | needs-played-check |
| Worldstone Keep and Throne | 129 | The Worldstone Keep Level 2 | Baal | 129 | enter Next level | — | enter Next level | needs-played-check |
| Worldstone Keep and Throne | 130 | The Worldstone Keep Level 3 | Baal | 129 | enter Next level | — | enter Next level | needs-played-check |
| Worldstone Keep and Throne | 131 | Throne of Destruction | Baal | 129 | enter Next level | boss | use Worldstone Chamber | needs-played-check |

