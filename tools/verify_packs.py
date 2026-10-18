#!/usr/bin/env python3
"""verify_packs.py - checks tools/out/packs/*.pak against the rules the PyGamerPortal sketch enforces.

Usage:  python verify_packs.py [folder]        (default: tools/out/packs next to this script)

Re-implements, per game, the sketch's validate function (see the *ValidateLevel functions in PyGamerPortal.ino)
plus the "really solvable" checks used by make_packs.py (Sokoban BFS, Flood Fill greedy vs move limit, Lights Out
parity, Cube Dash physics bot, Speed Maze BFS ...). make_packs.py imports the rules and solvers from this file, so
generator and verifier can never disagree about what "valid" means.

Pack file format (also documented in the sketch and in README_PACKS.txt):
  header (20 B): "ARPK", version u8 (=1), game u8 (LVLGAME_* id), count u8 (1..60), reserved u8, title[12] ASCII
  record: w u8, h u8, name[8] (A-Z 0-9 space '-'), par u8 (1-9 difficulty marker), cells[w*h] u8 (row-major, tile ids)
"""
import os
import struct
import sys
from collections import deque

MAGIC = b"ARPK"
MAX_LEVELS = 60
MAX_BYTES = 20480
NAME_OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -")

# id: (sketch title, w, h, numTiles)   -- kLevelGames[] rows of the games that have packs
CFG = {
    0: ("SOKOBAN MINI", 7, 7, 5),
    2: ("BREAKOUT", 10, 4, 2),
    4: ("SPEED MAZE", 9, 7, 4),
    5: ("SPACE INVADERS", 5, 3, 2),
    8: ("MINESWEEPER", 10, 8, 2),
    9: ("FLOOD FILL", 10, 10, 6),
    10: ("CUBE DASH", 24, 4, 5),
    11: ("BEAT TAPPER", 16, 4, 2),
    12: ("LUNAR LANDER", 20, 1, 10),
    13: ("LIGHTS OUT", 5, 5, 2),
    15: ("PLINKO", 9, 9, 3),
    16: ("TANK DUEL", 20, 1, 9),
    20: ("BLOCK STACK", 10, 8, 6),
    21: ("REVERSI", 8, 8, 4),
    22: ("GEM SWAP", 8, 8, 7),
    23: ("BUBBLE SHOOTER", 10, 8, 6),
    24: ("MASTERMIND", 5, 1, 9),
}
# games whose success event calls lvlOnClear() (LVL_CLEAR_MASK): only these get completion ticks
NO_CLEAR_EVENT = {15}


# --------------------------------------------------------------------------- shared solvers / rules
def count(cells, t):
    return sum(row.count(t) for row in cells)


def soko_solve(w, h, cells, limit=300000):
    """Shortest number of moves (BFS over player + boxes, pushes only, out-of-grid is a wall) or None."""
    walls, goals, boxes, start = set(), set(), [], None
    for y in range(h):
        for x in range(w):
            t = cells[y][x]
            if t == 1:
                walls.add((x, y))
            elif t == 3:
                goals.add((x, y))
            elif t == 2:
                boxes.append((x, y))
            elif t == 4:
                start = (x, y)
    s0 = (start, tuple(sorted(boxes)))
    if all(b in goals for b in boxes):
        return 0
    seen = {s0}
    q = deque([(s0, 0)])
    while q:
        ((px, py), bx), d = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = px + dx, py + dy
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in walls:
                continue
            nb = bx
            if (nx, ny) in bx:
                bnx, bny = nx + dx, ny + dy
                if not (0 <= bnx < w and 0 <= bny < h) or (bnx, bny) in walls or (bnx, bny) in bx:
                    continue
                nb = tuple(sorted([b for b in bx if b != (nx, ny)] + [(bnx, bny)]))
                if all(b in goals for b in nb):
                    return d + 1
            st = ((nx, ny), nb)
            if st not in seen:
                seen.add(st)
                if len(seen) > limit:
                    return None
                q.append((st, d + 1))
    return None


QUIET = ((0x0E, 0x15, 0x1B, 0x15, 0x0E), (0x15, 0x15, 0x00, 0x15, 0x15))


def lights_parity_ok(cells):
    for q in QUIET:
        par = 0
        for r in range(5):
            for c in range(5):
                if cells[r][c] == 1 and (q[r] & (1 << c)):
                    par ^= 1
        if par:
            return False
    return True


def _lights_press_mask(i):
    r, c = divmod(i, 5)
    m = 0
    for rr, cc in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= rr < 5 and 0 <= cc < 5:
            m |= 1 << (rr * 5 + cc)
    return m


def lights_min_presses(cells):
    """Minimum number of presses that turn the board off (Gaussian elimination over GF(2), kernel has dim 2)."""
    target = 0
    for r in range(5):
        for c in range(5):
            if cells[r][c] == 1:
                target |= 1 << (r * 5 + c)
    cols = [_lights_press_mask(i) for i in range(25)]
    # basis of combinations: (pattern, presses)
    basis = []
    kernel = []
    for i, m in enumerate(cols):
        v, p = m, 1 << i
        for bv, bp in basis:
            if v ^ bv < v:
                v ^= bv
                p ^= bp
        if v:
            basis.append((v, p))
            basis.sort(reverse=True)
        else:
            kernel.append(p)
    v, p = target, 0
    for bv, bp in basis:
        if v ^ bv < v:
            v ^= bv
            p ^= bp
    if v:
        return None
    best = None
    for k in range(1 << len(kernel)):
        pp = p
        for j, kv in enumerate(kernel):
            if k >> j & 1:
                pp ^= kv
        n = bin(pp).count("1")
        if best is None or n < best:
            best = n
    return best


def flood_greedy(w, h, cells):
    """(moves, colours) of a max-gain greedy flood from the top-left cell on the n x n board, n = min(w, h)."""
    n = min(w, h)
    bd = [row[:n] for row in cells[:n]]
    cols = len({v % 6 for row in bd for v in row})
    region = {(0, 0)}
    cur = bd[0][0] % 6

    def grow(reg, colour):
        stack = list(reg)
        reg = set(reg)
        while stack:
            x, y = stack.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < n and 0 <= ny < n and (nx, ny) not in reg and bd[ny][nx] % 6 == colour:
                    reg.add((nx, ny))
                    stack.append((nx, ny))
        return reg

    region = grow(region, cur)
    moves = 0
    while len(region) < n * n:
        best, bc = -1, None
        for c in range(6):
            if c == cur:
                continue
            g = len(grow(region, c))
            if g > best:
                best, bc = g, c
        region = grow(region, bc)
        cur = bc
        moves += 1
        if moves > 200:
            return None, cols
    return moves, cols


def maze_path(w, h, cells):
    """Shortest path length start -> goal over non-wall cells, or None. Also returns border-walled flag."""
    st = gl = None
    for y in range(h):
        for x in range(w):
            if cells[y][x] == 2:
                st = (x, y)
            elif cells[y][x] == 3:
                gl = (x, y)
    q = deque([(st, 0)])
    seen = {st}
    while q:
        (x, y), d = q.popleft()
        if (x, y) == gl:
            return d
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and cells[ny][nx] != 1:
                seen.add((nx, ny))
                q.append(((nx, ny), d + 1))
    return None


def gem_run_at(bd, x, y):
    g = bd[y][x]
    if g > 5:
        return False
    c = 1
    k = x - 1
    while k >= 0 and bd[y][k] == g:
        c += 1
        k -= 1
    k = x + 1
    while k < 8 and bd[y][k] == g:
        c += 1
        k += 1
    if c >= 3:
        return True
    c = 1
    k = y - 1
    while k >= 0 and bd[k][x] == g:
        c += 1
        k -= 1
    k = y + 1
    while k < 8 and bd[k][x] == g:
        c += 1
        k += 1
    return c >= 3


def gem_moves(bd):
    """Number of legal swaps (adjacent swap that creates a run)."""
    n = 0
    for y in range(8):
        for x in range(8):
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if nx > 7 or ny > 7:
                    continue
                bd[y][x], bd[ny][nx] = bd[ny][nx], bd[y][x]
                ok = gem_run_at(bd, x, y) or gem_run_at(bd, nx, ny)
                bd[y][x], bd[ny][nx] = bd[ny][nx], bd[y][x]
                if ok:
                    n += 1
    return n


def bub_nbr(r, c):
    out = []
    sh = r & 1
    if c > 0:
        out.append((r, c - 1))
    if c < 9:
        out.append((r, c + 1))
    for rr in (r - 1, r + 1):
        if rr < 0 or rr >= 11:
            continue
        c0 = c if sh else c - 1
        for j in (0, 1):
            cc = c0 + j
            if 0 <= cc < 10:
                out.append((rr, cc))
    return out


def bub_anchored_ok(cells):
    g = [[cells[r][c] if r < len(cells) else 0 for c in range(10)] for r in range(11)]
    seen = set()
    stack = [(0, c) for c in range(10) if g[0][c]]
    seen.update(stack)
    while stack:
        r, c = stack.pop()
        for rr, cc in bub_nbr(r, c):
            if g[rr][cc] and (rr, cc) not in seen:
                seen.add((rr, cc))
                stack.append((rr, cc))
    return all(not g[r][c] or (r, c) in seen for r in range(11) for c in range(10))


RV_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))


def rev_flips(bd, x0, y0, p):
    if bd[y0][x0] != 0:
        return 0
    tot = 0
    q = 3 - p
    for dx, dy in RV_DIRS:
        x, y, n = x0 + dx, y0 + dy, 0
        while 0 <= x < 8 and 0 <= y < 8 and bd[y][x] == q:
            x += dx
            y += dy
            n += 1
        if n and 0 <= x < 8 and 0 <= y < 8 and bd[y][x] == p:
            tot += n
    return tot


def rev_moves(bd, p):
    return sum(1 for y in range(8) for x in range(8) if rev_flips(bd, x, y, p))


# ---- Cube Dash physics bot (port of cdStep: fixed 1/120 s steps) ----
CD_BASE = (95.0, 120.0, 75.0, 140.0)
CD_RAMP = (0.022, 0.030, 0.016, 0.034)
CD_X0, CD_PITCH, CD_GROUND, CD_CUBE_X = 240, 64, 100, 36
CD_KIND = {1: (0, 12), 2: (2, 16), 3: (3, 34), 4: (1, 24)}   # tile -> (type, width)


def cube_obstacles(cells):
    obs = []
    idx = 0
    for row in cells:
        for t in row:
            if t in CD_KIND:
                ty, w = CD_KIND[t]
                obs.append((CD_X0 + idx * CD_PITCH + 16, ty, w))
            idx += 1
    return obs, CD_X0 + idx * CD_PITCH + 90


def _cd_step(st, obs, tier, want, hstep=1.0 / 120.0):
    scroll, cy, vy, ground = st
    scroll += min(210.0, CD_BASE[tier] + CD_RAMP[tier] * scroll) * hstep
    cxw = scroll + CD_CUBE_X
    prev_bottom = cy + 12.0
    if ground and want:
        vy = -260.0
        ground = False
    vy += 800.0 * hstep
    cy += vy * hstep
    cc = cxw + 6.0
    in_pit = any(ty == 3 and ox <= cc <= ox + w for ox, ty, w in obs)
    surf = 1e9 if in_pit else float(CD_GROUND)
    for ox, ty, w in obs:
        if ty == 2 and cxw + 11.0 > ox and cxw + 1.0 < ox + 16.0:
            top = float(CD_GROUND - 14)
            if prev_bottom <= top + 4.0 and top < surf:
                surf = top
    if vy >= 0.0 and cy + 12.0 >= surf:
        cy = surf - 12.0
        vy = 0.0
        ground = True
    else:
        ground = False
    if in_pit and cy + 12.0 > CD_GROUND + 6:
        return None
    if cy > 135.0:
        return None
    hx0, hx1, hy0, hy1 = cxw + 2.0, cxw + 10.0, cy + 1.0, cy + 11.0
    for ox, ty, w in obs:
        if ty == 3:
            continue
        if ty == 2:
            ox0, ox1, oy0 = ox, ox + 16.0, float(CD_GROUND - 14)
        else:
            ox0, ox1, oy0 = ox + 3.0, ox + w - 3.0, float(CD_GROUND - 9)
        if hx1 > ox0 and hx0 < ox1 and hy1 > oy0 and hy0 < float(CD_GROUND):
            return None
    return (scroll, cy, vy, ground)


def cube_bot_ok(cells, tier):
    """True when a bot that takes off a few pixels before each hazard (searching over takeoff distances) reaches the
    finish line at this speed tier. Not a proof for a human, but every hazard needs a real jump and none is impossible."""
    obs, finish = cube_obstacles(cells)
    cands = (24, 20, 28, 16, 32, 12, 36, 8, 40, 4, 48, 56)
    dead = set()

    def next_dist(st):
        cxw = st[0] + CD_CUBE_X
        for ox, ty, w in obs:
            if ox + w > cxw + 2.0:
                return ox - (cxw + 10.0)
        return None

    def plan(st, depth):
        key = (round(st[0], 1), round(st[1], 1))
        if key in dead or depth > 400:
            return False
        for D in cands:
            s = st
            ok = True
            for _ in range(20000):
                if s[0] + CD_CUBE_X >= finish:
                    return True
                nd = next_dist(s)
                if nd is None:                      # nothing left: run to the line
                    pass
                elif s[3] and nd <= D:
                    break
                s = _cd_step(s, obs, tier, False)
                if s is None:
                    ok = False
                    break
            else:
                ok = False
            if not ok:
                continue
            s = _cd_step(s, obs, tier, True)        # jump, then fly / land
            for _ in range(20000):
                if s is None:
                    break
                if s[0] + CD_CUBE_X >= finish:
                    return True
                if s[3]:
                    break
                s = _cd_step(s, obs, tier, False)
            if s is None:
                continue
            if plan(s, depth + 1):
                return True
        dead.add(key)
        return False

    return plan((0.0, float(CD_GROUND - 12), 0.0, True), 0)


# --------------------------------------------------------------------------- per-game validators
# each returns (ok, reason, metric)   metric = a difficulty number the generator can rank by (or None)
def v_soko(w, h, cells):
    box, goal, st = count(cells, 2), count(cells, 3), count(cells, 4)
    if st != 1:
        return False, "need exactly 1 start", None
    if box < 1 or box > 2:
        return False, "need 1-2 boxes", None
    if goal != box:
        return False, "goals must match boxes", None
    n = soko_solve(w, h, cells)
    if n is None:
        return False, "unsolvable", None
    return True, "", n


def v_brk(w, h, cells):
    return (count(cells, 1) >= 1, "need a brick", count(cells, 1))


def v_inv(w, h, cells):
    return (count(cells, 1) >= 1, "need an enemy", count(cells, 1))


def v_maze(w, h, cells):
    if count(cells, 2) != 1 or count(cells, 3) != 1:
        return False, "need 1 start + 1 goal", None
    if any(cells[0][c] != 1 or cells[h - 1][c] != 1 for c in range(w)) or any(cells[r][0] != 1 or cells[r][w - 1] != 1 for r in range(h)):
        return False, "border must be wall (raycaster)", None
    d = maze_path(w, h, cells)
    return (d is not None, "goal not reachable", d)


def v_mine(w, h, cells):
    n = count(cells, 1)
    if n < 1 or n > w * h - 9:
        return False, "mine count", None
    return True, "", n


def v_flood(w, h, cells):
    mv, cols = flood_greedy(w, h, cells)
    if cols < 2 or mv is None:
        return False, "need 2+ colours", None
    n = min(w, h)
    limit = cols * n // 2 + 2
    if mv > limit:
        return False, "greedy needs %d > limit %d" % (mv, limit), None
    return True, "", mv * 100 // limit


def v_cube(w, h, cells):
    if w * h - count(cells, 0) < 3:
        return False, "need 3+ obstacles", None
    for tier in range(4):
        if not cube_bot_ok(cells, tier):
            return False, "bot cannot finish at tier %d" % tier, None
    return True, "", w * h - count(cells, 0)


def v_beat(w, h, cells):
    n = count(cells, 1)
    return (n >= 8, "need 8+ notes", n)


def v_land(w, h, cells):
    runs, a, b = 0, 0, 0
    for c in range(w):
        if cells[0][c] != 9:
            continue
        if c == 0 or cells[0][c - 1] != 9:
            runs += 1
            a = c
        b = c + 1
    if runs != 1:
        return False, "need exactly one pad run", None
    if b - a < 3:
        return False, "pad needs 3+ columns", None
    return True, "", 12 - (b - a)


def v_lights(w, h, cells):
    if count(cells, 1) < 1:
        return False, "need a light on", None
    if not lights_parity_ok(cells):
        return False, "unsolvable pattern", None
    m = lights_min_presses(cells)
    return (m is not None, "no solution", m)


def v_plinko(w, h, cells):
    n = count(cells, 1) + count(cells, 2)
    return (n >= 10, "need 10+ pegs", n)


def v_tank(w, h, cells):
    return (max(cells[0]) != min(cells[0]), "flat terrain", max(cells[0]) - min(cells[0]))


def v_bstk(w, h, cells):
    filled = 0
    for r in range(h):
        f = sum(1 for v in cells[r] if v)
        if f >= w:
            return False, "row %d full" % (r + 1), None
        filled += f
    if filled < 4:
        return False, "too little garbage", None
    if filled * 10 > w * h * 7:
        return False, "over 70%", None
    return True, "", filled


def v_rev(w, h, cells):
    nb, nw = count(cells, 1), count(cells, 2)
    if nb < 2 or nw < 2:
        return False, "need 2+ discs of each colour", None
    if rev_moves(cells, 1) == 0:
        return False, "black has no move", None
    return True, "", nb + nw + 3 * count(cells, 3)


def v_gem(w, h, cells):
    nf = sum(1 for row in cells for v in row if v < 6)
    if nf < 4:
        return False, "too few gems", None
    for y in range(8):
        for x in range(8):
            if gem_run_at(cells, x, y):
                return False, "run at start", None
    n = gem_moves([r[:] for r in cells])
    return (n > 0, "no legal swap", n)


def v_bub(w, h, cells):
    n = sum(1 for row in cells for v in row if 1 <= v <= 5)
    if n < 10:
        return False, "need 10+ bubbles", None
    if any(v > 5 for row in cells for v in row):
        return False, "bad tile", None
    return (bub_anchored_ok(cells), "bubble not on ceiling", n)


def v_mind(w, h, cells):
    ok = all(1 <= cells[0][i] <= 8 for i in range(4))
    return (ok, "first 4 pegs must be colours", len(set(cells[0])))


RULES = {0: v_soko, 2: v_brk, 4: v_maze, 5: v_inv, 8: v_mine, 9: v_flood, 10: v_cube, 11: v_beat, 12: v_land,
         13: v_lights, 15: v_plinko, 16: v_tank, 20: v_bstk, 21: v_rev, 22: v_gem, 23: v_bub, 24: v_mind}


# --------------------------------------------------------------------------- file level
def build_pak(game, title, levels):
    """levels: list of (name, par, w, h, cells) -> bytes"""
    out = bytearray(MAGIC)
    out += bytes([1, game, len(levels), 0])
    out += title.upper().ljust(12)[:12].encode("ascii")
    for name, par, w, h, cells in levels:
        out += bytes([w, h]) + name.upper().ljust(8)[:8].encode("ascii") + bytes([par])
        for row in cells:
            out += bytes(row)
    return bytes(out)


def parse_pak(data):
    """-> (game, title, [(name, par, w, h, cells)], error)"""
    if len(data) < 20 or data[:4] != MAGIC:
        return None, None, [], "bad magic"
    ver, game, cnt = data[4], data[5], data[6]
    if ver != 1:
        return None, None, [], "bad version"
    if game not in CFG:
        return game, None, [], "game %d has no pack support here" % game
    if not 1 <= cnt <= MAX_LEVELS:
        return game, None, [], "bad count"
    if len(data) > MAX_BYTES:
        return game, None, [], "file too large (%d)" % len(data)
    title = data[8:20].decode("ascii", "replace").rstrip()
    _, gw, gh, nt = CFG[game]
    pos, recs = 20, []
    for i in range(cnt):
        if pos + 11 > len(data):
            return game, title, recs, "record %d truncated" % i
        w, h = data[pos], data[pos + 1]
        name = data[pos + 2:pos + 10].decode("ascii", "replace")
        par = data[pos + 10]
        if not (1 <= w <= gw and 1 <= h <= gh):
            return game, title, recs, "record %d bad size %dx%d" % (i, w, h)
        if pos + 11 + w * h > len(data):
            return game, title, recs, "record %d truncated" % i
        raw = data[pos + 11:pos + 11 + w * h]
        cells = [list(raw[r * w:(r + 1) * w]) for r in range(h)]
        recs.append((name, par, w, h, cells))
        pos += 11 + w * h
    err = "" if pos == len(data) else "%d trailing bytes" % (len(data) - pos)
    return game, title, recs, err


def check_pak(path):
    data = open(path, "rb").read()
    game, title, recs, err = parse_pak(data)
    problems = []
    if err:
        problems.append(err)
    if game in CFG:
        want = "g%d.pak" % game
        if os.path.basename(path) != want:
            problems.append("file name should be %s" % want)
        _, gw, gh, nt = CFG[game]
        names = set()
        for i, (name, par, w, h, cells) in enumerate(recs):
            if any(ch not in NAME_OK for ch in name):
                problems.append("rec %d: bad name %r" % (i, name))
            if name in names:
                problems.append("rec %d: duplicate name" % i)
            names.add(name)
            if not 1 <= par <= 9:
                problems.append("rec %d: par %d outside 1-9" % (i, par))
            if any(v >= nt for row in cells for v in row):
                problems.append("rec %d: tile id >= %d" % (i, nt))
                continue
            ok, why, _ = RULES[game](w, h, cells)
            if not ok:
                problems.append("rec %d (%s): %s" % (i, name.strip(), why))
        keys = {tuple(map(tuple, r[4])) for r in recs}
        if len(keys) != len(recs):
            problems.append("duplicate levels inside the pack")
    return game, title, len(recs), len(data), problems


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "out", "packs")
    files = sorted((f for f in os.listdir(folder) if f.lower().endswith(".pak")), key=lambda f: int(f[1:-4]) if f[1:-4].isdigit() else 999)
    if not files:
        print("no .pak files in", folder)
        return 1
    bad, tot_l, tot_b = 0, 0, 0
    print("%-6s %-16s %-12s %6s %7s  %s" % ("file", "game", "pack title", "levels", "bytes", "status"))
    for f in files:
        game, title, n, size, problems = check_pak(os.path.join(folder, f))
        gname = CFG[game][0] if game in CFG else "?"
        print("%-6s %-16s %-12s %6d %7d  %s" % (f, gname, title or "?", n, size, "OK" if not problems else "FAIL"))
        for p in problems:
            print("        -", p)
        bad += 1 if problems else 0
        tot_l += n
        tot_b += size
    print("%d files, %d levels, %d bytes, %d with problems" % (len(files), tot_l, tot_b, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
