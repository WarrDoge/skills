---
name: board-console-access
description: Open a debug channel to a headless single-board computer and confirm the channel is telling the truth. Covers serial console wiring and capture, SSH, netconsole, USB gadget, remote serial servers, and reading the boot media directly. Use when a board will not boot, boots to nothing, drops off the network, or produces no output on a console cable, and when a serial capture looks empty, garbled, or one-way. Do not use for ordinary SSH or networking questions about servers and workstations.
---

# Board console access

A headless board only tells you what some channel carries. Pick the channel by how far the board got, not by what is convenient to plug in: SSH cannot see a board that never reached userspace, and a serial capture that was never configured will report silence on a board that is talking.

## Scope

Getting a channel and trusting it. Board-specific boot chains, recovery modes and firmware settings live in the `raspberry-pi-boot-triage` and `jetson-orin-triage` skills. SWD/JTAG lives in `debug-probe-swd-jtag`.

## Process

### 1. Place the failure on the boot ladder

Each stage is visible only to channels that exist by then. Work out the highest stage with evidence before choosing a tool.

| Observation | Highest stage reached | Channels that can see it |
| --- | --- | --- |
| No LED, no current draw | Power | Meter, bench PSU. No digital channel exists yet |
| LED on, nothing anywhere | ROM / first-stage firmware | Serial only |
| Firmware output then stops | Bootloader | Serial only |
| Kernel messages then a hang or panic | Kernel | Serial, netconsole (if it loaded), the media after the fact |
| Login prompt on serial, nothing on the network | Userspace | Serial, USB gadget |
| Pings but no shell | Network | SSH |

A board that "does nothing" almost always reached further than it looks. Assume the channel is wrong before assuming the board is dead.

Completion criterion: the highest stage is named with the evidence for it, and the chosen channel can observe that stage.

### 2. Attach a serial console

Electrical rules, in order. Getting these wrong destroys ports:

- Every UART on these boards is 3.3 V. A 5 V adapter or an Arduino-style level damages the SoC pin. Use a 3.3 V USB-TTL adapter or a level shifter.
- Connect GND first, and leave it connected longest. Two self-powered systems with no common reference put their full ground offset across the signal pins.
- Cross the data lines: adapter RX to board TX, adapter TX to board RX. Straight-through wiring is the single most common "board sends nothing".
- Leave the adapter's VCC lead disconnected when the board has its own supply. Back-powering a board through a signal-level 3.3 V rail browns it out and produces boot loops that look like software faults.
- Use a galvanically isolated adapter when board and host sit on separate supplies, especially with a bench PSU or anything mains-powered attached to the board.

Find the port and open it:

```bash
ls -l /dev/serial/by-id/          # stable names, survives replug
sudo dmesg -w                      # watch the adapter enumerate
tio /dev/serial/by-id/usb-...      # reconnects across board resets, logs with -L
```

`tio` is the default because it survives the adapter disappearing on a power cycle. `picocom -b 115200 /dev/ttyUSB0` and `screen /dev/ttyUSB0 115200` work; `minicom` needs `-o` to skip its modem init string. Default line settings for the boards in this family: 115200 8N1, no flow control.

Completion criterion: characters arrive from the board during a power cycle, not just after.

### 3. Refuse to trust a capture you did not configure

A serial port keeps whatever `termios` state the last user left: baud, echo, and the `VMIN`/`VTIME` read timeout. That state is invisible and it fabricates results.

- `cat /dev/ttyUSB0` inherits it. With `VTIME` set, the read returns after the timeout and exits — on screen, indistinguishable from a board that sent nothing. A board can be written off as dead for days by this alone. Set the line explicitly, or use a tool that sets it for you.
- Wrong baud reads as continuous garbage. Wrong-by-a-factor baud reads as garbage that partially resolves into recognisable words — the most misleading case, because it looks like corruption rather than misconfiguration.
- Output arriving while input is ignored means TX is landing and RX is not: one broken wire, not a hung board.

```bash
stty -F /dev/ttyUSB0 raw -echo -echoe -echok 115200 min 1 time 0
stty -F /dev/ttyUSB0 -a            # confirm what you actually set
cat /dev/ttyUSB0 | tee boot.log    # only after the line is set
```

Capture rules that keep a result honest:

- Start the capture, then power-cycle. Everything diagnostic happens in the first few hundred milliseconds; attaching afterwards misses the entire firmware stage.
- Log to a file as you go (`tio -L`, `picocom -g file`, `screen -L`), never by scrollback. Scrollback truncates exactly the early output you need.
- Capture the same boot twice before concluding anything. Two runs that differ mean the instrument is unstable, and no conclusion drawn from one of them holds.
- A cold power cycle and a warm reboot are different events. Some failures only appear when rails actually drop; state that survives a warm reboot hides them.

Completion criterion: two captures of the same boot agree, and the line settings used are recorded alongside them.

### 4. Reach the board without a cable

In increasing order of how much of the stack must already work:

- **netconsole** — kernel log over UDP. Survives a userspace that never came up, needs a working NIC driver and link. Add `netconsole=6666@<board-ip>/<iface>,6666@<host-ip>/<host-mac>` to the kernel command line, or `modprobe netconsole ...` at runtime; receive with `socat -u UDP-RECV:6666 -` or `nc -u -l 6666`. Kernel messages only — nothing from firmware, nothing from userspace.
- **USB gadget** — the board enumerates on the host as a serial port or a network interface. Needs the kernel and the gadget driver loaded, so it sees nothing earlier than that. Availability is board-specific; check the per-board skill.
- **Remote serial** — `ser2net` or `conserver` on a machine near the board exports the console over TCP, so the capture keeps running across power cycles and across your own disconnections. Worth setting up as soon as a board needs more than one visit.
- **SSH** — last, because it needs the whole stack.

Completion criterion: the channel chosen exists at the stage the failure occurs.

### 5. Triage SSH one layer at a time

Name the layer that failed before touching the next one. Each command confirms exactly one layer:

```bash
ping -c1 <ip>                                  # L3 reachability
arp -n <ip>                                    # link and address, when ping is filtered
avahi-resolve -n <host>.local                  # name resolution, if mDNS is in use
nc -vz <ip> 22                                 # sshd listening and reachable
ssh -vvv <user>@<ip>                           # host key, auth method, then shell
```

Common layer-level answers: no ARP entry means link or DHCP; connection refused means the host is up and `sshd` is not; a host-key warning after a reflash is expected and is fixed with `ssh-keygen -R <ip>`, never with `StrictHostKeyChecking=no` left in a config; auth failures that survive a correct key are usually file modes or an account with no shell. A board that answers ping but refuses port 22 has reached userspace — switch to the serial console to read why `sshd` did not start, rather than guessing from the host side.

Completion criterion: the failing layer is named, and the fix is applied at that layer.

### 6. Read the media when nothing answers

The storage is a channel too, and it holds the evidence from the boot that failed.

```bash
lsblk -f                                       # identify the card/SSD, verify before mounting
sudo mount /dev/sdX2 /mnt && sudo mount /dev/sdX1 /mnt/boot
sudo journalctl -D /mnt/var/log/journal -b -1  # the previous boot, if the journal is persistent
```

From here you can read the failed boot's log, correct the kernel command line or firmware config, re-enable a unit that failed to start, or fix an `/etc/fstab` entry that dropped the board into emergency mode. Two traps: a journal is only there if it was made persistent, and a board with no RTC writes its logs at whatever time it believed it was, so timestamps are not an ordering you can trust.

Completion criterion: the failed boot's own output has been read, not inferred.

## Reference

[`references/serial-tools.md`](references/serial-tools.md) — adapter and chipset notes, a `stty` cheat sheet, tool invocations with logging, a `ser2net` configuration, the netconsole recipe in full, and what to do when a line looks dead under a logic analyser.
