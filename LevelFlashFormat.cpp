// LevelFlashFormat.cpp
//
// One-time fallback formatter for the PyGamer's onboard QSPI NOR flash,
// used only if Adafruit_Arcada's filesysBegin(ARCADA_FILESYS_QSPI) comes
// back with no filesystem mounted (i.e. the chip has never had a FAT
// filesystem written to it -- normally CircuitPython does this at the
// factory, so this path is a safety net, not the common case).
//
// This is deliberately a near-verbatim copy of the formatting approach in
// Adafruit's own bundled "SdFat_format" example (Adafruit_SPIFlash library)
// -- ff.c/ff.h/diskio.h/ffconf.h alongside this file are vendored straight
// from that example, unmodified. It uses a *separate* Adafruit_SPIFlash
// instance (own transport object, own disk_* glue) from the one
// Adafruit_Arcada_Filesystem.cpp owns internally, so there's no symbol or
// object collision -- it only ever touches the physical chip before
// Arcada's own filesysBegin() has successfully mounted anything, exactly
// like the real example sketch does.

#include <Adafruit_SPIFlash.h>
#include "ff.h"
#include "diskio.h"

#if defined(PIN_QSPI_SCK)
static Adafruit_FlashTransport_QSPI s_lvlFmtTransport(PIN_QSPI_SCK, PIN_QSPI_CS, PIN_QSPI_IO0,
                                                       PIN_QSPI_IO1, PIN_QSPI_IO2, PIN_QSPI_IO3);
#elif defined(EXTERNAL_FLASH_USE_QSPI)
static Adafruit_FlashTransport_QSPI s_lvlFmtTransport;
#elif defined(EXTERNAL_FLASH_USE_SPI)
static Adafruit_FlashTransport_SPI s_lvlFmtTransport(EXTERNAL_FLASH_USE_CS, EXTERNAL_FLASH_USE_SPI);
#else
#error "No onboard QSPI/SPI flash transport known for this board -- can't build the format fallback."
#endif

static Adafruit_SPIFlash s_lvlFmtFlash(&s_lvlFmtTransport);

extern "C" {
DSTATUS disk_status(BYTE pdrv) {
  (void)pdrv;
  return 0;
}

DSTATUS disk_initialize(BYTE pdrv) {
  (void)pdrv;
  return 0;
}

DRESULT disk_read(BYTE pdrv, BYTE *buff, DWORD sector, UINT count) {
  (void)pdrv;
  return s_lvlFmtFlash.readBlocks(sector, buff, count) ? RES_OK : RES_ERROR;
}

DRESULT disk_write(BYTE pdrv, const BYTE *buff, DWORD sector, UINT count) {
  (void)pdrv;
  return s_lvlFmtFlash.writeBlocks(sector, buff, count) ? RES_OK : RES_ERROR;
}

DRESULT disk_ioctl(BYTE pdrv, BYTE cmd, void *buff) {
  (void)pdrv;
  switch (cmd) {
    case CTRL_SYNC:
      s_lvlFmtFlash.syncBlocks();
      return RES_OK;
    case GET_SECTOR_COUNT:
      *((DWORD *)buff) = s_lvlFmtFlash.size() / 512;
      return RES_OK;
    case GET_SECTOR_SIZE:
      *((WORD *)buff) = 512;
      return RES_OK;
    case GET_BLOCK_SIZE:
      *((DWORD *)buff) = 8; // erase block size in units of sector size
      return RES_OK;
    default:
      return RES_PARERR;
  }
}
} // extern "C"

// Formats the onboard flash chip with a fresh FAT12/16 filesystem. Returns
// true on success (caller should then retry arcada.filesysBegin()).
bool lvlFormatQSPIFlash() {
  if (!s_lvlFmtFlash.begin()) {
    Serial.println("Levels: format failed -- flash chip did not respond.");
    return false;
  }

  uint8_t workbuf[4096];
  FATFS elmchamFatfs;

  FRESULT r = f_mkfs("", FM_FAT, 0, workbuf, sizeof(workbuf));
  if (r != FR_OK) {
    Serial.print("Levels: format failed, f_mkfs error ");
    Serial.println((int)r);
    return false;
  }

  r = f_mount(&elmchamFatfs, "0:", 1);
  if (r != FR_OK) {
    Serial.print("Levels: format failed, f_mount error ");
    Serial.println((int)r);
    return false;
  }

  f_setlabel("ARCADIA");
  f_unmount("0:");
  s_lvlFmtFlash.syncBlocks();

  Serial.println("Levels: flash formatted successfully.");
  return true;
}
