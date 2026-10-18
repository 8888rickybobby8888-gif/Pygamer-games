#!/usr/bin/env python3
"""Builds tools/out/quest.wld, the world file for Portal Quest (see README_QUEST.txt).

Python 3 only, no third-party packages.   Usage:  python make_quest_world.py [--seed N] [--out PATH] [--dump]

The world is 8x6 regions of 24x18 tiles: a hub town plus six themed areas (ice caves, swamp, laser
temple, conveyor factory, teleporter maze, crystal vault). Every region is generated, then checked; the
whole world is checked again at the end by a validator that plays it (keys, locks, crystal gates,
secrets, teleports, ice sliding, conveyors) and fails loudly if anything is unreachable.
"""
import argparse, os, random, struct, sys, zlib
from collections import deque

RW, RH = 24, 18                 # region size in tiles (fixed so doorways line up)
WORLD_W, WORLD_H = 8, 6
ROOM = (5, 18, 4, 13)           # interior x0, x1, y0, y1 of the central room
DOOR = {'N': [(0, 11), (0, 12)], 'S': [(RH - 1, 11), (RH - 1, 12)],
        'W': [(8, 0), (9, 0)], 'E': [(8, RW - 1), (9, RW - 1)]}
DV = {'N': (-1, 0), 'S': (1, 0), 'W': (0, -1), 'E': (0, 1)}
OPP = {'N': 'S', 'S': 'N', 'W': 'E', 'E': 'W'}
BLOCK = set('#N~^v<>')
CONV = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}
# object types (must match the sketch)
CRYSTAL, KEY, LOCK, SIGN, CHECK, TELE, SECRET, GATE, WIN, NPC = range(1, 11)
THEME = {'town': 0, 'ice': 1, 'factory': 2, 'temple': 3, 'maze': 4, 'swamp': 5, 'vault': 6}
GATE_NEED = 90


class Reg:
    def __init__(self, x, y, theme):
        self.x, self.y, self.theme = x, y, theme
        self.id = y * WORLD_W + x
        self.links = set()
        self.g = [['#'] * RW for _ in range(RH)]
        self.objs = []          # dicts: type,col,row,flag,a,b,c,d
        self.strs = []
        self.reserved = set()
        self.plate = False
        self.laser = None       # row of the laser branch (5 or 11)
        self.locks = {}         # dir -> lock key name

    def add(self, t, col, row, **kw):
        o = dict(type=t, col=col, row=row, flag=255, a=0, b=0, c=0, d=0)
        o.update(kw)
        self.objs.append(o)
        return o

    def string(self, text):
        assert len(text) <= 120, text
        self.strs.append(text)
        return len(self.strs) - 1


def rect(reg, x0, x1, y0, y1, ch='.'):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            reg.g[y][x] = ch


def base(reg):
    x0, x1, y0, y1 = ROOM
    rect(reg, x0, x1, y0, y1)
    for d in reg.links:
        if d == 'W': rect(reg, 0, 4, 8, 9)
        if d == 'E': rect(reg, 19, RW - 1, 8, 9)
        if d == 'N': rect(reg, 11, 12, 0, 3)
        if d == 'S': rect(reg, 11, 12, 14, RH - 1)


def room_cells(reg):
    x0, x1, y0, y1 = ROOM
    return [(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]


def edge_starts(reg):
    return [(r, c) for d in reg.links for (r, c) in DOOR[d]]


# ---------------------------------------------------------------- movement model
def step_local(g, r, c, d):
    """One D-pad move from stop (r,c). Returns (touched, final, exit_dir|None, trap)."""
    dr, dc = d
    nr, nc = r + dr, c + dc
    if not (0 <= nr < RH and 0 <= nc < RW):
        return [], (r, c), True, False        # walked off the edge (only possible on a doorway)
    if g[nr][nc] in BLOCK or g[nr][nc] == 'K':
        return None
    touched = [(nr, nc)]
    r, c = nr, nc
    for _ in range(120):
        t = g[r][c]
        if t == 'I':
            pass
        elif t in CONV:
            d = CONV[t]
        else:
            if t in 'TU':
                pr = [(rr, cc) for rr in range(RH) for cc in range(RW) if g[rr][cc] == ('U' if t == 'T' else 'T')]
                if pr:
                    r, c = pr[0]
                    touched.append((r, c))
            return touched, (r, c), False, False
        nr, nc = r + d[0], c + d[1]
        if not (0 <= nr < RH and 0 <= nc < RW):
            return touched, (r, c), True, False
        if g[nr][nc] in BLOCK or g[nr][nc] == 'K':
            if t in CONV:
                return touched, (r, c), False, True      # belt into a wall = trap
            return touched, (r, c), False, False         # ice: stop at the obstacle
        r, c = nr, nc
        touched.append((r, c))
    return touched, (r, c), False, True


def reach_local(g, starts):
    stops = set(starts)
    touched = set(starts)
    q = deque(starts)
    exits = set()
    trap = False
    while q:
        r, c = q.popleft()
        for d in DV.values():
            res = step_local(g, r, c, d)
            if res is None:
                continue
            tl, fin, ex, tr = res
            touched.update(tl)
            if tr:
                trap = True
            if ex:
                exits.add((r, c))
            if tl or not ex:
                if fin not in stops and not tr:
                    stops.add(fin)
                    q.append(fin)
    return touched, stops, trap


def region_ok(reg):
    """Doorways mutually reachable (both ways), no belt traps, every reachable stop can get back out."""
    starts = edge_starts(reg)
    if not starts:
        return False
    touched, stops, trap = reach_local(reg.g, starts[:1])
    if trap:
        return False
    for s in starts:
        if s not in touched:
            return False
    for s in stops:
        t2, _, tr = reach_local(reg.g, [s])
        if tr or not any(e in t2 for e in starts):
            return False
    return True


# ---------------------------------------------------------------- region building
def put_plate_room(reg, rng):
    """Closet above the room behind a plate door: push the box (row 6) onto the plate."""
    if reg.laser is not None or reg.theme in ('ice',):
        return False
    g = reg.g
    rect(reg, 7, 9, 1, 2)                      # closet
    g[3][8] = 'D'
    for x in range(10, 17): reg.reserved.add((6, x))
    g[6][11] = '.'
    g[6][13] = 'X'
    g[6][15] = 'P'
    for pos in [(4, 8), (5, 8), (3, 8), (6, 11), (6, 12)]: reg.reserved.add(pos)
    for y in range(1, 3):
        for x in range(7, 10): reg.reserved.add((y, x))
    reg.plate = True
    return True


def put_laser_branch(reg, rr):
    """East branch: lit column at x=21; push the box from (rr,19) east to (rr,21) to block the beam."""
    g = reg.g
    rect(reg, 19, 22, rr, rr + 1)
    g[rr - 1][21] = 'v'                         # emitter in the wall above the corridor
    g[rr][19] = 'X'
    reg.laser = rr
    for y in range(rr - 1, rr + 2):
        for x in range(16, 23): reg.reserved.add((y, x))
    return [(rr, 22), (rr + 1, 22)]             # reward cells


def put_secret(reg, rng):
    """Cracked wall + closet with a reward. Returns reward cells (or [])."""
    cands = [('top', 14), ('bot', 6), ('bot', 14), ('west', 5), ('west', 11)]
    rng.shuffle(cands)
    for kind, v in cands:
        if kind == 'top': cells, sec, inner = [(y, x) for y in (1, 2) for x in range(v, v + 3)], (3, v + 1), (4, v + 1)
        elif kind == 'bot': cells, sec, inner = [(y, x) for y in (15, 16) for x in range(v, v + 3)], (14, v + 1), (13, v + 1)
        else: cells, sec, inner = [(y, x) for y in (v, v + 1) for x in range(1, 4)], (v, 4), (v, 5)
        need = cells + [sec]
        if any(reg.g[y][x] != '#' or (y, x) in reg.reserved for y, x in need):
            continue
        if reg.g[inner[0]][inner[1]] in BLOCK or inner in reg.reserved:
            continue
        for y, x in cells: reg.g[y][x] = '.'
        for y, x in need + [inner]: reg.reserved.add((y, x))
        reg.add(SECRET, sec[1], sec[0], flag='alloc')
        # the wall tile stays '#': the sketch turns it into floor when the flag is set
        return cells
    return []


def decorate(reg, rng):
    g = reg.g
    th = reg.theme
    cells = [p for p in room_cells(reg) if p not in reg.reserved]
    if th == 'town':
        for (y, x) in [(6, 7), (6, 16), (11, 7), (11, 16)]:
            if (y, x) not in reg.reserved: g[y][x] = '#'
        for (y, x) in [(8, 11), (8, 12), (9, 11), (9, 12)]:
            if (y, x) not in reg.reserved and rng.random() < 0.6: g[y][x] = 'N'
    elif th == 'ice':
        for (y, x) in cells: g[y][x] = 'I'
        for _ in range(rng.randint(9, 14)):
            y, x = rng.choice(cells)
            g[y][x] = '#'
    elif th == 'swamp':
        for _ in range(rng.randint(3, 5)):
            cy, cx = rng.choice(cells)
            for dy in range(-1, 2):
                for dx in range(-2, 3):
                    p = (cy + dy, cx + dx)
                    if p in cells and p not in reg.reserved and rng.random() < 0.8: g[p[0]][p[1]] = 'M'
        for _ in range(rng.randint(2, 4)):
            cy, cx = rng.choice(cells)
            if (cy, cx) not in reg.reserved: g[cy][cx] = '~'
    elif th == 'factory':
        lanes = rng.sample([10, 11, 12], 2)
        for i, y in enumerate(lanes):
            ch = 'r' if i == 0 else 'l'
            xs = range(7, 17)
            for x in xs:
                if (y, x) not in reg.reserved: g[y][x] = ch
        for _ in range(rng.randint(2, 4)):
            y, x = rng.choice(cells)
            if g[y][x] == '.': g[y][x] = 'F'
        for _ in range(rng.randint(3, 6)):
            y, x = rng.choice(cells)
            if g[y][x] == '.': g[y][x] = '#'
    elif th == 'temple':
        for (y, x) in [(6, 8), (6, 15), (11, 8), (11, 15)]:
            if (y, x) not in reg.reserved: g[y][x] = 'N'
    elif th == 'maze':
        for _ in range(rng.randint(8, 12)):
            y, x = rng.choice(cells)
            if g[y][x] == '.': g[y][x] = '#'
    elif th == 'vault':
        for (y, x) in [(5, 7), (5, 16), (12, 7), (12, 16), (8, 9), (9, 9), (8, 14), (9, 14)]:
            if (y, x) not in reg.reserved: g[y][x] = 'N'


def free_touch_cells(reg, used):
    touched, stops, _ = reach_local(reg.g, edge_starts(reg)[:1])
    x0, x1, y0, y1 = ROOM
    out = [p for p in touched if y0 <= p[0] <= y1 and x0 <= p[1] <= x1 and p not in used
           and reg.g[p[0]][p[1]] in '.IMF' and p not in reg.reserved]
    out.sort()
    return out


def build_region(reg, seed, spec):
    """spec: dict with n_crystals, plate, laser, secret, key (name), check, signs[], npc, tele pads handled outside."""
    for attempt in range(80):
        rng = random.Random(seed * 1000 + attempt)
        r = Reg(reg.x, reg.y, reg.theme)
        r.links = set(reg.links)
        r.locks = dict(reg.locks)
        base(r)
        rewards = []
        if spec.get('plate'): put_plate_room(r, rng)
        if spec.get('laser'):
            rewards += put_laser_branch(r, spec['laser'])
        sec = []
        if spec.get('secret'):
            sec = put_secret(r, rng)
            if not sec: continue
        decorate(r, rng)
        if not region_ok(r):
            continue
        used = set()
        free = free_touch_cells(r, used)
        need = spec.get('n_crystals', 0) + (1 if spec.get('key') else 0) + (1 if spec.get('check') else 0) + len(spec.get('signs', [])) + (1 if spec.get('npc') else 0) + 2 * spec.get('pads', 0)
        if len(free) < need + 2:
            continue
        rng.shuffle(free)
        take = lambda: free.pop()
        for cell in rewards:        # laser rewards
            r.add(CRYSTAL, cell[1], cell[0], flag='alloc')
        if sec:
            for cell in sec[:2]: r.add(CRYSTAL, cell[1], cell[0], flag='alloc')
        if spec.get('plate'):
            for cell in [(1, 7), (1, 9), (2, 8)][:2]: r.add(CRYSTAL, cell[1], cell[0], flag='alloc')
            r.g[1][8] = '.'
        for _ in range(spec.get('n_crystals', 0)):
            p = take(); r.add(CRYSTAL, p[1], p[0], flag='alloc')
        if spec.get('key'):
            p = take(); k = r.add(KEY, p[1], p[0], flag='alloc'); k['name'] = spec['key']
        if spec.get('check'):
            p = take(); r.add(CHECK, p[1], p[0])
        for text in spec.get('signs', []):
            p = take(); r.add(SIGN, p[1], p[0], a=r.string(text))
        if spec.get('npc'):
            p = take(); r.add(NPC, p[1], p[0], a=r.string(spec['npc']))
        r.pad_cells = [take() for _ in range(2 * spec.get('pads', 0))]
        return r
    raise RuntimeError('could not build region %d,%d (%s)' % (reg.x, reg.y, reg.theme))


# ---------------------------------------------------------------- the world definition
def define_world():
    R = {}
    def reg(x, y, theme): R[(x, y)] = Reg(x, y, theme)
    reg(3, 2, 'town')
    reg(4, 2, 'factory'); reg(3, 3, 'swamp'); reg(4, 3, 'temple')   # hub neighbours look different from Town
    for p in [(2, 2), (1, 2), (0, 2), (1, 1), (0, 1), (1, 3), (0, 3)]: reg(*p, 'ice')
    for p in [(3, 1), (3, 0), (2, 0), (2, 1), (1, 0)]: reg(*p, 'temple')
    for p in [(4, 1), (4, 0)]: reg(*p, 'vault')
    for p in [(5, 2), (6, 2), (7, 2), (6, 1), (7, 1), (6, 3), (7, 3)]: reg(*p, 'factory')
    for p in [(4, 4), (5, 4), (6, 4), (4, 5), (5, 5), (6, 5)]: reg(*p, 'maze')
    for p in [(2, 3), (2, 4), (2, 5), (3, 4), (3, 5), (1, 4), (1, 5)]: reg(*p, 'swamp')
    links = [((3, 2), (4, 2)), ((3, 2), (3, 3)), ((4, 2), (4, 3)), ((3, 3), (4, 3)),
             ((3, 2), (2, 2)), ((2, 2), (1, 2)), ((1, 2), (0, 2)), ((1, 2), (1, 1)), ((1, 1), (0, 1)), ((1, 2), (1, 3)), ((1, 3), (0, 3)),
             ((3, 2), (3, 1)), ((3, 1), (3, 0)), ((3, 0), (2, 0)), ((2, 0), (2, 1)), ((2, 0), (1, 0)),
             ((4, 2), (4, 1)), ((4, 1), (4, 0)),
             ((4, 2), (5, 2)), ((5, 2), (6, 2)), ((6, 2), (7, 2)), ((6, 2), (6, 1)), ((6, 1), (7, 1)), ((6, 2), (6, 3)), ((6, 3), (7, 3)),
             ((4, 3), (4, 4)), ((4, 4), (4, 5)), ((5, 4), (5, 5)), ((6, 4), (6, 5)),
             ((3, 3), (3, 4)), ((3, 4), (3, 5)), ((3, 4), (2, 4)), ((2, 4), (2, 5)), ((2, 4), (2, 3)), ((2, 4), (1, 4)), ((1, 4), (1, 5))]
    for a, b in links:
        ax, ay = a; bx, by = b
        d = {(1, 0): 'E', (-1, 0): 'W', (0, 1): 'S', (0, -1): 'N'}[(bx - ax, by - ay)]
        R[a].links.add(d); R[b].links.add(OPP[d])
    # locks: (region, side) -> key name. A key opens one door.
    R[(3, 2)].locks['N'] = 'A'      # hub square -> temple
    R[(4, 2)].locks['E'] = 'B'      # market -> factory
    R[(4, 3)].locks['S'] = 'C'      # library -> teleporter maze
    R[(6, 3)].locks['E'] = 'D'      # factory inner vault
    return R


SPECS = {
    (3, 2): dict(n_crystals=2, check=True, signs=["Welcome to Portal Quest! Collect crystals. Press B or tap Start for the world map."],
                 npc="Ice caves west, swamp south. Stuck? Walls that look cracked may hide secrets: face them and press A."),
    (4, 2): dict(n_crystals=2, signs=["The Vault north needs 90 crystals. Keep collecting! Locked doors are K."], plate=True),
    (3, 3): dict(n_crystals=3, secret=True, signs=["Marsh garden. Blue rings at room edges lead to the next area."], check=True),
    (4, 3): dict(n_crystals=2, signs=["Library: the teleporter maze lies south. Its door needs a key from the temple."]),
    # ice caves
    (2, 2): dict(n_crystals=3, signs=["Ice! You slide until something stops you. Use the pillars."], check=True),
    (1, 2): dict(n_crystals=3),
    (0, 2): dict(n_crystals=3, secret=True),
    (1, 1): dict(n_crystals=3),
    (0, 1): dict(n_crystals=2, key='A', signs=["A key glints in the cold. Take it to the temple north of the square."]),
    (1, 3): dict(n_crystals=3),
    (0, 3): dict(n_crystals=3, secret=True, signs=["Dead end? Not quite. Press A on suspicious walls."]),
    # swamp
    (3, 4): dict(n_crystals=2, check=True, signs=["The swamp. Mud slows you down. A key is hidden far to the west."]),
    (3, 5): dict(n_crystals=3, plate=True),
    (2, 4): dict(n_crystals=3),
    (2, 5): dict(n_crystals=3, secret=True),
    (2, 3): dict(n_crystals=3),
    (1, 4): dict(n_crystals=3, check=True),
    (1, 5): dict(n_crystals=2, key='B', signs=["Found it! This key opens the door east of the market."]),
    # temple
    (3, 1): dict(n_crystals=2, check=True, signs=["Laser temple. Push the crate into the beam's path to block it."], laser=5),
    (3, 0): dict(n_crystals=2, laser=11),
    (2, 0): dict(n_crystals=2, secret=True, laser=5),
    (2, 1): dict(n_crystals=2, laser=11, signs=["Crates reset when you leave a room. Try again if you get stuck."]),
    (1, 0): dict(n_crystals=2, key='C', check=True, signs=["The temple's treasure: a key for the library's south door."]),
    # factory
    (5, 2): dict(n_crystals=3, check=True, plate=True, signs=["Factory floor. Belts carry you whether you like it or not."]),
    (6, 2): dict(n_crystals=3),
    (7, 2): dict(n_crystals=3, secret=True),
    (6, 1): dict(n_crystals=3, plate=True),
    (7, 1): dict(n_crystals=3, key='D', signs=["This key opens the inner door in the south-east."]),
    (6, 3): dict(n_crystals=3, check=True),
    (7, 3): dict(n_crystals=4, signs=["The factory's treasure room."]),
    # teleporter maze
    (4, 4): dict(n_crystals=2, check=True, pads=2, signs=["Teleporter maze. Pads send you to other rooms. Dead end? Try another pad."]),
    (5, 4): dict(n_crystals=2, pads=2),
    (6, 4): dict(n_crystals=2, pads=2),
    (4, 5): dict(n_crystals=2, pads=1, secret=True),
    (5, 5): dict(n_crystals=2, pads=2),
    (6, 5): dict(n_crystals=3, pads=1, check=True, signs=["Almost there - the crystals are the real treasure."]),
    # vault
    (4, 1): dict(n_crystals=2, check=True, signs=["The Crystal Gate. It opens when you carry 90 crystals."]),
    (4, 0): dict(n_crystals=4, signs=["You made it! Step on the great diamond to complete the quest."]),
}

def build_world(seed):
    R = define_world()
    built = {}
    for (x, y), reg in sorted(R.items(), key=lambda kv: kv[1].id):
        spec = dict(SPECS.get((x, y), {}))
        spec['pads'] = spec.get('pads', 0)
        built[(x, y)] = build_region(reg, seed + reg.id * 7, spec)
    # teleporter pads: every region lists (pad cell, landing cell) pairs; pairs below are bidirectional
    slots = {}
    for key, r in built.items():
        cells = getattr(r, 'pad_cells', [])
        slots[key] = [(cells[2 * i], cells[2 * i + 1]) for i in range(len(cells) // 2)]
    pairs = [(((4, 4), 0), ((5, 5), 0)), (((4, 4), 1), ((4, 5), 0)), (((5, 4), 0), ((6, 4), 0)),
             (((5, 4), 1), ((5, 5), 1)), (((6, 5), 0), ((4, 5), 0))]
    pairs[-1] = (((6, 5), 0), ((6, 4), 1))
    assigned = {}
    for (ka, ia), (kb, ib) in pairs:
        for k, i in ((ka, ia), (kb, ib)):
            assert (k, i) not in assigned, ('pad reused', k, i)
        assigned[(ka, ia)] = (kb, ib)
        assigned[(kb, ib)] = (ka, ia)
    for (k, i), (k2, i2) in assigned.items():
        (pr, pc) = slots[k][i][0]
        (lr, lc) = slots[k2][i2][1]
        built[k].add(TELE, pc, pr, a=built[k2].id, b=lc, c=lr)
    return R, built


def add_locks_gates_win(built):
    """Locks, the crystal gate and the win diamond."""
    # lock tiles: two cells in the corridor of the region that owns the door
    for key, r in built.items():
        for side, name in r.locks.items():
            cells = {'N': [(2, 11), (2, 12)], 'S': [(15, 11), (15, 12)], 'W': [(2, 0)], 'E': [(21, 8), (21, 9)]}[side]
            if side == 'W': cells = [(8, 2), (9, 2)]
            if side == 'E': cells = [(8, 21), (9, 21)]
            if side == 'N': cells = [(2, 11), (2, 12)]
            if side == 'S': cells = [(15, 11), (15, 12)]
            fl = 'lock_' + name
            for (y, x) in cells:
                assert r.g[y][x] == '.', (key, side)
                r.g[y][x] = 'K'
                r.add(LOCK, x, y, flag=fl)
    # crystal gate: vault antechamber, south corridor
    v = built[(4, 1)]
    for x in (11, 12):
        assert v.g[16][x] == '.'
        v.add(GATE, x, 16, a=GATE_NEED)
        v.g[16][x] = 'N'
    w = built[(4, 0)]
    w.add(WIN, 11, 8, flag=255)
    w.add(WIN, 12, 8, flag=255) if False else None


def alloc_flags(built):
    nxt = 0
    for key in sorted(built, key=lambda k: built[k].id):
        for o in built[key].objs:
            if o['type'] == CRYSTAL:
                o['flag'] = nxt; nxt += 1
    ncr = nxt
    names = {}
    for key in sorted(built, key=lambda k: built[k].id):
        for o in built[key].objs:
            f = o['flag']
            if o['type'] == KEY:
                nm = 'key_' + o.get('name', 'x')
                names[nm] = names.get(nm, nxt)
                if names[nm] == nxt: nxt += 1
                o['flag'] = names[nm]
            elif o['type'] == LOCK:
                if f not in names: names[f] = nxt; nxt += 1
                o['flag'] = names[f]
            elif f == 'alloc':
                o['flag'] = nxt; nxt += 1
    # keys are not tied to locks by name (any key opens any lock), only the counts matter
    assert nxt <= 250, nxt
    return ncr, nxt


# ---------------------------------------------------------------- global validator
def validate_world(built, ncr, verbose=True):
    byid = {r.id: r for r in built.values()}
    objat = {}
    for r in byid.values():
        for o in r.objs: objat[(r.id, o['row'], o['col'])] = o
    lockgroups = {}
    for r in byid.values():
        for o in r.objs:
            if o['type'] == LOCK: lockgroups.setdefault(o['flag'], []).append((r.id, o['row'], o['col']))
    start = (built[(3, 2)].id, 8, 6)
    opened = set()
    keys_spent = 0
    for _round in range(200):
        open_cells = set()
        for fl in opened: open_cells.update(lockgroups[fl])
        crystals = 0
        while True:
            reach = explore(byid, built, objat, start, open_cells, crystals)
            c2 = sum(1 for p in reach if objat.get(p) and objat[p]['type'] == CRYSTAL)
            if c2 == crystals: break
            crystals = c2
        keys = sum(1 for p in reach if objat.get(p) and objat[p]['type'] == KEY)
        progressed = False
        for fl, cells in lockgroups.items():
            if fl in opened or keys - len(opened) <= 0: continue
            for (rid, r, c) in cells:
                if any((rid, r + d[0], c + d[1]) in reach for d in DV.values()):
                    opened.add(fl); progressed = True; break
            if progressed: break
        if not progressed: break
    problems = []
    for r in byid.values():
        seen_cells = {}
        for o in r.objs:
            k = (o['row'], o['col'])
            if k in seen_cells: problems.append('two objects on one tile in region %d,%d at %s' % (r.x, r.y, k))
            seen_cells[k] = o
            if r.g[o['row']][o['col']] in BLOCK and o['type'] not in (SECRET, GATE):
                problems.append('object inside a wall in region %d,%d at %s' % (r.x, r.y, k))
    if (3, 2) in built and (8, 6) in {(o['row'], o['col']) for o in built[(3, 2)].objs}:
        problems.append('start tile is occupied')
    for r in byid.values():
        if not any(p[0] == r.id for p in reach): problems.append('region %d,%d never entered' % (r.x, r.y))
        for o in r.objs:
            if o['type'] in (CRYSTAL, KEY, WIN, CHECK, SIGN, NPC, TELE) and (r.id, o['row'], o['col']) not in reach:
                problems.append('unreachable object type %d in region %d,%d at %d,%d' % (o['type'], r.x, r.y, o['col'], o['row']))
    if len(opened) != len(lockgroups): problems.append('locks never opened: %d of %d' % (len(lockgroups) - len(opened), len(lockgroups)))
    total_keys = sum(1 for r in byid.values() for o in r.objs if o['type'] == KEY)
    if total_keys < len(lockgroups): problems.append('fewer keys (%d) than locks (%d)' % (total_keys, len(lockgroups)))
    if ncr < GATE_NEED: problems.append('fewer crystals than the gate needs')
    if verbose:
        print('validator: %d regions, %d crystals (gate needs %d), %d keys, %d locks, reached %d stops' %
              (len(byid), ncr, GATE_NEED, total_keys, len(lockgroups), len(reach)))
    return problems


def explore(byid, built, objat, start, open_cells, crystals):
    def passable(rid, r, c):
        t = byid[rid].g[r][c]
        o = objat.get((rid, r, c))
        if o and o['type'] == GATE: return crystals >= o['a']
        if o and o['type'] == SECRET: return True
        if t == 'K': return (rid, r, c) in open_cells
        return t not in BLOCK
    seen = set()
    reach = set()
    q = deque()

    def touch(p):
        reach.add(p)
        o = objat.get(p)
        if o and o['type'] == TELE:
            stop((o['a'], o['c'], o['b']))

    def stop(p):
        touch(p) if p not in reach else None
        if p not in seen:
            seen.add(p); q.append(p)

    stop(start)
    while q:
        rid, r, c = q.popleft()
        g = byid[rid].g
        for d in DV.values():
            nr, nc = r + d[0], c + d[1]
            if not (0 <= nr < RH and 0 <= nc < RW):
                x, y = rid % WORLD_W, rid // WORLD_W
                nx, ny = x + d[1], y + d[0]
                if (nx, ny) not in built: continue
                side = {(0, 1): 'W', (0, -1): 'E', (1, 0): 'N', (-1, 0): 'S'}[d]
                if side not in built[(nx, ny)].links: continue
                nrid = ny * WORLD_W + nx
                tr, tc = nr % RH, nc % RW
                if passable(nrid, tr, tc): stop((nrid, tr, tc))
                continue
            if not passable(rid, nr, nc): continue
            pr, pc, dd = nr, nc, d
            touch((rid, pr, pc))
            for _ in range(120):
                t = g[pr][pc]
                if t == 'I': pass
                elif t in CONV: dd = CONV[t]
                else: break
                qr, qc = pr + dd[0], pc + dd[1]
                if not (0 <= qr < RH and 0 <= qc < RW) or not passable(rid, qr, qc): break
                pr, pc = qr, qc
                touch((rid, pr, pc))
            fin = (rid, pr, pc)
            if g[pr][pc] in 'TU':
                other = 'U' if g[pr][pc] == 'T' else 'T'
                for rr in range(RH):
                    for cc in range(RW):
                        if g[rr][cc] == other: fin = (rid, rr, cc)
            stop(fin)
    return reach


# ---------------------------------------------------------------- file writer
def pack_region(r):
    objs = b''.join(struct.pack('8B', o['type'], o['col'], o['row'], o['flag'] if isinstance(o['flag'], int) else 255,
                                o['a'], o['b'], o['c'], o['d']) for o in r.objs)
    strs = b''.join(bytes([len(s)]) + s.encode('ascii') for s in r.strs)
    tiles = ''.join(''.join(row) for row in r.g).encode('ascii')
    assert len(r.objs) <= 28 and len(r.strs) <= 12 and len(strs) <= 360, (r.x, r.y, len(r.objs), len(r.strs), len(strs))
    return struct.pack('<BBBBHH', RW, RH, len(r.objs), len(r.strs), len(strs), 0) + objs + strs + tiles


def write_world(built, ncr, path):
    regs = sorted(built.values(), key=lambda r: r.id)
    n = WORLD_W * WORLD_H
    idx_end = 32 + n * 8
    blobs = {r.id: pack_region(r) for r in regs}
    body = b''.join(blobs[r.id] for r in regs)
    world_id = zlib.crc32(body) & 0xFFFFFFFF
    start = built[(3, 2)]
    hdr = b'ARQW' + struct.pack('<BBBBIHHBBBB', 1, WORLD_W, WORLD_H, len(regs), world_id, ncr, GATE_NEED, start.id, 6, 8, 0)
    hdr += b'Portal Quest'.ljust(12, b'\0')
    assert len(hdr) == 32, len(hdr)
    index = b''
    off = idx_end
    for i in range(n):
        if i in blobs:
            r = next(rr for rr in regs if rr.id == i)
            index += struct.pack('<IHBB', off, len(blobs[i]), THEME[r.theme], 0)
            off += len(blobs[i])
        else:
            index += struct.pack('<IHBB', 0, 0, 0, 0)
    data = hdr + index + body
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    return data


def read_back(path, built):
    """Parses the written file the way the sketch does and compares tiles / objects."""
    d = open(path, 'rb').read()
    assert d[:4] == b'ARQW' and d[4] == 1
    w, h, nreg = d[5], d[6], d[7]
    assert 1 <= w <= 8 and 1 <= h <= 8
    found = 0
    for i in range(w * h):
        off, ln, th, _ = struct.unpack_from('<IHBB', d, 32 + i * 8)
        if ln == 0: continue
        assert off >= 32 + w * h * 8 and off + ln <= len(d)
        rw, rh, no, ns, sb, _z = struct.unpack_from('<BBBBHH', d, off)
        assert 1 <= rw <= 40 and 1 <= rh <= 40 and no <= 28 and ns <= 12 and sb <= 360
        assert ln == 8 + no * 8 + sb + rw * rh, (i, ln)
        tiles = d[off + 8 + no * 8 + sb: off + ln]
        assert all(chr(t) in '#N.~IPD^v<>KudlrFMTUX' for t in tiles), 'bad tile char in region %d' % i
        r = next(rr for rr in built.values() if rr.id == i)
        assert tiles == ''.join(''.join(row) for row in r.g).encode()
        p = off + 8 + no * 8
        for _ in range(ns):
            p += 1 + d[p]
        assert p == off + 8 + no * 8 + sb
        found += 1
    assert found == nreg
    return len(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=2024)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'quest.wld'))
    ap.add_argument('--dump', action='store_true', help='print region maps')
    a = ap.parse_args()
    R, built = build_world(a.seed)
    add_locks_gates_win(built)
    for key, r in built.items():
        if not region_ok(r) and not r.laser and not r.plate:
            pass
    ncr, nflags = alloc_flags(built)
    problems = validate_world(built, ncr)
    if problems:
        print('VALIDATION FAILED:')
        for p in problems: print('  -', p)
        sys.exit(1)
    data = write_world(built, ncr, a.out)
    size = read_back(a.out, built)
    print('wrote %s (%d bytes, %d regions, %d crystals, %d flags)' % (a.out, size, len(built), ncr, nflags))
    if a.dump:
        for key in sorted(built, key=lambda k: built[k].id):
            r = built[key]
            print('--- region %d,%d %s links=%s' % (r.x, r.y, r.theme, ''.join(sorted(r.links))))
            for row in r.g: print(''.join(row))


if __name__ == '__main__':
    main()
