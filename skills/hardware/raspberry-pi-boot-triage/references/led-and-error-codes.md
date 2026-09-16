# LED flash codes and the HDMI diagnostics screen

## Activity LED flash codes

Long flashes always come before short ones, and there are sometimes no long flashes at all. The pattern repeats after a two-second pause.

| Long | Short | Meaning |
| --- | --- | --- |
| 0 | 3 | Generic failure to boot |
| 0 | 4 | `start*.elf` not found |
| 0 | 7 | Kernel image not found |
| 0 | 8 | SDRAM failure |
| 0 | 9 | Insufficient SDRAM |
| 0 | 10 | In HALT state |
| 1 | 2 | SD card overcurrent detected |
| 2 | 1 | Partition not FAT |
| 2 | 2 | Failed to read from partition |
| 2 | 3 | Extended partition not FAT |
| 2 | 4 | File signature/hash mismatch (Pi 4 and 5) |
| 3 | 1 | SPI EEPROM error (Pi 4 and 5) |
| 3 | 2 | SPI EEPROM is write protected (Pi 4 and 5) |
| 3 | 3 | I2C error (Pi 4 and 5) |
| 3 | 4 | Secure-boot configuration is not valid |
| 4 | 3 | RP1 not found |
| 4 | 4 | Unsupported board type |
| 4 | 5 | Fatal firmware error |
| 4 | 6 | Power failure type A |
| 4 | 7 | Power failure type B |

Source: [LED warning flash codes](https://www.raspberrypi.com/documentation/computers/configuration.html#led-warning-flash-codes). Note the LED hardware differs by model — Pi 4 has a separate red `PWR` and green `ACT` LED, and a red LED that is off or flickering is itself an undervoltage indication; Pi 5 has one bi-colour LED that goes red at power-on and green as firmware startup progresses, so a Pi 5 that stays red never got through firmware startup.

Reading them in groups: `0 x` codes are the firmware failing to find or load something on the boot media; `2 x` codes are the partition or filesystem being wrong; `3 x` codes are the EEPROM or the I2C/power path; `4 x` codes are the board or its power rails.

## HDMI diagnostics screen

Power down, remove the boot media, power up with a monitor attached. The same screen appears on its own whenever the bootloader cannot boot from any configured source.

| Line | What it tells you |
| --- | --- |
| `bootloader` | Bootloader git version, `RO` if the EEPROM is write-protected, and the build date |
| `update-ts` | When the EEPROM configuration was last updated |
| `secure-boot` | Processor revision and signed-boot flags, when secure boot is enabled; otherwise blank |
| `board` | Board revision, serial number, Ethernet MAC |
| `boot` | Current boot mode and number, the `BOOT_ORDER` in force, the retry count within this mode, and how many times it has cycled the whole list |
| `SD` | Whether a card is detected |
| `part` | Primary partitions found, as type:LBA |
| `fw` | The firmware filenames found, e.g. `start4x.elf` |
| `net` / `tftp` | Network boot: link state, IP, subnet, gateway, TFTP server |
| `display` | HDMI hotplug (`HPD=1`) and EDID read status per output |

Source: [Boot diagnostics](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#boot-diagnostics).

What to conclude:

- `SD` says not detected with a card inserted — card, socket, or card-detect switch, not software.
- `part` empty or unexpected — the partition table is wrong or the card is failing; re-image and re-check rather than editing files on it.
- `fw` blank with partitions present — the boot partition is there but the firmware files are missing, which matches the `0 4` LED code.
- `boot` cycling with a rising `restart` count — the bootloader is trying the whole list repeatedly; nothing in `BOOT_ORDER` is bootable.
- `display` showing `HPD=0` on a connected monitor — a cable or a micro-HDMI port problem masquerading as a boot failure, and the board may be booting fine.

`DISABLE_HDMI` in the bootloader configuration suppresses this screen; if a board shows nothing at all on a monitor it has previously used, check that before assuming worse.
