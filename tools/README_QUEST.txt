PORTAL QUEST - ONE BIG WORLD ON THE DRIVE
=========================================

What it is
  Game 56 "Portal Quest" is a separate game from Portal. The world (38 regions of 24x18 tiles, 129 crystals)
  lives in /worlds/quest.wld on the PyGamer drive and is streamed one region at a time (the neighbour is read when
  you walk through a doorway). Portal and its 1052 levels are unchanged.

Install
  1. Build:   cd tools ; python make_quest_world.py          (writes tools\out\quest.wld, validates it first)
  2. PyGamer: Settings > USB drive.
  3. PC:      powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Quest     (add -Drive E: if needed)
  4. EJECT the drive, press B on the PyGamer. Open Portal Quest from the picker.
  Without the file the title screen says so and nothing else happens.

Playing
  Up/Down walk, Left/Right turn, A read signs / talk / press on cracked walls, B or Start tap = world map,
  Start hold or Select = pause (Restart = back to the last checkpoint). Blue rings mark region exits.
  Collect crystals (cyan), keys open the K doors, plates+crates open D doors, laser beams are blocked by crates,
  purple rings are teleporters, green plates are checkpoints, the dark purple wall north of the market opens at 90
  crystals, the big green diamond in the vault ends the quest ("Quest Complete" award).
  Modes (title Left/Right): NORMAL; SPEED/CHILL change turn speed; EXTREME sends you to the world start on death;
  ZEN switches lasers off.  Progress is shared by all modes.

Progress files (on the drive, written by the game)
  /arcadia/quest0.bin, quest1.bin: two alternating 68-byte generations {magic AQS1, worldId, playSec, seq, crystals,
  flags[32], explored[8], checkpoint region/col/row, keys, done, FNV-1a checksum}. The newest valid one wins.
  Progress belongs to one world id (CRC of the world data): a regenerated world starts fresh.

File format /worlds/quest.wld (little endian)
  header 32 B  "ARQW", u8 version=1, u8 W, u8 H (1..8), u8 regionCount, u32 worldId, u16 crystalTotal (<=250),
               u16 crystalNeed (info), u8 startRegion, u8 startCol, u8 startRow, u8 0, char name[12]
  index        W*H entries x 8 B: u32 offset, u16 length (0 = no region), u8 theme (0 Town 1 Ice 2 Factory 3 Temple
               4 Maze 5 Swamp 6 Vault 7 Caves), u8 0.   Region id = row*W + col.
  region       u8 w, u8 h (1..40), u8 nObj (<=28), u8 nStr (<=12), u16 strBytes (<=360), u16 0,
               nObj x 8 B objects {type, col, row, flag, a, b, c, d},
               strBytes of strings (u8 length + ASCII, no terminator),
               w*h tile chars, row-major (same letters as Portal: # N . ~ I P D ^ v < > K u d l r F M T U X;
               no S, G, Y: start/goal/keys are objects)
               length must equal 8 + nObj*8 + strBytes + w*h exactly.
  Region edges: an open (non-wall) tile on the outer ring is a doorway; walking out loads region +-1 / +-W and
               lands at the same row/column. Tool rule: both sides of a link have matching 2-wide doorways.
  Objects (type): 1 crystal (flag), 2 key (flag), 3 locked door tile (flag; put a K tile there; all objects with the
               same flag open together), 4 sign (a = string), 5 checkpoint, 6 teleport pad (a = dest region,
               b = dest col, c = dest row; land on a walkable non-pad tile), 7 secret wall (flag; put # there),
               8 crystal gate (a = crystals needed; put N there), 9 win diamond, 10 NPC (a = string).
  flag = 0..254 progress bit, 255 = none. Crystals must use flags 0..crystalTotal-1 (they are counted from those).
  Limits: 2 laser emitters and 3 crates per region (extra ones are ignored by the Portal tile parser).

Validator (make_quest_world.py)
  Builds each region, then plays the whole world: ice sliding, belts, keys vs locks, crystal gate, secrets, teleport
  pads, doorways in both directions, every object reachable, no objects inside walls. It exits with an error list if
  anything is wrong. Plate and laser puzzles are built from fixed templates (crate row / beam column) that are
  verified by construction; the validator assumes they are solved. --seed N gives another world; --dump prints maps.
