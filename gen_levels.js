// Generates the bulk of PyGamerPortal's levels as REAL mazes (recursive
// backtracker / "perfect maze": exactly one path between any two cells,
// real dead ends -- not an open room with decorative walls) and emits
// them as a C++ header (levels_generated.h) containing extra
// `{{ ... }},` Level entries to splice into the LEVELS[] array.
//
// Because a perfect maze has exactly one path from S to G, any mechanic
// placed directly ON that path is mandatory, not optional -- that's what
// makes these genuinely harder than the old open-room templates. Every
// generated level is verified solvable by an automated BFS checker
// (isSolvable, below) before being included; if a random maze doesn't
// check out (rare, but the key/door placement can occasionally strand
// things) the generator retries with a new seed.
//
// Run with: node gen_levels.js

// --- Seeded RNG (deterministic across runs) --------------------------------

function mulberry32(a) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffle(arr, rand) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const DIRS4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];

// --- Perfect maze (recursive backtracker) ----------------------------------
//
// cellsW x cellsH logical cells, each cell occupying a tile at
// (2*cx+1, 2*cy+1); the tile directly between two adjacent cells is the
// wall that may or may not be carved through. Tile grid is
// (2*cellsW+1) x (2*cellsH+1).

function generateMaze(cellsW, cellsH, rand) {
  const W = 2 * cellsW + 1, H = 2 * cellsH + 1;
  const grid = Array.from({ length: H }, () => new Array(W).fill('#'));
  for (let cy = 0; cy < cellsH; cy++)
    for (let cx = 0; cx < cellsW; cx++)
      grid[2 * cy + 1][2 * cx + 1] = '.';

  const visited = Array.from({ length: cellsH }, () => new Array(cellsW).fill(false));
  const stack = [[0, 0]];
  visited[0][0] = true;

  while (stack.length) {
    const [cx, cy] = stack[stack.length - 1];
    const opts = shuffle(DIRS4, rand);
    let moved = false;
    for (const [dx, dy] of opts) {
      const nx = cx + dx, ny = cy + dy;
      if (nx >= 0 && nx < cellsW && ny >= 0 && ny < cellsH && !visited[ny][nx]) {
        grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = '.'; // carve the wall between
        visited[ny][nx] = true;
        stack.push([nx, ny]);
        moved = true;
        break;
      }
    }
    if (!moved) stack.pop();
  }
  return { grid, W, H };
}

// BFS over CELLS (using the maze's spanning tree) from (0,0) to the given
// goal cell. Since it's a perfect maze there's exactly one path.
function cellPath(grid, cellsW, cellsH, goalCx, goalCy) {
  const key = (x, y) => x + ',' + y;
  const prev = new Map();
  const seen = new Set([key(0, 0)]);
  const q = [[0, 0]];
  while (q.length) {
    const [cx, cy] = q.shift();
    if (cx === goalCx && cy === goalCy) break;
    for (const [dx, dy] of DIRS4) {
      const nx = cx + dx, ny = cy + dy;
      if (nx < 0 || nx >= cellsW || ny < 0 || ny >= cellsH) continue;
      if (grid[2 * cy + 1 + dy][2 * cx + 1 + dx] !== '.') continue; // wall
      const k = key(nx, ny);
      if (seen.has(k)) continue;
      seen.add(k);
      prev.set(k, [cx, cy]);
      q.push([nx, ny]);
    }
  }
  const path = [[goalCx, goalCy]];
  let cur = [goalCx, goalCy];
  while (!(cur[0] === 0 && cur[1] === 0)) {
    cur = prev.get(key(cur[0], cur[1]));
    path.push(cur);
  }
  path.reverse();
  return path; // [[cx,cy], ...] from start cell to goal cell
}

// Expands a cell-path into the actual tile coordinates along it (cell tile,
// connector tile, cell tile, connector tile, ...).
function pathToTiles(path) {
  const tiles = [];
  for (let i = 0; i < path.length; i++) {
    const [cx, cy] = path[i];
    tiles.push([2 * cx + 1, 2 * cy + 1]);
    if (i < path.length - 1) {
      const [nx, ny] = path[i + 1];
      const dx = nx - cx, dy = ny - cy;
      tiles.push([2 * cx + 1 + dx, 2 * cy + 1 + dy]);
    }
  }
  return tiles; // [[x,y], ...]
}

// --- Automated solvability check --------------------------------------
//
// A conservative BFS that also simulates "shoot a portal across a pit":
// from any floor tile adjacent to a pit, you can reach the first
// non-pit tile on the far side in a straight line (mirroring the real
// game's ray-to-nearest-wall placement). Locked doors ('K') are only
// passable in the second phase, after the key has been reached.

function isSolvable(grid, W, H, sx, sy, gx, gy, keyTile) {
  function bfs(starts, keyCollected) {
    const seen = new Set();
    const q = [];
    for (const [x, y] of starts) {
      const k = x + ',' + y;
      if (!seen.has(k)) { seen.add(k); q.push([x, y]); }
    }
    while (q.length) {
      const [x, y] = q.shift();
      for (const [dx, dy] of DIRS4) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
        const t = grid[ny][nx];
        if (t === '#' || t === 'N') continue;
        if (t === '~') continue; // can't just walk onto a pit
        if (t === 'K' && !keyCollected) continue;
        const k = nx + ',' + ny;
        if (!seen.has(k)) { seen.add(k); q.push([nx, ny]); }
      }
      // Pit bridge: scan past consecutive pit tiles to the first solid
      // landing spot beyond them, in each of the 4 directions.
      for (const [dx, dy] of DIRS4) {
        let fx = x + dx, fy = y + dy;
        if (fx < 0 || fx >= W || fy < 0 || fy >= H || grid[fy][fx] !== '~') continue;
        while (fx >= 0 && fx < W && fy >= 0 && fy < H && grid[fy][fx] === '~') {
          fx += dx; fy += dy;
        }
        if (fx < 0 || fx >= W || fy < 0 || fy >= H) continue;
        const ft = grid[fy][fx];
        if (ft === '#' || ft === 'N') continue;
        if (ft === 'K' && !keyCollected) continue;
        const k = fx + ',' + fy;
        if (!seen.has(k)) { seen.add(k); q.push([fx, fy]); }
      }
    }
    return seen;
  }

  if (keyTile) {
    const seen1 = bfs([[sx, sy]], false);
    if (!seen1.has(keyTile[0] + ',' + keyTile[1])) return false;
    const seen2 = bfs([keyTile], true);
    return seen2.has(gx + ',' + gy);
  }
  const seen = bfs([[sx, sy]], false);
  return seen.has(gx + ',' + gy);
}

// --- Building one hard level -------------------------------------------

function buildHardMaze(seed) {
  const rand = mulberry32(seed * 2654435761 + 1);

  const cellsW = 6 + (seed % 5); // 6..10
  const cellsH = 5 + ((seed >> 3) % 4); // 5..8
  const { grid, W, H } = generateMaze(cellsW, cellsH, rand);

  const goalCx = cellsW - 1, goalCy = cellsH - 1;
  const path = cellPath(grid, cellsW, cellsH, goalCx, goalCy);
  const tiles = pathToTiles(path);

  const [sx, sy] = tiles[0];
  const [gx, gy] = tiles[tiles.length - 1];

  // Mandatory pit crossing: pick a connector tile (odd tile-index in the
  // expanded path) roughly in the middle.
  let pitTile = null;
  for (let i = Math.floor(tiles.length / 2); i < tiles.length - 1; i++) {
    if (i % 2 === 1) { pitTile = tiles[i]; break; }
  }

  // Mandatory key + locked door: find the first path cell (scanning from
  // the start) with an off-path neighbor reachable through a carved wall
  // -- that neighbor becomes the key's dead-end detour. The door goes on
  // the path a bit further along (toward the goal) than the branch.
  const pathCellSet = new Set(path.map(([x, y]) => x + ',' + y));
  let keyCell = null, branchPathIdx = -1;
  for (let i = 1; i < path.length - 1 && !keyCell; i++) {
    const [cx, cy] = path[i];
    for (const [dx, dy] of DIRS4) {
      const nx = cx + dx, ny = cy + dy;
      if (nx < 0 || nx >= cellsW || ny < 0 || ny >= cellsH) continue;
      if (pathCellSet.has(nx + ',' + ny)) continue;
      if (grid[2 * cy + 1 + dy][2 * cx + 1 + dx] !== '.') continue;
      keyCell = [2 * nx + 1, 2 * ny + 1];
      branchPathIdx = i;
      break;
    }
  }

  let doorTileIdx = -1;
  if (keyCell) {
    // A cell index in the path list -> its tile index is 2*idx.
    const branchTileIdx = branchPathIdx * 2;
    doorTileIdx = Math.min(tiles.length - 3, branchTileIdx + 6);
    if (doorTileIdx % 2 === 1) doorTileIdx--; // land on a cell tile
    if (doorTileIdx <= branchTileIdx) keyCell = null; // maze too small, skip
  }

  if (pitTile) grid[pitTile[1]][pitTile[0]] = '~';
  if (keyCell && doorTileIdx > 0) {
    grid[tiles[doorTileIdx][1]][tiles[doorTileIdx][0]] = 'K';
  }

  if (!isSolvable(grid, W, H, sx, sy, gx, gy, keyCell)) {
    return null; // caller retries with a different seed
  }

  // Flavor (never blocks anything, purely a movement-feel modifier): turn
  // a couple of untouched path tiles into ice or mud.
  for (let i = 2; i < tiles.length - 2; i += 7) {
    const [x, y] = tiles[i];
    if (grid[y][x] === '.') grid[y][x] = (i % 14 === 2) ? 'I' : 'M';
  }

  if (keyCell) grid[keyCell[1]][keyCell[0]] = 'Y';
  grid[sy][sx] = 'S';
  grid[gy][gx] = 'G';

  return grid.map(row => row.join(''));
}

// --- Driver --------------------------------------------------------------

const levels = [];
let seed = 1;
let attempts = 0;
const TARGET = 473; // 27 hand-authored + 473 generated = 500 total

while (levels.length < TARGET && attempts < TARGET * 20) {
  attempts++;
  const rows = buildHardMaze(seed);
  seed++;
  if (!rows) continue; // unsolvable roll, try the next seed
  levels.push({ rows, comment: `Generated maze (seed ${seed - 1})` });
}

if (levels.length < TARGET) {
  console.error(`Only generated ${levels.length}/${TARGET} levels after ${attempts} attempts.`);
  process.exit(1);
}

let out = '';
for (const lvl of levels) {
  out += `    {{\n        // ${lvl.comment}\n`;
  for (const row of lvl.rows) {
    out += `        "${row}",\n`;
  }
  out += `    }},\n`;
}

require('fs').writeFileSync('levels_generated.h', out);
console.log(`Wrote ${levels.length} generated maze levels to levels_generated.h (${attempts} attempts)`);
