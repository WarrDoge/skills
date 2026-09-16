# Pi 4 vs Pi 5: the differences that change a procedure

| | Raspberry Pi 4 | Raspberry Pi 5 |
| --- | --- | --- |
| SoC | BCM2711 | BCM2712, with the RP1 southbridge carrying most I/O |
| UARTs | `UART0` PL011 + `UART1` mini UART, plus `UART2`-`UART5` PL011 disabled by default | `UART0`-`UART4` and `UART10` (the debug UART), all PL011; no mini UART |
| Primary UART | `UART1` (mini UART) on GPIO 14/15 | `UART10` on the dedicated 3-pin `UART` connector |
| `/dev/serial0` points at | `/dev/ttyS0` | `/dev/ttyAMA10` |
| `enable_uart` default | `0` (primary is the mini UART) | `1` (primary is a PL011) |
| Extra UART overlays | `uart2` … `uart5` | `uart0-pi5` … `uart4-pi5` |
| USB device/gadget mode | Available on the USB-C power connector, which carries the legacy USB 2.0 controller as a device by default (`otg_mode=0`) | Not available: `otg_mode` is documented as Pi 4 only |
| NVMe boot | CM4 only (via the IO board's PCIe) | Supported on the PCIe FFC connector, `0x6` in `BOOT_ORDER` |
| `BOOT_ORDER` `0x5` (BCM-USB-MSD) | Available | Not available |
| Bootloader UART baud | Fixed 115200 | Configurable with `UART_BAUD` |
| Power | 5 V/3 A USB-C typical | 5 V/5 A for full capability; at 5 V/3 A peripherals are limited to 600 mA |
| Power button | None; `WAKE_ON_GPIO` governs waking from halt | Dedicated button, soft-off state, `WAKE_ON_GPIO` not relevant |
| LEDs | Separate red `PWR` and green `ACT` | One bi-colour LED: red at power-on, green as firmware progresses |
| Arm JTAG | `enable_jtag_gpio=1`, GPIO 22-27 | `enable_jtag_gpio=1`, GPIO 22-27 (documented as working on all models) |

## Consequences worth remembering

**The Pi 4 console needs a decision, the Pi 5 console does not.** On Pi 4 the default primary UART is the mini UART, which is disabled outright under a variable core clock, which is why `enable_uart=1` is mandatory rather than optional — it pins the core clock as a side effect. If the console must be robust at higher baud rates, move it to a PL011 with `dtoverlay=disable-bt` and accept losing on-board Bluetooth. On Pi 5 the debug connector is a PL011 and is on by default.

**Two different "the UART is on GPIO 14/15" cases on Pi 5.** With nothing plugged into the debug connector and `enable_uart=1`, kernel logging goes to GPIO 14/15. With `enable_rp1_uart=1`, later firmware debug messages — including file accesses — go there too. Neither is the default, so a Pi 5 with a cable on pins 8/10 and no configuration will look silent.

**`/dev/serial0` is the portable name.** Anything written against `/dev/ttyS0` or `/dev/ttyAMA0` breaks when moved between these two boards. Use `/dev/serial0` in scripts and `console=serial0,115200` in `cmdline.txt`.

**Gadget-mode fallbacks do not port from Pi 4 to Pi 5.** A recovery procedure that relies on a USB serial or ethernet gadget over the power connector works on Pi 4 and has no equivalent on Pi 5; use the debug UART there instead.

**File locations moved with Bookworm.** `config.txt` and `cmdline.txt` live in `/boot/firmware/`, not `/boot/`. A procedure that edits `/boot/config.txt` on a current image edits nothing.
