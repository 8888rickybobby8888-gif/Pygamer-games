// Bakes the raycaster's procedural wall/sprite patterns into 16x16 1bpp
// bitmap tables, so the firmware does a plain bit lookup per pixel
// instead of evaluating a formula. Reuses the exact same shape logic that
// was live in PyGamerPortal.ino (texturePixelLit / spritePixelLit) so the
// visuals don't change, just how they're stored/read.
//
// Run with: node gen_textures.js -- prints C++ array literals to paste in.

const SIZE = 16;

function wallBrick(tx, ty) {
  const rowOffset = ((Math.floor(ty / 4)) % 2 === 0) ? 0 : (SIZE / 2);
  const mortarRow = (ty % 4) === 0;
  const mortarCol = ((tx + rowOffset) % (SIZE / 2)) === 0;
  return !(mortarRow || mortarCol);
}

function wallHazard(tx, ty) {
  return Math.floor((tx + ty) / 3) % 2 === 0;
}

function wallDoor(tx, ty) {
  if (tx < 1 || tx > SIZE - 2 || ty < 1 || ty > SIZE - 2) return true;
  return (tx % 5 !== 0) && (ty % 5 !== 0);
}

function wallEmitter(tx, ty) {
  const dx = tx - SIZE / 2, dy = ty - SIZE / 2;
  const d2 = dx * dx + dy * dy;
  return d2 < 10 || (d2 > 30 && d2 < 54);
}

function sprCrate(tx, ty) {
  const border = tx < 1 || tx > SIZE - 2 || ty < 1 || ty > SIZE - 2;
  const cross = Math.abs(tx - ty) <= 1 || Math.abs((SIZE - 1 - tx) - ty) <= 1;
  return !(border || cross);
}

function sprRing(tx, ty) {
  const dx = tx - SIZE / 2, dy = ty - SIZE / 2;
  const d2 = dx * dx + dy * dy;
  return d2 < 50 && !(d2 > 22 && d2 < 34);
}

function sprDiamond(tx, ty) {
  const dx = tx - SIZE / 2, dy = ty - SIZE / 2;
  return (Math.abs(dx) + Math.abs(dy)) < 7;
}

function sprKey(tx, ty) {
  const hx = tx - 5, hy = ty - 5;
  const head = (hx * hx + hy * hy) < 10;
  const shaft = tx >= 5 && tx <= 7 && ty >= 6 && ty <= 13;
  const tooth = ty >= 10 && ty <= 13 && tx >= 7 && tx <= 10 && (ty % 2 === 1);
  return head || shaft || tooth;
}

function sprBolt(tx, ty) {
  return tx > (SIZE / 2 - 2) - Math.floor(ty / 3) && tx < (SIZE / 2 + 2) - Math.floor(ty / 3);
}

function sprPlate(tx, ty) {
  const border = tx < 2 || tx > SIZE - 3 || ty < 2 || ty > SIZE - 3;
  return border || ((Math.floor(tx / 3) + Math.floor(ty / 3)) % 2 === 0);
}

function sprCheck(tx, ty) {
  return (Math.floor(tx / 4) + Math.floor(ty / 4)) % 2 === 0;
}

function bake(name, fn) {
  const rows = [];
  for (let y = 0; y < SIZE; y++) {
    let bits = 0;
    for (let x = 0; x < SIZE; x++) {
      if (fn(x, y)) bits |= (1 << x);
    }
    rows.push('0x' + bits.toString(16).padStart(4, '0'));
  }
  return `static const uint16_t ${name}[TEX_SIZE] = {${rows.join(', ')}};`;
}

const textures = [
  ['TEX_WALL_BRICK', wallBrick],
  ['TEX_WALL_HAZARD', wallHazard],
  ['TEX_WALL_DOOR', wallDoor],
  ['TEX_WALL_EMITTER', wallEmitter],
  ['TEX_SPR_CRATE', sprCrate],
  ['TEX_SPR_RING', sprRing],
  ['TEX_SPR_DIAMOND', sprDiamond],
  ['TEX_SPR_KEY', sprKey],
  ['TEX_SPR_BOLT', sprBolt],
  ['TEX_SPR_PLATE', sprPlate],
  ['TEX_SPR_CHECK', sprCheck],
];

for (const [name, fn] of textures) {
  console.log(bake(name, fn));
}
