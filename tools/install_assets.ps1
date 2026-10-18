<#
Installs optional Arcadia content onto the PyGamer USB drive:
  (default)  the art pack  out\banners.bin  ->  <drive>\assets\banners.bin
  -Packs     the level packs  out\packs\g*.pak  ->  <drive>\packs\
  -Portal    the Portal hand-made levels  out\portal.lvl  ->  <drive>\packs\portal.lvl
  -Words     the Hangman / Wordle word list  out\words.txt  ->  <drive>\data\words.txt  (build it with make_words.py)
  -Carts     the expansion cartridges  out\carts\*.arc  ->  <drive>\carts\  (build them with make_carts.py)
  -CleanCarts  (with -Carts) also deletes every <drive>\carts\*.arc that is NOT in out\carts (retired cartridges), listing each one
  -Roms      the CHIP-8 ROMs  out\roms\*.ch8 (+ *.key)  ->  <drive>\roms\  (build them with make_roms.py)
  -Levels    your custom level slot files  out\levels\g<id>s<slot>[a|b].lvl  ->  <drive>\levels\  (save them from creator\arcadia_levels.html)
  -Quest     the Portal Quest world  out\quest.wld  ->  <drive>\worlds\quest.wld  (build it with make_quest_world.py)

  1. On the PyGamer: Settings > USB drive (the drive appears on the PC).
  2. Run:   powershell -ExecutionPolicy Bypass -File install_assets.ps1                   (art pack, auto-detects the drive)
            powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Packs            (level packs)
            powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Packs -Drive E:  (or name the drive yourself)
  3. Eject the drive in Windows, then press B on the PyGamer (it reboots and picks up the files).

Only <drive>\assets\banners.bin (default) or the g<id>.pak files inside <drive>\packs\ (-Packs) are written.
Nothing else on the drive is touched. The script refuses to run when no PyGamer drive is found.
#>
param(
  [string]$Drive = "",
  [string]$Source = (Join-Path $PSScriptRoot "out\banners.bin"),
  [switch]$Packs,
  [switch]$Portal,
  [switch]$Quest,
  [switch]$Levels,
  [switch]$Words,
  [switch]$Carts,
  [switch]$CleanCarts,
  [switch]$Roms,
  [string]$CartsSource = (Join-Path $PSScriptRoot "out\carts"),
  [string]$RomsSource = (Join-Path $PSScriptRoot "out\roms"),
  [string]$WordsSource = (Join-Path $PSScriptRoot "out\words.txt"),
  [string]$QuestSource = (Join-Path $PSScriptRoot "out\quest.wld"),
  [string]$PortalSource = (Join-Path $PSScriptRoot "out\portal.lvl"),
  [string]$PacksSource = (Join-Path $PSScriptRoot "out\packs"),
  [string]$LevelsSource = (Join-Path $PSScriptRoot "out\levels")
)
$ErrorActionPreference = "Stop"
$marker = "ARCADIA - PyGamer drive"

function Test-ArcadiaDrive([string]$root) {
  $readme = Join-Path $root "README.TXT"
  if (-not (Test-Path -LiteralPath $readme)) { return $false }
  try { $head = Get-Content -LiteralPath $readme -TotalCount 3 -ErrorAction Stop } catch { return $false }
  return (($head -join "`n") -like "*$marker*")
}

# ---- validate the source files before looking for the drive ----
$packFiles = @()
$cartFiles = @()
$romFiles = @()
$levelFiles = @()
if ($Carts) {
  if (-not (Test-Path -LiteralPath $CartsSource)) {
    Write-Host "ERROR: $CartsSource not found. Run:  python make_carts.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  foreach ($f in (Get-ChildItem -LiteralPath $CartsSource -Filter "*.arc" -File)) {
    $b = [System.IO.File]::ReadAllBytes($f.FullName)
    if ($f.Name.Length -ge 20 -or $b.Length -lt 208 -or $b.Length -gt 14000 -or [System.Text.Encoding]::ASCII.GetString($b[0..3]) -ne "ARC1" -or $b[4] -ne 1) {
      Write-Host "ERROR: $($f.Name) is not a valid cartridge (name must be under 20 characters; rebuild with make_carts.py)." -ForegroundColor Red
      exit 1
    }
    $cartFiles += $f
  }
  if ($cartFiles.Count -eq 0) {
    Write-Host "ERROR: no .arc files in $CartsSource. Run:  python make_carts.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
} elseif ($Roms) {
  if (-not (Test-Path -LiteralPath $RomsSource)) {
    Write-Host "ERROR: $RomsSource not found. Run:  python make_roms.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  foreach ($f in (Get-ChildItem -LiteralPath $RomsSource -File | Where-Object { $_.Extension -in @(".ch8", ".key") })) {
    if ($f.Name.Length -ge 20 -or $f.Length -lt 1 -or $f.Length -gt 3584) {
      Write-Host "ERROR: $($f.Name) is not usable (name under 20 characters, size 1..3584 bytes)." -ForegroundColor Red
      exit 1
    }
    $romFiles += $f
  }
  if (@($romFiles | Where-Object { $_.Extension -eq ".ch8" }).Count -eq 0) {
    Write-Host "ERROR: no .ch8 files in $RomsSource. Run:  python make_roms.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
} elseif ($Words) {
  if (-not (Test-Path -LiteralPath $WordsSource)) {
    Write-Host "ERROR: $WordsSource not found. Run:  python make_words.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  $wb = [System.IO.File]::ReadAllBytes($WordsSource)
  $wtxt = [System.Text.Encoding]::ASCII.GetString($wb)
  $wlines = @($wtxt -split "`n" | Where-Object { $_.Trim() -ne "" })
  $wbad = @($wlines | Where-Object { $_.Trim() -notmatch "^[A-Za-z]{3,15}$" })
  if ($wb.Length -lt 200 -or $wb.Length -gt 400000 -or $wlines.Count -lt 50 -or $wbad.Count -gt 0) {
    Write-Host "ERROR: $WordsSource is not a valid word list (one a-z word per line, 3-15 letters; regenerate with make_words.py)." -ForegroundColor Red
    exit 1
  }
} elseif ($Levels) {
  if (-not (Test-Path -LiteralPath $LevelsSource)) {
    Write-Host "ERROR: $LevelsSource not found. Save slot files from tools\creator\arcadia_levels.html into tools\out\levels first." -ForegroundColor Red
    exit 1
  }
  foreach ($f in (Get-ChildItem -LiteralPath $LevelsSource -Filter "g*s*.lvl" -File)) {
    if ($f.Name -notmatch "^g(\d+)s([0-4])[ab]?\.lvl$") { Write-Host "ERROR: $($f.Name) is not a slot file name (g<id>s<0-4>a.lvl)." -ForegroundColor Red; exit 1 }
    $id = [int]$Matches[1]
    $b = [System.IO.File]::ReadAllBytes($f.FullName)
    if ($id -gt 24 -or $b.Length -lt 20 -or $b.Length -gt 16 + 24 * 16 + 2 -or ($b[0] -lt 0xA5 -or $b[0] -gt 0xA8) -or ($b[1] -band 0x7F) -ne $id) {
      Write-Host "ERROR: $($f.Name) is not a valid level slot file for game $id (re-export it from arcadia_levels.html)." -ForegroundColor Red
      exit 1
    }
    $levelFiles += $f
  }
  if ($levelFiles.Count -eq 0) {
    Write-Host "ERROR: no g<id>s<slot>a.lvl files in $LevelsSource." -ForegroundColor Red
    exit 1
  }
} elseif ($Quest) {
  if (-not (Test-Path -LiteralPath $QuestSource)) {
    Write-Host "ERROR: $QuestSource not found. Run:  python make_quest_world.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  $qb = [System.IO.File]::ReadAllBytes($QuestSource)
  if ($qb.Length -lt 32 -or [System.Text.Encoding]::ASCII.GetString($qb[0..3]) -ne "ARQW" -or $qb[4] -ne 1 -or $qb[5] -lt 1 -or $qb[5] -gt 8 -or $qb[6] -lt 1 -or $qb[6] -gt 8 -or $qb.Length -lt (32 + 8 * $qb[5] * $qb[6])) {
    Write-Host "ERROR: $QuestSource is not a valid Portal Quest world (regenerate with make_quest_world.py)." -ForegroundColor Red
    exit 1
  }
} elseif ($Portal) {
  if (-not (Test-Path -LiteralPath $PortalSource)) {
    Write-Host "ERROR: $PortalSource not found. Run:  python make_portal_pack.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  $pb = [System.IO.File]::ReadAllBytes($PortalSource)
  $pn = if ($pb.Length -ge 8) { $pb[5] + 256 * $pb[6] } else { 0 }
  if ($pb.Length -lt 8 -or [System.Text.Encoding]::ASCII.GetString($pb[0..3]) -ne "ARPL" -or $pb[4] -ne 1 -or $pn -lt 1 -or $pn -gt 1000 -or $pb.Length -ne (8 + $pn * 1616)) {
    Write-Host "ERROR: $PortalSource is not a valid Portal level pack (regenerate with make_portal_pack.py)." -ForegroundColor Red
    exit 1
  }
} elseif ($Packs) {
  if (-not (Test-Path -LiteralPath $PacksSource)) {
    Write-Host "ERROR: $PacksSource not found. Run:  python make_packs.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  foreach ($f in (Get-ChildItem -LiteralPath $PacksSource -Filter "g*.pak" -File)) {
    if ($f.Name -notmatch "^g(\d+)\.pak$") { continue }
    $id = [int]$Matches[1]
    $b = [System.IO.File]::ReadAllBytes($f.FullName)
    $okHdr = ($b.Length -ge 20 -and $b.Length -le 20480 -and [System.Text.Encoding]::ASCII.GetString($b[0..3]) -eq "ARPK" -and $b[4] -eq 1 -and $b[5] -eq $id -and $b[6] -ge 1 -and $b[6] -le 60)
    if (-not $okHdr) {
      Write-Host "ERROR: $($f.Name) is not a valid level pack (regenerate with make_packs.py)." -ForegroundColor Red
      exit 1
    }
    $packFiles += $f
  }
  if ($packFiles.Count -eq 0) {
    Write-Host "ERROR: no g<id>.pak files in $PacksSource. Run:  python make_packs.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
} else {
  if (-not (Test-Path -LiteralPath $Source)) {
    Write-Host "ERROR: $Source not found. Run:  python make_assets.py   (in the tools folder) first." -ForegroundColor Red
    exit 1
  }
  $srcSize = (Get-Item -LiteralPath $Source).Length
  $hdr = [System.IO.File]::ReadAllBytes($Source)[0..7]
  if ([System.Text.Encoding]::ASCII.GetString($hdr[0..3]) -ne "ARB1" -or $hdr[4] -ne 1 -or $hdr[6] -ne 64 -or $hdr[7] -ne 32 -or $srcSize -lt (8 + $hdr[5] * 4096)) {
    Write-Host "ERROR: $Source is not a valid ARB1 banner pack (regenerate it with make_assets.py)." -ForegroundColor Red
    exit 1
  }
}

# ---- find the PyGamer drive ----
$root = $null
if ($Drive -ne "") {
  $d = $Drive.TrimEnd("\", ":").ToUpper()
  if ($d -notmatch "^[A-Z]$") { Write-Host "ERROR: -Drive must be a drive letter such as E:" -ForegroundColor Red; exit 1 }
  $root = "${d}:\"
  if (-not (Test-Path -LiteralPath $root)) { Write-Host "ERROR: drive $root is not available." -ForegroundColor Red; exit 1 }
  if (-not (Test-ArcadiaDrive $root)) {
    Write-Host "ERROR: $root has no README.TXT starting with '$marker'. It does not look like the PyGamer drive; nothing was copied." -ForegroundColor Red
    Write-Host "       (Is the PyGamer in Settings > USB drive? A drive formatted by an older build may lack the README: press B to reboot, then enter USB drive again.)"
    exit 1
  }
} else {
  $found = @()
  foreach ($v in (Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -in @("Removable", "Fixed") })) {
    $r = "$($v.DriveLetter):\"
    if ((Test-Path -LiteralPath $r) -and (Test-ArcadiaDrive $r)) { $found += $r }
  }
  if ($found.Count -eq 0) {
    Write-Host "ERROR: PyGamer drive not found. On the PyGamer open Settings > USB drive, wait for the drive to appear, then run this again (or pass -Drive E:)." -ForegroundColor Red
    exit 1
  }
  if ($found.Count -gt 1) {
    Write-Host "ERROR: several PyGamer drives found ($($found -join ', ')). Re-run with -Drive <letter>:" -ForegroundColor Red
    exit 1
  }
  $root = $found[0]
}

Write-Host "PyGamer drive: $root"

if ($Carts -or $Roms) {
  $sub = if ($Carts) { "carts" } else { "roms" }
  $list = if ($Carts) { $cartFiles } else { $romFiles }
  $destDir = Join-Path $root $sub
  if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created $destDir"
  }
  $total = 0
  foreach ($f in $list) {
    $dest = Join-Path $destDir $f.Name
    Copy-Item -LiteralPath $f.FullName -Destination $dest -Force
    $got = (Get-Item -LiteralPath $dest).Length
    if ($got -ne $f.Length) {
      Write-Host "ERROR: copy of $($f.Name) incomplete ($got of $($f.Length) bytes). Do not eject yet; run this again." -ForegroundColor Red
      exit 1
    }
    $total += $got
    Write-Host ("  {0,-20} {1,6} bytes" -f $f.Name, $got)
  }
  Write-Host "Copied $($list.Count) files ($total bytes) to $destDir" -ForegroundColor Green
  if ($Carts -and $CleanCarts) {
    $keep = @{}
    foreach ($f in $list) { $keep[$f.Name.ToLowerInvariant()] = $true }
    $removed = 0
    foreach ($old in (Get-ChildItem -LiteralPath $destDir -Filter "*.arc" -File)) {
      if (-not $keep.ContainsKey($old.Name.ToLowerInvariant())) {
        Remove-Item -LiteralPath $old.FullName -Force
        Write-Host "  removed stale cart: $($old.Name)" -ForegroundColor Yellow
        $removed++
      }
    }
    Write-Host "CleanCarts: removed $removed stale cartridge file(s). (Scores in /arcadia/carts.bin are kept.)" -ForegroundColor Green
  }
  Write-Host ""
  Write-Host "Now EJECT the drive in Windows, THEN press B on the PyGamer (it reboots and rescans)." -ForegroundColor Yellow
  if ($Carts) { Write-Host "Cartridges appear in the game picker (Left = EXPANSIONS filter)." -ForegroundColor Yellow }
  else { Write-Host "Open 'RETRO CHIP-8' in the game picker." -ForegroundColor Yellow }
  exit 0
}

if ($Levels) {
  $destDir = Join-Path $root "levels"
  if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created $destDir"
  }
  Write-Host "NOTE: delete any older g<id>s<slot>*.lvl on the drive that you are replacing (the file with the newer generation wins)." -ForegroundColor Yellow
  $total = 0
  foreach ($f in $levelFiles) {
    $dest = Join-Path $destDir $f.Name
    Copy-Item -LiteralPath $f.FullName -Destination $dest -Force
    $got = (Get-Item -LiteralPath $dest).Length
    if ($got -ne $f.Length) {
      Write-Host "ERROR: copy of $($f.Name) incomplete ($got of $($f.Length) bytes). Do not eject yet; run this again." -ForegroundColor Red
      exit 1
    }
    $total += $got
    Write-Host ("  {0,-14} {1,5} bytes" -f $f.Name, $got)
  }
  Write-Host "Copied $($levelFiles.Count) level files ($total bytes) to $destDir" -ForegroundColor Green
  Write-Host ""
  Write-Host "Now EJECT the drive in Windows, THEN press B on the PyGamer. Open the game's Levels menu to see the slots." -ForegroundColor Yellow
  exit 0
}

if ($Words) {
  $destDir = Join-Path $root "data"
  if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created $destDir"
  }
  $dest = Join-Path $destDir "words.txt"
  Copy-Item -LiteralPath $WordsSource -Destination $dest -Force
  $got = (Get-Item -LiteralPath $dest).Length
  if ($got -ne $wb.Length) {
    Write-Host "ERROR: copy incomplete ($got of $($wb.Length) bytes). Do not eject yet; run this again." -ForegroundColor Red
    exit 1
  }
  Write-Host "Copied words.txt ($got bytes, $($wlines.Count) words) to $dest" -ForegroundColor Green
  Write-Host ""
  Write-Host "Now EJECT the drive in Windows, THEN press B on the PyGamer. Hangman and Wordle read the list each round." -ForegroundColor Yellow
  exit 0
}

if ($Quest) {
  $destDir = Join-Path $root "worlds"
  if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created $destDir"
  }
  $dest = Join-Path $destDir "quest.wld"
  Copy-Item -LiteralPath $QuestSource -Destination $dest -Force
  $got = (Get-Item -LiteralPath $dest).Length
  if ($got -ne $qb.Length) {
    Write-Host "ERROR: copy incomplete ($got of $($qb.Length) bytes). Do not eject yet; run this again." -ForegroundColor Red
    exit 1
  }
  Write-Host "Copied quest.wld ($got bytes) to $dest" -ForegroundColor Green
  Write-Host ""
  Write-Host "Now EJECT the drive in Windows, THEN press B on the PyGamer. Portal Quest reads the world from the drive when you open it." -ForegroundColor Yellow
  exit 0
}

if ($Portal) {
  $destDir = Join-Path $root "packs"
  if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created $destDir"
  }
  $dest = Join-Path $destDir "portal.lvl"
  Copy-Item -LiteralPath $PortalSource -Destination $dest -Force
  $got = (Get-Item -LiteralPath $dest).Length
  if ($got -ne $pb.Length) {
    Write-Host "ERROR: copy incomplete ($got of $($pb.Length) bytes). Do not eject yet; run this again." -ForegroundColor Red
    exit 1
  }
  Write-Host "Copied portal.lvl ($got bytes, $pn levels) to $dest" -ForegroundColor Green
  Write-Host ""
  Write-Host "Now EJECT the drive in Windows, THEN press B on the PyGamer. Portal levels 6-52 are then read from the drive." -ForegroundColor Yellow
  exit 0
}

if ($Packs) {
  $destDir = Join-Path $root "packs"
  if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
    Write-Host "Created $destDir"
  }
  $total = 0
  foreach ($f in $packFiles) {
    $dest = Join-Path $destDir $f.Name
    Copy-Item -LiteralPath $f.FullName -Destination $dest -Force
    $got = (Get-Item -LiteralPath $dest).Length
    if ($got -ne $f.Length) {
      Write-Host "ERROR: copy of $($f.Name) incomplete ($got of $($f.Length) bytes). Do not eject yet; run this again." -ForegroundColor Red
      exit 1
    }
    $total += $got
    Write-Host ("  {0,-8} {1,6} bytes" -f $f.Name, $got)
  }
  Write-Host "Copied $($packFiles.Count) level packs ($total bytes) to $destDir" -ForegroundColor Green
  Write-Host ""
  Write-Host "Now EJECT the drive in Windows (tray icon > Eject, or right-click the drive > Eject)," -ForegroundColor Yellow
  Write-Host "THEN press B on the PyGamer. Open a game's Levels menu: 'Browse Packs' appears when its pack is installed." -ForegroundColor Yellow
  exit 0
}

$destDir = Join-Path $root "assets"
if (-not (Test-Path -LiteralPath $destDir)) {
  New-Item -ItemType Directory -Path $destDir | Out-Null
  Write-Host "Created $destDir"
}
$dest = Join-Path $destDir "banners.bin"
Copy-Item -LiteralPath $Source -Destination $dest -Force
$got = (Get-Item -LiteralPath $dest).Length
if ($got -ne $srcSize) {
  Write-Host "ERROR: copy incomplete ($got of $srcSize bytes). Do not eject yet; run this again." -ForegroundColor Red
  exit 1
}
Write-Host "Copied banners.bin ($got bytes) to $dest" -ForegroundColor Green
Write-Host ""
Write-Host "Now EJECT the drive in Windows (tray icon > Eject, or right-click the drive > Eject)," -ForegroundColor Yellow
Write-Host "THEN press B on the PyGamer. It reboots and shows banners on the game title screens." -ForegroundColor Yellow
