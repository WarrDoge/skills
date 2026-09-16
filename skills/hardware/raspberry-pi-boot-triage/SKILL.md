---
name: raspberry-pi-boot-triage
description: Diagnose a Raspberry Pi 4 or 5 that will not boot, boots to a black screen, or dies partway — using the activity-LED flash codes, the HDMI diagnostics screen, firmware and kernel serial output, the bootloader EEPROM, and the boot media. Use for a Pi stuck at a blinking LED, no display, an unbootable SD card or SSD, a wrong boot order, a suspected EEPROM or config.txt problem, or undervoltage and throttling.
---

# Raspberry Pi boot triage

A Raspberry Pi that fails to boot is reporting the reason, usually on three channels you have not opened yet: the activity LED, an HDMI diagnostics screen, and the firmware UART. Read those before changing anything, because each one names a different link in the chain and the fixes are not interchangeable.

## Scope

Raspberry Pi 4 and Pi 5 (and the 400/500 and Compute Module variants where noted), from power-on to a login prompt. Cabling, capture and SSH triage are in the `board-console-access` skill; JTAG is in `debug-probe-swd-jtag`.

## Process

### 1. Read the free channels before touching a cable

The bootloader talks before any console exists.

- **LED flash codes.** Long flashes come first, then short ones, then a two-second pause and a repeat. Look the pattern up in [`references/led-and-error-codes.md`](references/led-and-error-codes.md) — it distinguishes "no `start*.elf`" from "SDRAM failure" from "EEPROM is write protected", which are three completely different jobs.
- **HDMI diagnostics.** On Pi 4 and later, power down, remove the boot media, and power up with a monitor attached: the bootloader draws a diagnostics screen with its own version, the board revision and serial, the `BOOT_ORDER` in force, the boot mode and retry count, SD detect status, the partition table it found, and HDMI hotplug/EDID status. The same screen appears whenever the bootloader cannot boot from anything. It is the fastest way to tell "the firmware never saw the card" from "the firmware read the card and rejected it".

Completion criterion: the LED pattern and, where a display is available, the diagnostics screen have been read and recorded, before any configuration is edited.

### 2. Open the firmware-stage serial console

The model decides where the primary UART is. Getting this wrong produces a silent cable on a talking board.

| | Raspberry Pi 4 | Raspberry Pi 5 |
| --- | --- | --- |
| Primary UART | `UART1`, the mini UART | `UART10`, a PL011 |
| Where it comes out | GPIO 14 (header pin 8, TX) and GPIO 15 (header pin 10, RX); GND on pin 6 | The dedicated 3-pin JST-SH connector labelled `UART` |
| Device node | `/dev/ttyS0` (`/dev/serial0`) | `/dev/ttyAMA10` (`/dev/serial0`) |
| `enable_uart` default | `0` — you must set `enable_uart=1` | `1` |

On Pi 5 the debug connector takes the Debug Probe's JST-SH cable directly; the connector is specified in [RP-008189-DS](https://pip.raspberrypi.com/documents/RP-008189-DS). If nothing is plugged into that connector and `enable_uart=1` is set, Pi 5 routes kernel logging to GPIO 14/15 instead, and `enable_rp1_uart=1` additionally routes later firmware messages there.

To make the bootloader itself talk, set `BOOT_UART=1` in the EEPROM configuration (step 4). Receive at 115200 8N1; Pi 5 and later can change this with `UART_BAUD`.

The mini UART on Pi 4 has a second trap: its clock derives from the VPU core clock, so a variable core frequency disables it. `enable_uart=1` fixes the core clock at 250 MHz as a side effect, which is why it is required rather than merely helpful. To get a proper PL011 on GPIO 14/15 instead, add `dtoverlay=disable-bt` (and `sudo systemctl disable hciuart`), which makes `UART0` primary and gives up on-board Bluetooth; `dtoverlay=miniuart-bt` keeps Bluetooth by moving it to the mini UART, and needs a fixed core clock of its own (`core_freq=250`).

Completion criterion: firmware-stage output appears on the console during a cold power cycle, or the board is confirmed to reach no stage that produces it.

### 3. Get the kernel to talk on the same line

Firmware output and kernel output are separately configured. A console that goes quiet the moment the kernel starts is a `cmdline.txt` problem, not a hardware one.

In `/boot/firmware/cmdline.txt` (one single line, no line breaks):

```
console=serial0,115200 console=tty1 root=PARTUUID=... rootfstype=ext4 fsck.repair=yes rootwait
```

For a hang before the console driver initialises, add an `earlycon` — the address is model-specific, and the wrong one prevents boot:

| Model | Parameter |
| --- | --- |
| Pi 5, via the debug header | `earlycon=pl011,0x107d001000,115200n8` |
| Pi 4, 400, CM4, CM4S | `earlycon=uart8250,mmio32,0xfe215040` (mini UART) or `earlycon=pl011,mmio32,0xfe201000` |

Also useful on the same line while triaging: `ignore_loglevel` to raise everything to the console, and dropping `quiet` if the distribution added it.

Completion criterion: kernel messages reach the console, or the hang is confirmed to occur before the kernel is entered.

### 4. Interrogate and repair the bootloader EEPROM

Pi 4 and Pi 5 boot from a bootloader in SPI EEPROM, not from the card. It holds the boot order and its own debug switches.

```bash
vcgencmd bootloader_version          # what is actually running
rpi-eeprom-config                    # current configuration
sudo rpi-eeprom-config --edit        # edit; schedules an update on reboot
sudo rpi-eeprom-update               # what is available
sudo rpi-eeprom-update -a            # apply the latest, then reboot
```

`BOOT_ORDER` is a 32-bit value read right to left, one nibble per boot mode: `0x1` SD, `0x2` network, `0x3` RPIBOOT, `0x4` USB mass storage, `0x6` NVMe, `0x7` HTTP, `0xe` stop and show the error pattern, `0xf` restart the list. `0xf41` — the default when unset — means SD, then USB, then repeat. A Pi that ignores a perfectly good NVMe drive usually has a `BOOT_ORDER` without `6` in it, and a Pi that stops dead with an LED code may have a trailing `0xe`.

When the EEPROM itself is the problem — the board will not boot from anything, or the LED reports an SPI EEPROM error — the ROM on BCM2711 and BCM2712 looks for `recovery.bin` in the root of the boot partition on the **SD card** at power-on and runs it instead of the EEPROM contents. Write the bootloader recovery image to a FAT-formatted card, boot it, and the EEPROM is reflashed to a known-good image with factory defaults. On success the HDMI output turns green and the activity LED flashes rapidly; on failure the output turns red and the LED reports an error code. This path is SD-only: the ROM will not load `recovery.bin` from USB or TFTP.

Completion criterion: the running bootloader version and `BOOT_ORDER` are known, and match the media the board is supposed to boot from.

### 5. Reach the media without pulling it

On Compute Modules and on boards configured for it, `RPIBOOT` (`0x3` in the boot order, or the `nRPIBOOT` jumper on a CM IO board) makes the Pi enumerate on a host running [`usbboot`](https://github.com/raspberrypi/usbboot), which can expose the eMMC as a block device on the host. On a flagship board without that path, pull the card and work on it directly.

Either way, the repairs are the same and are usually one line: an over-ambitious `config.txt`, a `cmdline.txt` that got a second line, a `root=` pointing at a PARTUUID that no longer exists, or an `/etc/fstab` entry for a device that is not there — which drops the board into emergency mode with a perfectly healthy kernel. Mount the boot partition, fix the line, and keep a copy of what you changed.

Completion criterion: the failed boot's configuration has been read directly, not reconstructed from memory.

### 6. Rule out power and thermal before believing anything else

Undervoltage produces symptoms that mimic every software fault: random hangs, filesystem corruption, USB devices that vanish, boots that succeed one time in three.

```bash
vcgencmd get_throttled     # 0x0 is clean
vcgencmd measure_temp
dmesg | grep -i -E 'voltage|throttl'
```

Bits 0-3 are live conditions (undervoltage, ARM frequency capped, currently throttled, soft temperature limit); bits 16-19 are the same conditions latched since boot. A non-zero value in the high bits with clean low bits means it happened and recovered — still a fault, still worth fixing. Pi 5 expects 5 V at 5 A; at 5 V/3 A it runs but limits peripherals to 600 mA, which is enough to make a USB SSD drop out under load. Suspect the cable and the supply before the board, and re-test with a known-good supply rather than reasoning about the label on the old one.

Completion criterion: `get_throttled` is `0x0` across a full test cycle, or the power fault is fixed before other causes are investigated.

## Reference

- [`references/pi4-vs-pi5.md`](references/pi4-vs-pi5.md) — the differences that change a procedure: UART routing, USB gadget availability, boot media, power, JTAG.
- [`references/led-and-error-codes.md`](references/led-and-error-codes.md) — the LED flash-code table and how to read the HDMI diagnostics screen.
