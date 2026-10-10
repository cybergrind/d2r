extends RefCounted
## The viewer's colours, in one place. Recorded play is always orange, the policy always blue:
## nothing else on screen uses either.

const BACKGROUND := Color("101216")
const PANEL := Color("181b22")
const PANEL_EDGE := Color("2c313c")
const TEXT := Color("e6e8ec")
const TEXT_DIM := Color("9aa0ac")

const RECORDED := Color("ff9d2e")  # the player's recorded casts
const POLICY := Color("3db8ff")  # the policy's casts
const GOOD := Color("6fe08a")  # the policy ahead
const BAD := Color("ff6b6b")  # the policy behind

const FLOOR := Color("171a21")
const LOW := Color("272d3b")  # blocks walking, a blade flies over it
const WALL := Color("434c66")  # stops a blade
const UNREAD := Color("101216")

const PLAYER := Color("ffffff")
const PLAYER_RING := Color("6fe08a")
const COMPANION := Color("58c470")
const MONSTER := Color("c9ccd4")
const ELITE := Color("ff5fd0")
const DEAD := Color("5a5f6b")
const POINTER := Color("ffffff")
const DOOR_CLOSED := Color("e05252")
const DOOR_OPEN := Color("6a7285")
const MOMENT := Color("f4e04d")
const CURSOR := Color("ffffff")
