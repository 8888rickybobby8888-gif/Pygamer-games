ARCADIA ERROR CODES
===================
Every failure shows a code like E304. Look at Settings > Error log on the console for the last 8
(newest first; "old" = from an earlier session). The same list is stored on the drive in
/arcadia/errlog.txt, one line per error: "<code> <uptime seconds> <unseen flag>", oldest first.
After a reboot a toast "Last run: E###, see log" is shown once if the last session logged an error.
The same code repeated within 60 s is logged once. A, then A again, in the Error log clears it.

Area   Code  Meaning                         What to do
-----  ----  ------------------------------  ----------------------------------------
E1xx   Storage / drive
       E101  No flash chip responds          Saves are not kept this run
       E102  Flash disk blank, no filesystem Set up storage at the boot prompt
       E103  Flash disk cannot be mounted    Back up from the PC, then format
       E104  Format failed                   Reboot; try Settings > USB drive
       E105  No flash filesystem (RAM only)  Reboot and set up storage
       E106  USB drive mode failed to start  Reboot and retry
       E107  Backup failed (factory reset)   Nothing was erased; free disk space
       E108  Restore failed                  Check /arcadia/bak files
       E109  No backup found                 Backups are made by USB drive / reset
E2xx   Save data
       E201  Save file (save.bin) write fail Disk full? Reboot
       E202  Settings save write failed      Disk full? Reboot
       E203  Extra save (save_ext) write     Disk full? Reboot
       E204  Level save failed               Delete a level; disk may be full
       E205  Quest progress save failed      Free disk space
       E206  Save file invalid, started new  Settings > Restore backup
E3xx   Cartridges (/carts)
       E301  No storage for cart             Check the disk in Settings
       E302  Cart file missing               Reinstall the cart
       E303  Cart file bad / wrong version   Rebuild the cart on the PC
       E304  Cart corrupt (checksum)         Reinstall the cart
       E305  Not enough memory for cart      Use a smaller cart
       E306  carts.bin could not be saved    Free disk space
       E310  Cart stopped (runtime fault)    Detail line says why; the cart needs a fix
       E311  Cart not loaded                 Open it again
E4xx   CHIP-8 (/roms)
       E401  ROM file missing                Copy the ROM to /roms
       E402  ROM empty or over 3584 bytes    Use a valid .ch8
       E403  Not enough memory               Reboot and retry
       E404  ROM not loaded                  Open it again
E5xx   Portal Quest (/worlds/quest.wld)
       E501  Drive not available             Set up storage first
       E502  quest.wld not found             Install via Settings > USB drive
       E503  quest.wld damaged               Copy quest.wld again
       E504  Region read error               Try again (log only)
       E505  World became unreadable         Reinstall quest.wld
E6xx   Packs / levels / words
       E601  Portal level pack record bad    Rebuild / reinstall portal pack
E7xx   System
       E701  Watchdog reset (last run froze) Report if it repeats
       E702  Brownout reset                  Check battery / USB power
       E703  Portrait buffer not allocated   Portrait games unavailable
       E799  Unknown code                    -

Notes: E502 is shown on screen but not logged (not having Quest installed is normal).
errlog.txt is safe to delete; it is recreated on the next error.
