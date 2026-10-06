from inventory_tracking.macros.journey import Journey


def test_the_level_before_this_one_and_the_time_since_are_remembered():
    journey = Journey()
    journey.note('cyber32', 102, 10.0)
    journey.note('cyber32', 102, 11.0)
    journey.note('cyber32', 103, 12.0)
    journey.note('cyber32', 103, 20.0)
    assert journey.arrival(25.0) == (102, 13.0)


def test_the_first_level_of_a_game_has_no_level_before_it():
    journey = Journey()
    journey.note('cyber32', 102, 10.0)
    journey.note(None, None, 12.0)  # the lobby
    journey.note('cyber33', 103, 20.0)
    assert journey.arrival(21.0)[0] is None


def test_an_unreadable_level_changes_nothing():
    journey = Journey()
    journey.note('cyber32', 102, 10.0)
    journey.note('cyber32', None, 11.0)
    journey.note('cyber32', 103, 12.0)
    assert journey.arrival(12.0) == (102, 0.0)
