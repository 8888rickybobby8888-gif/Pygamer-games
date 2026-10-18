#!/usr/bin/env python3
"""Reference interpreter for the Arcadia cartridge VM ("ARC1" format).

This file is the executable specification of the VM that PyGamerPortal.ino runs.
make_carts.py imports the opcode tables from here, and uses run_cart() to self-test
every cartridge headlessly (no board needed).  Keep this file and the C++ VM
(cartRun() in PyGamerPortal.ino) in lock-step: same opcodes, same int16 maths.

Machine model
  * all values are signed 16-bit (arithmetic wraps); the data stack holds 64 values
  * 128 global slots, a local-variable stack of 128 slots, a call stack of 12 frames
  * "mem": up to 1024 int16 words (arrays, tile maps), bounds checked on every access
  * code is read-only; strings live in a pool, a string value is its pool offset
  * every frame the VM may run at most BUDGET opcodes, then the cart is stopped with an error
"""
import struct, sys, math

BUDGET = 30000
STACK_MAX = 64
LOCALS_MAX = 128
CALLS_MAX = 12
GLOBALS_MAX = 128
MEM_MAX = 1024
SPR_MAX = 64
CODE_MAX = 8192
STR_MAX = 2048
HDR_SIZE = 208
SCREEN_W, SCREEN_H = 160, 128

# ---- core opcodes ------------------------------------------------------------------
CORE = {
    'PUSH8': 1, 'PUSH16': 2, 'DUP': 3, 'DROP': 4, 'SWAP': 5, 'OVER': 6,
    'ADD': 10, 'SUB': 11, 'MUL': 12, 'DIV': 13, 'MOD': 14, 'NEG': 15, 'AND': 16, 'OR': 17,
    'XOR': 18, 'NOT': 19, 'SHL': 20, 'SHR': 21, 'LNOT': 22,
    'EQ': 23, 'NE': 24, 'LT': 25, 'LE': 26, 'GT': 27, 'GE': 28,
    'MIN': 29, 'MAX': 30, 'ABS': 31, 'FMUL': 32, 'CLAMP': 33, 'SIGN': 34,
    'LDG': 40, 'STG': 41, 'LDL': 42, 'STL': 43, 'LDM': 44, 'STM': 45,
    'JMP': 50, 'JZ': 51, 'JNZ': 52, 'CALL': 53, 'RET': 54, 'FRAME': 55,
}
# ---- builtins: name -> (opcode, nargs, returns_value) -------------------------------
BUILTINS = {
    # maths that map to a core opcode (compiled inline by make_carts.py)
    'min': (29, 2, 1), 'max': (30, 2, 1), 'abs': (31, 1, 1), 'fmul': (32, 2, 1),
    'clamp': (33, 3, 1), 'sign': (34, 1, 1),
    'wait': (55, 0, 0),
    # drawing
    'cls': (60, 1, 0), 'pix': (61, 3, 0), 'rect': (62, 5, 0), 'box': (63, 5, 0),
    'line': (64, 5, 0), 'circ': (65, 4, 0), 'disc': (66, 4, 0), 'text': (67, 4, 0),
    'num': (68, 4, 0), 'ctext': (69, 3, 0), 'tsize': (70, 1, 0), 'spr': (71, 4, 0),
    'sprf': (72, 5, 0), 'drawmap': (73, 5, 0), 'setpal': (74, 2, 0), 'getpix': (75, 2, 1),
    'rgb': (76, 3, 1), 'hit': (77, 8, 1), 'numw': (78, 5, 0),
    # input
    'btn': (85, 1, 1), 'btnp': (86, 1, 1),
    # numbers
    'rnd': (90, 1, 1), 'frames': (91, 0, 1), 'sin': (92, 1, 1), 'cos': (93, 1, 1),
    'sqrt': (94, 1, 1), 'rndseed': (95, 1, 0),
    # sound / effects
    'tone': (100, 2, 0), 'sfx': (101, 1, 0), 'burst': (102, 4, 0), 'shake': (103, 2, 0),
    'led': (104, 4, 0),
    # game flow
    'score': (110, 1, 0), 'getscore': (111, 0, 1), 'gameover': (112, 1, 0),
    'hiscore': (113, 0, 1), 'tier': (114, 0, 1), 'player': (115, 0, 1),
    'saveget': (116, 1, 1), 'saveset': (117, 2, 0), 'memfill': (118, 3, 0),
    'mget': (119, 5, 1), 'mset': (120, 6, 0), 'addscore': (121, 1, 0), 'twop': (122, 0, 1),
}
OPNAME = {}
for _k, _v in CORE.items():
    OPNAME[_v] = _k
for _k, _v in BUILTINS.items():
    OPNAME.setdefault(_v[0], _k.upper())


# palette (index -> RGB565); colour arguments < 16 are palette indices, others raw RGB565
def _c565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


PALETTE_RGB = [
    (0, 0, 0), (255, 255, 255), (240, 50, 50), (60, 220, 90), (60, 110, 255), (255, 230, 70),
    (60, 220, 230), (230, 80, 230), (255, 150, 40), (150, 150, 160), (60, 60, 75), (255, 150, 190),
    (160, 240, 60), (150, 90, 40), (20, 30, 110), (140, 80, 220),
]
PALETTE = [_c565(*c) for c in PALETTE_RGB]
COLOR_NAMES = ['BLACK', 'WHITE', 'RED', 'GREEN', 'BLUE', 'YELLOW', 'CYAN', 'MAGENTA', 'ORANGE',
               'GRAY', 'DKGRAY', 'PINK', 'LIME', 'BROWN', 'NAVY', 'PURPLE']

# quarter-wave sine table: SINQ[i] = round(127*sin(2*pi*i/256)), i = 0..64
SINQ = [int(round(127 * math.sin(2 * math.pi * i / 256.0))) for i in range(65)]


def vm_sin(a):
    a &= 255
    if a <= 64:
        return SINQ[a]
    if a <= 128:
        return SINQ[128 - a]
    if a <= 192:
        return -SINQ[a - 128]
    return -SINQ[256 - a]


def w16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def isqrt(n):
    if n <= 0:
        return 0
    return int(math.isqrt(n))


def fnv1a(data):
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


class CartError(Exception):
    pass


class Cart:
    """A parsed .arc file."""
    def __init__(self, blob):
        if len(blob) < HDR_SIZE or blob[:4] != b'ARC1' or blob[4] != 1:
            raise CartError('bad header')
        (self.flags, self.version, self.nspr, self.code_len, self.str_len, self.mem_words,
         self.mem_init, self.init_addr, self.frame_addr, self.checksum, self.nglobals, self.color) = \
            struct.unpack_from('<BBBHHHHHHIBB', blob, 5)
        self.name = blob[32:48].split(b'\0')[0].decode('latin1')
        self.blurb = blob[48:72].split(b'\0')[0].decode('latin1')
        self.author = blob[72:88].split(b'\0')[0].decode('latin1')
        self.tiers = [blob[88 + i * 8: 96 + i * 8].split(b'\0')[0].decode('latin1') for i in range(4)]
        self.icon = list(blob[120:128])
        self.help = [blob[128 + i * 24: 152 + i * 24].split(b'\0')[0].decode('latin1') for i in range(3)]
        pay = blob[HDR_SIZE:]
        want = self.code_len + self.str_len + self.nspr * 8 + self.mem_init * 2
        if len(pay) != want:
            raise CartError('size mismatch')
        if fnv1a(pay) != self.checksum:
            raise CartError('bad checksum')
        if (self.code_len > CODE_MAX or self.str_len > STR_MAX or self.nspr > SPR_MAX or
                self.mem_words > MEM_MAX or self.mem_init > self.mem_words or self.nglobals > GLOBALS_MAX):
            raise CartError('limits')
        o = 0
        self.code = pay[o:o + self.code_len]; o += self.code_len
        self.strs = pay[o:o + self.str_len]; o += self.str_len
        self.sprites = [list(pay[o + i * 8: o + i * 8 + 8]) for i in range(self.nspr)]; o += self.nspr * 8
        self.meminit = list(struct.unpack_from('<%dh' % self.mem_init, pay, o))
        self.two_player = bool(self.flags & 1)
        self.lower_better = bool(self.flags & 2)


class VM:
    """Headless VM.  Drawing is rasterised into a 160x128 array of RGB565 so getpix() works
    and screenshots can be dumped; text is drawn as filled glyph boxes (no font here)."""

    def __init__(self, cart, tier=0, player=1, twop=False, seed=0x12345678, best=-1):
        self.cart = cart
        self.tier = tier & 3
        self.player_no = player
        self.twop = twop
        self.best = best
        self.rng = seed & 0xFFFFFFFF
        self.fb = [0] * (SCREEN_W * SCREEN_H)
        self.render = True      # False = skip rasterising (fast self-tests); arguments are still validated
        self.reset()

    def reset(self):
        c = self.cart
        self.g = [0] * GLOBALS_MAX
        self.mem = [0] * max(c.mem_words, 1)
        for i, v in enumerate(c.meminit):
            self.mem[i] = v
        self.stack = []
        self.lstk = [0] * LOCALS_MAX
        self.lsp = 0
        self.fp = 0
        self.calls = []
        self.pc = 0
        self.phase = 0          # 0 = running __init, 1 = frame loop
        self.suspended = False  # waiting inside wait()
        self.score_v = 0
        self.over = False
        self.over_head = None
        self.frame_no = 0
        self.tsz = 1
        self.pal = [PALETTE[1]] * 8
        self.save = [0] * 16
        self.save_dirty = False
        self.held = 0
        self.pressed = 0
        self.max_ops = 0
        self.sounds = []
        self.start_entry(c.init_addr)

    def start_entry(self, addr):
        self.pc = addr
        self.stack = []
        self.lsp = 0
        self.fp = 0
        self.calls = []

    def err(self, msg):
        raise CartError('%s at pc=%d' % (msg, self.pc))

    def color(self, v):
        v &= 0xFFFF
        return PALETTE[v] if v < 16 else v

    def string(self, off):
        s = self.cart.strs
        if off < 0 or off >= len(s):
            self.err('bad string')
        e = s.find(b'\0', off)
        if e < 0:
            self.err('bad string')
        return s[off:e].decode('latin1')

    def px(self, x, y, c):
        if not self.render:
            return
        if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H:
            self.fb[y * SCREEN_W + x] = c

    def fillrect(self, x, y, w, h, c):
        if not self.render:
            return
        for yy in range(max(y, 0), min(y + h, SCREEN_H)):
            for xx in range(max(x, 0), min(x + w, SCREEN_W)):
                self.fb[yy * SCREEN_W + xx] = c

    def line(self, x0, y0, x1, y1, c):
        if not self.render or max(abs(x0), abs(y0), abs(x1), abs(y1)) > 512:
            return
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        e = dx + dy
        n = 0
        while n < 2000:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * e
            if e2 >= dy:
                e += dy; x0 += sx
            if e2 <= dx:
                e += dx; y0 += sy
            n += 1

    def circle(self, cx, cy, r, c, fill):
        if r < 0 or r > 127 or not self.render:
            return
        for yy in range(-r, r + 1):
            for xx in range(-r, r + 1):
                d = xx * xx + yy * yy
                if (fill and d <= r * r + r // 2) or (not fill and abs(d - r * r) <= r):
                    self.px(cx + xx, cy + yy, c)

    def text(self, x, y, c, s):
        sz = self.tsz
        for i, ch in enumerate(s):
            if ch != ' ':
                self.fillrect(x + i * 6 * sz, y, 5 * sz, 7 * sz, c)

    def sprite(self, x, y, idx, c, flags=0):
        sp = self.cart.sprites
        if idx < 0 or idx >= len(sp):
            self.err('bad sprite')
        sc = 2 if flags & 4 else 1
        for r in range(8):
            row = sp[idx][7 - r if flags & 2 else r]
            for cc in range(8):
                bit = (0x01 << cc) if flags & 1 else (0x80 >> cc)
                if row & bit:
                    if sc == 1:
                        self.px(x + cc, y + r, c)
                    else:
                        self.fillrect(x + cc * 2, y + r * 2, 2, 2, c)

    # ---- one frame ----
    def frame(self, buttons=0):
        """Advance one display frame.  buttons: bit0 L, 1 R, 2 U, 3 D, 4 A, 5 B."""
        if self.over:
            return
        self.pressed = buttons & ~self.held
        self.held = buttons
        self.frame_no += 1
        if not self.suspended and self.phase == 1:
            self.start_entry(self.cart.frame_addr)
        self.suspended = False
        ops = self.run()
        self.max_ops = max(self.max_ops, ops)

    def pop(self):
        if not self.stack:
            self.err('stack underflow')
        return self.stack.pop()

    def push(self, v):
        if len(self.stack) >= STACK_MAX:
            self.err('stack overflow')
        self.stack.append(w16(v))

    def mem_addr(self, a):
        if a < 0 or a >= self.cart.mem_words:
            self.err('mem out of range')
        return a

    def run(self):
        code = self.cart.code
        n = len(code)
        ops = 0
        while True:
            ops += 1
            if ops > BUDGET:
                self.err('cart too slow')
            if self.pc < 0 or self.pc >= n:
                self.err('pc out of range')
            op = code[self.pc]
            self.pc += 1
            if op == 1:
                self.need(1)
                v = code[self.pc]; self.pc += 1
                self.push(v - 256 if v > 127 else v)
            elif op == 2:
                self.need(2)
                v = code[self.pc] | (code[self.pc + 1] << 8); self.pc += 2
                self.push(w16(v))
            elif op == 3:
                a = self.pop(); self.push(a); self.push(a)
            elif op == 4:
                self.pop()
            elif op == 5:
                b = self.pop(); a = self.pop(); self.push(b); self.push(a)
            elif op == 6:
                b = self.pop(); a = self.pop(); self.push(a); self.push(b); self.push(a)
            elif 10 <= op <= 34:
                if op in (15, 19, 22, 31, 34):
                    a = self.pop()
                    r = {15: -a, 19: ~a, 22: int(a == 0), 31: abs(a), 34: (a > 0) - (a < 0)}[op]
                    self.push(r)
                elif op == 33:
                    hi = self.pop(); lo = self.pop(); v = self.pop()
                    self.push(lo if v < lo else hi if v > hi else v)
                else:
                    b = self.pop(); a = self.pop()
                    if op == 10: r = a + b
                    elif op == 11: r = a - b
                    elif op == 12: r = a * b
                    elif op == 13:
                        r = 0 if b == 0 else (abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1)
                    elif op == 14:
                        r = 0 if b == 0 else a - b * ((abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1))
                    elif op == 16: r = a & b
                    elif op == 17: r = a | b
                    elif op == 18: r = a ^ b
                    elif op == 20: r = a << (b & 15)
                    elif op == 21: r = a >> (b & 15)
                    elif op == 23: r = int(a == b)
                    elif op == 24: r = int(a != b)
                    elif op == 25: r = int(a < b)
                    elif op == 26: r = int(a <= b)
                    elif op == 27: r = int(a > b)
                    elif op == 28: r = int(a >= b)
                    elif op == 29: r = min(a, b)
                    elif op == 30: r = max(a, b)
                    elif op == 32: r = (a * b) >> 8
                    else:
                        self.err('bad opcode %d' % op)
                    self.push(r)
            elif op == 40:
                self.need(1); i = self.code_byte()
                if i >= GLOBALS_MAX: self.err('global range')
                self.push(self.g[i])
            elif op == 41:
                self.need(1); i = self.code_byte()
                if i >= GLOBALS_MAX: self.err('global range')
                self.g[i] = self.pop()
            elif op == 42:
                self.need(1); i = self.code_byte()
                if self.fp + i >= LOCALS_MAX: self.err('local range')
                self.push(self.lstk[self.fp + i])
            elif op == 43:
                self.need(1); i = self.code_byte()
                if self.fp + i >= LOCALS_MAX: self.err('local range')
                self.lstk[self.fp + i] = self.pop()
            elif op == 44:
                a = self.pop(); self.push(self.mem[self.mem_addr(a)])
            elif op == 45:
                v = self.pop(); a = self.pop(); self.mem[self.mem_addr(a)] = v
            elif op == 50:
                self.need(2); self.pc = code[self.pc] | (code[self.pc + 1] << 8)
            elif op == 51 or op == 52:
                self.need(2); t = code[self.pc] | (code[self.pc + 1] << 8); self.pc += 2
                v = self.pop()
                if (v == 0) == (op == 51):
                    self.pc = t
            elif op == 53:
                self.need(4)
                t = code[self.pc] | (code[self.pc + 1] << 8)
                na = code[self.pc + 2]; nl = code[self.pc + 3]; self.pc += 4
                if len(self.calls) >= CALLS_MAX: self.err('call depth')
                if self.lsp + nl > LOCALS_MAX or nl < na: self.err('locals overflow')
                if len(self.stack) < na: self.err('stack underflow')
                base = self.lsp
                for k in range(nl):
                    self.lstk[base + k] = 0
                for k in range(na - 1, -1, -1):
                    self.lstk[base + k] = self.pop()
                self.calls.append((self.pc, self.fp, self.lsp))
                self.fp = base
                self.lsp = base + nl
                self.pc = t
            elif op == 54:
                rv = self.pop()
                if not self.calls:
                    # end of the entry stub
                    if self.phase == 0:      # init finished: run the first frame in the same tick
                        self.phase = 1
                        self.start_entry(self.cart.frame_addr)
                        continue
                    return ops
                self.pc, self.fp, self.lsp = self.calls.pop()
                self.push(rv)
            elif op == 55:
                self.suspended = True
                return ops
            elif 60 <= op <= 122:
                self.builtin(op)
                if self.over:
                    return ops
            else:
                self.err('bad opcode %d' % op)

    def code_byte(self):
        b = self.cart.code[self.pc]
        self.pc += 1
        return b

    def need(self, k):
        if self.pc + k > len(self.cart.code):
            self.err('truncated operand')

    def builtin(self, op):
        P = self.pop
        if op == 60:
            c = self.color(P())
            if self.render: self.fb = [c] * (SCREEN_W * SCREEN_H)
        elif op == 61:
            c = self.color(P()); y = P(); x = P(); self.px(x, y, c)
        elif op == 62:
            c = self.color(P()); h = P(); w = P(); y = P(); x = P(); self.fillrect(x, y, w, h, c)
        elif op == 63:
            c = self.color(P()); h = P(); w = P(); y = P(); x = P()
            if w > 0 and h > 0:
                self.fillrect(x, y, w, 1, c); self.fillrect(x, y + h - 1, w, 1, c)
                self.fillrect(x, y, 1, h, c); self.fillrect(x + w - 1, y, 1, h, c)
        elif op == 64:
            c = self.color(P()); y1 = P(); x1 = P(); y0 = P(); x0 = P(); self.line(x0, y0, x1, y1, c)
        elif op == 65 or op == 66:
            c = self.color(P()); r = P(); y = P(); x = P(); self.circle(x, y, r, c, op == 66)
        elif op == 67:
            s = self.string(P()); c = self.color(P()); y = P(); x = P(); self.text(x, y, c, s)
        elif op == 68:
            n = P(); c = self.color(P()); y = P(); x = P(); self.text(x, y, c, str(n))
        elif op == 69:
            s = self.string(P()); c = self.color(P()); y = P()
            self.text((SCREEN_W - len(s) * 6 * self.tsz) // 2, y, c, s)
        elif op == 70:
            v = P(); self.tsz = 2 if v >= 2 else 1
        elif op == 71:
            c = self.color(P()); i = P(); y = P(); x = P(); self.sprite(x, y, i, c)
        elif op == 72:
            f = P(); c = self.color(P()); i = P(); y = P(); x = P(); self.sprite(x, y, i, c, f)
        elif op == 73:
            oy = P(); ox = P(); h = P(); w = P(); base = P()
            if w < 0 or h < 0 or base < 0 or base + w * h > self.cart.mem_words:
                self.err('map out of range')
            for yy in range(h):
                for xx in range(w):
                    v = self.mem[base + yy * w + xx]
                    if v & 63:
                        self.sprite(ox + xx * 8, oy + yy * 8, (v & 63) - 1, self.pal[(v >> 6) & 7])
        elif op == 74:
            c = self.color(P()); i = P()
            if 0 <= i < 8: self.pal[i] = c
        elif op == 75:
            y = P(); x = P()
            self.push(w16(self.fb[y * SCREEN_W + x]) if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H else -1)
        elif op == 76:
            b = P(); g = P(); r = P(); self.push(w16(_c565(r & 255, g & 255, b & 255)))
        elif op == 77:
            h2 = P(); w2 = P(); y2 = P(); x2 = P(); h1 = P(); w1 = P(); y1 = P(); x1 = P()
            self.push(int(x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1))
        elif op == 78:
            w = P(); n = P(); c = self.color(P()); y = P(); x = P()
            w = max(0, min(w, 8))
            self.text(x, y, c, '%0*d' % (w, n))
        elif op == 85:
            n = P(); self.push(int(0 <= n < 6 and (self.held >> n) & 1))
        elif op == 86:
            n = P(); self.push(int(0 <= n < 6 and (self.pressed >> n) & 1))
        elif op == 90:
            n = P()
            self.rng = (self.rng * 1664525 + 1013904223) & 0xFFFFFFFF
            self.push(0 if n <= 0 else ((self.rng >> 16) & 0x7FFF) % n)
        elif op == 91:
            self.push(self.frame_no & 0x7FFF)
        elif op == 92:
            self.push(vm_sin(P()))
        elif op == 93:
            self.push(vm_sin(P() + 64))
        elif op == 94:
            self.push(isqrt(P()))
        elif op == 95:
            self.rng = (P() & 0xFFFF) * 40503 + 1
        elif op == 100:
            ms = P(); f = P(); self.sounds.append(('tone', f, ms))
        elif op == 101:
            self.sounds.append(('sfx', P()))
        elif op == 102:
            c = self.color(P()); n = P(); y = P(); x = P()
        elif op == 103:
            P(); P()
        elif op == 104:
            P(); P(); P(); P()
        elif op == 110:
            self.score_v = P()
        elif op == 111:
            self.push(max(-32768, min(32767, self.score_v)))
        elif op == 112:
            head = P()
            self.over_head = self.string(head)
            self.over = True
        elif op == 113:
            self.push(max(-32768, min(32767, self.best)))
        elif op == 114:
            self.push(self.tier)
        elif op == 115:
            self.push(self.player_no)
        elif op == 116:
            i = P(); self.push(self.save[i & 15])
        elif op == 117:
            v = P(); i = P(); self.save[i & 15] = v & 255; self.save_dirty = True
        elif op == 118:
            v = P(); n = P(); base = P()
            if n < 0 or base < 0 or base + n > self.cart.mem_words: self.err('memfill range')
            for k in range(n): self.mem[base + k] = v
        elif op == 119:
            y = P(); x = P(); h = P(); w = P(); base = P()
            if w < 0 or h < 0 or base < 0 or base + w * h > self.cart.mem_words: self.err('mget range')
            self.push(self.mem[base + y * w + x] if 0 <= x < w and 0 <= y < h else -1)
        elif op == 120:
            v = P(); y = P(); x = P(); h = P(); w = P(); base = P()
            if w < 0 or h < 0 or base < 0 or base + w * h > self.cart.mem_words: self.err('mset range')
            if 0 <= x < w and 0 <= y < h: self.mem[base + y * w + x] = v
        elif op == 121:
            self.score_v += P()
        elif op == 122:
            self.push(int(self.twop))
        else:
            self.err('bad opcode %d' % op)


def run_cart(path_or_blob, frames=600, bot=None, tier=0, seed=0x12345678, quiet=True, render=True):
    """Runs a cart for `frames` frames.  bot(frame_no, vm) -> button mask.
    Returns the VM (check .over, .score_v, .max_ops).  Raises CartError on a VM fault."""
    blob = open(path_or_blob, 'rb').read() if isinstance(path_or_blob, str) else path_or_blob
    cart = Cart(blob)
    vm = VM(cart, tier=tier, seed=seed)
    vm.render = render
    vm.frame(0)
    for f in range(frames):
        if vm.over:
            break
        vm.frame(bot(f, vm) if bot else 0)
    return vm


def dump_png(vm, path, scale=3):
    import zlib
    W, H = SCREEN_W * scale, SCREEN_H * scale
    raw = bytearray()
    for y in range(SCREEN_H):
        row = bytearray([0])
        for x in range(SCREEN_W):
            v = vm.fb[y * SCREEN_W + x] & 0xFFFF
            r = (v >> 8) & 0xF8; g = (v >> 3) & 0xFC; b = (v << 3) & 0xF8
            px = bytes((r | (r >> 5), g | (g >> 6), b | (b >> 5)))
            row += px * scale
        raw += bytes(row) * scale

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        v = run_cart(p, 300)
        print(p, 'over' if v.over else 'running', 'score', v.score_v, 'maxops', v.max_ops)
