#!/usr/bin/env node
// Self-test for arcadia_gamemaker.html (needs only node >= 16 and, optionally, python for the cross-check).
//   node test_gamemaker.js
// 1. extracts the <script id="core"> of the HTML (the very code the browser runs)
// 2. JS assembler vs tools/out/carts/*.arc: byte-for-byte on every tools/carts/*.arcl
// 3. every template: compile, round-trip through JSON, run headless in the JS VM (several bots / tiers)
// 4. compiler negative tests (forever, nested wait, bad names, collision guard ...)
// 5. generated .arcl compiled by tools/make_carts.py (python) must give the same bytes as the JS assembler
'use strict';
const fs = require('fs'), path = require('path'), cp = require('child_process');
const HERE = __dirname, TOOLS = path.join(HERE, '..');
const html = fs.readFileSync(path.join(HERE, 'arcadia_gamemaker.html'), 'utf8');
const m = /<script id="core">([\s\S]*?)<\/script>/.exec(html);
if (!m) throw new Error('core script not found');
const mod = { exports: {} };
new Function('module', m[1])(mod);
const ARC = mod.exports;
let fails = 0, passes = 0;
function ok(cond, msg) { if (cond) { passes++; } else { fails++; console.log('  FAIL: ' + msg); } }
function section(t) { console.log('\n== ' + t); }

// ---------------------------------------------------------------- 1. assembler byte-for-byte
section('assembler vs tools/out/carts (byte for byte)');
const srcDir = path.join(TOOLS, 'carts'), outDir = path.join(TOOLS, 'out', 'carts');
let nCart = 0;
for (const f of fs.readdirSync(srcDir).filter(f => f.endsWith('.arcl')).sort()) {
  const ref = path.join(outDir, f.replace(/\.arcl$/, '.arc'));
  if (!fs.existsSync(ref)) { console.log('  (skipped, no reference .arc for ' + f + ')'); continue; }
  let blob;
  try { blob = ARC.compileSource(fs.readFileSync(path.join(srcDir, f), 'latin1')).blob; }
  catch (e) { ok(false, f + ': ' + e.message); continue; }
  const want = fs.readFileSync(ref);
  const same = Buffer.compare(Buffer.from(blob), want) === 0;
  ok(same, f + ' differs from reference');
  nCart++;
  // the JS VM must also run the reference carts without faults
  try {
    const vm = ARC.runCart(blob, 900, fr => (fr % 6 < 3 ? 16 : 0) | [1, 4, 2, 8][(fr >> 5) & 3]);
    console.log('  ' + (same ? 'identical' : 'DIFFERENT') + '  ' + f.padEnd(14) + String(blob.length).padStart(6) + ' bytes   VM maxops ' + vm.maxOps);
  } catch (e) { ok(false, f + ' VM fault: ' + e.message); }
}
ok(nCart >= 11, 'expected at least 11 reference carts, got ' + nCart);

// ---------------------------------------------------------------- built-in list
section('built-in game list embedded in the page');
const txt = ARC.parseBuiltinText(fs.readFileSync(path.join(TOOLS, 'builtin_games.txt'), 'utf8'));
const have = new Set(ARC.getBuiltinNames());
ok(txt.every(n => have.has(n)), 'every line of builtin_games.txt is in the page (re-run build if you added games)');
const ino = path.join(TOOLS, '..', 'PyGamerPortal.ino');
if (fs.existsSync(ino)) {
  const s = fs.readFileSync(ino, 'utf8'); const i = s.indexOf('kGameNames[NUM_GAMES] = {'); const j = s.indexOf('};', i);
  const names = [...s.slice(i, j).matchAll(/"([^"]+)"/g)].map(x => x[1]);
  ok(names.length > 30 && names.every(n => have.has(n)), 'all ' + names.length + ' kGameNames of the sketch are in the page');
}
console.log('  ' + have.size + ' built-in names embedded');

// ---------------------------------------------------------------- collision guard
section('name / ID collision guard');
ARC.setBuiltinNames(ARC.getBuiltinNames());
const bad = ['SNAKE', 'Pong Plus', 'TETRIS 2', 'SPACE INVADERS', 'SUPER BREAKOUT', 'MY WORDLE', 'REVERSI', 'CHESS', 'DODGE IT', 'Lunar Lander'];
for (const n of bad) ok(ARC.collisionCheck(n, '')[0].length > 0, 'name "' + n + '" should be blocked');
for (const n of ['COMET GUARD', 'HILL HOP', 'WORM TRAIL', 'ROCK RAIN', 'COIN CHASE', 'MY GAME']) ok(ARC.collisionCheck(n, '')[0].length === 0, 'name "' + n + '" should pass');
ok(ARC.collisionCheck('NICE', 'Arcade: a snake game')[1].length > 0, 'genre keyword in blurb should warn');
ok(ARC.idCheck('snake', 'X')[0].length > 0, 'id equal to built-in blocked');
ok(ARC.idCheck('Bad Id!', 'X')[0].length > 0, 'id with odd characters blocked');
ok(ARC.idCheck('a'.repeat(16), 'X')[0].length > 0, 'id of 16 chars blocked (file name must be < 20)');
ok(ARC.idCheck('fishing', 'Y')[1].length > 0, 'id equal to a sample cart warns');
ok(ARC.idCheck('okid_1', 'Y')[0].length === 0, 'plain id passes');
{
  const p = ARC.TEMPLATES[1].build(); p.meta.name = 'SNAKE';
  const r = ARC.buildProject(p);
  ok(r.guardErrors.some(e => /collides/.test(e)) && r.blob, 'buildProject reports the collision (name SNAKE) as a guard error that blocks export');
}

// ---------------------------------------------------------------- templates
section('templates: compile, JSON round trip, headless runs');
function bots() {
  return [['idle', () => 0], ['mash', f => (f % 6 < 3 ? 16 : 0) | (f % 11 < 2 ? 32 : 0)],
  ['sweep', f => [1, 4, 2, 8][(f >> 5) & 3] | (f % 8 < 4 ? 16 : 0)],
  ['random', (() => { let s = 12345, mask = 0, until = 0; return f => { if (f >= until) { s = (s * 1103515245 + 12345) & 0x7fffffff; mask = [0, 1, 2, 4, 8, 16, 32, 17, 18, 20, 24][s % 11]; until = f + 1 + (s >> 8) % 20; } return mask; }; })()]];
}
const built = {};
for (const t of ARC.TEMPLATES) {
  const p = ARC.normalizeForTest ? ARC.normalizeForTest(t.build()) : t.build();
  const r = ARC.buildProject(p);
  ok(r.errors.length === 0 && r.guardErrors.length === 0, t.id + ': errors ' + JSON.stringify(r.errors.concat(r.guardErrors)));
  ok(r.warnings.length === 0, t.id + ': warnings ' + JSON.stringify(r.warnings));
  if (!r.blob) continue;
  built[t.id] = { p, r };
  // JSON round trip
  const p2 = JSON.parse(JSON.stringify(p));
  const r2 = ARC.buildProject(p2);
  ok(r2.blob && Buffer.compare(Buffer.from(r.blob), Buffer.from(r2.blob)) === 0, t.id + ': save/load round trip changes the cart');
  // header sanity
  const cart = new ARC.Cart(r.blob);
  ok(cart.name === p.meta.name && cart.nspr === p.sprites.length, t.id + ': header name/sprites');
  let worst = 0, over = 0, nruns = 0, best = 0;
  for (const tier of [0, 1, 2, 3]) for (const [bn, bot] of bots()) {
    try {
      const vm = ARC.runCart(r.blob, 1500, bot, { tier, seed: 777 + tier });
      worst = Math.max(worst, vm.maxOps); nruns++; if (vm.over) over++; best = Math.max(best, vm.scoreV);
    } catch (e) { ok(false, t.id + ' tier ' + tier + ' bot ' + bn + ': VM fault ' + e.message); }
  }
  ok(worst < ARC.R.BUDGET * 0.6, t.id + ': worst frame ' + worst + ' steps (limit 60% of ' + ARC.R.BUDGET + ')');
  console.log('  ' + t.id.padEnd(11) + String(r.blob.length).padStart(5) + ' bytes  ' + nruns + ' runs ok  worst ' + String(worst).padStart(5) + ' steps/frame  game-overs ' + over + '/' + nruns + '  best score ' + best);
}
// game-specific play tests (bots that read the VM's variables)
function gidx(b, name) { const i = b.r.g.globals.get(name); if (i === undefined) throw new Error('no global ' + name); return i; }
{
  const b = built.snake; const G = n => gidx(b, n);
  const hx = G('v_hx'), hy = G('v_hy'), fx = G('v_fx'), fy = G('v_fy'), dx = G('v_dx'), dy = G('v_dy');
  const bot = (f, vm) => {
    const g = vm.g; const X = g[hx], Y = g[hy], FX = g[fx], FY = g[fy], DX = g[dx], DY = g[dy];
    let want = 0;
    if (FX > X && DX !== -1) want = 2; else if (FX < X && DX !== 1) want = 1;
    else if (FY > Y && DY !== -1) want = 8; else if (FY < Y && DY !== 1) want = 4;
    else if (DX === 0) want = Y > 5 ? 4 : 8; else want = X > 7 ? 1 : 2;
    if (X <= 0 && DX === -1) want = 8; if (X >= 15 && DX === 1) want = 8;
    if (Y <= 0 && DY === -1) want = 2; if (Y >= 11 && DY === 1) want = 2;
    return want === 1 ? 1 : want === 2 ? 2 : want === 4 ? 4 : want === 8 ? 8 : 0;
  };
  const vm = ARC.runCart(b.r.blob, 2500, bot, { tier: 0 });
  ok(vm.scoreV >= 30, 'snake: the grid-trail game lets a food-seeking bot eat 3+ dots (score ' + vm.scoreV + ', len var ' + vm.g[G('v_len')] + ')');
  ok(vm.g[G('v_len')] >= 6, 'snake: trail grows');
}
{
  const b = built.shooter; const G = n => gidx(b, n);
  const ship = G('x_ship'), foe = [G('x_foe1'), G('x_foe2'), G('x_foe3')];
  const bot = (f, vm) => { const target = Math.min(...foe.map(i => vm.g[i])); const sx = vm.g[ship]; return (sx + 4 < target ? 2 : sx - 4 > target ? 1 : 0) | (f % 4 === 0 ? 16 : 0); };
  let best = 0;
  for (let k = 0; k < 6; k++) best = Math.max(best, ARC.runCart(b.r.blob, 1500, bot, { seed: k + 1 }).scoreV);
  ok(best >= 30, 'shooter: firing and hitting comets scores points (best ' + best + ')');
}
{
  const b = built.platformer; const G = n => gidx(b, n);
  const X = G('x_hero'), Y = G('y_hero'), GR = G('gnd_hero'), VY = G('vy_hero');
  const src = b.r.src;
  ok(/p_gravity|func solid/.test(src) && !/v_ground/.test(src), 'platformer template uses the built-in physics (no user gravity variables)');
  const mk = () => { const vm = new ARC.VM(new ARC.Cart(b.r.blob), { seed: 9 }); vm.frame(0); return vm; };
  let vm = mk(); for (let f = 0; f < 12; f++) vm.frame(0);
  ok(vm.g[Y] === 104 && vm.g[GR] === 1, 'platformer: hero stands on the floor (y ' + vm.g[Y] + ', on ground ' + vm.g[GR] + ')');
  let minY = 999; vm.frame(16); for (let f = 0; f < 40; f++) { vm.frame(0); minY = Math.min(minY, vm.g[Y]); }
  ok(minY <= 70 && vm.g[Y] === 104, 'platformer: Z jumps about 36px and lands back (min y ' + minY + ')');
  vm = mk(); for (let f = 0; f < 4; f++) vm.frame(0); vm.frame(0); vm.frame(16); vm.frame(0);
  const y1 = vm.g[Y]; vm.frame(0); vm.frame(0); // in the air: a second press must not double-jump
  vm.frame(16); vm.frame(0); vm.frame(0);
  ok(vm.g[VY] > -9 && y1 < 104, 'platformer: no double jump in mid air');
  // land on platform 1 (tiles x3..7, row 11 -> top y 88): drop the hero above it
  vm = mk(); vm.g[X] = 40; vm.g[Y] = 60; for (let f = 0; f < 20; f++) vm.frame(0);
  ok(vm.g[Y] === 80 && vm.g[GR] === 1, 'platformer: falls onto a platform and stops on top (y ' + vm.g[Y] + ')');
  // head bump from below
  vm = mk(); vm.g[X] = 40; vm.g[Y] = 100; vm.frame(0); vm.frame(16); let miny = 999; for (let f = 0; f < 12; f++) { vm.frame(0); miny = Math.min(miny, vm.g[Y]); }
  ok(miny >= 97, 'platformer: platforms block the hero from below (min y ' + miny + ')');
  // wall: walking into the platform edge from the side is blocked
  vm = mk(); vm.g[X] = 8; vm.g[Y] = 80; vm.g[GR] = 0; for (let f = 0; f < 6; f++) vm.frame(2); // right
  ok(vm.g[X] > 8, 'platformer: arrow right moves the hero');
  // pit: walk right off the floor edge (tiles 0..8 -> x < 72) and fall = life lost
  vm = mk(); const lives0 = vm.g[G('v_lives')]; for (let f = 0; f < 200 && vm.g[G('v_lives')] === lives0 && !vm.over; f++) vm.frame(2);
  ok(vm.g[G('v_lives')] === lives0 - 1, 'platformer: walking into the pit costs a life (' + lives0 + ' -> ' + vm.g[G('v_lives')] + ')');
  ok(vm.g[X] === 8 && vm.g[Y] === 104, 'platformer: hero respawns at the start after falling');
  // collect a coin
  vm = mk(); vm.g[X] = 40; vm.g[Y] = 76; vm.frame(0); vm.frame(0);
  ok(vm.scoreV === 10, 'platformer: touching a coin scores (score ' + vm.scoreV + ')');
  // a scripted run (hold right, jump from three spots) climbs all platforms, collects coins and reaches the flag
  vm = mk();
  for (let f = 0; f < 400 && !vm.over; f++) {
    const x = vm.g[X], y = vm.g[Y], gr = vm.g[GR];
    const jump = gr && ((y === 104 && x >= 10 && x < 14) || (y === 80 && x >= 52 && x < 56) || (y === 56 && x >= 100 && x < 104));
    vm.frame(2 | (jump ? 16 : 0));
  }
  ok(vm.over && /MADE IT/.test(vm.overHead) && vm.scoreV >= 20, 'platformer: scripted run with only arrow right + Z reaches the flag (score ' + vm.scoreV + ')');
  // goal
  vm = mk(); vm.g[X] = 144; vm.g[Y] = 32; vm.frame(0);
  ok(vm.over && /MADE IT/.test(vm.overHead), 'platformer: reaching the flag wins (' + vm.overHead + ')');
}
{
  const b = built.dodger; const G = n => gidx(b, n);
  const vm = ARC.runCart(b.r.blob, 1500, () => 0, { seed: 5 });
  ok(vm.scoreV > 0 || vm.over, 'dodger: rocks fall and score');
}

// ---------------------------------------------------------------- compiler checks
section('compiler behaviour');
const k = (t, ...a) => ({ t, a, c: [] });
const C = (t, a, ...body) => ({ t, a, c: [body] });
function mini(scripts, mut) {
  const p = ARC.newProject();
  p.scripts = scripts.map((blocks, i) => ({ x: 0, y: i * 100, blocks }));
  if (mut) mut(p);
  return p;
}
{ // forever without an exit
  const r = ARC.buildProject(mini([[k('h_frame'), C('c_forever', [], k('m_move', 'hero', 1, 0))]]));
  ok(r.errors.some(e => /never ends/.test(e)), 'forever without exit is rejected');
  const r2 = ARC.buildProject(mini([[k('h_start'), C('c_forever', [], k('c_waitf', 5), k('g_addscore', 1))]]));
  ok(r2.errors.length === 0, 'forever with a wait inside "when game starts" is fine: ' + JSON.stringify(r2.errors));
  const r3 = ARC.buildProject(mini([[k('h_frame'), C('c_forever', [], k('c_break'))]]));
  ok(r3.errors.length === 0, 'forever with exit loop is fine');
}
{ // nested wait
  const r = ARC.buildProject(mini([[k('h_frame'), C('c_if', [1], k('c_waitf', 3))]]));
  ok(r.errors.some(e => /wait/.test(e)), 'wait inside if (non-start script) is rejected');
}
{ // unknown sprite / bad number
  const r = ARC.buildProject(mini([[k('h_frame'), k('m_move', 'ghost', 1, 1)]]));
  ok(r.errors.some(e => /ghost/.test(e)), 'unknown sprite reported');
  const r2 = ARC.buildProject(mini([[k('h_frame'), k('m_move', 'hero', 'abc', 1)]]));
  ok(r2.errors.some(e => /whole number/.test(e)), 'bad number reported');
  const r3 = ARC.buildProject(mini([[k('h_frame')]], p => { p.sprites[0].name = 'cls'; }));
  ok(r3.errors.some(e => /reserved/.test(e)), 'reserved sprite name rejected');
}
{ // too many variables
  const r = ARC.buildProject(mini([[k('h_frame')]], p => { for (let i = 0; i < 130; i++) p.vars.push('v' + i); }));
  ok(r.errors.some(e => /too many global/.test(e)), 'more than 128 variables is an error from the assembler');
}
{ // wait state machine: after pressing A, x moves right 3 frames later, then 2 more later
  const p = mini([[k('h_btnp', 'A'), k('m_goto', 'hero', 10, 10), k('c_waitf', 3), k('m_goto', 'hero', 50, 10), k('c_waits', 1), k('g_addscore', 7)]],
    q => { q.settings.autoClear = true; });
  const r = ARC.buildProject(p); ok(r.errors.length === 0, 'wait script compiles: ' + JSON.stringify(r.errors));
  const vm = new ARC.VM(new ARC.Cart(r.blob), {});
  const xi = r.g.globals.get('x_hero');
  vm.frame(0);
  const log = [];
  for (let f = 1; f <= 45; f++) { vm.frame(f === 2 ? 16 : 0); log.push(vm.g[xi]); }
  // press at frame 2: x=10 immediately, x=50 three frames later (frame 6), score 7 after 30 more frames
  ok(log[1] === 10 && log[2] === 10 && log[3] === 10 && log[4] === 50, 'timed script: x set, wait 3, x set (' + log.slice(0, 8) + ')');
  ok(vm.scoreV === 7, 'timed script: wait 1 second then score (score ' + vm.scoreV + ')');
  const vm2 = new ARC.VM(new ARC.Cart(r.blob), {}); vm2.frame(0);
  for (let f = 1; f <= 20; f++) vm2.frame(f === 2 ? 16 : 0);
  ok(vm2.scoreV === 0, 'timed script: score is NOT given before the wait ends');
}
{ // when-game-starts waits are real pauses: intro text then game
  const p = mini([[k('h_start'), k('l_ctext', 'READY', 60, 'WHITE'), k('c_waitf', 10), k('g_setscore', 5)], [k('h_frame'), k('g_addscore', 1)]]);
  const r = ARC.buildProject(p); ok(r.errors.length === 0, 'start wait compiles');
  const vm = new ARC.VM(new ARC.Cart(r.blob), {}); vm.frame(0);
  for (let f = 0; f < 5; f++) vm.frame(0);
  ok(vm.scoreV === 0, 'game logic is paused while the intro wait runs (score ' + vm.scoreV + ')');
  for (let f = 0; f < 20; f++) vm.frame(0);
  ok(vm.scoreV > 5, 'game logic starts after the intro (score ' + vm.scoreV + ')');
}
{ // HUD repaint when auto-clear is off
  const mk = clear => mini([[k('h_frame'), k('l_num', k('g_score'), 4, 4, 'WHITE', 0), k('l_text', 'HI', 4, 20, 'WHITE')]], q => { q.settings.autoClear = clear; });
  const off = ARC.buildProject(mk(false)), on = ARC.buildProject(mk(true));
  ok(off.errors.length === 0 && /rect\(4, 4, \d+, \d+, bgc\);\s*num\(4, 4/.test(off.src), 'auto-clear off: a background box is painted before each HUD number');
  ok(/rect\(4, 20, \d+, \d+, bgc\);\s*text\(4, 20/.test(off.src), 'auto-clear off: ... and before text');
  ok(!/cls\(bgc\)/.test(off.src) && /cls\(bgc\)/.test(on.src), 'cls only when auto-clear is on');
  // behaviour: digits must not stack
  const vm = new ARC.VM(new ARC.Cart(off.blob), {}); vm.frame(0);
  const sig = () => Array.from(vm.fb.slice(4 * 160, 12 * 160)).join(',');
  vm.scoreV = 88888; vm.frame(0); vm.scoreV = 1; vm.frame(0); const a = sig();
  const vm3 = new ARC.VM(new ARC.Cart(off.blob), {}); vm3.frame(0); vm3.scoreV = 1; vm3.frame(0);
  ok(a === sig.call(null) && Array.from(vm3.fb.slice(4 * 160, 12 * 160)).join(',') === a, 'auto-clear off: shrinking numbers leave no leftover pixels');
}
{ // messages
  const p = mini([[k('h_btnp', 'A'), k('e_bcast', 'boom')], [k('h_msg', 'boom'), k('g_addscore', 3)]], q => { q.msgs = ['boom']; });
  const r = ARC.buildProject(p); ok(r.errors.length === 0, 'messages compile ' + JSON.stringify(r.errors));
  const vm = new ARC.VM(new ARC.Cart(r.blob), {}); vm.frame(0); vm.frame(0); vm.frame(16); vm.frame(0); vm.frame(0); vm.frame(0);
  ok(vm.scoreV === 3, 'broadcast reaches its receiver exactly once (score ' + vm.scoreV + ')');
}
{ // lists and grid, loops
  const p = mini([[k('h_start'), k('v_lset', 3, 9), k('v_gset', 2, 2, 5), C('c_for', ['lives', 0, 3], k('v_lchg', 0, 2)), k('g_setscore', k('o_math', k('v_lget', 3), '+', k('v_gget', 2, 2)))]]);
  const r = ARC.buildProject(p); ok(r.errors.length === 0, 'list/grid compile ' + JSON.stringify(r.errors));
  const vm = new ARC.VM(new ARC.Cart(r.blob), {}); vm.frame(0);
  ok(vm.scoreV === 14, 'list item 9 + grid cell 5 = 14 (' + vm.scoreV + ')');
}
{ // limits: sprite count
  const p = mini([[k('h_frame')]], q => { q.sprites = []; for (let i = 0; i < 65; i++) q.sprites.push({ name: 's' + i, rows: new Array(8).fill('........'), color: 'WHITE', x: 0, y: 0, stage: false, visible: true }); });
  ok(ARC.buildProject(p).errors.some(e => /Too many sprites/.test(e)), '65 sprites rejected');
}
{ // runaway loop is caught by the 30000-step budget exactly like the device
  const p = mini([[k('h_frame'), C('c_while', [1], k('v_chg', 'lives', 1))]]);
  const r = ARC.buildProject(p);
  let msg = ''; try { ARC.runCart(r.blob, 3, null); } catch (e) { msg = e.message; }
  ok(/too slow/.test(msg), 'endless "while" is stopped by the step budget: ' + msg);
}

// ---------------------------------------------------------------- background tiles
section('background tiles (bgTiles)');
{
  // templates unchanged vs the pre-change page (bytes and generated source)
  const bak = path.join(HERE, 'arcadia_gamemaker.html.pre-bgfix.bak');
  if (fs.existsSync(bak)) {
    const mb = /<script id="core">([\s\S]*?)<\/script>/.exec(fs.readFileSync(bak, 'utf8'));
    const m0 = { exports: {} }; new Function('module', mb[1])(m0); const OLD = m0.exports;
    let n = 0;
    for (let i = 0; i < ARC.TEMPLATES.length; i++) {
      const a = OLD.buildProject(OLD.TEMPLATES[i].build()), b = ARC.buildProject(ARC.TEMPLATES[i].build());
      ok(a.src === b.src && Buffer.compare(Buffer.from(a.blob), Buffer.from(b.blob)) === 0, ARC.TEMPLATES[i].id + ': identical source and bytes to the pre-bgTiles page'); n++;
    }
    console.log('  ' + n + ' templates byte-identical to the previous page');
  } else console.log('  (no .pre-bgfix.bak, old-page comparison skipped)');
  for (const t of ARC.TEMPLATES) {
    const p = t.build(); const a = ARC.buildProject(p);
    p.bgTiles = new Array(16).fill('.'.repeat(20)); const b = ARC.buildProject(p);
    ok(a.src === b.src && !/Background/i.test(b.src), t.id + ': empty bgTiles emits nothing');
  }
  // compile path: greedy merge into rect() after cls(bgc), before platforms
  const p = ARC.newProject();
  p.bgTiles = new Array(16).fill('.'.repeat(20));
  p.bgTiles[0] = '4'.repeat(20); p.bgTiles[1] = '4'.repeat(20);           // one 160x16 BLUE band
  p.bgTiles[5] = '.....' + '3'.repeat(4) + '..' + '2' + '.'.repeat(8);      // GREEN 4 wide, RED single
  p.tiles = new Array(16).fill('.'.repeat(20)); p.tiles[14] = '#'.repeat(20);
  const r = ARC.buildProject(p);
  ok(r.errors.length === 0 && r.blob, 'bgTiles project compiles: ' + JSON.stringify(r.errors));
  const fr = r.src.slice(r.src.indexOf('func frame()'));
  ok(/cls\(bgc\);\s*rect\(0, 0, 160, 16, BLUE\);\s*rect\(40, 40, 32, 8, GREEN\);\s*rect\(88, 40, 8, 8, RED\);\s*rect\(0, 112, 160, 8, ORANGE\);/.test(fr), 'bgTiles become merged rect() calls after cls and before platforms:\n' + fr);
  // JSON round trip
  const p2 = JSON.parse(JSON.stringify(p));
  ok(JSON.stringify(p2.bgTiles) === JSON.stringify(p.bgTiles), 'bgTiles survive JSON');
  const r2 = ARC.buildProject(p2);
  ok(Buffer.compare(Buffer.from(r.blob), Buffer.from(r2.blob)) === 0, 'bgTiles save/load round trip leaves the cart unchanged');
  // runs headless, pixels land in the framebuffer, within budget
  const vm = ARC.runCart(r.blob, 5, null);
  const px = (x, y) => vm.fb[y * 160 + x];
  ok(px(3, 3) !== px(3, 60) && px(3, 3) === px(150, 10), 'background band is drawn (pixel differs from the empty area)');
  ok(vm.maxOps < ARC.R.BUDGET * 0.1, 'few background rects stay cheap (' + vm.maxOps + ' steps)');
  // checkerboard stress: worst case = many rects -> error beyond the cap
  const q = ARC.newProject(); q.bgTiles = [];
  for (let y = 0; y < 16; y++) { let row = ''; for (let x = 0; x < 20; x++) row += (x + y) % 2 ? '1' : '4'; q.bgTiles.push(row); }
  const rq = ARC.buildProject(q);
  ok(rq.errors.some(e => /Background painting needs 320 rectangles/.test(e)), 'checkerboard (320 rects) is rejected with a Checks error');
  // just under the cap compiles, runs within the step budget and the cart/code limits
  const q2 = ARC.newProject(); q2.bgTiles = new Array(16).fill('.'.repeat(20));
  let cnt = 0;
  for (let y = 0; y < 16 && cnt < 100; y++) for (let x = 0; x < 20 && cnt < 100; x += 2) { q2.bgTiles[y] = q2.bgTiles[y].slice(0, x) + (y % 2 ? '2' : '4') + q2.bgTiles[y].slice(x + 1); cnt++; }
  const r3 = ARC.buildProject(q2);
  ok(r3.errors.length === 0 && r3.blob, '100 background rects (the cap) compile: ' + JSON.stringify(r3.errors));
  if (r3.blob) {
    const vm3 = ARC.runCart(r3.blob, 5, null);
    ok(vm3.maxOps < ARC.R.BUDGET, 'worst-case background stays under ' + ARC.R.BUDGET + ' steps (' + vm3.maxOps + ')');
    ok(r3.blob.length < 14000 && r3.g.code.length < 8192, 'worst-case background fits the cart (' + r3.blob.length + ' bytes, code ' + r3.g.code.length + ')');
    console.log('  100-rect background: ' + r3.blob.length + ' bytes, code ' + r3.g.code.length + ', ' + vm3.maxOps + ' steps/frame');
  }
  const q3 = ARC.newProject(); q3.bgTiles = q2.bgTiles.map(r => r); 
  for (let y = 0; y < 16; y++) q3.bgTiles[y] = q3.bgTiles[y].replace(/\./g, (c, i) => (i + y) % 3 === 0 ? '2' : '.');
  const w3 = ARC.buildProject(q3);
  ok(w3.errors.length || w3.warnings.some(x => /rectangles/.test(x)), 'many rects give a warning or an error');
}

// ---------------------------------------------------------------- python cross-check
section('generated .arcl vs tools/make_carts.py (python)');
try {
  const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'gm-'));
  const files = [];
  for (const id in built) { const f = path.join(tmp, id + '.arcl'); fs.writeFileSync(f, built[id].r.src, 'latin1'); files.push([id, f]); }
  const py = [
    'import sys, os', 'sys.path.insert(0, sys.argv[1])', 'import make_carts as M', 'import json',
    'res = {}', 'for p in sys.argv[2:]:', '    blob, meta, g = M.compile_file(p)', '    res[os.path.basename(p)] = blob.hex()', 'print(json.dumps(res))'].join('\n');
  const out = cp.spawnSync('python', ['-I', '-c', py, TOOLS].concat(files.map(f => f[1])), { encoding: 'utf8' });
  if (out.status !== 0) { console.log('  python not usable, skipped (' + (out.stderr || out.error || '').toString().split('\n')[0] + ')'); }
  else {
    const res = JSON.parse(out.stdout.trim().split('\n').pop());
    for (const [id] of files) ok(res[id + '.arcl'] === Buffer.from(built[id].r.blob).toString('hex'), id + ': python assembler gives the same bytes as the JS assembler');
    console.log('  python make_carts.py and the JS assembler agree on ' + files.length + ' generated carts');
  }
  fs.rmSync(tmp, { recursive: true, force: true });
} catch (e) { console.log('  skipped: ' + e.message); }

console.log('\n' + passes + ' checks passed, ' + fails + ' failed');
process.exit(fails ? 1 : 0);
