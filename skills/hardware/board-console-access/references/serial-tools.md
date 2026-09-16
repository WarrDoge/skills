# Serial tooling reference

## Adapters

| Chipset | Notes |
| --- | --- |
| CP210x | Stable, no driver fuss on modern Linux. Common on genuine and clone boards alike |
| FT232R / FT2232 | Reliable; FT2232 gives two channels, one of which can drive JTAG/SWD. Counterfeits exist and can be bricked by vendor drivers on other OSes |
| CH340/CH341 | Cheapest, works, but the weakest at high baud and on long cables |
| PL2303 | Older revisions are unsupported by current vendor drivers on some hosts; avoid for new work |

Requirements that matter more than the chipset: 3.3 V signalling, a separate GND lead, and a VCC lead you can leave unconnected. Galvanic isolation (ADUM-based adapters) is worth the cost on any bench where the board has its own supply.

`/dev/ttyUSB*` is an ordering, not an identity — it changes when two adapters enumerate in a different order. Use `/dev/serial/by-id/` in anything you write down, and pin a name with a udev rule if the board is a fixture:

```
# /etc/udev/rules.d/60-console.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{serial}=="0001", SYMLINK+="console-bench"
```

## stty

```bash
stty -F /dev/ttyUSB0 -a                                    # dump current state
stty -F /dev/ttyUSB0 raw -echo -echoe -echok 115200 min 1 time 0
stty -F /dev/ttyUSB0 115200 cs8 -cstopb -parenb -crtscts   # 8N1, no hardware flow control
stty -F /dev/ttyUSB0 sane                                  # back to a known state
```

`min 1 time 0` makes a read block until at least one byte arrives. The opposite — a non-zero `time` — is what makes `cat` exit on its own and report a silent board that is not silent.

Opening the port can itself reset the board: adapters that assert DTR/RTS on open pulse a reset line if one is wired. `stty -F /dev/ttyUSB0 -hupcl` stops the port dropping DTR on close.

## Terminal programs

```bash
tio /dev/serial/by-id/usb-...                  # auto-reconnect; ctrl-t q to quit, ctrl-t ? for help
tio -b 115200 -L -l /tmp/boot.log /dev/ttyUSB0 # log to file while showing output
picocom -b 115200 -g /tmp/boot.log /dev/ttyUSB0  # ctrl-a ctrl-x to quit
screen -L -Logfile /tmp/boot.log /dev/ttyUSB0 115200  # ctrl-a k to kill
minicom -b 115200 -o -D /dev/ttyUSB0           # -o skips the modem init string; ctrl-a x to quit
```

Only one process may hold the port. "Device or resource busy" means something else has it — `fuser -v /dev/ttyUSB0` names it, and it is usually a forgotten `screen` session or a `getty`.

Capture without a terminal program, for scripting a boot test:

```bash
stty -F /dev/ttyUSB0 raw -echo 115200 min 1 time 0
timeout 120 cat /dev/ttyUSB0 | tee boot.log
```

`timeout` bounds the run from the outside, which is the honest way to stop a capture. A read timeout set inside the port bounds it invisibly.

## ser2net

Exports a console over TCP so captures survive your disconnection and several people can watch one board.

```yaml
# /etc/ser2net.yaml
connection: &bench
  accepter: tcp,3333
  connector: serialdev,/dev/serial/by-id/usb-...,115200n81,local
  options:
    kickolduser: true
```

Connect with `telnet localhost 3333`, or `socat -,raw,echo=0 TCP:host:3333` for a clean binary path. `conserver` is the heavier alternative: it keeps a permanent logged connection per board and lets clients attach read-only, which is what you want when more than one person is debugging the same unit.

## netconsole

```bash
# On the board, at runtime
sudo modprobe netconsole netconsole=6666@192.168.1.50/eth0,6666@192.168.1.10/aa:bb:cc:dd:ee:ff

# On the receiving host
socat -u UDP-RECV:6666 - | tee netconsole.log
```

Both MAC addresses matter: the target MAC is the next hop, so it is the router's MAC when the host is on another subnet. To have it running before userspace, put the same string on the kernel command line as `netconsole=...`. It carries kernel messages only — a userspace hang produces a perfectly quiet netconsole on a perfectly healthy board.

Not every vendor kernel ships `CONFIG_NETCONSOLE`. Check `zgrep NETCONSOLE /proc/config.gz` or `grep NETCONSOLE /boot/config-$(uname -r)` before relying on it.

## When the line looks dead

Before concluding a board is not transmitting, prove the instrument:

1. Loop the adapter back — short its RX to its TX, open a terminal, type. No echo means the adapter or the port is the fault, not the board.
2. Meter the idle line. A UART TX idles high; on a 3.3 V board that is ~3.3 V DC against board GND. 0 V idle means the pin is not configured as a UART, or you are on the wrong pin.
3. Put a logic analyser or scope on the board's TX pin and power-cycle. Traffic on the wire with nothing on screen is a host-side problem: baud, line settings, or the wrong `/dev` node. No traffic at all is a board-side or configuration problem.
4. Measure the bit width to recover an unknown baud: baud is 1/(narrowest pulse width). A 8.68 µs bit is 115200; 4.34 µs is 230400. `sigrok-cli` or PulseView will decode it once the rate is right.
