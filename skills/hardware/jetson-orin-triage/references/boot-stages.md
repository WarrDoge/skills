# Jetson Orin boot stages

## Stage, symptom, first probe

| Stage | What you see on the console | What it means | First probe |
| --- | --- | --- | --- |
| Power / boot ROM | Nothing at all, no matter how long you wait | Either the board is not starting, or your console is not connected to it | Loopback-test the adapter; meter the idle TX line; confirm J14 pins 3/4/11 and a 3.3 V adapter |
| Boot ROM, recovery | Nothing on console, but the host sees `0955:xxxx` on `lsusb` | The ROM is alive and in recovery mode — the silicon is fine | Flash from the host; the board is recoverable |
| Early bootloader | Vendor banners appear, then stop | A pre-UEFI stage is failing to load or verify the next one | Reflash the bootloader partitions; check the A/B slot state first |
| UEFI | UEFI banner, then a shell prompt or a boot-device menu | UEFI ran and found nothing to boot, or the slot state sent it here | `nvbootctrl dump-slots-info`; inspect the boot entries from the UEFI menu |
| extlinux / kernel load | UEFI hands over, then nothing, or "cannot load" style errors | The kernel, initrd or device tree named in `extlinux.conf` is missing or wrong | Mount the rootfs and read `/boot/extlinux/extlinux.conf` against what is actually in `/boot` |
| Kernel | Kernel messages, then hang or panic | Driver, device tree or rootfs problem | Read the panic; add `ignore_loglevel`; check the `root=` device exists |
| Init / userspace | Kernel finishes, no login prompt | Userspace failed, or the console getty is not running | `systemctl status serial-getty@ttyTCU0`; `systemctl --failed` once you have any shell |
| Running | Login prompt, no network | Networking or userspace configuration | USB device mode at `192.168.55.1`, then fix from a shell |

## UEFI over serial

The UEFI stage prints a prompt for a keypress early in boot; pressing it opens the boot manager, where you can inspect and reorder boot entries, enter the UEFI shell, and see which devices UEFI actually enumerated. Two practical notes:

- The window is short and the keypress must land on the *serial* console, so the capture has to be attached and interactive before power-up, not after.
- A board that enumerates no boot device in that menu has a storage or partition problem; a board that lists the device but still will not boot has a bootloader or `extlinux` problem. That distinction saves a reflash.

## Files worth reading on a mounted rootfs

| Path | Why |
| --- | --- |
| `/boot/extlinux/extlinux.conf` | The kernel, initrd, device tree and command line actually used, including `console=` |
| `/boot/` | Whether the files `extlinux.conf` names are really there |
| `/etc/fstab` | A stale entry here drops an otherwise healthy board into emergency mode |
| `/etc/nvpmodel.conf` | Which power model the board comes up in |
| `/var/log/journal/` | The failed boot's journal, if persistent logging was enabled |
| `/etc/nv_tegra_release` | Which L4T release is actually installed, which decides which documentation applies |

## Things that are easy to get backwards

**A flash resets state you may still need.** Slot status, retry counters and anything stored in the bootloader partitions go back to defaults. Read `nvbootctrl dump-slots-info` and capture a boot log *before* reflashing, or the evidence is gone.

**Recovery mode is not a failure.** A board that is in recovery and visible on `lsusb` is a healthy board waiting to be written to. The failure would be a board that will not enter recovery at all.

**The console is shared.** The combined UART carries output from more than one processor, so interleaved or unfamiliar-looking lines are normal, not corruption.

**The module and the carrier are separate variables.** A module moved to a different carrier changes pinouts, recovery procedure and board config name. Confirm which carrier you have before following any procedure that names a pin.
