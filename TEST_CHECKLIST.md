# Arcadia hand-test checklist (54 games)

This build is on the board (flashed 2026-10-11). Nothing in it has been tested on hardware yet, so
start with the first section and work down. To reflash:

    arduino-cli upload --fqbn adafruit:samd:adafruit_pygamer_m4 -p COMx .

(Double-tap reset if the board doesn't show up in `arduino-cli board list`.)

## 1. Boot, menus, settings
- [ ] Splash: no flicker, any button skips. Serial on first boot: "Levels: filesystem ready." and "Saves: ..."
- [ ] Picker: icons readable, smooth glide, Left = filter (All/Favorites/Recent/categories/Most played/Unplayed), Right = star, Up-hold = random game, B-hold = High Scores, B or Select tap = Settings
- [ ] Idle 30 s in the picker: screensaver starts, any button wakes it
- [ ] Settings (redesigned) shows grouped sections with header bars: DISPLAY (Brightness, Menu, Cart anim, Portrait), SOUND (Sound, Volume, Boot sound, Menu music, Sound test), PLAY (2 Player, Boot, Auto help, Tilt, Tilt gain), MORE (Challenges & Awards, Credits), SYSTEM (Diagnostics, USB drive, Restore backup), DANGER ZONE (red: Reset achievements, Delete levels, Reset saves, Factory reset)
- [ ] Settings look: rounded highlight slides smoothly between rows and gently pulses; selected label white, icon yellow; scrollbar on the right and n/23 in the title; list scrolls so a group header shows when you land on its first row; Up on the first row wraps to Factory reset and Down on it wraps to Brightness
- [ ] Settings widgets: toggles are switches (ON green / OFF grey) for Sound, Boot sound, Menu music, 2 Player, Auto help; Brightness = 5-step bar or AUTO pill; Volume = 3-step bar; choice rows (Menu Shelf/List, Cart anim Full/Quick/Off, Portrait Auto/Flip A/Flip B, Boot Picker/Last game, Tilt Normal/Invert, Tilt gain Low/Med/High) show < value > and L/R changes them exactly as before
- [ ] Settings footer hint changes with the row (L/R change, A: open, A: play, A twice..., A, then hold to confirm, and A: confirm / other: cancel while armed); armed rows (Restore, Reset achievements, Delete levels, Reset saves) turn the highlight red and the prompt (SURE? A=yes, other=no / Restore? A=yes / Delete N lvls? A=yes) is fully readable; moving or pressing any other button disarms
- [ ] Settings sub-screens (Challenges & Awards, Credits, USB drive, Diagnostics, Factory reset cancel) return to the SAME selected row; toasts (No backup, Saves reset...) still slide in over the screen; screen fades in on open; no flicker while idle
- [ ] Reset achievements: one summary toast, not dozens
- [ ] How to Play: pause menu > How to Play > back (dimmed backdrop kept); first launch of a game shows it once

## 2. Select button
- [ ] Select tap = pause menu in games (Block Stack: Select/A rotate, B slam)
- [ ] Select = back on Settings, Stats, Trophies, Credits, High Scores, help; Mastermind title: B toggles symbols, Select backs out
- [ ] Portal: Select opens the level menu

## 3. Portrait games (9): Block Stack, Road Cross, Beam Dodge, Asteroid Dodge, Fruit Catch, Space Invaders, Sky Hop, Space Blaster, Tower Stack, Road Racer
- [ ] Turn prompt appears when held landscape, clears when you turn the device
- [ ] Picture upright and controls match; if upside-down use Settings > Portrait: Flip A / Flip B
- [ ] Pause menu, game over slide, High Scores all look right in portrait
- Minesweeper, 2048 and Gap Flyer are landscape again

## 4. vs CPU / 2 PLAYERS games: Tic-Tac-Toe, Connect Four, Reversi, Tank Duel, Mastermind, Checkers
- [ ] Title: Up toggles mode (Reversi/Mastermind/Tank Duel: Down opens Levels), Left/Right = CPU difficulty
- [ ] Checkers 2P: board flips for P2 (Left/Right on title toggles FLIP), Start tap = undo, B on your turn replays the last move
- [ ] Mastermind: Start tap = hint (vs CPU only, costs points); the round-starting Start press must NOT spend a hint

## 5. Other 2-player and challenge modes
- [ ] Settings > 2 Player: P1 then P2 play the SAME round, results screen
- [ ] Challenge #N: same game/tier/seed for the same N (list is now 12 games, so old numbers changed). Mix Mode: 5 games, stars out of 15

## 6. Level creator (25 games)
- [ ] Open with Up on the title (Down on Reversi, Mastermind, Tank Duel)
- [ ] Editor: A paint (hold to drag), B erase, Select = next brush, A+B = pick tile, Start-hold or Select-hold = menu
- [ ] Menu: Test Play, Save (stays in editor), Rename, Tool (pencil/line/rect/filled rect), Copy/Paste, Flip/Rotate/Mirror, Fill, Clear, Undo, Brush...
- [ ] Verified tick appears after clearing a level in Test Play; per-level best + "NEW LEVEL BEST!"
- [ ] Levels menu: thumbnails, Play / Edit / Copy / Delete, "Play All Custom" pack
- [ ] Save, power off, power on: levels and names still there. Settings > Delete levels clears them

## 7. New games, try all four difficulties, pause/restart, game over, 2P
- Block Stack, 2048, Minesweeper, Road Cross, Maze Chase, Lunar Lander, Sky Hop, Beat Tapper, Reversi, Tank Duel, Space Blaster, Tower Stack, Slide 15, Plinko, Lucky Slots, Cube Dash, Flood Fill, Asteroids (A+B = hyperspace), Gem Swap (bomb and colour-clear gems, Down = MOVES mode), Road Racer (themes every 1000 m), Bubble Shooter (bomb and rainbow bubbles), Mastermind, Checkers

## 8. USB drive mode (needs the TinyUSB build)
Build / flash from now on (sketch.yaml makes the TinyUSB stack the default for this sketch):
- `arduino-cli compile --build-path /tmp/pgbuild .`  (= `--fqbn adafruit:samd:adafruit_pygamer_m4:usbstack=tinyusb`)
- `arduino-cli upload -p <PyGamer port> --fqbn adafruit:samd:adafruit_pygamer_m4:usbstack=tinyusb --input-dir /tmp/pgbuild .`
- After the first TinyUSB flash the COM port number may change and the board re-enumerates; if upload cannot find it, double-tap reset (PYGAMERBOOT drive) and re-run `arduino-cli board list`.

Checks:
- [ ] Settings > "USB drive" (after Diagnostics, just above Restore backup): A opens the confirm page; B / Select cancels back to Settings
- [ ] A on the confirm page first copies save.bin / save_ext.bin / save_misc.bin to arcadia/bak/ ("Backup saved" toast, a few hundred ms); the PC then shows arcadia/bak/ with the three copies
- [ ] A starts it: "USB DRIVE ON", "Connect USB to PC" turns into "PC connected" when the PC enumerates it; "Disk activity" flickers while copying
- [ ] PC shows a drive with arcadia/ (save.bin, save_ext.bin, save_misc.bin), levels/, assets/ and README.TXT
- [ ] Copy arcadia/ and levels/ to the PC (backup). Edit nothing, eject (safely remove) the drive, press B (or Select / Start) on the PyGamer: "Rebooting..." then the game restarts with all scores/levels intact
- [ ] Restore test: change a setting or score, enter USB mode, copy the backed-up save.bin back over arcadia/save.bin, eject, press B: the old values are back (the game must NOT write its RAM state over the restored file)
- [ ] Copy a level file (e.g. g0s1a.lvl) in from another unit, eject, B: the level shows in the Levels menu; a junk/short file dropped in as save.bin is ignored (starts fresh, no crash)
- [ ] Achievement "Plugged In" unlocks when the mode is opened; Settings > Reset achievements clears it
- [ ] If Windows asks to format the disk: click Cancel, unplug/replug and wait, or run chkdsk on it. Do not format unless you want to lose everything (the game would recreate its folders)
- [ ] USB cable unplugged / no PC: mode still works, shows "Connect USB to PC"; B still reboots

## 9. Backups, Restore backup, storage-problem screen
- [ ] Settings list order ends: ... Diagnostics, USB drive, Restore backup, then the red DANGER ZONE: Reset achievements, Delete levels, Reset saves, Factory reset (last)
- [ ] Restore backup with no backup yet (fresh unit, never used USB / Reset / Delete): A shows the "No backup" toast, nothing else happens
- [ ] Make a backup (open USB drive mode and press B to cancel on the confirm page does NOT back up; press A, then eject + B, which reboots). Play a game so a score changes, then Settings > Restore backup: A once = "Restore? A=yes", any other button cancels; A again = "Rebooting..." and the game restarts with the OLD scores (the game must not save over the restored files first)
- [ ] Settings > Reset saves (A twice) backs up first when anything was played: afterwards Restore backup brings the scores back. A second Reset right after the first must not replace that backup with the empty one
- [ ] Delete levels (A twice) also copies the save files to arcadia/bak first (levels themselves are not in the backup)
- [ ] Storage-problem screen (hard to provoke; do this only on a unit whose data you can lose): boot with a volume Arcada cannot mount (for example after a Windows format to NTFS/exFAT, or an interrupted USB eject that corrupted the FAT). Expect "STORAGE PROBLEM / The flash disk can't be read." and nothing erased. B / Select / Start, or 30 s idle ("No storage in Ns" counts down), = play without storage (saves stay in RAM, USB drive says "No flash filesystem"). A = second screen "REALLY ERASE?"; release A, hold it 2 s (bar fills) to format; B goes back. After a format the game recreates its folders and starts with default scores
- [ ] A chip that reads completely blank (never formatted) shows "NEW STORAGE / Set up the flash disk?": A formats at once, B skips
- [ ] Normal boots (mountable volume) never show either screen

## 10. Diagnostics (Settings > Diagnostics, 2 pages; Left/Right flips page; hold B or Start for 1 s to leave; achievement "Mechanic")
- [ ] Top row of boxes A B ST SE < > ^ v lights while the button is down (raw device buttons). Press Select: SE lights and the page STAYS open (Select is not "back" here). B and Start also light; they only leave when HELD for 1 s (a bar fills along the bottom)
- [ ] Page 1 joystick: X/Y read about 0 (within +-60) at rest and "Stick: centered"; pushing right gives X positive and the > box, pushing down gives Y positive and the v box (the dot in the little square follows the stick). Values reach about +-500 at the stops
- [ ] Page 1 accelerometer: lying flat X and Y about 0.00 g and Z about +1.00 g (or -1.00 g, depending on the chip orientation); the bars follow. Tilt the RIGHT edge of the screen down (landscape): the Maze line "ax" should go POSITIVE (that is what Tilt Maze expects; if it goes negative use Settings > Tilt: Invert). Tilt the BOTTOM edge down: "ay" should go positive. The X/Y/Z bars show the raw LIS3DH values (before Invert and gain), the "Maze:" line the values after them
- [ ] Page 2 light: cover the sensor and "Light raw" drops toward 0, point it at a lamp and it rises (the auto-backlight uses 0..800); Backlight follows in AUTO, or shows the fixed level in MANUAL
- [ ] Page 2 battery: on battery roughly 3.5-4.2 V; on USB power it reads high (about 4.5-5 V) or pegs near 6.6 V, which is the ADC limit; "n/a" would mean no sensor
- [ ] Page 2 RAM free / min: free is the gap between the heap end and the stack, in KB; min only ever goes down (it is sampled once per frame and once per screen draw, so it is a good estimate, not a guaranteed worst-case stack depth). Play a few big games (Chess, Level editor, Minesweeper) and look again
- [ ] Page 2 Up / Loop: uptime minutes:seconds and the rolling average loop time in ms (about 30-35 ms in menus, which are capped at ~30 fps)
- [ ] Page 2 storage: "Disk: mounted" and "Free X of Y KB" (about 8 MB volume), or "RAM only (no FS)" after choosing play-without-storage; "USB PC: connected" only while a PC has the board enumerated (use USB drive mode to test)
- [ ] Reset achievements clears "Mechanic"; opening Diagnostics earns it again

## 11. Art pack (optional banners, needs the TinyUSB build)
- [ ] PC: `cd tools`, `python make_assets.py` -> "56 banners, 229384 bytes"; out\preview.png looks right
- [ ] Without the pack: title screens (Block Stack, 2048, Slide 15 ...) show the small icon exactly as before; no errors on Serial
- [ ] PyGamer: Settings > USB drive; PC: `powershell -ExecutionPolicy Bypass -File tools\install_assets.ps1` finds the drive, copies assets\banners.bin, says to eject; (with the board NOT in USB mode it refuses: "PyGamer drive not found")
- [ ] Eject on the PC, press B on the PyGamer (reboots). Serial: "Assets: banner pack found"
- [ ] Title screens of the shared-layout games (Block Stack, 2048, Minesweeper, Road Cross, Maze Chase, Lunar Lander, Sky Hop, Beat Tapper, Space Blaster, Tower Stack, Slide 15, Plinko, Lucky Slots, Cube Dash, Flood Fill, Asteroids, Gem Swap, Road Racer, Bubble Shooter, Tilt Slalom): 64x32 banner top-left, name to its right, Best line under the banner, text not overlapping, accent line and prompt still animate, no flicker
- [ ] Left/Right on a title (mode change) redraws the banner cleanly; Mastermind / Checkers / Chess / older games keep their old look
- [ ] First banner shown: toast "Unlocked: Art Lover"; Settings > Reset achievements clears it (it returns on the next banner)
- [ ] Remove: Settings > USB drive, delete assets\banners.bin, eject, B: old icons are back
- [ ] A truncated banners.bin (copy only part of the file): ignored, icons shown, no crash

## 12. Level packs (optional, needs the TinyUSB build)
- [ ] PC: `cd tools`, `python make_packs.py` -> 17 files, 322 levels, 20,257 bytes in out\packs; `python verify_packs.py` -> every file OK, "0 with problems"
- [ ] PyGamer: Settings > USB drive; PC: `powershell -ExecutionPolicy Bypass -File tools\install_assets.ps1 -Packs` copies the g*.pak files into <drive>\packs\ and says to eject (not in USB mode it refuses: "PyGamer drive not found"). The drive also shows an empty packs folder and the README lists it
- [ ] Eject, press B (reboot). Open Sokoban Mini > Levels (Up on the title): row "Browse Packs" is there (also in Lights Out, Flood Fill, Minesweeper, Cube Dash ...); a game without a pack (Snake) shows no such row; with 5 saved slots + Play All Custom the 9 rows still fit above the footer
- [ ] Browse Packs: title + "0/30" counter, list with name, D1..D9 marker, thumbnail of the highlighted level (changes when you move, no stutter), Left/Right pages by 5, B / Select goes back to the Levels menu (thumbnails there still fine)
- [ ] A plays the level (Sokoban, Lights Out, Flood Fill, Mastermind, Cube Dash, Reversi ...) exactly like Test Play; pause menu says "Back to Packs" and returns to the list on the same level; B on the over screen returns too
- [ ] Clear a level: toast "Pack level cleared!", the over screen offers A = next level (games that keep playing, e.g. Sokoban, jump straight to the next); after the last level "Pack finished" and back to the list; ticks appear next to cleared levels and survive a reboot
- [ ] Start on a level copies it to your first free custom slot ("Saved to slot N"; "No free slot" when all 5 are used); it shows up in the Levels menu with the pack name and plays/edits normally
- [ ] Pack levels never change the High Scores screen or a custom slot's best; Plinko pack levels have no ticks (no clear event)
- [ ] Awards: "Pack Rat" after 10 pack levels cleared in total, "Completionist" after clearing every level of one pack (try the 12-level Invaders pack); Settings > Reset achievements keeps the ticks, Reset saves clears them
- [ ] Bad files: truncate g0.pak to ~300 bytes -> the list ends at the last complete level; change the magic or the game byte -> no "Browse Packs" row; a level with a wrong tile id shows greyed "bad" and cannot be played; nothing crashes
- [ ] 2 Player on: no "Browse Packs" row. USB drive mode / RAM-only fallback: packs are never read
- [ ] Remove: Settings > USB drive, delete <drive>\packs\g0.pak, eject, B: the row is gone, saves untouched

## Known unverified guesses
- Accelerometer direction for portrait Auto (override in Settings)
- Tilt Maze tilt sign
- Picker frame rate with icons and parallax stars
- RAM headroom (TinyUSB build): about 96 KB static (data+bss, 95.8 KB) plus two 40 KB screen buffers = about 176 of 192 KB; Diagnostics page 2 shows the live free / minimum free RAM (expect the free figure to stay in the low teens of KB; if the minimum ever drops under ~3 KB, report it)
- Road Racer EXTREME difficulty near top pace

## Portal levels on the drive (/packs/portal.lvl)
Prep: the build BEFORE this change is flashed; run `python tools\make_portal_pack.py` (52 levels, 84,040 bytes).
1. Settings > USB drive; `install_assets.ps1 -Portal`; eject; press B. Then flash the new build.
2. Portal > level menu: still "level number, of 1052", tutorial label "TUTORIAL n/52" for 1-52. Play levels 6-52:
   each plays identically to before (same layout, boxes, doors, emitters, keys; level 52 is the empty sandbox).
   Win screen "next level" advances 52 -> 53 (first generated); tiers/Easy-Hard bar unchanged; reroll still works.
3. Fallback: USB drive mode, delete `packs/portal.lvl`, eject, B. Levels 1-5 are the hand-made tutorials;
   6-52 are generated mazes (solvable, same maze each time for the same number); no crash; numbering the same.
4. Corrupt: (a) truncate the file to ~5 KB -> header check fails -> all of 6-52 generated; (b) change one tile
   char inside a record to `Z` -> only that level is generated, others fine (serial: "Portal: bad pack record n");
   (c) wrong magic -> ignored. (d) RAM-only fallback / USB drive mode: no file access, levels generated.
5. Other games, saves and the USB drive mode still work as before.

## Portal Quest (game 56, /worlds/quest.wld)
Prep: `python tools\make_quest_world.py` (38 regions, 129 crystals, ~20 KB); Settings > USB drive; `install_assets.ps1 -Quest`; eject; press B.
- [ ] Picker shows "PORTAL QUEST" (crystal icon, blurb "Quest: explore a world"), first launch shows How to Play
- [ ] No file: delete `worlds/quest.wld` -> title says "quest.wld not found" + install hint, A re-probes, B backs out, no crash. Truncate/garble the file -> "damaged"; USB drive mode / RAM-only -> "Drive not available"
- [ ] Title: crystals x/129, regions n/38, Left/Right cycles mode (NORMAL SPEED CHILL EXTREME ZEN); Up twice (within 4 s) erases progress
- [ ] Controls: Up/Down walk, Left/Right turn, A reads signs / talks to the orange ring / presses cracked walls, B or a Start TAP opens the world map, Start HOLD / Select pauses
- [ ] Crossing the blue rings at region edges loads the neighbour with no hang (<~0.3 s), you land at the matching doorway, walking back returns to the same spot; no wall-clipping at any doorway; try all 4 directions
- [ ] Crystals: cyan diamonds, HUD counter x/129, sound; K/key: yellow key, HUD "K1"; locked doors (K tiles) consume one key and stay open after leaving/re-entering the region
- [ ] Plate door: push the crate (row of 5 free tiles) onto the plate -> door above the room opens -> 2 crystals in the closet. Leave and return: crate resets
- [ ] Laser branches (temple): push the crate east into the beam column so the beam goes out, walk past on the free row; stepping in the beam respawns you at the checkpoint
- [ ] Ice rooms slide; factory belts carry you and never trap you; swamp mud slows; teleporter maze pads (purple rings) send you between regions and you can always get back
- [ ] Checkpoint (green plate + beam) toast "Checkpoint saved"; Pause > Restart returns to it; EXTREME sends you to the start; ZEN has no lasers
- [ ] Secret closets: face a suspicious wall, A -> "A hidden door opens!" -> crystals inside; stays open after relaunch
- [ ] Crystal Gate (north of the market, needs 90): dark purple wall, opens with a toast at the 90th crystal; Vault diamond -> win screen, "Quest Complete" award, best = crystals
- [ ] Progress survives power cycle: crystals, keys, opened doors/secrets, explored regions on the map, last checkpoint. Pull the power during a crystal pickup several times: the game still loads (two generation files /arcadia/quest0.bin, quest1.bin)
- [ ] Regenerate the world with another --seed: old progress is ignored (world id differs), no crash
- [ ] Theme tints: walls, floor and ceiling change colour per region (Ice blue, Factory orange, Temple gold, Maze green, Swamp murky green, Vault purple, Caves brown, Town normal); hub east = Factory, south = Swamp, SE = Temple; crossing toast reads e.g. "Swamp 27"
- [ ] Serial: no "Quest: bad region" lines in normal play. Normal Portal (1052 levels), other games, saves unchanged; Diagnostics free RAM about 0.8 KB lower

## More games (57-62): Hangman, Wordle, Sudoku mini, Nonogram, Missile Command, Pipe Link
Word list: build `python make_words.py` (tools), Settings > USB drive, `install_assets.ps1 -Words`, eject, press B. File = `/data/words.txt`.
- [ ] Picker shows 6 new games (HANGMAN, WORDLE, SUDOKU MINI, NONOGRAM, MISSILE CMD, PIPE LINK) with icons/blurbs, first launch shows How to Play; High Scores rows read "HANG NORMAL" etc.
- [ ] Every new game: title L/R cycles 4 modes, A starts, B backs out, Select tap / Start hold pauses (Resume/Restart/How to Play/Back), over screen A retry / B back, "NEW BEST!" appears, 2P hot-seat plays both rounds with the identical word/puzzle
- [ ] Hangman: no file -> built-in 60 words still work; with file longer words on HARD (7-10 letters); letters mark green/red, gallows grows, word reveals on loss, next word follows a win; Down on title sets a seed (same words)
- [ ] Wordle: letters typed with A, B / `<` deletes, OK submits; "Need 5 letters" toast; colours correct for repeated letters (e.g. guess SPEED vs ABIDE); keyboard keys remember best colour; EXTREME rejects guesses that ignore clues ("Reuse the clues"); EASY shows the first letter on the keyboard; losing reveals the word
- [ ] Sudoku: puzzle always has a unique solution, given digits cannot be edited, a wrong digit is flagged when you leave the cell (+15 s), timer, solving ends the round; score is seconds (lower = better, High Scores show "Ns")
- [ ] Nonogram: clues match the picture, hold A + move paints, B marks X, wrong fill becomes X and costs 10 s (EASY free), clues grey when a line is done, all 4 sizes fit the screen (8x8: clues on top/left not clipped)
- [ ] Missile Command: crosshair speeds up when held, A/B fires (max 4 in flight), ammo count, fireballs chain-react, cities explode when hit, wave bonus, a city is rebuilt every 3rd wave, splitters on EXTREME / later waves, game over when all 6 cities fall
- [ ] Pipe Link: A on a dot starts a pipe, stepping back undoes, crossing your own pipe cuts back, crossing another colour cuts it, partner dot completes, B lets go, EXTREME needs every cell covered, win -> over screen
- [ ] Achievements: Wordsmith, Green Light, Defender (bests), Sudoku Sage, Pixel Artist, Plumber (EXTREME bests), Word Games, Quick Draw (play 57-59 / 60-62)
- [ ] Other games, saves and the Portal Quest data unchanged; Diagnostics free RAM about 2 KB lower

## Expansion cartridges (/carts/*.arc) and Retro CHIP-8 (game 63)
Prep: `python tools\make_carts.py` (compiles + self-tests 11 carts; the collision guard rejects names that duplicate built-in games), `python tools\make_roms.py`; Settings > USB drive; `install_assets.ps1 -Carts -CleanCarts` (removes retired carts from the drive) then `-Roms`; eject; press B. See tools/README_CARTS.txt and README_CHIP8.txt.
- [ ] Picker: the 11 carts (LIGHT CYCLES, MINI GOLF, BOULDER DIG, BOMBER ARENA, PINBALL, BASE DEFENSE, ARCHERY, FISHING, BOWLING, LIFE LAB, TINY DUNGEON) follow the built-in games in ALL (sorted by name, own icon/colour/blurb); Left cycles filters, the new last one "EXPANSIONS" lists only carts; category filters (ARCADE...) include carts with that blurb prefix; carts cannot be starred (Right does nothing); counter "i/N" counts them
- [ ] No /carts folder or no carts: EXPANSIONS shows "No cartridges found" + install hint, nothing else changes; USB drive mode reboot rescans
- [ ] Cart title: name/icon/3 help lines/tier name, Left/Right cycle the 4 tiers, "Best/Plays" line, A starts, B back; first launch does NOT open the built-in How to Play; Pause > How to Play shows the cart's own page (blurb, 3 lines, author, version)
- [ ] Each cart plays at a steady ~30 fps with sound, particles, screen shake; game over slides in with the headline, big score, "NEW BEST!" on a record, A retry, B back; Select tap / Start hold pauses; Pause > Restart restarts, Back to Games frees it
- [ ] 2P hot-seat (Settings > 2 Player ON): carts with @twoplayer (cycles, golf, dig, bomber, pinball, defense, archery, fishing, bowling, lifelab) run P1 then P2 on the same seed and show RESULTS; dungeon (solo only) ignores the 2P setting
- [ ] After `-CleanCarts` the old carts (MOON LANDER, STAR INVADERS, BRIX, PAIRS, HOPPER, ZAP ZAP, TURBO RACER, SNAKE PLUS, RALLY PONG, METEOR DODGE, SKY RUNNER) are gone from the picker; no cart shares a name or core mechanic with a built-in game
- [ ] Scores persist across reboot (/arcadia/carts.bin); pull the power during a game-over save a few times: scores still load (carts.bin / carts.tmp); delete carts.bin: cart scores reset, nothing else
- [ ] Bad files: truncate a .arc, change a byte of one, rename one to a 25-char name, put a 17th cart in: bad ones are skipped (Diagnostics page 3 counts them), a cart that is corrupt after boot shows "Cart is corrupt", never hangs, B/A returns to the picker
- [ ] RAM: Diagnostics "RAM free" before and after playing a cart returns to the same value (cart memory is freed when you leave); no crash after playing all carts in a row
- [ ] Diagnostics page 3 "EXPANSIONS": carts found/bad, /carts ok, CHIP-8 ROM count, carts.bin records, last cart RAM, last error
- [ ] Achievements: "Expansion Slot" (play any cart to game over), "Cartridge Club" (4 different carts), "Retro Gamer" (run a CHIP-8 ROM); the Awards total is now 110
- [ ] RETRO CHIP-8 in the picker (game 63, chip icon): no /roms or no ROMs -> friendly install message; with ROMs: list, A runs, B back
- [ ] logo.ch8 draws a striped banner with "C8"; keypad.ch8 shows the hex digit of the key you press (preset STD: D-pad 2/4/6/8, A=5, B=0); selftest.ch8 shows a tick (a digit = number of failed checks) under every quirk combination; pong.ch8 with Keys: PONG (or FILE + pong.key) moves the left paddle with Up/Down
- [ ] Select menu: speed changes the pace, quirk toggles take effect immediately, Reset ROM restarts, Exit returns to the list; buzzer beeps when the ST timer runs; display sharp 2x centred
- [ ] Other games, saves, Portal Quest and packs unchanged; High Scores list does not show Retro

## Shelf menu (virtual cartridges) + flash trim
Build note: a mechanical size trim replaced ~840 `setCursor + print` pairs with pt()/ptc() helpers (about 12.8 KB flash). Spot-check that text screens look the same as before (Settings, hub, hi-scores, game titles / over screens, HUD lines).
- [ ] Picker defaults to the SHELF: the highlighted cartridge is centred, raised and larger (bigger icon + 4-letter name on its label), 2 neighbours each side smaller and dimmer on a wooden shelf; name, blurb and "Best ... xN plays" (or "Played xN" / "New!") are shown under the shelf
- [ ] Up/Down slide the row smoothly (wraps at both ends); Left cycles filters (the new row slides in), Right stars, hold Up = Surprise me, hold Down = Awards, hold B = High Scores, B/Select = Settings: all unchanged
- [ ] Cartridge details: favourites get a yellow star sticker at the top-right corner; games with a saved best get a red ribbon at the top-left; expansion carts (/carts) have gold side stripes and gold pins; Portal / Retro (no score) never get a ribbon
- [ ] Filters in the shelf: FAVORITES (empty shows the old "No favorites yet" text screen), RECENT, categories, MOST PLAYED, UNPLAYED, EXPANSIONS with 16 carts and with 1 cart; "i/N" counter matches; no cartridge drawn outside the list (list of 1, 2, 3 items looks sane)
- [ ] A: cartridge lifts, drops to the console slot at the bottom, slides in with a click, brief white flash, then the game's title screen fades in (about 0.6 s). First-time launch still shows How to Play afterwards; carts still open their title screen
- [ ] Settings > "Cartridge anim": Full (default) / Quick (about 0.3 s) / Off (no animation, A goes straight to the title); persists across reboot
- [ ] Back to the menu from a game (B on title, pause > Back to Games, game over > B): the cartridge pops back out of the console (about 0.4 s; none with Off). No pop-out when returning from Settings / Challenges / High Scores / after boot or the attract screen
- [ ] Settings > "Menu: Shelf / List": List shows the OLD list picker exactly as before (rows, highlight bar, blurb strip), Shelf returns; persists across reboot; Settings now has 2 more rows (Menu, Cartridge anim after Auto help): scrolling top to bottom and wrap-around still correct, the ^/v arrows right
- [ ] Reset saves KEEPS Menu and Cartridge anim (like the other settings); Delete levels, Restore backup etc. unchanged
- [ ] Frame rate stays smooth while sliding (no stutter); Diagnostics RAM free about the same as before (+8 bytes static only)

## Factory reset (Settings > Factory reset, last row)
- [ ] Settings still scrolls top to bottom and wraps; Factory reset is the last row after Reset saves; Reset saves / Reset achievements rows unchanged
- [ ] A opens the warning screen (erases scores, stats, settings, levels, progress; installed games/files kept; backup + Restore hint). The A that opened it does not start the hold; releasing A mid-hold resets the bar
- [ ] B or Select cancels at any time (warning screen and during the hold): back to Settings, nothing erased, no backup written
- [ ] Hold A (or Start) about 2 s: "Saving a backup...", "Resetting..." bar, "Done. Backup saved." then any button reboots
- [ ] After reboot: scores/stats/favorites/achievements/trophies empty, brightness/sound/volume/boot mode/menu layout/cartridge anim/portrait/auto help back to defaults, help screens show again, custom levels and slots gone, Portal Quest starts fresh, cartridge scores gone, chess save gone, ghosts gone
- [ ] Kept: /assets/banners.bin, /packs/*, /worlds/quest.wld, /data/words.txt, /carts/*.arc, /roms/*, README.TXT, drive not reformatted (carts and Quest still appear)
- [ ] Settings > Restore backup (A twice) brings the old scores/settings/levels-saved marks back (carts.bin, quest and level files are NOT in the backup)
- [ ] Play Quest, leave it to Settings within 1 s of a change, Factory reset: Quest is fresh after reboot (no late save)
- [ ] Not offered in USB drive mode / RAM-only volume: toast message, nothing erased
- [ ] If a file cannot be removed the screen says "N files could not be removed" before rebooting
- [ ] Ice tile: slide into a wall -> stop dead immediately (no diagonal drift), then a new direction press steers you away; ordinary ice sliding unchanged (Portal levels + Portal Quest).

## Error codes (see tools\README_ERRORCODES.txt for the full table)
- [ ] Settings > SYSTEM has a new row "Error log" (between Diagnostics and USB drive); A opens it, B/Select returns
- [ ] Empty log reads "No errors logged."; with entries the list shows newest first: code, short meaning, age (12s / 3m / 1h, or "old" for an earlier run); U/D moves, the hint for the selected code shows below the list
- [ ] A then A again clears the log (first A only arms, any other button cancels); toast "Error log cleared"; /arcadia/errlog.txt becomes empty
- [ ] Cart: delete a cart's file after listing (or truncate it on the PC), start it: screen "ERROR E302/E303/E304" with message and hint, cart name, A/B returns to games; Diagnostics > Expansions shows "Last error: E3xx"
- [ ] Cart that faults at run time (bad opcode etc.): E310 with the VM text on the detail line
- [ ] CHIP-8: empty .ch8 or one over 3584 B -> E402; delete the ROM while its menu is open -> E401
- [ ] Quest: no quest.wld -> title shows "E502 quest.wld not found"; damaged file -> "E503 quest.wld damaged" (logged); no drive -> "E501"
- [ ] Toasts carry the code: USB drive / Restore / Factory reset on a RAM-only volume show "E105 No flash filesystem"; Restore with no backup "E109 ..."
- [ ] Level editor save with a full disk -> "E204 Save failed (full?)" (editor stays open)
- [ ] Reboot after an error was logged: a toast "Last run: E###, see log" appears once; the following boot (no new error) has no toast
- [ ] errlog.txt is rewritten only when an error happens (not at idle); the same code within 60 s counts once; the file keeps at most 8 lines
- [ ] Errors logged while the disk is unavailable still show in the list (RAM) but are not persisted; USB drive mode never writes errlog.txt
