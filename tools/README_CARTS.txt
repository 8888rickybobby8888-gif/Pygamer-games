ARCADIA EXPANSION CARTRIDGES (.arc)
===================================
Full games that live on the PyGamer's USB drive in /carts and run on a tiny bytecode VM built into
Arcadia. Every cartridge appears in the game picker as a game of its own (after the built-in games in
ALL, and alone under the EXPANSIONS filter: press Left on the picker to cycle filters). They have a
title screen with 4 difficulty tiers, the normal pause menu (Select tap / hold Start), a game-over
screen, per-cart high scores, and hot-seat 2 Player if the cart declares it.

Files in this folder
  make_carts.py     compiler + self-test:  python make_carts.py   (builds tools/out/carts/*.arc)
  arcvm_ref.py      reference interpreter = the specification of the VM (also used by the self-test)
  carts/*.arcl      the cartridge sources (11 games, see below) - read them, copy them, change them
  carts/retired/    old sources that duplicated built-in games (NOT compiled; kept for reference)
  builtin_games.txt the built-in game names used by the collision guard (see below)
  install_assets.ps1 -Carts   copies tools\out\carts\*.arc to <drive>:\carts\

INSTALL
  1. python make_carts.py                      (needs only Python 3; compiles and self-tests every cart)
  2. On the PyGamer: Settings > USB drive      (the drive shows up on the PC)
  3. powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Carts -CleanCarts     (add -Drive E: if needed;
     -CleanCarts removes retired/old carts from the drive and prints each file it removes)
  4. Eject the drive in Windows, THEN press B on the PyGamer (it reboots and scans /carts).
  Up to 16 cartridges are listed (sorted by name). File names must be under 20 characters, *.arc.
  Diagnostics (Settings > Diagnostics, page 3) shows how many carts were found and how many were skipped.
  Scores, play counts and 16 save bytes per cart live in /arcadia/carts.bin (checksummed, written
  atomically). Deleting a cart file keeps its record; deleting carts.bin resets all cart scores.

THE LANGUAGE (ARCL)
  A small C-like language. All numbers are signed 16-bit and wrap. // starts a comment.

  Directives (one per line, before or between code; strings may continue on following lines):
    @name "TINY DUNGEON"          (required, max 15 chars)
    @blurb "Quest: crawl"         (max 23 chars; a "Category:" prefix of Arcade/Reflex/Puzzle/Strategy/Battle
                                   puts the cart into that picker filter and colours it)
    @author "you"  @version 1  @color orange   (picker colour, any palette name below)
    @twoplayer                    the cart supports hot-seat 2P (both players play the same seed)
    @lower                        a LOWER score is better (times, move counts)
    @tiers "NORMAL" "EASY" "HARD" "EXTREME"   four names (max 7 chars), read with tier() = 0..3
    @help "line" "line" "line"    shown on the title screen / pause > How to Play (max 23 chars each)
    @icon "........" x8           8x8 picker icon, '#' = pixel (8 strings of 8)
    @sprite NAME "........" x8    8x8 sprite (up to 64); NAME becomes a constant 0,1,2...

  Declarations:
    const NAME = 5;               var a, b = 3, c;          (globals, set at the start of every round)
    array grid[64];               array t[4] = {1, 2, 3, 4};  (shared "mem": 1024 words in total)
    func name(p1, p2) { ... }     func init() { }   func frame() { }
  frame() is required and runs 30 times a second. init() is optional and runs at the start of each
  round. wait() ends the current frame early and continues after the call next frame (cut-scenes).
  Statements: var x = e;  x = e;  x += e;  (+= -= *= /= %= &= |= ^= <<= >>=)  x++; x--;  a[i] = e;
              if / else if / else   while   for (init; cond; step)   break  continue  return e;
  Expressions: + - * / %  & | ^ ~ << >>  == != < <= > >=  && || !  c ? a : b  f(x)  a[i]  "text"  'c'  0x1F
  Division by zero yields 0. Array indices are clamped to the array. A string value is its offset in
  the string pool (builtins that take text accept literals or such values).
  Predefined constants:
    colours  BLACK WHITE RED GREEN BLUE YELLOW CYAN MAGENTA ORANGE GRAY DKGRAY PINK LIME BROWN NAVY PURPLE
             (colour arguments 0..15 are these palette entries; any other value is a raw RGB565 from rgb())
    buttons  LEFT RIGHT UP DOWN A B   (Start/Select are reserved: pause menu)       SW=160 SH=128

BUILTINS  (x,y in pixels, 0,0 = top left of the 160x128 screen; c = colour)
  drawing   cls(c) pix(x,y,c) rect(x,y,w,h,c) box(x,y,w,h,c) line(x0,y0,x1,y1,c) circ(x,y,r,c)
            disc(x,y,r,c) text(x,y,c,"s") ctext(y,c,"s") num(x,y,c,n) numw(x,y,c,n,width) tsize(1|2)
            spr(x,y,sprite,c) sprf(x,y,sprite,c,flags: 1 flipX, 2 flipY, 4 double size)
            drawmap(base,w,h,ox,oy) draws a tile map stored in mem at array 'base' (cell: low 6 bits = sprite+1,
            0 = empty; bits 6-8 = palette slot set with setpal(slot,c)); getpix(x,y) -> colour or -1
            rgb(r,g,b) -> colour   hit(x1,y1,w1,h1,x2,y2,w2,h2) -> 1 if the rectangles overlap
  tile mem  mget(base,w,h,x,y) -> value or -1 outside   mset(base,w,h,x,y,v)   memfill(base,count,v)
  input     btn(b) held now   btnp(b) pressed this frame
  numbers   rnd(n) 0..n-1   frames() frame counter   sin(a) cos(a) (a = 0..255 full turn, result -127..127)
            sqrt(n)  min max abs sign clamp(v,lo,hi)  fmul(a,b) = a*b/256 (32-bit intermediate)  rndseed(n)
  sound     tone(hz,ms)   sfx(0..7) presets: 0 blip 1 select 2 win 3 crash 4 coin 5 laser 6 low 7 jump
            burst(x,y,count,c) particles (drawn on top automatically)   shake(ms,power 1..4)   led(r,g,b,ms)
  game      addscore(n) score(n) getscore()   gameover("HEADLINE")  ends the round (score is recorded)
            hiscore() best for this tier (-1 if none)   tier() 0..3   player() 1|2   twop() 1 in 2P mode
            saveget(i) saveset(i,v) 16 persistent bytes (0..255) per cart

LIMITS (checked by the compiler, enforced by the VM)
  code 8 KB, strings 2 KB, 64 sprites, 1024 mem words, 128 globals, 60 locals/function, 12 nested calls,
  data stack 64. At most 30000 opcodes per frame ("Cart too slow" error). Any fault (bad memory/
  array/sprite/string access, stack overflow, running off the code) stops the cart, shows its message
  and returns to the picker. A cart cannot touch the drive or anything outside its own memory; the
  16 save bytes are the only thing it can persist. A cart needs about 4-9 KB of free RAM while it runs
  (loaded when you press play, freed when you leave) and says "Not enough memory" if that fails.

FILE FORMAT "ARC1" (little endian)
  header 208 bytes: 0 "ARC1" | 4 u8 format=1 | 5 u8 flags (1 2P, 2 lower-is-better) | 6 u8 version |
    7 u8 sprites | 8 u16 codeLen | 10 u16 strLen | 12 u16 memWords | 14 u16 memInit (words) |
    16 u16 initAddr | 18 u16 frameAddr | 20 u32 FNV-1a(payload) | 24 u8 globals | 25 u8 colour |
    32 name[16] | 48 blurb[24] | 72 author[16] | 88 4 x tier[8] | 120 icon[8] | 128 3 x help[24]
  payload: code, string pool, sprites (8 bytes each), initial mem words (int16).

OPCODES (stack machine; operands little endian; jump targets are absolute code offsets)
  1 PUSH8 s8 | 2 PUSH16 s16 | 3 DUP | 4 DROP | 5 SWAP | 6 OVER
  10 ADD 11 SUB 12 MUL 13 DIV 14 MOD 15 NEG 16 AND 17 OR 18 XOR 19 NOT 20 SHL 21 SHR 22 LNOT
  23 EQ 24 NE 25 LT 26 LE 27 GT 28 GE 29 MIN 30 MAX 31 ABS 32 FMUL 33 CLAMP 34 SIGN
  40 LDG n | 41 STG n | 42 LDL n | 43 STL n | 44 LDM | 45 STM
  50 JMP a16 | 51 JZ a16 | 52 JNZ a16 | 53 CALL a16 nargs nlocals | 54 RET | 55 FRAME (= wait())
  60-122 builtins (see arcvm_ref.py BUILTINS: name -> opcode, argument count, returns-a-value);
  arguments are pushed left to right and popped right to left.

TESTING WITHOUT THE BOARD
  python make_carts.py          compiles, then runs every cart for 8 scripted runs of 1500 frames
                                (idle, button mash, sweeping D-pad, random input on all tiers) and
                                fails on any VM fault or on a frame that uses over 60% of the budget.
  python make_carts.py --shots  also writes tools/out/shots/<cart>.png (rough screenshots, text drawn as boxes)
  python make_carts.py --test-only     re-test the .arc files already built

NOTE: text is transparent (no background box), so a cart must cls() or repaint the area behind
HUD numbers every frame, or the digits stack on top of each other.

THE CARTRIDGES (expansion list - none overlaps a built-in game)
  LIGHT CYCLES  Tron duel vs the CPU on a grid     MINI GOLF     5 putting holes, fewest strokes
  BOULDER DIG   dig dirt, gems, falling rocks      BOMBER ARENA  bomb crates and the CPU
  PINBALL       flippers + bumpers + combos        BASE DEFENSE  build turrets, survive waves
  ARCHERY       wind + steady-aim, 10 arrows       FISHING       hook a fish, reel it in
  BOWLING       10 real frames, curve the ball     LIFE LAB      Conway's Life as a score game
  TINY DUNGEON  turn-based crawler
  The firmware lists at most 16 carts. Keep each cart under about 4.5 KB.

COLLISION GUARD (make_carts.py)
  Expansion carts must not duplicate a built-in game. On every build make_carts.py reads the built-in names from
  ..\PyGamerPortal.ino (kGameNames table) plus toolsuiltin_games.txt (the same list, plus hand-added extras such
  as PONG, TETRIS, FROGGER). It FAILS the build ("BUILT-IN GAME COLLISION ... Pick a different, original game") when a
  cart's @name, compared case-insensitively with spaces/punctuation ignored, equals a built-in name or contains /
  is contained in one (4+ letters). A name that contains a genre keyword of a built-in game (lander, invader, breakout, brick, frogger, pong,
  snake, tetris, racer, memory, pairs, meteor, dodge, whack, zap, runner, ...) also fails; a keyword only in the
  blurb prints a WARNING. The keyword table is
  GENRE_WORDS at the top of the guard section in make_carts.py. When you add a built-in game to the sketch, add its
  name to builtin_games.txt (or just rebuild: the sketch is re-read every time).
