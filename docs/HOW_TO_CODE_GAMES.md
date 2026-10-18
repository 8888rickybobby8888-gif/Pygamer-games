# How to code games for Arcadia

There are three ways to add a game, from easiest to most involved:

| Way | Language | Needs reflashing? | Best for |
| --- | --- | --- | --- |
| [Game Maker](#1-no-code-game-maker) | Drag-and-drop blocks | No | First game, quick ideas |
| [Cartridge (`.arcl` → `.arc`)](#2-write-a-cartridge-in-arcl) | ARCL, a small C-like language | No | Real games without touching firmware |
| [Built-in game](#3-add-a-built-in-game-to-the-firmware) | C++ in `PyGamerPortal.ino` | Yes | Games that need full hardware speed or access |

## 1. No-code Game Maker

Open `tools/creator/arcadia_gamemaker.html` in a browser. It needs no install and works offline. Snap blocks together, paint 8x8 sprites, press Run to play in a live preview, then download the `.arc` cartridge. Full instructions are in `tools/creator/README_GAMEMAKER.txt`.

## 2. Write a cartridge in ARCL

A cartridge is one text file that the PC compiles to a small `.arc` file. The firmware runs it on a built-in bytecode VM, so you don't change or reflash the firmware. The complete language and builtin reference is `tools/README_CARTS.txt`. Working examples are in `tools/carts/*.arcl`.

### A complete example

Save this as `tools/carts/starcatch.arcl`. It compiles and passes the self-test:

```c
// STAR CATCH : move the paddle, catch the falling stars.
@name "STAR CATCH"
@blurb "Reflex: catch stars"
@author "you"
@version 1
@color yellow
@tiers "NORMAL" "EASY" "HARD" "EXTREME"
@help "Left/Right: move" "Catch the stars" "Miss 3 and it's over"
@icon "...##..."
      "...##..."
      ".######."
      "..####.."
      "..####.."
      ".##..##."
      "........"
      "........"
@sprite STAR "...##..."
             "...##..."
             ".######."
             "..####.."
             "..####.."
             ".##..##."
             "........"
             "........"

var px, sx, sy, lives, speed;

func init() {                      // runs at the start of every round
  px = 76; sx = rnd(150); sy = 0; lives = 3;
  speed = 1 + tier();              // difficulty tier 0..3
}

func frame() {                     // runs 30 times a second
  if (btn(LEFT))  px = max(0, px - 3);
  if (btn(RIGHT)) px = min(SW - 24, px + 3);
  sy += speed;
  if (hit(sx, sy, 8, 8, px, 118, 24, 6)) {
    addscore(1); sfx(4); sx = rnd(150); sy = 0;
  } else if (sy > SH) {
    lives--; sfx(3); sx = rnd(150); sy = 0;
    if (lives <= 0) gameover("GAME OVER");
  }
  cls(BLACK);                      // text is transparent: repaint every frame
  spr(sx, sy, STAR, YELLOW);
  rect(px, 118, 24, 6, CYAN);
  text(2, 2, WHITE, "SCORE");
  num(40, 2, WHITE, getscore());
  num(140, 2, RED, lives);
}
```

### The essentials

- **Required:** `@name` (max 15 characters) and a `frame()` function. `init()` is optional.
- **Numbers** are signed 16-bit and wrap. The screen is 160x128 with `0,0` at the top left.
- **Input:** `btn(b)` is held now and `btnp(b)` is pressed this frame, for `LEFT RIGHT UP DOWN A B`. Start and Select belong to the pause menu, so a cartridge can't read them.
- **Drawing:** `cls`, `rect`, `box`, `line`, `circ`, `disc`, `text`, `num`, `spr` and more.
- **Scoring:** `addscore(n)`, then `gameover("HEADLINE")` ends the round and records the score. Add `@lower` if a lower score is better.
- **Sound and effects:** `sfx(0..7)`, `tone(hz, ms)`, `burst`, `shake`, `led`.
- **Limits:** code 8 KB, strings 2 KB, 64 sprites, 1024 words of array memory, 30,000 opcodes per frame. The compiler enforces these.
- **Name rule:** a cartridge can't duplicate a built-in game. The build fails with a collision error if it does.

### Build, test and install

```sh
cd tools
python make_carts.py                 # compiles every cart and runs the self-test
python make_carts.py --shots         # also writes rough screenshots to tools/out/shots/
```

`make_carts.py` writes `.arc` files to `tools/out/carts/`. To put them on the board:

1. On the PyGamer, open **Settings → USB drive**.
2. Run `powershell -ExecutionPolicy Bypass -File tools/install_assets.ps1 -Carts`. Add `-Drive E:` if the drive isn't detected.
3. Eject the drive, then press **B** on the PyGamer. It reboots and rescans `/carts`.

The firmware lists at most 16 cartridges, and each one should stay under about 4.5 KB.

## 3. Add a built-in game to the firmware

Built-in games are C++ state machines inside `PyGamerPortal.ino`. Each game has a title screen, a playing state and a game-over state, and it is wired in through the `// @@...` marker comments. Each marker sits at the end of one list, so a new entry goes just above it.

`NUM_GAMES` (defined just above `kGameNames`) is the number of built-in games and sizes all the per-game tables. Bump it, then add your game's entry to each of these:

| Marker | What to add |
| --- | --- |
| `// @@ENUM` | `ST_MYGAME_TITLE`, `ST_MYGAME_PLAYING`, `ST_MYGAME_OVER` in the `GameState` enum |
| `// @@OVER` | `case ST_MYGAME_OVER:` in the shared game-over switch |
| `// @@NAMES` | The picker name in `kGameNames` (keep it unique, in capitals) |
| `// @@BLURBS` | A one-line description in `kGameBlurbs`, 24 characters or fewer, as `"Category: text"` |
| `// @@ICONS` | An 8x8 icon in the icons table (eight row bytes, the most significant bit is the leftmost pixel) |
| `// @@COLORS` | The picker colour, `s_pickerColors[N] = ...;` |
| `// @@HELP` | The How to Play text: tagline, four control lines and a tier note |
| `// @@ACH` | Optional achievements |
| `// @@CODE` | Your game's functions: `enterMyGameTitle()`, per-frame tick functions and the draw code |
| `// @@LAUNCH` | `case N: g_variant = v; enterMyGameTitle(); break;` in `launchGameV` |
| `// @@SELB` | `case ST_MYGAME_TITLE:` so Select acts as Back on the title screen |
| `// @@DISPATCH` | `if (gameState == ST_MYGAME_PLAYING) { myGameTick(pressed, buttons); return; }` in the main loop |

Search for an existing game that is close to yours and copy its pattern. `ST_MISSILE_*` and `ST_PIPE_*` are recent, small examples. Every marker also lists the most recently added game just above it.

Other things to know:

- **Keep names in sync.** After adding a game, add its name to `tools/builtin_games.txt` (or just rerun `make_carts.py`, which re-reads `kGameNames`). Rerun `tools/make_assets.py` if you want a banner for it.
- **Level support is optional.** To give a game a level editor and level packs, follow the contract in the comment headed `HOW TO ADD A LEVEL GAME` in `PyGamerPortal.ino`.
- **Screen and timing.** The display is 160x128. Draw only what changed where you can, because the whole sketch shares one frame budget.
- **Build and flash** with the commands in the main [README](../README.md#building-and-flashing). Then add your game to `TEST_CHECKLIST.md` and test it on the board.
