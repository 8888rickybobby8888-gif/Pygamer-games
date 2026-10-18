# Arcadia (PyGamerPortal)

A multi-game collection for the **Adafruit PyGamer (SAMD51)**, written as a single Arduino sketch. It has built-in games, a virtual-cartridge shelf menu, a first-person "Portal" mode with a large streamed adventure (Portal Quest), word and puzzle games, a small CHIP-8 emulator, and a cartridge virtual machine that runs games stored on the board's 8 MB drive.

Most content lives on the board's USB drive, not in the program, so new levels, packs, worlds and games can be added without reflashing.

## Features

- **Game picker:** a cartridge shelf (with a slot-in animation) or a list. Left/Right move between games, Up marks a favourite, Down filters by category.
- **Built-in games:** arcade, puzzle, board and word games, with high scores, achievements and saves.
- **Portal and Portal Quest:** a first-person raycaster. Quest is a large world split into themed regions (Town, Ice, Factory, Temple, Maze, Swamp, Vault, Caves) streamed from the drive.
- **Expansion cartridges:** small games in `.arc` files in `/carts`, run by a built-in virtual machine.
- **CHIP-8:** plays `.ch8` ROMs from `/roms`.
- **On-device level creators** for 25 games, with level packs on the drive.
- **Settings and tools:** grouped Settings menu, error codes with an on-board error log, factory reset, and a USB drive mode.

## Hardware

- Adafruit PyGamer (160x128 screen, 8 MB QSPI flash drive, about 512 KB program flash and about 192 KB RAM).
- The program uses most of the flash (about 96%), so new content is added as data on the drive.

## Build and flash

Requirements: [arduino-cli](https://arduino.github.io/arduino-cli/) with the Adafruit SAMD core and the **Adafruit Arcada** library (its dependencies install with it).

```bash
arduino-cli compile --build-path /tmp/pgbuild
arduino-cli upload -p COMx
```

`sketch.yaml` selects the board (`adafruit:samd:adafruit_pygamer_m4`) with the TinyUSB stack. Double-tap the reset button to enter the bootloader if the board is not detected.

## Put content on the drive

1. On the board, open **Settings > USB drive** so the board appears as a drive on your PC.
2. Run the installer from the `tools` folder, one switch at a time, for example:

```powershell
cd tools
.\install_assets.ps1            # banners
.\install_assets.ps1 -Packs     # level packs
.\install_assets.ps1 -Portal    # Portal levels
.\install_assets.ps1 -Quest     # Quest world
.\install_assets.ps1 -Words     # word list
.\install_assets.ps1 -Carts     # expansion cartridges
.\install_assets.ps1 -Roms      # CHIP-8 ROMs
.\install_assets.ps1 -Levels    # level slot files
```

3. Eject the drive from Windows, or press B on the board.

Use `-Drive D:` if the drive letter is not detected. See the `README_*.txt` files in `tools` for details on each part.

## Desktop creators

Both are single offline HTML files in `tools/creator`. Open them by double-clicking.

- **`arcadia_levels.html` - Level creator.** Tile editors for the 25 level games, Portal levels and the Portal Quest world. Exports the exact files the board loads.
- **`arcadia_gamemaker.html` - Game maker.** A no-code, block-based editor for cartridge games, with a sprite painter, platformer blocks, a background painter, templates and a live preview. It builds the `.arc` file to copy into the drive's `/carts` folder.

## Error codes

Failures show a code such as `E304` with a short message and a hint. The last errors are listed under **Settings > System > Error log**. The full table is in `tools/README_ERRORCODES.txt`.

## Repository layout

| Path | What it is |
|---|---|
| `PyGamerPortal.ino` | The whole program |
| `sketch.yaml` | Board and build settings |
| `TEST_CHECKLIST.md` | Manual test list for each feature |
| `tools/` | Python and PowerShell generators, the installer, and docs |
| `tools/creator/` | The desktop level creator and game maker |
| `tools/out/` | Generated drive files (packs, Quest world, carts, ROMs, words) |
| `ff.c`, `ff.h`, `ffconf.h`, `diskio.h` | FatFs by ChaN |

## Credits and licenses

- FatFs by ChaN is included under its own license (see the headers in `ff.c`).
- The sketch depends on the Adafruit Arcada library and its dependencies, which are not bundled.
- The CHIP-8 ROMs and word list are generated or original files; check their sources before redistributing anything you add.

No license has been chosen for the original code yet. Add a `LICENSE` file before others reuse it.
