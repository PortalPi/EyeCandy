# Eye Candy

Graphics presets, curated looks, hidden graphics settings and dated backups for World of Warcraft: Forever.

Version 1.0.0, the first under this name. Up to its version 1.9.0 this addon was called **Vista**. Open it with `/ec` or `/graphics` (`/vista` still works for one release).

CurseForge: not published yet.

## What it does

- **Presets in one click.** Six quality levels (Performance to Showcase), five Looks (Beautiful, Painterly, Crisp, Moody, Classic) and four for a job (Raid & PvP, Laptop, Screenshot, Capital city).
- **Your own presets.** Save, rename, duplicate and delete. Export one as a short text string. A friend imports it and sees what it changes before it saves.
- **Hidden settings.** About 55 settings the game's menu does not show, each with a plain description. Every number setting is a slider with a typed box.
- **Standard tab.** The game's own Graphics menu in one place.
- **Dated backups.** Your Original settings (made once and kept for good) and backups you name. Eye Candy makes no other backup by itself. On the Backups tab, Restore shows what will change first.
- **Back to before.** After a preset, one click puts back your settings from just before it. One step back, and only until you change something else.
- **Steadier frames in cities.** Off until you turn it on (`/ec city`). In a capital city it lowers view distance, environment detail, fog and far-away character detail where yours are higher, and puts them back when you leave.

## Install

Copy the `EyeCandy` folder into `World of Warcraft\_forever_\Interface\AddOns\` and start the game.

Coming from Vista: before starting the game, copy `WTF\Account\<account>\SavedVariables\Vista.lua` to `EyeCandy.lua` in the same folder, and delete the old `Vista` addon folder. Eye Candy picks up your settings and backup from it.

## Slash commands

`/ec` and `/graphics` do the same thing. `/ec help` lists these in game.

| Command | What it does |
| --- | --- |
| `/ec` | Open the window |
| `/ec peek` | Hide the game's UI and Eye Candy to see the picture; Back or Esc returns |
| `/ec compare` | Flip between before your last preset and now; `compare stop` ends on now |
| `/ec hidden` | Open the Hidden tab (also `advanced`) |
| `/ec preset <performance\|balanced\|high\|ultra\|cinematic>` | Set every system to one quality level and apply |
| `/ec showcase` | Cinematic plus the Showcase hidden settings |
| `/ec look <beautiful\|painterly\|crisp\|moody\|classic>` | Apply a Look |
| `/ec look <raid\|laptop\|screenshot\|city>` | Apply a preset for a job |
| `/ec back` | Back to before your last preset (one step, until you change something) |
| `/ec presets` | List presets |
| `/ec save <name>` | Save your current settings as a preset |
| `/ec use <name>` | Apply a preset |
| `/ec share <name>` | Make a share code |
| `/ec backups` | List backups |
| `/ec backup [name]` | Make a backup |
| `/ec restore <number>` | Restore a backup, no question asked. It makes no backup of now (`/ec restore` alone restores the Original) |
| `/ec city` | Turn the city switch on or off (`city on`, `city off`) |
| `/ec apply` | Apply your settings again |
| `/ec minimap` | Show or hide the minimap button |
| `/ec find <word>` | Search the game's settings, with the game's own descriptions |
| `/ec export [all]` | Copy box with your settings |
| `/ec report` | Copy box with a bug report |

## Report a bug

1. In game, type `/ec report`. A box opens with your Eye Candy version, game build, settings and any recent Lua errors from Eye Candy. Press Ctrl+C to copy it.
2. Open [a new bug report](https://github.com/PortalPi/EyeCandy/issues/new/choose) and paste the text into the form.

## Build and test

The addon is plain Lua. There is nothing to build: the `EyeCandy` folder is the addon.

Tests run in Python with Lua 5.1 stubs (a stand-in for the game, in `tests/harness.lua`):

```
pip install -r tests/requirements.txt
python tests/test_presets.py
```

Each change has its own test file in `tests/test_<area>.py`. Run the one for the area you changed. They print PASS or FAIL for each check, and "ALL PASS" at the end. `tests/run.py` is the older full suite.

Nothing in the game itself can be tested this way. Try changes in game with `/reload` (a `.toc` change needs a full restart).

## Docs

- `CONTRIBUTING.md`: layout, dev loop, game facts and rules.
- `docs/cvar_audit.txt`: Blizzard's help text and defaults for each setting.
- `CHANGELOG.md`: what changed, for players.

## Licence

Not chosen yet.
