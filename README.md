# skills

WarrDoge's agent skills.

## Skills

- `functional-simplicity` - separate actions, calculations, and data during coding work.
- `herdr` - control [Herdr](https://herdr.dev) panes, tabs, and agents, and coordinate a fleet of worker agents.

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

## License

Apache-2.0. See [LICENSE](LICENSE).

`skills/orchestration/herdr` is a derivative of the
[Herdr](https://github.com/ogulcancelik/herdr) project's `SKILL.md`.
Attribution and a list of changes are in [NOTICE](NOTICE).
