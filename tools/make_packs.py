#!/usr/bin/env python3
"""make_packs.py - generates the PyGamerPortal level packs into tools/out/packs/g<id>.pak.

    python make_packs.py            (deterministic: every game has a fixed seed, so the output never changes)
    python verify_packs.py          (re-checks every file)
    powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Packs     (copies them to the PyGamer drive)

Every level is run through the same rules/solvers as verify_packs.py before it is written (Sokoban BFS solver, Flood
Fill greedy solver vs the in-game move limit, Lights Out GF(2) solver, Cube Dash physics bot, Speed Maze BFS ...), so
a pack only ever contains levels the sketch's own validate functions accept. See README_PACKS.txt for the format.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_packs as vp   # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "packs")


def rank_par(i, n):
    """difficulty marker 1..9 from the position in an easy-to-hard ordered list"""
    return 1 + (8 * i) // max(1, n - 1)


def spread(items, n):
    """n items spread evenly over a list that is already sorted by difficulty"""
    if len(items) <= n:
        return list(items)
    return [items[(i * (len(items) - 1)) // (n - 1)] for i in range(n)]


def finish(game, title, prefix, rows, w, h):
    """rows: [(cells,)] already ordered easy -> hard"""
    n = len(rows)
    levels = []
    for i, cells in enumerate(rows):
        levels.append(("%s %02d" % (prefix, i + 1), rank_par(i, n), w if w else len(cells[0]), h if h else len(cells), cells))
    return game, title, levels


def grid(w, h, v=0):
    return [[v] * w for _ in range(h)]


# --------------------------------------------------------------------------- Sokoban Mini (id 0)
def gen_soko(rng):
    pool = {}
    tries = 0
    while len(pool) < 420 and tries < 6000:
        tries += 1
        g = grid(7, 7)
        for i in range(7):
            g[0][i] = g[6][i] = g[i][0] = g[i][6] = 1
        inner = [(x, y) for y in range(1, 6) for x in range(1, 6)]
        nb = 1 if rng.random() < 0.4 else 2
        nw = rng.randint(0, 6)
        pts = rng.sample(inner, nw + 2 * nb + 1)
        for x, y in pts[:nw]:
            g[y][x] = 1
        for x, y in pts[nw:nw + nb]:
            g[y][x] = 2
        for x, y in pts[nw + nb:nw + 2 * nb]:
            g[y][x] = 3
        x, y = pts[-1]
        g[y][x] = 4
        ok, _, m = vp.v_soko(7, 7, g)
        if ok and m >= 6:
            pool[tuple(map(tuple, g))] = m
    ordered = sorted(pool.items(), key=lambda kv: (kv[1], kv[0]))
    pick = spread(ordered, 30)
    return finish(0, "SOKO ROOMS", "ROOM", [[list(r) for r in k] for k, _ in pick], 7, 7)


# --------------------------------------------------------------------------- Lights Out (id 13)
def gen_lights(rng):
    pool = {}
    for _ in range(900):
        k = rng.randint(2, 13)
        presses = rng.sample(range(25), k)
        b = [[0] * 5 for _ in range(5)]
        for p in presses:
            r, c = divmod(p, 5)
            for rr, cc in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= rr < 5 and 0 <= cc < 5:
                    b[rr][cc] ^= 1
        if sum(map(sum, b)) < 3:
            continue
        ok, _, m = vp.v_lights(5, 5, b)
        if ok and m >= 2:
            pool[tuple(map(tuple, b))] = m
    ordered = sorted(pool.items(), key=lambda kv: (kv[1], kv[0]))
    pick = spread(ordered, 30)
    game, title, levels = finish(13, "LIGHTS OUT", "PZL", [[list(r) for r in k] for k, _ in pick], 5, 5)
    # par = fewest presses mapped onto 1..9 (presses are 2..15 on a 5x5 board)
    levels = [(n, max(1, min(9, (m * 9 + 14) // 15)), w, h, c) for (n, _, w, h, c), (_, m) in zip(levels, pick)]
    return game, title, levels


# --------------------------------------------------------------------------- Flood Fill (id 9)
def gen_flood(rng):
    rows = []
    for i in range(20):
        n = 6 + (i * 4) // 19
        nc = 3 + (i * 3) // 19
        limit = nc * n // 2 + 2
        want = 0.50 + 0.45 * i / 19
        best = None
        for _ in range(60):
            b = [[rng.randrange(nc) for _ in range(n)] for _ in range(n)]
            if len({v for r in b for v in r}) != nc:
                continue
            mv, _c = vp.flood_greedy(n, n, b)
            if mv is None or mv > limit or mv < nc + 1:
                continue
            score = abs(mv / limit - want)
            if best is None or score < best[0]:
                best = (score, b)
        if best is None:
            raise SystemExit("flood: no board for level %d" % i)
        rows.append(best[1])
    return finish(9, "FLOOD BOARDS", "FLD", rows, 0, 0)


# --------------------------------------------------------------------------- Minesweeper (id 8)
def gen_mine(rng):
    rows = []
    for i in range(20):
        nm = 8 + (i * 20) // 19
        pos = rng.sample(range(80), nm)
        g = grid(10, 8)
        for p in pos:
            g[p // 10][p % 10] = 1
        rows.append(g)
    return finish(8, "MINEFIELDS", "FIELD", rows, 10, 8)


# --------------------------------------------------------------------------- Mastermind (id 24)
def gen_mind(rng):
    seen, rows = set(), []
    i = 0
    while len(rows) < 20:
        ncol = 4 + (len(rows) * 4) // 19
        distinct = ncol >= 5 and len(rows) < 12
        if distinct:
            code = rng.sample(range(1, ncol + 1), 5)
        else:
            code = [rng.randint(1, ncol) for _ in range(5)]
            if len(set(code)) < 3 and ncol > 3:
                continue
        if tuple(code) in seen:
            continue
        seen.add(tuple(code))
        rows.append([code])
    return finish(24, "CODEBREAKER", "CODE", rows, 5, 1)


# --------------------------------------------------------------------------- Cube Dash (id 10)
def gen_cube(rng):
    rows = []
    seen = set()
    n = 20
    attempts = 0
    while len(rows) < n:
        attempts += 1
        if attempts > 4000:
            raise SystemExit("cube: could not build enough tracks")
        i = len(rows)
        R = 2 if i < 7 else (3 if i < 14 else 4)
        L = 24 * R
        kinds = [1, 1, 1, 2]
        if i >= 3:
            kinds += [4, 3] if i >= 6 else [4]
        if i >= 9:
            kinds += [3, 4, 2]
        cells = [0] * L
        pos = 2
        while pos < L - 2:
            cells[pos] = rng.choice(kinds)
            gap = 3 + (1 if rng.random() < max(0.15, 0.7 - 0.04 * i) else 0) + (1 if rng.random() < 0.12 else 0)
            pos += gap
        if sum(1 for c in cells if c) < 3 + R:
            continue
        key = tuple(cells)
        if key in seen:
            continue
        g = [cells[r * 24:(r + 1) * 24] for r in range(R)]
        ok, why, _ = vp.v_cube(24, R, g)
        if not ok:
            continue
        seen.add(key)
        rows.append(g)
    return finish(10, "CUBE TRACKS", "TRACK", rows, 24, 0)


# --------------------------------------------------------------------------- Beat Tapper (id 11)
RHYTHMS = [
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1],
    [1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
    [1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]
LANES = [
    lambda c, r: c % 4,
    lambda c, r: (0, 1, 2, 3, 2, 1)[c % 6],
    lambda c, r: (0, 3)[c % 2],
    lambda c, r: (1, 2)[c % 2],
    lambda c, r: (0, 1, 3, 2)[c % 4],
    lambda c, r: (3, 2, 1, 0)[c % 4],
    lambda c, r: r.randrange(4),
]


def gen_beat(rng):
    rows, seen = [], set()
    while len(rows) < 20:
        i = len(rows)
        rhythm = RHYTHMS[min(7, (i * 8) // 20 + rng.randint(0, 1))] if i else RHYTHMS[0]
        lane = LANES[rng.randrange(len(LANES)) if i >= 4 else rng.randrange(4)]
        g = grid(16, 4)
        prev = -1
        for c in range(16):
            if not rhythm[c]:
                continue
            ln = lane(c, rng)
            if i < 6 and ln == prev:
                ln = (ln + 1) % 4
            g[ln][c] = 1
            prev = ln
            if i >= 13 and c % 4 == 0 and rng.random() < 0.6:     # chords on the accents (become two quick steps)
                g[(ln + 2) % 4][c] = 1
        if vp.count(g, 1) < 8:
            continue
        key = tuple(map(tuple, g))
        if key in seen:
            continue
        seen.add(key)
        rows.append(g)
    rows.sort(key=lambda g: vp.count(g, 1))
    return finish(11, "BEAT CHARTS", "BEAT", rows, 16, 4)


# --------------------------------------------------------------------------- Lunar Lander (id 12)
def gen_land(rng):
    rows = []
    for i in range(20):
        padw = 5 if i < 7 else (4 if i < 14 else 3)
        rough = 1 + i // 6
        while True:
            a = rng.randint(2, 18 - padw)
            h = [0] * 20
            h[0] = rng.randint(2, 6)
            for c in range(1, 20):
                step = rng.choice((-rough, -1, 0, 0, 1, rough))
                h[c] = max(0, min(8, h[c - 1] + step))
            pad_h = h[a - 1]
            row = h[:]
            for c in range(a, a + padw):
                row[c] = 9
            if a + padw < 20:
                row[a + padw] = pad_h          # same height on both sides of the pad
            if max(h) - min(h) < 3:
                continue
            ok, _, _m = vp.v_land(20, 1, [row])
            if ok:
                rows.append([row])
                break
    return finish(12, "LANDING ZONE", "SITE", rows, 20, 1)


# --------------------------------------------------------------------------- Tank Duel (id 16)
def gen_tank(rng):
    rows = []
    for i in range(15):
        while True:
            base = rng.randint(1, 3)
            nh = 1 + (1 if i >= 5 else 0) + (1 if i >= 10 else 0)
            row = [base] * 20
            for _ in range(nh):
                cx = rng.randint(6, 13)
                amp = rng.randint(2, 3 + i // 3)
                wid = rng.choice((2.0, 3.0, 4.0))
                for c in range(20):
                    row[c] += int(round(amp * max(0.0, 1.0 - abs(c - cx) / wid)))
            row = [max(0, min(8, v + rng.choice((0, 0, 0, 1, -1)))) for v in row]
            ok, _, _m = vp.v_tank(20, 1, [row])
            if ok and max(row) - min(row) >= 3 and [row] not in rows:
                rows.append([row])
                break
    rows.sort(key=lambda g: max(g[0]) - min(g[0]))
    return finish(16, "TANK HILLS", "HILL", rows, 20, 1)


# --------------------------------------------------------------------------- Plinko (id 15)
def gen_plinko(rng):
    rows, seen = [], set()
    kinds = ["std", "funnel", "diamond", "cols", "checker", "rings", "rand", "vee", "rows"]
    i = 0
    while len(rows) < 15:
        kind = kinds[i % len(kinds)] if i < 9 else rng.choice(kinds)
        i += 1
        g = grid(9, 9)
        for r in range(9):
            for k in range(9):
                if kind == "std":
                    v = 1 if ((r & 1) or k >= 1) else 0
                elif kind == "funnel":
                    v = 1 if abs(k - 4) >= (8 - r) // 2 + (1 if r & 1 else 0) and r < 8 else 0
                elif kind == "diamond":
                    v = 1 if abs(k - 4) + abs(r - 4) in (2, 4) else 0
                elif kind == "cols":
                    v = 1 if k % 2 == (r & 1) and r > 0 else 0
                elif kind == "checker":
                    v = 1 if (r + k) % 2 == 0 and 0 < r < 8 else 0
                elif kind == "rings":
                    v = 1 if max(abs(k - 4), abs(r - 4)) in (1, 3) and (k + r) % 2 == 0 else 0
                elif kind == "vee":
                    v = 1 if abs(k - 4) == r // 2 + (r & 1) and r < 8 else 0
                elif kind == "rows":
                    v = 1 if r % 2 == 1 and k % 3 != (r // 2) % 3 else 0
                else:
                    v = 1 if rng.random() < 0.55 and 0 < r < 8 else 0
                g[r][k] = v
        # sprinkle a few jittered extras / bumpers; more bumpers in later boards
        for _ in range(rng.randint(1, 4)):
            g[rng.randint(1, 7)][rng.randint(0, 8)] = 1
        for _ in range(min(6, len(rows) // 2)):
            r, k = rng.randint(1, 7), rng.randint(0, 8)
            if g[r][k]:
                g[r][k] = 2
        ok, _, n = vp.v_plinko(9, 9, g)
        key = tuple(map(tuple, g))
        if ok and key not in seen:
            seen.add(key)
            rows.append(g)
    return finish(15, "PEG BOARDS", "BOARD", rows, 9, 9)


# --------------------------------------------------------------------------- Gem Swap (id 22)
def gen_gem(rng):
    rows = []
    for i in range(15):
        types = 4 + i // 5
        target = max(3, 16 - i)
        best = None
        for _ in range(80):
            g = grid(8, 8)
            for y in range(8):
                for x in range(8):
                    for _t in range(20):
                        v = rng.randrange(types)
                        g[y][x] = v
                        if not vp.gem_run_at(g, x, y):
                            break
                    else:
                        break
            if any(vp.gem_run_at(g, x, y) for y in range(8) for x in range(8)):
                continue
            m = vp.gem_moves([r[:] for r in g])
            if m < 2:
                continue
            score = abs(m - target)
            if best is None or score < best[0]:
                best = (score, g)
        if best is None:
            raise SystemExit("gem: no board")
        rows.append(best[1])
    return finish(22, "GEM BOARDS", "GEMS", rows, 8, 8)


# --------------------------------------------------------------------------- Bubble Shooter (id 23)
def gen_bubble(rng):
    rows, seen = [], set()
    while len(rows) < 15:
        i = len(rows)
        nrows = 3 + (i * 5) // 14
        ncol = 3 + (i * 2) // 14
        g = grid(10, 8)
        for r in range(nrows):
            for c in range(10):
                if r > 0 and rng.random() < 0.12 + 0.01 * i:
                    continue
                if c > 0 and g[r][c - 1] and rng.random() < 0.55:
                    g[r][c] = g[r][c - 1]
                elif r > 0 and g[r - 1][c] and rng.random() < 0.4:
                    g[r][c] = g[r - 1][c]
                else:
                    g[r][c] = 1 + rng.randrange(ncol)
        # drop everything that is not hanging from the ceiling (the sketch refuses such fields)
        full = [row[:] for row in g] + [[0] * 10 for _ in range(3)]
        seenc = set()
        stack = [(0, c) for c in range(10) if full[0][c]]
        seenc.update(stack)
        while stack:
            r, c = stack.pop()
            for rr, cc in vp.bub_nbr(r, c):
                if full[rr][cc] and (rr, cc) not in seenc:
                    seenc.add((rr, cc))
                    stack.append((rr, cc))
        for r in range(8):
            for c in range(10):
                if g[r][c] and (r, c) not in seenc:
                    g[r][c] = 0
        ok, _, n = vp.v_bub(10, 8, g)
        key = tuple(map(tuple, g))
        if ok and key not in seen:
            seen.add(key)
            rows.append(g)
    rows.sort(key=lambda g: vp.count(g, 0) * -1 + 0)   # fewer empty cells = harder
    return finish(23, "BUBBLE FIELD", "BUBS", rows, 10, 8)


# --------------------------------------------------------------------------- Block Stack (id 20)
def gen_bstk(rng):
    rows, seen = [], set()
    while len(rows) < 15:
        i = len(rows)
        height = 2 + (i * 5) // 14
        g = grid(10, 8)
        for k in range(height):
            r = 7 - k
            holes = set(rng.sample(range(10), rng.randint(1, 2 + (1 if i > 7 else 0))))
            for c in range(10):
                if c in holes:
                    continue
                if r < 7 and not g[r + 1][c]:
                    continue                      # pile: no floating garbage
                g[r][c] = 1 if rng.random() < 0.6 else rng.randint(2, 5)
        ok, _, n = vp.v_bstk(10, 8, g)
        key = tuple(map(tuple, g))
        if ok and key not in seen:
            seen.add(key)
            rows.append(g)
    rows.sort(key=lambda g: sum(1 for row in g for v in row if v))
    return finish(20, "GARBAGE", "PILE", rows, 10, 8)


# --------------------------------------------------------------------------- Reversi (id 21)
def gen_rev(rng):
    rows, seen = [], set()
    while len(rows) < 15:
        i = len(rows)
        g = grid(8, 8)
        g[3][3] = g[4][4] = 2
        g[3][4] = g[4][3] = 1
        extra = 1 + i // 2
        free = [(x, y) for y in range(2, 6) for x in range(2, 6) if g[y][x] == 0]
        rng.shuffle(free)
        for k in range(min(len(free), extra * 2)):
            x, y = free[k]
            g[y][x] = 1 + (k & 1)
        nblk = min(6, i // 2)
        spots = [(x, y) for y in range(8) for x in range(8) if g[y][x] == 0]
        for x, y in rng.sample(spots, nblk):
            g[y][x] = 3
        ok, _, m = vp.v_rev(8, 8, g)
        if not ok or vp.rev_moves(g, 2) == 0:
            continue
        key = tuple(map(tuple, g))
        if key in seen:
            continue
        seen.add(key)
        rows.append(g)
    return finish(21, "REVERSI SETS", "SET", rows, 8, 8)


# --------------------------------------------------------------------------- Speed Maze (id 4)
def lattice_maze(rng, extra):
    g = grid(9, 7, 1)
    cells = [(cx, cy) for cy in range(3) for cx in range(4)]
    start = rng.choice(cells)
    seen = {start}
    stack = [start]
    g[2 * start[1] + 1][2 * start[0] + 1] = 0
    while stack:
        cx, cy = stack[-1]
        nb = [(cx + dx, cy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= cx + dx < 4 and 0 <= cy + dy < 3 and (cx + dx, cy + dy) not in seen]
        if not nb:
            stack.pop()
            continue
        nx, ny = rng.choice(nb)
        g[cy + ny + 1][cx + nx + 1] = 0
        g[2 * ny + 1][2 * nx + 1] = 0
        seen.add((nx, ny))
        stack.append((nx, ny))
    walls = [(x, y) for y in range(1, 6) for x in range(1, 8) if g[y][x] == 1 and (x % 2) != (y % 2)]
    for x, y in rng.sample(walls, min(extra, len(walls))):
        g[y][x] = 0
    return g


def place_start_goal(rng, g):
    floor = [(x, y) for y in range(7) for x in range(9) if g[y][x] == 0]
    best = None
    for _ in range(40):
        a, b = rng.sample(floor, 2)
        g[a[1]][a[0]] = 2
        g[b[1]][b[0]] = 3
        d = vp.maze_path(9, 7, g)
        g[a[1]][a[0]] = 0
        g[b[1]][b[0]] = 0
        if d is not None and (best is None or d > best[0]):
            best = (d, a, b)
    if best is None:
        return None
    d, a, b = best
    g[a[1]][a[0]] = 2
    g[b[1]][b[0]] = 3
    return d


def gen_maze(rng):
    pool = {}
    tries = 0
    while len(pool) < 140 and tries < 4000:
        tries += 1
        if tries % 5 < 3:
            g = lattice_maze(rng, rng.randint(0, 3))
        else:
            g = grid(9, 7, 1)
            p = rng.uniform(0.18, 0.36)
            for y in range(1, 6):
                for x in range(1, 8):
                    g[y][x] = 1 if rng.random() < p else 0
        d = place_start_goal(rng, g)
        if d is None or d < 8:
            continue
        ok, _, m = vp.v_maze(9, 7, g)
        if ok:
            pool[tuple(map(tuple, g))] = m
    ordered = sorted(pool.items(), key=lambda kv: (kv[1], kv[0]))
    pick = spread(ordered, 25)
    return finish(4, "SPEED MAZES", "MAZE", [[list(r) for r in k] for k, _ in pick], 9, 7)


# --------------------------------------------------------------------------- Space Invaders (id 5)
def gen_inv(rng):
    pats = []
    for m in range(512):
        rows = [[(m >> (3 * r + k)) & 1 for k in range(3)] for r in range(3)]
        full = [[row[0], row[1], row[2], row[1], row[0]] for row in rows]
        n = sum(map(sum, full))
        if 5 <= n <= 15:
            pats.append((n, full))
    rng.shuffle(pats)
    pats.sort(key=lambda t: t[0])
    chosen, seen = [], set()
    for target in (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 10):   # 12 waves, easy -> hard (the last one: a second 10-invader shape)
        for n, p in pats:
            if n == target and tuple(map(tuple, p)) not in seen:
                chosen.append(p)
                seen.add(tuple(map(tuple, p)))
                break
    chosen.sort(key=lambda p: sum(map(sum, p)))
    return finish(5, "INVASIONS", "WAVE", chosen[:12], 5, 3)


# --------------------------------------------------------------------------- Breakout (id 2)
def gen_brk(rng):
    rows, seen = [], set()

    def add(g):
        key = tuple(map(tuple, g))
        if key not in seen and vp.count(g, 1) >= 1:
            seen.add(key)
            rows.append(g)

    add([[1] * 10 for _ in range(1)] + grid(10, 3))
    add([[0] * 10] + [[1] * 10] + grid(10, 2))
    add([[1, 0] * 5, [0, 1] * 5, [1, 0] * 5, [0, 1] * 5])
    add([[1] * 10, [1] * 10, grid(10, 1)[0], grid(10, 1)[0]])
    add([[0, 0, 1, 1, 1, 1, 1, 1, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 0], [1] * 10, grid(10, 1)[0]])
    add([[1, 1, 0, 1, 1, 1, 1, 0, 1, 1]] * 3 + [grid(10, 1)[0]])
    add([[1] * 10, [1, 0] * 5, [1] * 10, [0, 1] * 5])
    add([[1, 1, 1, 1, 0, 0, 1, 1, 1, 1]] * 4)
    add([[0, 0, 0, 0, 1, 1, 0, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 0, 0, 0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0], [0, 1, 1, 1, 1, 1, 1, 1, 1, 0]])
    add([[1, 0, 1, 0, 1, 1, 0, 1, 0, 1]] * 2 + [[1] * 10] * 2)
    add([[1] * 10, [1, 0, 0, 1, 1, 1, 1, 0, 0, 1], [1, 0, 0, 1, 1, 1, 1, 0, 0, 1], [1] * 10])
    add([[1] * 10, [1] * 10, [1] * 10, [1] * 10])
    while len(rows) < 15:                    # symmetric random fill
        g = grid(10, 4)
        d = rng.uniform(0.45, 0.8)
        for r in range(4):
            for c in range(5):
                v = 1 if rng.random() < d else 0
                g[r][c] = g[r][9 - c] = v
        add(g)
    rows = [[list(r) for r in g] for g in rows]
    rows.sort(key=lambda g: vp.count(g, 1))
    return finish(2, "BRICK WALLS", "WALL", rows[:15], 10, 4)


GENERATORS = [
    (0, gen_soko), (13, gen_lights), (9, gen_flood), (8, gen_mine), (24, gen_mind), (10, gen_cube),
    (11, gen_beat), (12, gen_land), (16, gen_tank), (15, gen_plinko), (22, gen_gem), (23, gen_bubble),
    (20, gen_bstk), (21, gen_rev), (4, gen_maze), (5, gen_inv), (2, gen_brk),
]

SKIPPED = {
    1: "Tilt Maze (tilt-controlled, not in the requested list)",
    3: "Platform Dash (not requested; jump rules need a bot like Cube Dash)",
    6: "Snake (no clear event, no solvability notion)",
    7: "Wall Pong (no clear event)",
    14: "Maze Chase (not requested)",
    17: "Air Hockey (no clear event)",
    18: "Gap Flyer (not requested)",
    19: "Road Cross (not requested)",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for gid, fn in GENERATORS:
        rng = random.Random(7000 + gid)
        game, title, levels = fn(rng)
        assert len(levels) <= vp.MAX_LEVELS and len(title) <= 12
        for name, par, w, h, cells in levels:
            assert len(name) <= 8 and all(ch in vp.NAME_OK for ch in name), name
            ok, why, _ = vp.RULES[game](w, h, cells)
            if not ok:
                raise SystemExit("game %d level %s invalid: %s" % (game, name, why))
        data = vp.build_pak(game, title, levels)
        assert len(data) <= vp.MAX_BYTES
        with open(os.path.join(OUT, "g%d.pak" % game), "wb") as f:
            f.write(data)
        total += len(data)
        print("g%-2d %-16s %-13s %2d levels %6d bytes" % (game, vp.CFG[game][0], title, len(levels), len(data)))
    print("total %d bytes in %s" % (total, OUT))
    print("skipped:")
    for gid, why in sorted(SKIPPED.items()):
        print("  g%d %s" % (gid, why))


if __name__ == "__main__":
    main()
