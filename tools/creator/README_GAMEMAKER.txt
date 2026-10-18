ARCADIA GAME MAKER  (no-code, Scratch-style cartridge creator)
================================================================
One self-contained offline page: arcadia_gamemaker.html. Double-click it (any modern browser, no
internet, no install). You snap blocks together, paint 8x8 sprites, press Run to play the game in a live
preview, then download a finished .arc cartridge for the PyGamer's /carts folder.

Files in tools\creator\
  arcadia_gamemaker.html   the whole app (editor, block compiler, ARCL assembler, VM, preview)
  test_gamemaker.js        self-test:  node test_gamemaker.js   (needs only node; python optional)
  README_GAMEMAKER.txt     this file

QUICK START
  1. Open arcadia_gamemaker.html. A shooter template is loaded and running in the preview.
  2. Pick another template in the top bar (Blank, Shooter, Platformer, Grid/worm game, Dodger, Chase)
     and press "New from template", or start from Blank.
  3. Drag blocks from the left list into the big area. Snap them under a yellow event block.
     Round/hexagon value blocks drop into the white slots of other blocks. Drag a block back onto the
     left list (or right-click > Delete) to remove it. Ctrl+Z / Undo works. "Clean up" tidies the scripts.
  4. Sprites tab: paint 8x8 sprites (click/drag, right-drag erases), name them, give them a colour, a start
     position, and say whether they are drawn on the stage automatically. The "icon" entry is the 8x8
     picture shown in the game picker.
  5. Project tab: name (max 15), file ID, picker category/blurb, author, colour, 2-player, difficulty names,
     help lines, lives, background colour, auto-clear, auto-draw sprites.
  6. Press Run / Restart. Keys: arrows = D-pad, Z = A, X = B, Enter = pause/resume (Start),
     Shift = pause/resume (Select). On-screen buttons work too (touch / mouse). Tier selector and 2P toggle
     are next to Run. The "Speed" meter shows VM steps per frame against the 30,000 limit.
  7. "Download .arc cartridge" saves <id>.arc. Install it like any cart: Settings > USB drive on the
     PyGamer, copy to the drive's /carts folder, eject in Windows, press B to reboot (see README_CARTS.txt).
     "Download .arcl" gives the generated source, usable with tools\make_carts.py. "Save project" /
     "Open project" store the whole game (blocks, sprites, settings) as an editable .arcgm.json file
     (you can also drop a .json onto the page). The page also autosaves to browser storage.

HOW THE BLOCKS BEHAVE
  Scripts are event stacks. Every frame (30/s) the generated frame() does, in this order:
    clear the screen (if "clear every frame" is on) -> all "when [button] pressed/held", "when X touches Y",
    "when X hits the edge", "when I receive" scripts -> all "every frame" scripts, TOP TO BOTTOM as they sit
    in the workspace -> sprites that are "shown on stage" are drawn (if auto-draw is on) -> message timers.
  "when game starts" scripts run once per round (init) before the first frame.
  Sprites are positioned entities: each used sprite gets x, y (and, only if you use the blocks, speed,
  show/hide, colour and flip variables). Motion blocks move them, "draw ... where it is" and auto-draw
  paint them, touching blocks use an 8x8 box shrunk by 1 pixel on every side.
  Waits: "wait N frames/seconds" and "wait until" placed directly in a script pause only that script
  (the compiler turns the script into a small state machine, other scripts keep running). Inside
  "when game starts" they are real pauses of the whole game (intro screens, countdowns).
  Waits nested inside loops or if-blocks are allowed only in "when game starts".
  "forever" is only accepted if it contains an exit (exit loop / stop script / win / lose) or, in
  "when game starts", a wait - otherwise the cart would hit the 30,000-step limit.
  Messages: "broadcast X" reaches every "when I receive X" on the next frame.
  Variables: "lives" is built in (starting value in Project; "lose a life" ends the game at 0);
  "score" has its own blocks (add / set / value). Make more variables with "Make a variable".
  Lists and the grid: one list of 128 numbers and one 16x12 grid (cells outside read as -1) live in the
  VM's 1024-word memory; "draw grid tiles" draws cells as sprites (cell value = tile number of a sprite,
  see "tile number of").
  Game blocks: win / lose (with your headline), add/set score, save slot (16 persistent bytes, 0..255).
  Start/Select are the device's pause menu keys; a cartridge cannot read them, so there are no blocks
  for them (Enter/Shift just pause the preview).

PLATFORMER PHYSICS (gravity and platforms built in)
  Level tab: a 20 x 16 tile layer (8x8-pixel tiles). Drag a rectangle to place solid platforms, right-drag to
  erase, "Add floor" / "Clear", pick the platform colour. Letters mark where each sprite starts. Platforms are
  drawn automatically (switchable) and are solid from every side.
  Platformer block group (no gravity code to write):
    move [sprite] left/right with platform collision, speed N   (reads the D-pad, stops at platform sides)
    apply gravity to [sprite]     (falls up to 6 px/frame, lands on tops, bumps heads, sets the ground flag)
    jump if [sprite] is on the ground, power N                 (power 9 = about 36 px; no double jump)
    [sprite] on ground?   and   [sprite] fell off the screen?   (yes/no blocks for your own rules)
  Typical script set: every frame { move hero left/right..., apply gravity to hero, if hero fell off the
  screen { lose a life, put hero back } }, when A is pressed { jump if hero is on the ground }.
  Each sprite used with these blocks costs 6 variables (x, y, speed x/y, ground flag, ...).
  The HILL HOP template is built only from these blocks: arrows move, Z jumps, 3 coins, a flag ends the
  level (win), falling into the pit costs a life and respawns the hero.

EDITING SPRITES AND THE BACKGROUND
  Sprites tab: the big pixel grid is at the top (click or drag to paint, right-drag erases); the list of
  sprites is below it, and picking one scrolls the grid into view. Each sprite has ONE colour: pick it with
  the colour swatches under the grid. If a sprite name is refused (reserved word, duplicate ...) a red
  message appears under the Name box and the old name is kept.
  Background colour: colour swatches at the bottom of the Level tab (also a drop-down on the Project tab).
  Level tab > "Background" mode: a 20 x 16 painter for 8x8-pixel tiles. Pick a colour swatch, click/drag to
  paint, right-drag (or the striped swatch) erases, "Fill all" / "Clear background". Tiles are drawn right
  after the screen is cleared, behind platforms and sprites, and are saved in the project JSON (bgTiles).
  The compiler merges same-colour neighbours into rect() calls. Limit: 100 rectangles (a warning from 70);
  more is an error in the Checks tab - paint larger blocks of one colour instead. Carts with no painted
  background tiles are byte-for-byte what they were before.
  The preview restarts by itself about 0.3 s after you change a sprite, the level, the background or a
  Project setting (block edits do not restart it, press Run for that).

TEXT IS TRANSPARENT
  On the device text and numbers have no background box, so old digits would stack. With "Clear the screen
  every frame" ON (default) nothing needs doing. If you switch it OFF (trails, paint programs ...) the
  compiler automatically paints a background-coloured box (colour = "set background colour") behind every
  "write", "write centred" and "show number" block before drawing it.

LIMITS (enforced like the device; see README_CARTS.txt)
  cart file 14,000 bytes; code 8 KB; strings 2 KB; 64 sprites; 128 variables (a moving sprite uses 2 to 7,
  messages/waits use more); 1024 memory words; 30,000 VM steps per frame (the preview raises "cart too slow"
  exactly like the firmware; the Speed bar turns amber above 60%); 12 nested calls; 60 locals per script.
  The Checks tab lists all problems and a usage bar for each limit. Errors in a block name the block.
  Not available (VM limits): reading Start/Select, true clones/many-of-one-sprite (use several sprites or
  the list/grid), sound beyond tone/note/8 preset effects, text outside the 160x128 screen.

NAME / ID COLLISION GUARD
  The page embeds the list from tools\builtin_games.txt plus the kGameNames table of PyGamerPortal.ino
  (71 names) and the 11 sample cartridges. It applies the same rules as make_carts.py: a game name that equals,
  contains or is contained in (4+ letters) a built-in name, or that contains a genre keyword (snake, pong,
  tetris, dodge, runner, platform, invader, ...), is an ERROR and blocks the .arc download (the preview still
  runs). A genre keyword only in the blurb is a warning. The file ID must be a-z, 0-9, _ (max 15 characters so
  the .arc name stays under 20), must not equal a built-in name, and warns if it equals a sample cart (copying
  it would overwrite that cart). If you add built-in games, rebuild or use Checks > "Reload built-in game list".
  The shipped templates are named COMET GUARD, HILL HOP, WORM TRAIL, ROCK RAIN, COIN CHASE so they pass.

VERIFICATION (what test_gamemaker.js does)
  node test_gamemaker.js     (run from this folder; takes a few seconds)
  - pulls the very <script id="core"> out of the HTML (so it tests the code the browser runs)
  - JS assembler vs tools\out\carts\*.arc: all 11 sample carts compile to the identical bytes
  - collision guard rules (blocked / allowed names and IDs)
  - every template: compiles with no error or warning, survives a JSON save/load with identical output,
    runs 16 headless runs (4 tiers x idle/mash/sweep/random bots, 1500 frames each) with no VM fault and
    under 60% of the step budget; scripted bots check that snake grows, shooter scores, dodger scores; platformer physics checks:
    stands on floor, jumps and lands, no double jump, lands on a platform, head bump, pit costs a life,
    coin scores, flag wins, and a scripted run (arrow right + Z only) climbs to the flag
  - compiler checks: forever/wait rules, bad names/numbers, >128 variables, >64 sprites, timed (wait)
    scripts, start-script waits, HUD repaint with auto-clear off, messages, list/grid, runaway loop
  - python: tools\make_carts.py compiles the generated .arcl of every template to the same bytes as the JS
    assembler (skipped automatically if python is missing)

FOR TINKERERS
  The page has two scripts: id="core" (assembler + VM + block catalogue + compiler + templates, pure JS, no DOM)
  and id="ui". The assembler is a straight port of make_carts.py and the VM a port of arcvm_ref.py; the text
  font in the preview is a 5x7 bitmap font (the device uses its own, glyph shapes can differ slightly).
  Block definitions are the def(...) calls in the core script: label with %1 %2 slots, argument kinds and a
  gen() that returns ARCL text. Add a block there and it appears in the palette automatically.
