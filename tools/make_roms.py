#!/usr/bin/env python3
"""make_roms.py - writes a few tiny hand-assembled CHIP-8 programs into tools/out/roms/ and
self-checks them in a reference CHIP-8 interpreter (the same semantics as the firmware's).

All programs are original, written for this project (public domain / CC0); nothing is downloaded.

    python make_roms.py            build + self-check
    python make_roms.py --ascii X  also print the screen of ROM X after a short run
"""
import os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'roms')


# ------------------------------------------------------------------ assembler
class Asm:
    def __init__(self):
        self.items = []     # ('w', word) | ('ref', base, label) | ('lab', name) | ('db', bytes)
        self.labels = {}

    def lab(self, n): self.items.append(('lab', n))
    def w(self, word): self.items.append(('w', word & 0xFFFF))
    def ref(self, base, l): self.items.append(('ref', base, l))
    def db(self, *b): self.items.append(('db', bytes(b)))

    # mnemonics (x, y = register numbers)
    def cls(self): self.w(0x00E0)
    def ret(self): self.w(0x00EE)
    def jp(self, l): self.ref(0x1000, l)
    def call(self, l): self.ref(0x2000, l)
    def seq(self, x, nn): self.w(0x3000 | x << 8 | nn)
    def sne(self, x, nn): self.w(0x4000 | x << 8 | nn)
    def seqr(self, x, y): self.w(0x5000 | x << 8 | y << 4)
    def ld(self, x, nn): self.w(0x6000 | x << 8 | nn)
    def add(self, x, nn): self.w(0x7000 | x << 8 | nn)
    def mov(self, x, y): self.w(0x8000 | x << 8 | y << 4)
    def or_(self, x, y): self.w(0x8001 | x << 8 | y << 4)
    def and_(self, x, y): self.w(0x8002 | x << 8 | y << 4)
    def xor(self, x, y): self.w(0x8003 | x << 8 | y << 4)
    def addr(self, x, y): self.w(0x8004 | x << 8 | y << 4)
    def sub(self, x, y): self.w(0x8005 | x << 8 | y << 4)
    def shr(self, x, y): self.w(0x8006 | x << 8 | y << 4)
    def subn(self, x, y): self.w(0x8007 | x << 8 | y << 4)
    def shl(self, x, y): self.w(0x800E | x << 8 | y << 4)
    def sner(self, x, y): self.w(0x9000 | x << 8 | y << 4)
    def ldi(self, l): self.ref(0xA000, l)
    def jpv0(self, l): self.ref(0xB000, l)
    def rnd(self, x, nn): self.w(0xC000 | x << 8 | nn)
    def drw(self, x, y, n): self.w(0xD000 | x << 8 | y << 4 | n)
    def skp(self, x): self.w(0xE09E | x << 8)
    def sknp(self, x): self.w(0xE0A1 | x << 8)
    def getdt(self, x): self.w(0xF007 | x << 8)
    def waitk(self, x): self.w(0xF00A | x << 8)
    def setdt(self, x): self.w(0xF015 | x << 8)
    def setst(self, x): self.w(0xF018 | x << 8)
    def addi(self, x): self.w(0xF01E | x << 8)
    def font(self, x): self.w(0xF029 | x << 8)
    def bcd(self, x): self.w(0xF033 | x << 8)
    def store(self, x): self.w(0xF055 | x << 8)
    def load(self, x): self.w(0xF065 | x << 8)

    def build(self):
        addr = 0x200
        for it in self.items:
            if it[0] == 'lab':
                self.labels[it[1]] = addr
            elif it[0] == 'db':
                addr += len(it[1])
            else:
                addr += 2
        out = bytearray()
        for it in self.items:
            if it[0] == 'w':
                out += bytes((it[1] >> 8, it[1] & 255))
            elif it[0] == 'ref':
                v = it[1] | self.labels[it[2]]
                out += bytes((v >> 8, v & 255))
            elif it[0] == 'db':
                out += it[1]
        return bytes(out)


# ------------------------------------------------------------------ reference interpreter
FONT = [0xF0, 0x90, 0x90, 0x90, 0xF0, 0x20, 0x60, 0x20, 0x20, 0x70, 0xF0, 0x10, 0xF0, 0x80, 0xF0, 0xF0, 0x10, 0xF0, 0x10, 0xF0,
        0x90, 0x90, 0xF0, 0x10, 0x10, 0xF0, 0x80, 0xF0, 0x10, 0xF0, 0xF0, 0x80, 0xF0, 0x90, 0xF0, 0xF0, 0x10, 0x20, 0x40, 0x40,
        0xF0, 0x90, 0xF0, 0x90, 0xF0, 0xF0, 0x90, 0xF0, 0x10, 0xF0, 0xF0, 0x90, 0xF0, 0x90, 0x90, 0xE0, 0x90, 0xE0, 0x90, 0xE0,
        0xF0, 0x80, 0x80, 0x80, 0xF0, 0xE0, 0x90, 0x90, 0x90, 0xE0, 0xF0, 0x80, 0xF0, 0x80, 0xF0, 0xF0, 0x80, 0xF0, 0x80, 0x80]


class Chip8:
    def __init__(self, rom, shift_vy=True, ls_inc=True, jump_vx=False, vf_reset=True, seed=1):
        self.mem = bytearray(4096)
        self.mem[0x50:0x50 + 80] = bytes(FONT)
        self.mem[0x200:0x200 + len(rom)] = rom
        self.v = [0] * 16
        self.i = 0
        self.pc = 0x200
        self.stack = []
        self.dt = 0
        self.st = 0
        self.keys = 0
        self.prev = 0
        self.disp = [[0] * 64 for _ in range(32)]
        self.q = (shift_vy, ls_inc, jump_vx, vf_reset)
        self.rng = random.Random(seed)

    def step(self):
        m, v = self.mem, self.v
        op = (m[self.pc & 0xFFF] << 8) | m[(self.pc + 1) & 0xFFF]
        pc = self.pc
        self.pc = (pc + 2) & 0xFFF
        x, y, n, nn, nnn = (op >> 8) & 15, (op >> 4) & 15, op & 15, op & 255, op & 0xFFF
        shift_vy, ls_inc, jump_vx, vf_reset = self.q
        t = op >> 12
        if t == 0:
            if op == 0x00E0:
                self.disp = [[0] * 64 for _ in range(32)]
            elif op == 0x00EE and self.stack:
                self.pc = self.stack.pop()
        elif t == 1: self.pc = nnn
        elif t == 2:
            if len(self.stack) < 16:
                self.stack.append(self.pc); self.pc = nnn
        elif t == 3:
            if v[x] == nn: self.pc = (self.pc + 2) & 0xFFF
        elif t == 4:
            if v[x] != nn: self.pc = (self.pc + 2) & 0xFFF
        elif t == 5:
            if n == 0 and v[x] == v[y]: self.pc = (self.pc + 2) & 0xFFF
        elif t == 6: v[x] = nn
        elif t == 7: v[x] = (v[x] + nn) & 255
        elif t == 8:
            a, b, f, setf = v[x], v[y], v[15], True
            if n == 0: r = b; setf = False
            elif n in (1, 2, 3):
                r = (a | b, a & b, a ^ b)[n - 1]
                if vf_reset: f = 0
                else: setf = False
            elif n == 4: s = a + b; r = s & 255; f = int(s > 255)
            elif n == 5: r = (a - b) & 255; f = int(a >= b)
            elif n == 6: s = b if shift_vy else a; r = s >> 1; f = s & 1
            elif n == 7: r = (b - a) & 255; f = int(b >= a)
            elif n == 14: s = b if shift_vy else a; r = (s << 1) & 255; f = s >> 7
            else: return
            v[x] = r
            if setf: v[15] = f
        elif t == 9:
            if n == 0 and v[x] != v[y]: self.pc = (self.pc + 2) & 0xFFF
        elif t == 0xA: self.i = nnn
        elif t == 0xB: self.pc = (nnn + v[x if jump_vx else 0]) & 0xFFF
        elif t == 0xC: v[x] = self.rng.randrange(256) & nn
        elif t == 0xD:
            px0, py0, hit = v[x] & 63, v[y] & 31, 0
            for r in range(n):
                if py0 + r >= 32: break
                bits = m[(self.i + r) & 0xFFF]
                for b in range(8):
                    if px0 + b >= 64: break
                    if bits & (0x80 >> b):
                        if self.disp[py0 + r][px0 + b]: hit = 1
                        self.disp[py0 + r][px0 + b] ^= 1
            v[15] = hit
        elif t == 0xE:
            k = (self.keys >> (v[x] & 15)) & 1
            if (nn == 0x9E and k) or (nn == 0xA1 and not k): self.pc = (self.pc + 2) & 0xFFF
        elif t == 0xF:
            if nn == 0x07: v[x] = self.dt
            elif nn == 0x0A:
                nw = self.keys & ~self.prev
                if not nw: self.pc = pc
                else: v[x] = (nw & -nw).bit_length() - 1
            elif nn == 0x15: self.dt = v[x]
            elif nn == 0x18: self.st = v[x]
            elif nn == 0x1E: self.i = (self.i + v[x]) & 0xFFFF
            elif nn == 0x29: self.i = 0x50 + (v[x] & 15) * 5
            elif nn == 0x33:
                m[self.i & 0xFFF] = v[x] // 100; m[(self.i + 1) & 0xFFF] = (v[x] // 10) % 10; m[(self.i + 2) & 0xFFF] = v[x] % 10
            elif nn == 0x55:
                for k in range(x + 1): m[(self.i + k) & 0xFFF] = v[k]
                if ls_inc: self.i += x + 1
            elif nn == 0x65:
                for k in range(x + 1): v[k] = m[(self.i + k) & 0xFFF]
                if ls_inc: self.i += x + 1

    def run_frames(self, frames, ips=700, keyfn=None):
        per = max(1, ips // 60)
        for f in range(frames):
            self.prev = self.keys
            self.keys = keyfn(f) if keyfn else 0
            for _ in range(per): self.step()
            if self.dt: self.dt -= 1
            if self.st: self.st -= 1

    def ascii(self):
        return '\n'.join(''.join('#' if p else '.' for p in row) for row in self.disp)


# ------------------------------------------------------------------ the programs
def rom_logo():
    """Draw test (IBM-logo style): a striped banner, then the letters C8, then idle."""
    a = Asm()
    a.cls()
    # three striped bars (8x15 sprite) forming a banner, x = 8, 16, 24 .. at y = 8
    a.ldi('bar'); a.ld(0, 6); a.ld(1, 8)
    for i in range(6):
        a.drw(0, 1, 15); a.add(0, 8)
    # hex digit glyphs from the built-in font: C and 8 in the middle band
    a.ld(0, 0xC); a.font(0); a.ld(2, 20); a.ld(3, 12); a.drw(2, 3, 5)
    a.ld(0, 8); a.font(0); a.ld(2, 28); a.drw(2, 3, 5)
    # frame
    a.ldi('hbar'); a.ld(0, 0)
    for xx in range(0, 64, 8):
        a.ld(0, xx); a.ld(1, 0); a.drw(0, 1, 1); a.ld(1, 31); a.drw(0, 1, 1)
    a.lab('idle'); a.jp('idle')
    a.lab('bar'); a.db(0xFF, 0xFF, 0xF0, 0xF0, 0xFC, 0xFC, 0xF0, 0xF0, 0xFC, 0xFC, 0xF0, 0xF0, 0xFF, 0xFF, 0xFF)
    a.lab('hbar'); a.db(0xFF)
    return a.build()


def rom_keypad():
    """Shows the hex digit of the last key pressed (FX0A + FX29)."""
    a = Asm()
    a.lab('top'); a.waitk(0); a.cls(); a.font(0); a.ld(1, 28); a.ld(2, 13); a.drw(1, 2, 5)
    a.ld(3, 4); a.setst(3)
    a.lab('hold'); a.jp('top')
    return a.build()


def rom_selftest():
    """Checks the arithmetic / memory opcodes; draws a tick (all fine) or the failure count."""
    a = Asm()
    a.ld(14, 0)                                   # VE = failures
    def check(reg, val):
        a.seq(reg, val); a.call('fail')
    # add with carry
    a.ld(0, 0x80); a.ld(1, 0x90); a.addr(0, 1); check(0, 0x10); check(15, 1)
    a.ld(0, 0x10); a.ld(1, 0x20); a.addr(0, 1); check(0, 0x30); check(15, 0)
    # sub / borrow
    a.ld(0, 5); a.ld(1, 7); a.sub(0, 1); check(0, 0xFE); check(15, 0)
    a.ld(0, 9); a.ld(1, 4); a.sub(0, 1); check(0, 5); check(15, 1)
    a.ld(0, 3); a.ld(1, 10); a.subn(0, 1); check(0, 7); check(15, 1)
    # shifts (VX = VY first so every quirk agrees)
    a.ld(1, 0x05); a.mov(0, 1); a.shr(0, 1); check(0, 2); check(15, 1)
    a.ld(1, 0x81); a.mov(0, 1); a.shl(0, 1); check(0, 2); check(15, 1)
    # logic
    a.ld(0, 0xF0); a.ld(1, 0x3C); a.and_(0, 1); check(0, 0x30)
    a.ld(0, 0xF0); a.ld(1, 0x0F); a.or_(0, 1); check(0, 0xFF)
    a.ld(0, 0xFF); a.ld(1, 0x0F); a.xor(0, 1); check(0, 0xF0)
    # 7XNN wraps without touching VF
    a.ld(15, 0); a.ld(0, 0xFF); a.add(0, 2); check(0, 1); check(15, 0)
    # BCD + store/load round trip
    a.ld(0, 234); a.ldi('buf'); a.bcd(0)
    a.ld(3, 0); a.ld(4, 0); a.ld(5, 0); a.ldi('buf'); a.load(2); check(0, 2); check(1, 3); check(2, 4)
    a.ld(0, 11); a.ld(1, 22); a.ld(2, 33); a.ldi('buf'); a.store(2)
    a.ld(0, 0); a.ld(1, 0); a.ld(2, 0); a.ldi('buf'); a.load(2); check(0, 11); check(1, 22); check(2, 33)
    # skips
    a.ld(0, 7); a.ld(1, 7); a.ld(6, 0)
    a.seqr(0, 1); a.ld(6, 1); check(6, 0)
    a.ld(1, 8); a.sner(0, 1); a.ld(6, 1); check(6, 0)
    # subroutine call / return, 16-bit I add
    a.call('inc'); a.call('inc'); check(7, 2)
    # sprite collision: drawing the same sprite twice sets VF the second time
    a.ldi('dot'); a.ld(0, 60); a.ld(1, 30); a.drw(0, 1, 1); check(15, 0); a.drw(0, 1, 1); check(15, 1)
    # result: tick or failure digit
    a.cls()
    a.seq(14, 0); a.jp('bad')
    a.ldi('tick'); a.ld(0, 28); a.ld(1, 12); a.drw(0, 1, 5); a.jp('done')
    a.lab('bad'); a.font(14); a.ld(0, 28); a.ld(1, 12); a.drw(0, 1, 5)
    a.lab('done'); a.jp('done')
    a.lab('fail'); a.add(14, 1); a.ret()
    a.lab('inc'); a.add(7, 1); a.ret()
    a.lab('tick'); a.db(0x08, 0x10, 0x20, 0x94 & 0xFF, 0x48)
    a.lab('dot'); a.db(0x80)
    a.lab('buf'); a.db(0, 0, 0, 0)
    return a.build()


def rom_pong():
    """One-player pong. Keys 1/4 move the left paddle (use the PONG key preset: Up=1, Down=4).
    A miss costs nothing but is counted in the top-left digit."""
    a = Asm()
    a.cls()
    a.ld(0, 13); a.ld(5, 13); a.ld(1, 32); a.ld(2, 16); a.ld(3, 1); a.ld(4, 1); a.ld(7, 0); a.ld(0xB, 0)
    a.call('drawall')
    a.lab('loop')
    a.ld(8, 2); a.setdt(8)                         # ~30 frames per second
    # ---- update
    a.ld(8, 1); a.sknp(8); a.jp('mvup')
    a.lab('aup'); a.ld(8, 4); a.sknp(8); a.jp('mvdn')
    a.lab('adn')
    a.addr(1, 3); a.addr(2, 4)                     # ball
    a.sne(2, 0); a.ld(4, 1)
    a.sne(2, 30); a.ld(4, 0xFF)
    # CPU paddle: moves toward the ball on every other frame
    a.add(0xB, 1); a.mov(9, 0xB); a.ld(10, 1); a.and_(9, 10); a.seq(9, 1); a.jp('cpudone')
    a.mov(9, 5); a.add(9, 2)                       # paddle centre
    a.mov(10, 2); a.sub(10, 9); a.seq(15, 1); a.jp('cpuup')   # ball y >= centre ?
    a.sne(5, 26); a.jp('cpudone'); a.add(5, 1); a.jp('cpudone')
    a.lab('cpuup'); a.seq(5, 0); a.add(5, 0xFF)
    a.lab('cpudone')
    # left paddle hit
    a.sne(1, 3); a.jp('lchk')
    a.lab('afl')
    a.sne(1, 60); a.jp('rchk')
    a.lab('afr')
    a.sne(1, 0); a.jp('miss')
    a.sne(1, 63); a.jp('serve')
    a.lab('draw')
    a.call('drawall')
    a.lab('wait'); a.getdt(8); a.seq(8, 0); a.jp('wait')
    a.call('drawall')                              # erase (XOR) before the next update
    a.jp('loop')
    a.lab('mvup'); a.seq(0, 0); a.add(0, 0xFF); a.jp('aup')
    a.lab('mvdn'); a.sne(0, 26); a.jp('adn'); a.add(0, 1); a.jp('adn')
    a.lab('lchk')
    a.mov(9, 2); a.sub(9, 0); a.seq(15, 1); a.jp('afl')
    a.ld(10, 5); a.sub(10, 9); a.seq(15, 1); a.jp('afl')
    a.ld(3, 1); a.ld(8, 3); a.setst(8); a.jp('afl')
    a.lab('rchk')
    a.mov(9, 2); a.sub(9, 5); a.seq(15, 1); a.jp('afr')
    a.ld(10, 5); a.sub(10, 9); a.seq(15, 1); a.jp('afr')
    a.ld(3, 0xFF); a.ld(8, 3); a.setst(8); a.jp('afr')
    a.lab('miss')
    a.add(7, 1); a.sne(7, 10); a.ld(7, 0)
    a.ld(1, 20); a.ld(2, 16); a.ld(3, 1); a.ld(8, 10); a.setst(8); a.jp('draw')
    a.lab('serve')
    a.ld(1, 40); a.ld(2, 16); a.ld(3, 0xFF); a.jp('draw')
    a.lab('drawall')
    a.ldi('ball'); a.drw(1, 2, 1)
    a.ldi('pad'); a.ld(9, 2); a.drw(9, 0, 6)
    a.ld(9, 61); a.drw(9, 5, 6)
    a.font(7); a.ld(9, 30); a.ld(10, 1); a.drw(9, 10, 5)
    a.ret()
    a.lab('ball'); a.db(0x80)
    a.lab('pad'); a.db(0x80, 0x80, 0x80, 0x80, 0x80, 0x80)
    return a.build()


ROMS = {'logo': rom_logo, 'keypad': rom_keypad, 'selftest': rom_selftest, 'pong': rom_pong}


def check_roms(roms):
    # selftest must finish with no failures under every quirk set
    for q in [(True, True, False, True), (False, False, True, False), (True, False, False, False), (False, True, False, True)]:
        c = Chip8(roms['selftest'], *q)
        c.run_frames(10)
        tick = sum(map(sum, c.disp))
        c2 = Chip8(roms['selftest'], *q)
        c2.run_frames(10)
        assert c.v[14] == 0, 'selftest failed %d checks under quirks %s' % (c.v[14], q)
        assert tick > 0, 'selftest drew nothing'
    # logo draws something
    c = Chip8(roms['logo']); c.run_frames(20)
    assert sum(map(sum, c.disp)) > 100, 'logo drew too little'
    # keypad: press key 7 after a few frames; expect a glyph and the buzzer
    c = Chip8(roms['keypad'])
    c.run_frames(30, keyfn=lambda f: (1 << 7) if f > 5 else 0)
    assert c.v[0] == 7 and sum(map(sum, c.disp)) > 5
    # pong: ball moves and bounces; paddle keys move the paddle
    c = Chip8(roms['pong'])
    seen = set()
    for f in range(600):
        c.prev = c.keys
        c.keys = (1 << 4) if (f // 40) % 2 else (1 << 1)
        for _ in range(11):
            c.step()
        if c.dt: c.dt -= 1
        if c.st: c.st -= 1
        seen.add((c.v[1], c.v[2]))
    assert len(seen) > 40, 'pong ball does not move (%d positions)' % len(seen)
    assert 0 <= c.v[0] <= 26 and 0 <= c.v[5] <= 26
    print('  CHIP-8 self-checks passed (selftest x4 quirk sets, logo, keypad, pong: %d ball positions)' % len(seen))


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    roms = {}
    for n, f in ROMS.items():
        roms[n] = f()
        open(os.path.join(OUT, n + '.ch8'), 'wb').write(roms[n])
        print('wrote %s.ch8 (%d bytes)' % (n, len(roms[n])))
    # a sample key map: pong uses the Up/Down = 1/4 layout (hex digits: L R U D A B Start)
    open(os.path.join(OUT, 'pong.key'), 'w').write('C D 1 4 5 0 A\n')
    check_roms(roms)
    if '--ascii' in argv:
        n = argv[argv.index('--ascii') + 1]
        c = Chip8(roms[n]); c.run_frames(60)
        print(c.ascii())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
