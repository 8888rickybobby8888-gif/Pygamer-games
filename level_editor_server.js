// level_editor_server.js
//
// Small local companion for level_editor.html: a plain browser page can't
// touch the filesystem or run a compiler, so this is what actually splices
// a new level into PyGamerPortal.ino and drives arduino-cli to build and
// flash it. No npm install needed -- only built-in Node modules.
//
// Run with:  node level_editor_server.js
// Then open: http://localhost:8787
//
// Requires arduino-cli on PATH (or set ARDUINO_CLI below) and the
// adafruit:samd core + PyGamer board libraries already installed, same as
// any normal build of this sketch.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 8787;
const SKETCH_DIR = __dirname;
const INO_PATH = path.join(SKETCH_DIR, 'PyGamerPortal.ino');
const HTML_PATH = path.join(SKETCH_DIR, 'level_editor.html');
const FQBN = 'adafruit:samd:adafruit_pygamer_m4';
const INSERT_MARKER = '// LEVEL_EDITOR_INSERT_POINT';

function runCommand(cmd, args, cwd) {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { cwd, shell: true });
    let out = '';
    proc.stdout.on('data', (d) => (out += d.toString()));
    proc.stderr.on('data', (d) => (out += d.toString()));
    proc.on('close', (code) => resolve({ code, out }));
    proc.on('error', (err) => resolve({ code: -1, out: String(err) }));
  });
}

// Resolved once at startup: the process this server runs under isn't
// guaranteed to inherit the same PATH as an interactive shell, so a bare
// "arduino-cli" can silently fail to spawn there even though it works
// fine from a terminal. `where`/`which` finds the real absolute path
// once, and everything after uses that instead of the bare command name.
let ARDUINO_CLI = 'arduino-cli';
// A couple of common install spots to fall back to if this process's PATH
// doesn't happen to include arduino-cli (it may not match an interactive
// shell's PATH depending on how this server was launched).
const FALLBACK_PATHS = [
  path.join(process.env.USERPROFILE || '', 'bin', 'arduino-cli.exe'),
  path.join(process.env.LOCALAPPDATA || '', 'Arduino15', 'arduino-cli.exe'),
];

async function resolveArduinoCli() {
  const finder = process.platform === 'win32' ? 'where' : 'which';
  const { code, out } = await runCommand(finder, ['arduino-cli'], SKETCH_DIR);
  const first = out.split(/\r?\n/).map((l) => l.trim()).find(Boolean);
  if (code === 0 && first) {
    ARDUINO_CLI = first;
    console.log(`Using arduino-cli at: ${ARDUINO_CLI}`);
    return;
  }
  const fallback = FALLBACK_PATHS.find((p) => p && fs.existsSync(p));
  if (fallback) {
    ARDUINO_CLI = fallback;
    console.log(`Could not resolve via ${finder}; using fallback: ${ARDUINO_CLI}`);
    return;
  }
  console.log(
    `Could not find arduino-cli via ${finder} or common install paths -- ` +
    'falling back to bare "arduino-cli" on PATH, which may fail. ' +
    'If uploads fail, edit ARDUINO_CLI/FALLBACK_PATHS at the top of this file with the real path ' +
    '(run "where arduino-cli" in a terminal to find it).'
  );
}

async function detectPort() {
  const { out } = await runCommand(ARDUINO_CLI, ['board', 'list'], SKETCH_DIR);
  for (const line of out.split('\n')) {
    if (line.toLowerCase().includes('pygamer')) {
      const port = line.trim().split(/\s+/)[0];
      if (port) return port;
    }
  }
  return null;
}

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
      if (data.length > 2_000_000) {
        reject(new Error('body too large'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

// ---- Portal levels now live in tools/portal_levels.txt -> tools/out/portal.lvl (copied to the drive) ----
// "Upload" appends the exported level to portal_levels.txt, rebuilds portal.lvl with make_portal_pack.py
// (which validates it); POST /api/copy-portal copies it to the PyGamer when mounted as a USB drive.
const TOOLS_DIR = path.join(SKETCH_DIR, 'tools');
const LEVELS_TXT = path.join(TOOLS_DIR, 'portal_levels.txt');
const PACK_OUT = path.join(TOOLS_DIR, 'out', 'portal.lvl');
const DRIVE_MARKER = 'ARCADIA - PyGamer drive';

function findPyGamerDrive() {
  if (process.platform !== 'win32') return null;
  for (let c = 67; c <= 90; c++) {
    const root = String.fromCharCode(c) + ':' + path.sep;
    try {
      const head = fs.readFileSync(root + 'README.TXT', 'utf8').split(/\r?\n/).slice(0, 3).join('\n');
      if (head.includes(DRIVE_MARKER)) return root;
    } catch (e) { /* not our drive */ }
  }
  return null;
}

function countLevels(txt) {
  return txt.split(/\r?\n/).filter((l) => /^# L\d+$/.test(l)).length;
}

async function handleUpload(req, res) {
  let payload;
  try {
    payload = JSON.parse(await readBody(req));
  } catch (e) {
    return sendJson(res, 400, { ok: false, log: 'Bad request: ' + e.message });
  }
  const levelBlock = (payload && payload.code) || '';
  if (!levelBlock.includes('{{') || !levelBlock.includes('}}')) {
    return sendJson(res, 400, { ok: false, log: 'That does not look like an exported level block.' });
  }
  const rows = [...levelBlock.replace(/\/\/[^\n]*/g, '').matchAll(/"([^"]*)"/g)].map((m) => m[1]);
  if (!rows.length) return sendJson(res, 400, { ok: false, log: 'No level rows found in the exported block.' });

  let before;
  try {
    before = fs.readFileSync(LEVELS_TXT, 'utf8');
  } catch (e) {
    return sendJson(res, 500, { ok: false, log: 'Could not read tools/portal_levels.txt (run extract_portal_levels.py first): ' + e.message });
  }
  const n = countLevels(before) + 1;
  const name = 'L' + String(n).padStart(2, '0');
  fs.writeFileSync(LEVELS_TXT + '.bak', before, 'utf8');
  fs.writeFileSync(LEVELS_TXT, before.replace(/\s*$/, '\n') + '\n# ' + name + '\n' + rows.join('\n') + '\n', 'utf8');
  const py = await runCommand(process.platform === 'win32' ? 'python' : 'python3', ['make_portal_pack.py'], TOOLS_DIR);
  let log = py.out;
  if (py.code !== 0) {
    fs.writeFileSync(LEVELS_TXT, before, 'utf8');
    log += '\nThe level was rejected; portal_levels.txt is unchanged.';
    return sendJson(res, 200, { ok: false, log });
  }
  log += `\nAppended ${name} (level ${n}) to tools/portal_levels.txt and rebuilt tools/out/portal.lvl.`;
  log += '\nNote: the sketch plays pack records 6..52 (NUM_HAND_LEVELS); records beyond 52 are stored but not played yet.';
  const drive = findPyGamerDrive();
  if (drive) {
    log += `\nPyGamer drive found at ${drive}. POST /api/copy-portal (or run tools\install_assets.ps1 -Portal) to copy portal.lvl.`;
  } else {
    log += '\nPyGamer drive not mounted (Settings > USB drive). Run tools\install_assets.ps1 -Portal when it is.';
  }
  sendJson(res, 200, { ok: true, log, driveFound: !!drive });
}

async function handleCopyPortal(req, res) {
  const drive = findPyGamerDrive();
  if (!drive) return sendJson(res, 200, { ok: false, log: 'PyGamer drive not found.' });
  try {
    fs.mkdirSync(path.join(drive, 'packs'), { recursive: true });
    fs.copyFileSync(PACK_OUT, path.join(drive, 'packs', 'portal.lvl'));
    const got = fs.statSync(path.join(drive, 'packs', 'portal.lvl')).size;
    if (got !== fs.statSync(PACK_OUT).size) throw new Error('copy incomplete');
    sendJson(res, 200, { ok: true, log: `Copied portal.lvl to ${drive}packs. Eject the drive, then press B on the PyGamer.` });
  } catch (e) {
    sendJson(res, 200, { ok: false, log: 'Copy failed: ' + e.message });
  }
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && (req.url === '/' || req.url === '/level_editor.html')) {
      const html = fs.readFileSync(HTML_PATH, 'utf8');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
      return;
    }
    if (req.method === 'GET' && req.url === '/api/status') {
      const port = await detectPort();
      return sendJson(res, 200, { ok: true, connected: !!port, port });
    }
    if (req.method === 'POST' && req.url === '/api/copy-portal') {
      return await handleCopyPortal(req, res);
    }
    if (req.method === 'POST' && req.url === '/api/upload') {
      return await handleUpload(req, res);
    }
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  } catch (e) {
    sendJson(res, 500, { ok: false, log: 'Server error: ' + (e && e.message) });
  }
});

resolveArduinoCli().then(() => {
  server.listen(PORT, () => {
    console.log(`PyGamerPortal level editor server running at http://localhost:${PORT}`);
    console.log(`Sketch directory: ${SKETCH_DIR}`);
    console.log('Open the URL above in a browser (not the .html file directly) so uploads work.');
  });
});
