---
name: jetson-orin-triage
description: Diagnose a Jetson Orin Nano (and Orin NX/AGX) that will not boot, stops in UEFI, boots the wrong slot, or is unreachable — using the J14 debug UART, forced recovery and host flashing, nvbootctrl A/B slots, USB device mode, and the L4T boot log. Use for a Jetson with no display or console output, a board that drops to a UEFI shell or prompt, a failed or repeated flash, a device that will not enter recovery mode, or Jetson-specific power, clock and thermal faults.
---

# Jetson Orin triage

A Jetson fails differently from a general-purpose SBC: the boot chain has several vendor stages before anything Linux-shaped exists, output from all of them is multiplexed onto one combined UART, and the board carries A/B redundancy that can silently move you to the other slot. Identify the stage first — the fix for a UEFI-stage failure has nothing in common with the fix for a kernel-stage one.

## Scope

Jetson Orin Nano Developer Kit primarily, with Orin NX and AGX Orin differences noted. Cabling, capture discipline and SSH triage are in the `board-console-access` skill.

## Process

### 1. Attach the debug console before anything else

On the Orin Nano Developer Kit the console comes out on the 12-pin button header, `J14`, on the carrier board edge under the module. Use a 3.3 V USB-TTL adapter:

| J14 pin | Signal | Adapter |
| --- | --- | --- |
| 3 | Jetson UART TXD | adapter RX |
| 4 | Jetson UART RXD | adapter TX |
| 11 | GND | adapter GND |

On AGX Orin the debug console is exposed over the developer kit's USB port as a `/dev/ttyACM<n>` device on the host instead — the same console, different transport; confirm which port on the user guide for your carrier. Either way it is the *combined* UART: on Orin, output from the CCPLEX cluster and from the other on-die processors is multiplexed through the Sensor Processing Engine onto one channel, which is why the target-side device is `/dev/ttyTCU0` and not a `ttyS*` or `ttyTHS*`. Its rate is fixed at 115200 8N1 — a baud mismatch here is a wiring or adapter fault, never a configuration one.

Target-side, the login shell on that console is `serial-getty@ttyTCU0`; a board that prints a full boot log and then offers no prompt has that unit masked or failed, which is a userspace problem, not a console problem.

Completion criterion: vendor boot messages appear on the console during a cold power-up, or the board is confirmed to produce none.

### 2. Name the stage that failed

Each stage looks different on the console and is fixed differently. [`references/boot-stages.md`](references/boot-stages.md) has the full symptom table; the short version:

- **Nothing at all** — the board is not reaching the boot ROM, or the console wiring is wrong. Prove the instrument before believing the board (loopback test, `references/serial-tools.md` in `board-console-access`).
- **Vendor firmware banners, then silence** — an early bootloader stage is failing. This is flash territory, not configuration.
- **UEFI banner, then a shell or a boot menu instead of Linux** — the boot entries or the A/B slot state are the problem. Step 4.
- **Kernel messages, then a hang or a panic** — kernel, device tree, or rootfs. `/boot/extlinux/extlinux.conf` holds the kernel, initrd, device tree and command line the board actually used.
- **Login prompt, no network** — userspace. Step 5.

Completion criterion: the failing stage is named from console output, not inferred from the symptom.

### 3. Force recovery and flash from a host

Recovery mode is how you replace anything below the rootfs. On the Orin Nano Developer Kit: disconnect power, jumper the `REC` and `GND` pins on the 12-pin button header, reconnect power. On AGX Orin: hold the Force Recovery button, press and release Power, release Force Recovery.

Confirm from the host — this is the step people skip, and it is the difference between a failed flash and a board that was never listening:

```bash
lsusb | grep -i nvidia     # ID 0955:<nnnn> Nvidia Corp.
```

The four digits identify the module (`7523` Orin Nano 8 GB, `7323` Orin NX 16 GB), so they also catch the case where the host is talking to a different board than you think.

Flashing an Orin Nano devkit to NVMe, from an unpacked Linux_for_Tegra:

```bash
sudo ./tools/kernel_flash/l4t_initrd_flash.sh --external-device nvme0n1p1 \
  -c tools/kernel_flash/flash_l4t_t234_nvme.xml \
  -p "-c bootloader/generic/cfg/flash_t234_qspi.xml" \
  --showlogs --network usb0 jetson-orin-nano-devkit internal
```

Two things to hold on to: the board config name (`jetson-orin-nano-devkit`) must match the hardware, and `--showlogs` is what turns a silent half-hour into a readable failure. Keep the debug console open during the flash; the board reports its own side of the transaction there.

Completion criterion: the host sees the recovery USB ID before the flash starts, and the flash's own log — not just its exit status — has been read.

### 4. Check the A/B slot state before reflashing again

Orin carries two complete bootloader partition sets. The bootloader marks a slot unbootable when it fails and switches to the other one, which means a board can quietly be running the *other* half of what you flashed, and a board that boots "sometimes" may be alternating.

```bash
nvbootctrl dump-slots-info        # status of both slots, current and active
nvbootctrl get-current-slot       # 0 = A, 1 = B
nvbootctrl set-active-boot-slot 0 # force the next boot
nvbootctrl verify                 # verify the bootloader and rootfs boot
```

The failure mode worth knowing: a board whose retry budget drains without anything confirming a successful boot stops trying and lands in UEFI instead of Linux. It looks like a corrupted image and is not one. Check `dump-slots-info` before concluding anything from a boot that reached UEFI and stopped. Note also that a flash resets this state, so a reflash destroys the evidence — read the slot state first.

Completion criterion: which slot booted, and the status of both, is known before any reflash.

### 5. Use USB device mode when the network is the problem

A Jetson that reached userspace exposes itself over the USB device port: an RNDIS virtual ethernet with the Jetson at `192.168.55.1`, bridged on the target as `l4tbr0`, plus a serial gadget. That gives SSH and a shell with no network configuration at all, which is the right tool for a misconfigured interface, a wrong static address, or a firewall change that locked you out.

It needs the kernel and the gadget drivers loaded, so it sees nothing earlier than that — it is a userspace channel, not a boot-debug one.

Completion criterion: either a shell over `192.168.55.1`, or confirmation that the board never reached the stage where the gadget comes up.

### 6. Account for the missing clock

The developer kit has no battery-backed RTC. A board with no network time comes up believing it is whatever its default epoch is, which breaks anything that checks validity dates, makes package tooling fail in confusing ways, and makes log timestamps meaningless.

Worse for debugging: when the clock jumps mid-boot, the journal is split across the jump, so boot-time evidence may not appear where `journalctl -b` looks for it. Set the clock before drawing conclusions from timestamps, and keep the serial capture, which is ordered by arrival and does not care what the board believes the date is.

Completion criterion: the board's clock is known-correct, or timestamp-based reasoning has been abandoned in favour of the serial capture.

### 7. Rule out power, clocks and thermals

```bash
sudo tegrastats                # live CPU/GPU/EMC load, temperatures, power rails
sudo nvpmodel -q               # active power model
sudo nvpmodel -m 0             # maximum-performance model
sudo jetson_clocks --show      # whether clocks are pinned
```

Instability that tracks load, boots that succeed only when cold, and USB or NVMe devices that vanish under GPU load are supply problems. The devkit is sensitive to both the barrel/USB-C supply's real current capability and to what the carrier is powering; test with a known-good supply rather than reasoning about the rating printed on the old one. A low-power model plus a heavy workload also produces watchdog resets that read like software faults.

Completion criterion: the fault reproduces with a known-good supply at a known power model, or it does not and the supply was the cause.

## Reference

[`references/boot-stages.md`](references/boot-stages.md) — stage-by-stage symptom and first-probe table, UEFI-over-serial navigation, and the L4T files worth reading on a mounted rootfs.

Primary sources: [Jetson Linux Developer Guide](https://docs.nvidia.com/jetson/archives/), [Orin Nano Developer Kit User Guide](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/), [Tegra Combined UART](https://docs.nvidia.com/jetson/archives/r39.2/DeveloperGuide/AT/JetsonLinuxDevelopmentTools/TegraCombinedUART.html). Pin numbers and board config names change between carrier revisions and L4T releases — confirm against the documentation for the release you are running.
