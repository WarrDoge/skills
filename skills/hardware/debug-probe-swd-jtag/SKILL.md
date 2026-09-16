---
name: debug-probe-swd-jtag
description: Use a Raspberry Pi Debug Probe or equivalent CMSIS-DAP/FTDI adapter as either a USB-to-UART console cable or an SWD/JTAG debug port, and know which of the two a given target actually supports. Use when wiring a Debug Probe to a Pico, a Raspberry Pi or a Jetson, when OpenOCD will not detect a target, when deciding whether a board can be halted and single-stepped at all, or when attaching GDB to bare-metal firmware.
---

# Debug probe: SWD, JTAG and UART

A Debug Probe is two instruments that share a case: a USB-to-UART bridge and an Arm SWD port. They solve different problems, and conflating them is how an afternoon disappears. Decide which one the target supports before wiring anything, because for most Raspberry Pi and Jetson work the answer is "the UART half, and only the UART half".

## Scope

The probe as an instrument, and what each target class permits. Console wiring hygiene and capture discipline are in `board-console-access`; board boot chains are in `raspberry-pi-boot-triage` and `jetson-orin-triage`.

## Process

### 1. Decide which half of the probe applies

| Target | SWD / JTAG | UART console |
| --- | --- | --- |
| RP2040 / RP2350 (Pico family) | Yes — SWD, halt, single-step, flash over the probe | Yes |
| Raspberry Pi 4 / Pi 5 running Linux | Arm JTAG can be enabled on GPIO 22-27, but it is a specialist tool: it debugs a running SoC, not the boot failure you are probably chasing | Yes — this is the normal answer |
| Jetson Orin modules | Not a practical route on a developer kit | Yes, via the debug UART header |
| Other Cortex-M microcontrollers | Yes, if SWD pins are broken out | Yes, if the board has a UART |

For a Linux board that will not boot, the console is the instrument. Reach for SWD/JTAG when you are debugging bare-metal or early firmware you built yourself, or when you need to halt a core rather than read what it printed.

Completion criterion: the chosen half matches what the target supports, and the reason for choosing it is the failure being investigated, not the capability of the tool.

### 2. Wire it, ground first

The probe operates at 3.3 V nominal and has two three-pin JST-SH ports:

| Port | Purpose | Orange | Black | Yellow |
| --- | --- | --- | --- | --- |
| `D` | SWD | `SC` — SWCLK | `GND` | `SD` — SWDIO |
| `U` | UART | TX, output from the probe | `GND` | RX, input to the probe |

Connect GND before any signal line whenever the target has its own supply — a voltage difference between two separately powered systems damages the probe. If in doubt, power the target down, wire everything, then power up.

Three cables ship with the probe: JST-SH to JST-SH for boards with the standard three-pin debug connector (which includes the Raspberry Pi 5 `UART` connector), and JST-SH to 0.1-inch header in male and female flavours for everything else. On flying leads, remember that the probe's orange wire is its *output*: it goes to the target's RX.

The UART half enumerates on the host as a CDC device, typically `/dev/ttyACM0`. The SWD half is CMSIS-DAP and is claimed by OpenOCD.

Completion criterion: GND is connected first and the signal direction is confirmed at both ends.

### 3. Use it as a console

```bash
tio -b 115200 /dev/ttyACM0
minicom -b 115200 -o -D /dev/ttyACM0
```

Same rules as any serial console: set the line explicitly, log to a file, and start the capture before power-cycling the target. The probe's advantage over a bare USB-TTL adapter here is the standard connector and a known-good 3.3 V level — it is not a different kind of channel.

Completion criterion: target output appears during a cold power-up.

### 4. Use it as an SWD/JTAG adapter

```bash
# Program and exit
sudo openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg \
  -c "adapter speed 5000" -c "program firmware.elf verify reset exit"

# Server mode, for GDB
sudo openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 5000"
```

Then attach a debugger — `gdb-multiarch` on a non-Arm Linux host, `arm-none-eabi-gdb` elsewhere:

```
(gdb) target extended-remote localhost:3333
(gdb) load
(gdb) monitor reset init
(gdb) break main
(gdb) continue
```

Build the firmware with debug information (`-DCMAKE_BUILD_TYPE=Debug` for a CMake project); an optimised build will single-step through code that does not match the source.

Failure signatures, in the order they are worth checking:

- **No target detected** — wiring or power. SWDIO and SWCLK swapped, no common ground, or the target unpowered. The probe's DAP LEDs light when OpenOCD connects to a target and go out on disconnect, which is a free first check.
- **Detected, then unstable or dropping out** — `adapter speed` too high for the wiring. Halve it and retest; long or unshielded leads do not tolerate 5 MHz.
- **Target held in reset** — a reset line asserted by the wiring or by a previous OpenOCD invocation that did not release it.
- **Pins in the wrong function** — on an SoC where the debug pins are muxed, they must be configured as debug pins before the adapter can see anything.

Completion criterion: OpenOCD reports the expected target IDCODE and GDB can halt the core.

### 5. Arm JTAG on a Raspberry Pi, when it is genuinely the right tool

`enable_jtag_gpio=1` in `config.txt` selects Alt4 on GPIO 22-27 and wires up the SoC's Arm JTAG interface. It is documented as working on all Raspberry Pi models.

| GPIO | Signal |
| --- | --- |
| 22 | `ARM_TRST` |
| 23 | `ARM_RTCK` |
| 24 | `ARM_TDO` |
| 25 | `ARM_TCK` |
| 26 | `ARM_TDI` |
| 27 | `ARM_TMS` |

This is a six-wire JTAG interface, so it needs an adapter that speaks JTAG rather than SWD alone — the Debug Probe's `D` port is SWD-only, so an FT2232-based adapter is the usual choice here. Two caveats worth stating before anyone spends a day on it: the setting consumes six GPIOs that other hardware may want, and it debugs the application cores of a booted SoC, which is not where most Raspberry Pi boot failures live. If the question is "why did this Pi not boot", the answer is on the UART and the LED, not on JTAG.

Completion criterion: JTAG is in use because a core needs halting, and the same information was not already available from the console.

## Reference

Primary sources: [Raspberry Pi Debug Probe documentation](https://www.raspberrypi.com/documentation/microcontrollers/debug-probe.html), the [three-pin debug connector specification](https://rpltd.co/debug-spec), and [`enable_jtag_gpio`](https://www.raspberrypi.com/documentation/computers/config_txt.html#enable_jtag_gpio).
