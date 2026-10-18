ARCADIA RETRO (CHIP-8)
======================
"RETRO CHIP-8" in the game picker lists the .ch8 programs found in /roms on the PyGamer drive and
runs the one you pick with a CHIP-8 interpreter (64x32 display shown at 2x, 60 Hz timers, buzzer
through the speaker). It has no score. Pick a ROM with Up/Down, A to run, B to go back.

INSTALL
  1. python make_roms.py      writes four small original demo ROMs into tools/out/roms/
                              (logo = draw test, keypad = key tester, selftest = opcode checks, pong)
                              and checks them in a reference interpreter with the same semantics
  2. Settings > USB drive on the PyGamer, then
     powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Roms        (-Drive E: if needed)
  3. Eject the drive in Windows, THEN press B on the PyGamer.
  Any other .ch8 file you own can simply be copied into <drive>:\roms\ the same way (names under
  20 characters, 1..3584 bytes; up to 16 are listed). Nothing is downloaded or bundled except the demos.

CONTROLS
  The 16-key hex pad is mapped from D-pad, A, B and Start (Select opens the menu):
     preset STD    Left 4  Right 6  Up 2  Down 8  A 5  B 0  Start A
     preset PONG   Left C  Right D  Up 1  Down 4  A 5  B 0  Start A
     preset SHOOT  Left 4  Right 6  Up 2  Down 8  A 5  B 5
     preset BLOCK  Left 5  Right 6  Up 4  Down 7  A 4  B 7
     preset FILE   reads <rom>.key next to the ROM
  A .key file holds up to 7 hex digits in the order  Left Right Up Down A B Start,
  e.g. "C D 1 4 5 0 A" (spaces and anything else are ignored). The demo pong.key is included; choose
  "Keys: FILE .key" in the menu to use it. The menu choice is remembered until the next boot.

SELECT MENU (while a ROM runs)
  Resume | Speed (100..2000 instructions/s, default 700) | Keys preset | quirk toggles:
    Shift      VY (original CHIP-8: 8XY6/8XYE shift VY into VX)  or  VX (CHIP-48 / SCHIP style)
    Load/store FX55/FX65 leave I increased by X+1 (original)  or  leave I unchanged
    Jump B     BNNN jumps to NNN+V0 (original)  or  XNN+VX (SCHIP style)
    AND/OR/XOR VF is reset to 0 (original)  or  left alone
  | Reset ROM | Exit to list.
  Defaults are the original COSMAC VIP behaviour, which most classic ROMs expect.

WHAT IS IMPLEMENTED
  All 35 standard CHIP-8 opcodes: 00E0 00EE 1NNN 2NNN 3XNN 4XNN 5XY0 6XNN 7XNN 8XY0..8XY7 8XYE 9XY0
  ANNN BNNN CXNN DXYN EX9E EXA1 FX07 FX0A FX15 FX18 FX1E FX29 FX33 FX55 FX65. Sprites are clipped at the
  right/bottom edge (start coordinates wrap); DXYN sets VF on collision; 4 KB memory with the
  hex font at 0x050 and programs at 0x200; a 16-level call stack (a call beyond that is ignored).
  Not included: SUPER-CHIP / XO-CHIP extras (hi-res mode, scrolling, 16x16 sprites), sound pitch/pattern.
  The firmware interpreter (ch8Exec() in PyGamerPortal.ino) has the same semantics as make_roms.py's reference
  interpreter, and the demo selftest.ch8 verifies arithmetic, flags, BCD, load/store, skips,
  call/return and collisions under all quirk combinations.

MEMORY
  The 4.3 KB machine is allocated only while a ROM runs and freed when you leave; if there is not
  enough free RAM the screen says so instead of starting.
