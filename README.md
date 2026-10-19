# Arcadia (PyGamerPortal)

A multi-game collection for the [Adafruit PyGamer](https://www.adafruit.com/product/4242) (SAMD51 / ATSAMD51J19). It started as a first-person portal puzzle game rendered with a grid raycaster and grew into **Arcadia**: a game picker with 64 built-in games plus expansion cartridges, a settings menu, high scores, achievements, and support for extra content loaded from the board's USB drive.

## Features

- **Portal**: Wolfenstein-style raycaster puzzle game. Fire linked portals, push boxes, dodge lasers, ride ice and use pressure plates. There are 52 hand-made levels plus about 1000 generated mazes.
- **Many built-in games**: 64 in total, including Snake, Breakout, Block Stack, 2048, Minesweeper, Chess, Checkers, Reversi, Sudoku Mini, Wordle, Missile Cmd, Portal Quest and a CHIP-8 emulator. The names are in `kGameNames` in `PyGamerPortal.ino`.
- **Game picker** with icons, favourites, recents, category filters, a screensaver and a random-game shortcut.
- **Settings**: display, sound, tilt controls, diagnostics, a USB drive mode, and save and reset options.
- **Expansion content from the USB drive**:
  - `.arc` cartridges (11 sources included) that run on a built-in bytecode VM
  - level packs
  - art banners
  - the Portal level file
  - Portal Quest world data
  - word lists
  - CHIP-8 ROMs
- **PC-side creators**: browser tools for making levels and games.

## Controls

| Input | Action |
| --- | --- |
| Joystick | Move or navigate |
| A / B | Primary and secondary action. In menus, B is back. |
| Select | Pause menu, or back in menus |
| Start | Context-dependent. In Portal, tap resets the level and a long hold opens level select. |

Each game documents its own controls on its title screen.

## Building and flashing

Requires [`arduino-cli`](https://arduino.github.io/arduino-cli/), the `adafruit:samd` core, and these libraries: Adafruit Arcada, Adafruit TinyUSB Library, Adafruit SPIFlash, and SdFat (Adafruit fork).

`sketch.yaml` selects the board and the TinyUSB USB stack, which the *Settings → USB drive* mode needs.

```sh
arduino-cli compile --build-path /tmp/pgbuild .
arduino-cli upload -p <PyGamer port> --fqbn adafruit:samd:adafruit_pygamer_m4:usbstack=tinyusb --input-dir /tmp/pgbuild .
```

Double-tap reset if the board doesn't show up in `arduino-cli board list`.

## Making your own games

[`docs/HOW_TO_CODE_GAMES.md`](docs/HOW_TO_CODE_GAMES.md) explains the three ways to add a game: the no-code Game Maker, ARCL cartridges and built-in C++ games.

## Repository layout

| Path | Purpose |
| --- | --- |
| `PyGamerPortal.ino` | The firmware: Arcadia, Portal and all built-in games |
| `LevelFlashFormat.cpp`, `ff.c`, `ff.h`, `ffconf.h`, `diskio.h` | Fallback formatter for the onboard QSPI flash, with FatFs vendored from Adafruit's `SdFat_format` example |
| `sketch.yaml` | Default board (FQBN) and USB stack |
| `gen_levels.js` | Seeded generator for Portal levels. Run with `node gen_levels.js`. |
| `gen_textures.js` | Bakes the raycaster textures into 16x16 bitmap tables. Run with `node gen_textures.js`. |
| `level_editor.html`, `level_editor_server.js`, `launch_level_editor.bat`, `launch_level_editor.sh` | Portal level editor. The local server splices levels into the sketch and drives `arduino-cli`. On Windows, run `launch_level_editor.bat`. On macOS and Linux, run `./launch_level_editor.sh`. |
| `docs/HOW_TO_CODE_GAMES.md` | Guide to writing games |
| `TEST_CHECKLIST.md` | Hardware test checklist |
| `tools/` | Python asset builders, cartridge sources and creators (below) |

## Tools (`tools/`)

Python 3 with no extra packages is enough for most scripts. Pillow is optional and gives nicer banner text. Output goes to `tools/out/`, which is not tracked in git. Run the scripts to regenerate it.

| Script | Produces |
| --- | --- |
| `make_carts.py` | Compiles and self-tests `.arc` cartridges from `carts/*.arcl` |
| `make_packs.py`, `verify_packs.py` | Level packs (`g<id>.pak`), plus a check of the generated files |
| `make_assets.py` | `banners.bin` art pack |
| `make_portal_pack.py` | `portal.lvl` from `portal_levels.txt` |
| `make_quest_world.py` | `quest.wld` for Portal Quest |
| `make_words.py` | Word list for Hangman and Wordle |
| `make_roms.py` | CHIP-8 ROMs |
| `install_assets.py`, `install_assets.ps1` | Copy built assets to the PyGamer drive (cross-platform Python, and the Windows PowerShell original) |

The `tools/` folder has a detailed README for each part: `README_CARTS.txt`, `README_PACKS.txt`, `README_ASSETS.txt`, `README_PORTAL.txt`, `README_QUEST.txt`, `README_WORDS.txt`, `README_CHIP8.txt` and `README_ERRORCODES.txt`.

`tools/creator/` holds browser-based editors: `arcadia_levels.html` for levels and `arcadia_gamemaker.html` for games. Their docs are `README_LEVELS.txt` and `README_GAMEMAKER.txt`.

### Installing assets to the board

1. On the PyGamer, open **Settings → USB drive**. The drive appears on your PC.
2. Run `python tools/install_assets.py` with the switch for what you built (`--carts`, `--packs`, `--portal`, `--quest`, `--words`, `--roms`, `--levels`, or none for banners). Add `--drive PATH` if auto-detection fails. On Windows, `powershell -ExecutionPolicy Bypass -File tools/install_assets.ps1` takes the same switches in PowerShell style (`-Carts`, `-Drive E:`).
3. Eject the drive, then press **B** on the PyGamer. It reboots and picks up the new files.

## License

MIT, see [`LICENSE`](LICENSE). The vendored FatFs files (`ff.c`, `ff.h`, `ffconf.h`, `diskio.h`) keep their own licence.
