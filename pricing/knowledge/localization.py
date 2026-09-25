"""Consistent English display-name fallback for offline game-data importers."""


def merge_game_strings(english, planner_rows):
    """Keep valid planner translations; fill missing keys from pinned English."""
    result = {key: value for key, value in english.items() if isinstance(key, str) and isinstance(value, str)}
    for row in planner_rows:
        if isinstance(row, list) and len(row) == 2 and all(isinstance(value, str) for value in row):
            result[row[0]] = row[1]
    return result
