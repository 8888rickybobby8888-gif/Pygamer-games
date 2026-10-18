#!/usr/bin/env python3
"""Cross-platform twin of install_assets.ps1: copies optional Arcadia content onto the PyGamer USB drive.

  (default)      art pack      out/banners.bin     -> <drive>/assets/banners.bin
  --packs        level packs   out/packs/g*.pak    -> <drive>/packs/
  --portal       Portal levels out/portal.lvl      -> <drive>/packs/portal.lvl
  --words        word list     out/words.txt       -> <drive>/data/words.txt
  --carts        cartridges    out/carts/*.arc     -> <drive>/carts/   (--clean-carts also removes stale .arc files)
  --roms         CHIP-8 ROMs   out/roms/*.ch8,*.key -> <drive>/roms/
  --levels       level slots   out/levels/g<id>s<slot>[a|b].lvl -> <drive>/levels/
  --quest        Portal Quest  out/quest.wld       -> <drive>/worlds/quest.wld

  1. On the PyGamer: Settings > USB drive (the drive appears on the PC).
  2. python install_assets.py --packs        (auto-detects the drive by its README.TXT; --drive PATH to name it)
  3. Eject the drive, then press B on the PyGamer (it reboots and picks up the files).
"""
import argparse, os, re, shutil, string, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
MARKER = 'ARCADIA - PyGamer drive'


def fail(msg):
    print('ERROR: ' + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def need(path, hint):
    if not os.path.exists(path):
        fail('%s not found. Run:  python %s   (in the tools folder) first.' % (path, hint))


def list_files(d, pred):
    return [os.path.join(d, n) for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n)) and pred(n)]


# ---- source validation (same rules as install_assets.ps1) ----
def check_carts(src):
    need(src, 'make_carts.py')
    files = []
    for p in list_files(src, lambda n: n.lower().endswith('.arc')):
        b = read(p)
        if len(os.path.basename(p)) >= 20 or not 208 <= len(b) <= 14000 or b[:4] != b'ARC1' or b[4] != 1:
            fail('%s is not a valid cartridge (name must be under 20 characters; rebuild with make_carts.py).' % os.path.basename(p))
        files.append(p)
    if not files:
        fail('no .arc files in %s. Run:  python make_carts.py   (in the tools folder) first.' % src)
    return files


def check_roms(src):
    need(src, 'make_roms.py')
    files = []
    for p in list_files(src, lambda n: n.lower().endswith(('.ch8', '.key'))):
        size = os.path.getsize(p)
        if len(os.path.basename(p)) >= 20 or not 1 <= size <= 3584:
            fail('%s is not usable (name under 20 characters, size 1..3584 bytes).' % os.path.basename(p))
        files.append(p)
    if not any(p.lower().endswith('.ch8') for p in files):
        fail('no .ch8 files in %s. Run:  python make_roms.py   (in the tools folder) first.' % src)
    return files


def check_words(path):
    need(path, 'make_words.py')
    b = read(path)
    lines = [l.strip() for l in b.decode('ascii', 'replace').split('\n') if l.strip()]
    if not 200 <= len(b) <= 400000 or len(lines) < 50 or any(not re.fullmatch(r'[A-Za-z]{3,15}', l) for l in lines):
        fail('%s is not a valid word list (one a-z word per line, 3-15 letters; regenerate with make_words.py).' % path)
    return len(lines)


def check_levels(src):
    if not os.path.exists(src):
        fail('%s not found. Save slot files from tools/creator/arcadia_levels.html into tools/out/levels first.' % src)
    files = []
    for p in list_files(src, lambda n: re.fullmatch(r'g\d+s\d[ab]?\.lvl', n) is not None):
        n = os.path.basename(p)
        m = re.fullmatch(r'g(\d+)s([0-4])[ab]?\.lvl', n)
        if not m:
            fail('%s is not a slot file name (g<id>s<0-4>a.lvl).' % n)
        gid = int(m.group(1))
        b = read(p)
        if gid > 24 or not 20 <= len(b) <= 16 + 24 * 16 + 2 or not 0xA5 <= b[0] <= 0xA8 or (b[1] & 0x7F) != gid:
            fail('%s is not a valid level slot file for game %d (re-export it from arcadia_levels.html).' % (n, gid))
        files.append(p)
    if not files:
        fail('no g<id>s<slot>a.lvl files in %s.' % src)
    return files


def check_quest(path):
    need(path, 'make_quest_world.py')
    b = read(path)
    if len(b) < 32 or b[:4] != b'ARQW' or b[4] != 1 or not 1 <= b[5] <= 8 or not 1 <= b[6] <= 8 or len(b) < 32 + 8 * b[5] * b[6]:
        fail('%s is not a valid Portal Quest world (regenerate with make_quest_world.py).' % path)


def check_portal(path):
    need(path, 'make_portal_pack.py')
    b = read(path)
    n = b[5] + 256 * b[6] if len(b) >= 8 else 0
    if len(b) < 8 or b[:4] != b'ARPL' or b[4] != 1 or not 1 <= n <= 1000 or len(b) != 8 + n * 1616:
        fail('%s is not a valid Portal level pack (regenerate with make_portal_pack.py).' % path)
    return n


def check_packs(src):
    need(src, 'make_packs.py')
    files = []
    for p in list_files(src, lambda n: re.fullmatch(r'g\d+\.pak', n) is not None):
        gid = int(re.fullmatch(r'g(\d+)\.pak', os.path.basename(p)).group(1))
        b = read(p)
        if not (20 <= len(b) <= 20480 and b[:4] == b'ARPK' and b[4] == 1 and b[5] == gid and 1 <= b[6] <= 60):
            fail('%s is not a valid level pack (regenerate with make_packs.py).' % os.path.basename(p))
        files.append(p)
    if not files:
        fail('no g<id>.pak files in %s. Run:  python make_packs.py   (in the tools folder) first.' % src)
    return files


def check_banners(path):
    need(path, 'make_assets.py')
    b = read(path)
    if len(b) < 8 or b[:4] != b'ARB1' or b[4] != 1 or b[6] != 64 or b[7] != 32 or len(b) < 8 + b[5] * 4096:
        fail('%s is not a valid ARB1 banner pack (regenerate it with make_assets.py).' % path)


# ---- find the PyGamer drive ----
def is_arcadia_drive(root):
    try:
        with open(os.path.join(root, 'README.TXT'), 'r', errors='replace') as f:
            head = ''.join(f.readline() for _ in range(3))
    except OSError:
        return False
    return MARKER in head


def candidate_roots():
    if os.name == 'nt':
        return ['%s:\\' % c for c in string.ascii_uppercase if os.path.exists('%s:\\' % c)]
    roots = []
    for base in ('/Volumes', '/media', '/run/media', '/mnt'):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if not os.path.isdir(p):
                continue
            roots.append(p)
            if base in ('/media', '/run/media'):   # /media/<user>/<label>
                try:
                    roots += [os.path.join(p, s) for s in sorted(os.listdir(p)) if os.path.isdir(os.path.join(p, s))]
                except OSError:
                    pass
    return roots


def find_drive(arg):
    if arg:
        root = arg
        if os.name == 'nt' and re.fullmatch(r'[A-Za-z]:?', arg):
            root = arg[0].upper() + ':\\'
        if not os.path.isdir(root):
            fail('drive %s is not available.' % root)
        if not is_arcadia_drive(root):
            fail("%s has no README.TXT starting with '%s'. It does not look like the PyGamer drive; nothing was copied.\n"
                 "       (Is the PyGamer in Settings > USB drive? A drive formatted by an older build may lack the README: "
                 "press B to reboot, then enter USB drive again.)" % (root, MARKER))
        return root
    found = [r for r in candidate_roots() if is_arcadia_drive(r)]
    if not found:
        fail('PyGamer drive not found. On the PyGamer open Settings > USB drive, wait for the drive to appear, '
             'then run this again (or pass --drive PATH).')
    if len(found) > 1:
        fail('several PyGamer drives found (%s). Re-run with --drive PATH.' % ', '.join(found))
    return found[0]


def copy_all(files, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    total = 0
    for p in files:
        dest = os.path.join(dest_dir, os.path.basename(p))
        shutil.copyfile(p, dest)
        got, want = os.path.getsize(dest), os.path.getsize(p)
        if got != want:
            fail('copy of %s incomplete (%d of %d bytes). Do not eject yet; run this again.' % (os.path.basename(p), got, want))
        total += got
        print('  %-20s %6d bytes' % (os.path.basename(p), got))
    print('Copied %d file(s) (%d bytes) to %s' % (len(files), total, dest_dir))


def main(argv):
    ap = argparse.ArgumentParser(description='Install optional Arcadia content onto the PyGamer USB drive.')
    ap.add_argument('--drive', default='', help='drive letter (E:) or mount path; auto-detected when omitted')
    for k in ('packs', 'portal', 'quest', 'levels', 'words', 'carts', 'roms'):
        ap.add_argument('--' + k, action='store_true')
    ap.add_argument('--clean-carts', action='store_true', help='with --carts: delete .arc files on the drive that are not in out/carts')
    ap.add_argument('--out', default=OUT, help='folder holding the built files (default tools/out)')
    a = ap.parse_args(argv)
    o = a.out
    modes = [k for k in ('carts', 'roms', 'words', 'levels', 'quest', 'portal', 'packs') if getattr(a, k)]
    mode = modes[0] if modes else 'banners'   # same precedence as the .ps1

    if mode == 'carts':
        files = check_carts(os.path.join(o, 'carts'))
    elif mode == 'roms':
        files = check_roms(os.path.join(o, 'roms'))
    elif mode == 'words':
        nwords = check_words(os.path.join(o, 'words.txt'))
    elif mode == 'levels':
        files = check_levels(os.path.join(o, 'levels'))
    elif mode == 'quest':
        check_quest(os.path.join(o, 'quest.wld'))
    elif mode == 'portal':
        nlev = check_portal(os.path.join(o, 'portal.lvl'))
    elif mode == 'packs':
        files = check_packs(os.path.join(o, 'packs'))
    else:
        check_banners(os.path.join(o, 'banners.bin'))

    root = find_drive(a.drive)
    print('PyGamer drive: ' + root)

    if mode in ('carts', 'roms'):
        sub = 'carts' if mode == 'carts' else 'roms'
        copy_all(files, os.path.join(root, sub))
        if mode == 'carts' and a.clean_carts:
            keep = {os.path.basename(p).lower() for p in files}
            removed = 0
            d = os.path.join(root, 'carts')
            for n in sorted(os.listdir(d)):
                if n.lower().endswith('.arc') and n.lower() not in keep:
                    os.remove(os.path.join(d, n))
                    print('  removed stale cart: ' + n)
                    removed += 1
            print('clean-carts: removed %d stale cartridge file(s). (Scores in /arcadia/carts.bin are kept.)' % removed)
        print('\nNow EJECT the drive, THEN press B on the PyGamer (it reboots and rescans).')
        print('Cartridges appear in the game picker (Left = EXPANSIONS filter).' if mode == 'carts'
              else "Open 'RETRO CHIP-8' in the game picker.")
    elif mode == 'levels':
        print('NOTE: delete any older g<id>s<slot>*.lvl on the drive that you are replacing (the file with the newer generation wins).')
        copy_all(files, os.path.join(root, 'levels'))
        print("\nNow EJECT the drive, THEN press B on the PyGamer. Open the game's Levels menu to see the slots.")
    elif mode == 'words':
        copy_all([os.path.join(o, 'words.txt')], os.path.join(root, 'data'))
        print('(%d words)\nNow EJECT the drive, THEN press B on the PyGamer. Hangman and Wordle read the list each round.' % nwords)
    elif mode == 'quest':
        copy_all([os.path.join(o, 'quest.wld')], os.path.join(root, 'worlds'))
        print('\nNow EJECT the drive, THEN press B on the PyGamer. Portal Quest reads the world from the drive when you open it.')
    elif mode == 'portal':
        copy_all([os.path.join(o, 'portal.lvl')], os.path.join(root, 'packs'))
        print('(%d levels)\nNow EJECT the drive, THEN press B on the PyGamer. Portal levels 6-52 are then read from the drive.' % nlev)
    elif mode == 'packs':
        copy_all(files, os.path.join(root, 'packs'))
        print("\nNow EJECT the drive, THEN press B on the PyGamer. Open a game's Levels menu: 'Browse Packs' appears when its pack is installed.")
    else:
        copy_all([os.path.join(o, 'banners.bin')], os.path.join(root, 'assets'))
        print('\nNow EJECT the drive, THEN press B on the PyGamer. It reboots and shows banners on the game title screens.')


if __name__ == '__main__':
    main(sys.argv[1:])
