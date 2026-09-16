# skills

WarrDoge's agent skills.

## Skills

- `functional-simplicity` - separate actions, calculations, and data during coding work.
- `herdr` - control [Herdr](https://herdr.dev) panes, tabs, and agents, and coordinate a fleet of worker agents.
- `board-console-access` - open a debug channel to a headless single-board computer, and confirm the channel is telling the truth.
- `raspberry-pi-boot-triage` - diagnose a Raspberry Pi 4 or 5 that will not boot, from LED codes to the bootloader EEPROM.
- `jetson-orin-triage` - diagnose a Jetson Orin Nano over the debug UART, forced recovery, A/B slots, and USB device mode.
- `debug-probe-swd-jtag` - use a Debug Probe as a console cable or an SWD/JTAG port, and know which one a target supports.

## Install

```sh
npx skills@latest add WarrDoge/skills
```

Or with [skillfish](https://skill.fish):

```sh
skillfish add WarrDoge/skills --all --global
```

The `herdr` skill replaces the upstream one and uses the same skill name. Remove
the upstream copy first so they do not both register:

```sh
skillfish remove herdr
```

## Auto-load `functional-simplicity`

Skills cannot register hooks themselves. To inject the skill into every session
(like the ponytail plugin does) add a `SessionStart` hook to
`~/.claude/settings.json`:

```json
"hooks": {
  "SessionStart": [
    {
      "matcher": "startup|resume|clear|compact",
      "hooks": [
        { "type": "command", "command": "sed '1,/^---$/d' ~/.claude/skills/functional-simplicity/SKILL.md" }
      ]
    }
  ]
}
```

`sed` drops the frontmatter; the body lands in context as plain text and is
re-injected after compaction.

## License

Apache-2.0. See [LICENSE](LICENSE).

`skills/orchestration/herdr` is a derivative of the
[Herdr](https://github.com/ogulcancelik/herdr) project's `SKILL.md`.
Attribution and a list of changes are in [NOTICE](NOTICE).
