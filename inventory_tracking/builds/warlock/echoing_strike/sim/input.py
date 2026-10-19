"""The input model's numbers (combat/plan.md stage 5): the game casts every CAST_FRAMES while the strike button is
down or tapped, and the blades appear BIRTH_LAG frames after the cast starts. The press-to-cast model and its check
against the takes are in git history (sim/input.py `casts_from_presses`, before 2026-10-19).
"""

CAST_FRAMES = 9  # frames one cast occupies the character (0.36 s cast bouts; 9 beats 10 and 11 on the takes)
BIRTH_LAG = 5  # frames from the cast start to the blades' first frame
