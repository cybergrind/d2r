# Golden net — the base (framework-plan.md, Task 0.1)

Recorded 2026-10-12 on branch `combat-framework`, on the tree frozen as commit `99df689`.

    uv run --offline pytest tests/inventory_tracking -q
    3985 passed, 1 skipped, 63 xfailed in 186 s

None of the 63 expected failures below may change state in Stages 0–3. The 13 of
`scenarios/threat/test_scenarios.py` are Stage 4's targets.

Added by Stage 2 on purpose (2026-10-12), and Stage 3.7's target:
`tests/inventory_tracking/scenarios/arena/test_dummy_in_arena.py::test_the_second_build_clears_a_scene_with_its_own_attack`.
With it the suite reads 5580 passed, 8 skipped, 64 xfailed.

## Expected failures

- tests/inventory_tracking/scenarios/battle/test_baseline.py::test_the_model_takes_the_heralds_life_when_the_game_did
- tests/inventory_tracking/scenarios/battle/test_enchanted.py::test_the_blow_that_killed_is_within_what_the_pack_deals_by_the_tables
- tests/inventory_tracking/scenarios/battle/test_monsters_fit.py::test_every_monster_is_placed_better_than_by_leaving_it_where_it_stood
- tests/inventory_tracking/scenarios/battle/test_tower_cellar5.py::test_every_recorded_action_is_replayed
- tests/inventory_tracking/scenarios/exits/test_exits.py::test_a_level_whose_only_marked_way_is_back_is_no_stop
- tests/inventory_tracking/scenarios/exits/test_exits.py::test_a_spot_learnt_standing_west_of_the_stairs_costs_no_hop_from_the_east
- tests/inventory_tracking/scenarios/exits/test_exits.py::test_a_spot_off_the_screen_from_the_start_gets_the_one_hop_that_leaves_a_walk
- tests/inventory_tracking/scenarios/exits/test_exits.py::test_a_spot_on_the_far_side_of_the_stairs_walls_is_one_hop_and_the_click
- tests/inventory_tracking/scenarios/exits/test_exits.py::test_the_hop_that_lands_on_the_doors_spot_goes_on_to_the_click
- tests/inventory_tracking/scenarios/exits/test_exits.py::test_the_same_door_from_54_units_is_two_hops_and_the_click
- tests/inventory_tracking/scenarios/loop/test_handover.py::test_a_click_during_death_mark_lets_the_strike_go_within_a_tick
- tests/inventory_tracking/scenarios/loop/test_handover.py::test_a_look_at_the_world_reads_no_research_bytes
- tests/inventory_tracking/scenarios/loop/test_handover.py::test_hunting_one_elite_does_not_scan_the_ground_again_on_every_hop
- tests/inventory_tracking/scenarios/loop/test_handover.py::test_one_look_at_the_loot_walks_the_item_table_once
- tests/inventory_tracking/scenarios/loop/test_handover.py::test_the_left_button_is_looked_at_once_a_slice[fighting]
- tests/inventory_tracking/scenarios/loop/test_handover.py::test_the_left_button_is_looked_at_once_a_slice[idle]
- tests/inventory_tracking/scenarios/loop/test_reaction.py::test_a_monster_out_of_reach_for_a_moment_does_not_end_the_hold
- tests/inventory_tracking/scenarios/loop/test_reaction.py::test_a_monster_walking_into_reach_is_struck_within_three_ticks
- tests/inventory_tracking/scenarios/loop/test_reaction.py::test_no_sigil_is_cast_under_an_elite_behind_a_wall_on_the_way_to_a_strike
- tests/inventory_tracking/scenarios/loop/test_reaction.py::test_the_swap_to_the_main_weapons_keeps_the_strike_up_half_a_second_at_most
- tests/inventory_tracking/scenarios/loop/test_tick_cost.py::test_a_decision_over_sixty_hostiles_fits_between_two_looks_of_the_fight
- tests/inventory_tracking/scenarios/loop/test_tick_cost.py::test_doors_out_of_the_blades_reach_are_not_asked_about_every_blade
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_planner_of_today_needs_no_more_hops_than_the_macro_made_on_the_day[recorded-door-1725]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_arrives_and_every_teleport_lands_on_footing[unloaded-room]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_is_not_much_longer_than_the_reference_route[down-the-screen-narrow]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_is_not_much_longer_than_the_reference_route[unloaded-room]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_routes_together_take_the_fewest_hops
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_at_most_one_hop_more_than_the_reference[down-the-screen-narrow]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_at_most_one_hop_more_than_the_reference[recorded-door-1725]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_at_most_one_hop_more_than_the_reference[unloaded-room]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[across-and-back]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[around-the-void]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[corner-west]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[down-the-screen-narrow]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[last-hop-short]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[recorded-door-1725]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[recorded-door-1837]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[recorded-hunt-1848]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[recorded-hunt-2124]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[unloaded-room]
- tests/inventory_tracking/scenarios/navigation/test_routes.py::test_the_route_takes_the_fewest_hops[up-the-screen]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[shaman_behind_a_wall]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[shaman_in_a_closed_cell]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[shaman_out_of_reach]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[terror_two_shamans_cover_each_other]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[tough_two_shamans_cover_each_other]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[tough_unraveler_off_the_line_of_its_skeletons]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[two_shamans_cover_each_other]
- tests/inventory_tracking/scenarios/revivers/test_scenarios.py::test_the_fight_ends_the_pack_without_grinding_what_comes_back[unraveler_raises_from_out_of_reach]
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_a_dying_shooter_is_finished_before_a_fresh_brute
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_a_herald_pack_that_kills_in_a_second_is_not_stood_in
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_a_pack_the_blades_cannot_hurt_is_not_stood_in
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_a_step_out_of_the_pincer_before_it_closes
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_dolls_on_the_character_are_not_blown_up_there
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_exploding_dolls_die_before_they_arrive
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_low_life_in_melee_breaks_contact_first
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_low_life_under_fire_it_cannot_outkill_yields
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_no_cast_goes_through_an_immune_elite_while_killable_shooters_stand_beside
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_of_two_lines_worth_the_same_the_one_in_contact_goes_first
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_the_frail_casters_die_before_the_tanky_elite
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_the_killable_die_first_when_immune_ghosts_stand_in_front
- tests/inventory_tracking/scenarios/threat/test_scenarios.py::test_the_shooters_behind_a_fat_slow_pack_die_first
- tests/inventory_tracking/terror/test_danger.py::test_the_pack_that_killed_the_character_is_marked

## Decision goldens: what the fixtures gave (Task 0.2, 2026-10-12)

`decisions.json` holds 660 cases (`cases.py`): stand 234, step 117, due 101, landing 64, aim 55,
tough 39, jumps 32, pickup 18. The module runs in about 5 s, so it carries no `slow` mark (the
repo defines none).

- `Ground` None: none of the 39 stance fixtures; every one has grids (4 or more), and
  `scenarios/stance/harness.py` `load` gives None only for a fixture without any. No case is excluded
  or marked for it. Were one to come: `stance.no_footing` and `policy.walls` take None (nothing
  bars), but `sight.clear_shot` calls `len(ground)`, so `in_reach`, `Travel.stride` with a Blade
  Warp and `Travel.make` raise TypeError on None. The 16 threat scenes have no level, and their
  cases pass an empty `Ground(())`: every shot clear, nothing barred.
- `aim`: 15 of the 39 stance moments have nothing in reach with a clear shot; `Hunter.choose` is
  asked only with something in reach (it asserts so), and those cases record null without a call.
- `step`: no fixture reaches the stride toward the nearest hostile (`Hunter.toward`): of 117 cases
  70 are a place from `better_stand` and 47 are None. That branch is not in the net.
- `stand`: staff "none" (Teleport as the character's own skill) reads the same as a staff of 69 in
  hand in all 78 pairs: `Travel.jumps` gives the same jumps for both.
- `landing`: the aims beside the skill bar (`view.CORNERS`) are on in the game and off under
  `scenarios/conftest.py`, and 13 of 32 landings differ between the two; each case sets the switch
  itself and both states are recorded.
- Strides (added the same day, 538 cases; the total is 1198, the module runs in about 7 s):
  `toward` 470 through `Hunter.toward`, `around` 68 through `Travel.around`. In the `step` cases a
  place from `better_stand` comes first, and no stride was ever the answer; these cases ask
  `toward` directly.
  - `toward`, 15 moments × 10 variants (staff none / 69 / 14 / 9 / 0 in hand × warp ready / in
    delay): those 15 moments as recorded, the character not moved. 40 Blade Warp, 24 Teleport,
    16 walks, 70 None.
  - `toward`, 32 synthetic worlds × 10 variants: one hostile alone on the ground of
    `20261010T204733Z-25-234739`, 18 / 24 / 34 / 46 units from where the character stood, on 8
    bearings. Synthetic because the recorded packs give no goal nearer than JUMP_LEAST or further
    than JUMP_REACH on a clear line; the character stays on its recorded spot, which is known
    footing, where a moved one could stand in a wall. 85 Blade Warp, 60 Teleport, 68 walks, 107 None;
    at 3 spots the wall refuses the Blade Warp and Teleport goes. A stride with Blade Warp ready and
    a wall in its line is walked or dropped, never handed to Teleport (`Travel.stride` asks
    `jump_by` once).
  - `around`, 34 goals × warp ready / in delay, the staff empty: goals with footing and no clear
    line, 14 to 32 units off, on the ground of three stance fixtures. 15 Blade Warp, 30 walks, 23 None.
  - A staff of 14 reads as one of 69 and a staff of 9 as an empty one in every `toward` case.
