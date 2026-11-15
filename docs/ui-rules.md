# Eye Candy UI rules

Every screen, button and line of text a player sees follows these rules. They come from a full
review of the window in November 2026 (four tabs, every string). Most of its faults came from
features built one at a time, each fine alone, that clashed once they sat side by side. A new
feature must pass the checklist at the end before its pull request merges.

## 1. Words

1. **Plain words, short sentences.** One idea a sentence. British spelling. No em-dashes.
   Everyday words, never the game's internal names.
2. **One word for each thing, and one thing for each word.** Use these:

   | Say | For | Never say |
   |---|---|---|
   | setting | a graphics value | CVar, variable |
   | quality level | Performance to Cinematic, the preset group | tier |
   | `<System> level` | a per-system level on the Hidden tab | tier |
   | Look, Situation | the other two built-in groups | |
   | preset | anything in the Presets list | profile |
   | share code | the text that carries a preset | share string, export string |
   | far detail | level of detail at distance | LOD |
   | Back to before | undo the last preset, or Autotune (Back to before Autotune) | revert, rollback |
   | Copy my settings | the box of your settings to copy | Export |

   The table is for words on screen. Slash commands (`/ec export`) keep their names.

   Name a graphics technique (SSAO, VRS, CMAA) only where Blizzard's own label does, and say what
   it does in the plain line.
3. **Same label, same action.** Two buttons that do different things never share a label on one
   screen (an "Apply" on the bar and an "Apply" on a row did). Two buttons that do the same
   thing never sit on one screen.
4. **Say when it applies.** A control that acts at once says nothing. A control that waits for
   Apply says so ("Applies when you press Apply"). An action that changes settings says so on its
   button or in its tooltip.
5. **Never promise what the code does not do.** When a behaviour changes (backups, undo, what
   Apply does), search every `.lua` file and CHANGELOG.md for each sentence that describes it,
   and fix them in the same pull request. A false promise is a bug.
6. **Say the result where it happened.** A refusal or error shows in the window, next to the
   thing that failed, in red. Chat is for slash commands. Never "see chat" for something the row
   can say itself. A box that refused its input stays open and says why under it.
7. **A notice makes sense alone.** Someone who opens the window cold, with no memory of what
   they did, can read it. Name the preset or setting it is about.

## 2. State

8. **The window always says what is on.** The preset you are on shows on the Presets tab's card
   and in the title bar, with how many settings changed since (`ns.OnPreset`, Presets.lua). A
   feature that changes settings by itself (a Situation switch, Autotune) says so where the
   player will look: the card or title, and its own row.
9. **Three states, three looks.** Waiting: grey, "not applied yet". Done: normal, "now X".
   Refused: red, "the game kept X". Never draw a waiting value as refused.
10. **New things are marked.** Something the player just added (an import, a saved preset)
    gets a green "New" tag and is scrolled into view.

## 3. Layout

11. **Headings look like headings.** `GameFontNormalLarge` in gold, a 1px gold rule at 35% under
    it, the grey note under the rule. Never the same font as the rows under it. `ns.Header`
    (UI.lua) draws this. Use it, do not build another.
12. **Groups are further apart than rows.** Space between groups is always bigger than space
    inside a group: rows 4px apart, groups at least 16px apart (the Presets list uses 24).
13. **One left edge.** Content starts at the same x on every tab. Do not invent a new inset.
14. **A row is: name, one grey line, one main action, a "..." menu.** The name is white
    (`GameFontHighlight`). The one-line summary is always visible, not only in a tooltip. The
    main action is one button. Everything else (Share, Duplicate, Rename, Delete) goes in the
    "..." menu, which right-click on the row opens too.
15. **One primary button per area.** Secondary actions are smaller or in a menu. Delete is
    last, in red text, behind a confirm, and at least 12px from the button beside it.
16. **Nothing overlaps or wraps by accident.** Every FontString in a fixed-height row has a width
    or a right anchor, and word wrap off. Cut long names with `ns.ShortName` and put the full
    name in the tooltip. Check the longest real string, not a short test one.
17. **A button shows only where it does something.** No dead buttons. The bottom bar's Apply
    shows on the Hidden tab and the shrunk bar only (`PlaceBottomBar`, UI.lua).
18. **Inline before popup.** If a strip on the page can do it (Import), do not open a new window.
    Every new window uses `MakeWindow` (drag, scale, remembered), closes on Esc, and is added
    to `ns.PEEK_WINDOWS`.
19. **Fit the window.** New tabs keep the tab row clear of the search box. A list that can
    outgrow the page uses `ns.ScrollPage`.

## 4. Colour

20. **Colour means one thing.** Only these:

    | Colour | Means |
    |---|---|
    | gold `ffffd100` (1, 0.82, 0) | on now, headings, the selected thing |
    | green to red stripe (`ns.TIER_COLOURS`) | a quality level's FPS cost, cheap to costly |
    | grey 0.62 (`ff9d9d9d`) | secondary text, waiting |
    | red `ffff4040` | refused, error, Delete |
    | green `ff7cff7c` | just saved, New |

    Names are white. Looks, Situations and new features get no colour of their own.

## 5. Tooltips

21. **The tooltip rule** (CONTRIBUTING.md): Blizzard's words first, then one plain line, then
    the game default, built by `ns.SettingTip`. "Not documented by Blizzard" where there is none.
    "Unconfirmed" on any guess.
22. **Tooltips stay inside the window.** Controls on the right half anchor `ANCHOR_LEFT`. Rows
    anchor `ANCHOR_CURSOR`. Pass the anchor to `Tooltip(frame, title, body, anchor)`.
23. **Nothing needed lives only in a tooltip.** What a thing is and whether it is on are on the
    screen. The tooltip adds detail.

## 6. Behaviour

24. **Safe by default.** An action that changes settings needs its own click on a button that
    says so. Import saves only. A new automatic feature is off until the player turns it on, and
    its switch says in one line what it will do.
25. **Never change settings in combat.** Queue it until `PLAYER_REGEN_ENABLED`, and say on the
    row that it is waiting.
26. **Works untouched.** A new feature needs nothing from the player day to day. If it must ask
    something, it asks once, and the question stands alone.

## 7. Checks

27. Each rule a change touches gets a check in its own `tests/test_<area>.py`: the text the
    player reads, which buttons show on which tab, the state words. Prefer a check that drives the
    UI (click, read `.text`, read `.shown`) over one that reads the source file.

## Checklist for a pull request that adds or changes UI

Go through every string and frame the change adds. Each line is yes or a fix.

- [ ] Every word is in the table in rule 2, or is plain English. No tier, CVar, LOD, Extra, share string.
- [ ] British spelling, no em-dashes, short sentences.
- [ ] No label is shared with a different action on the same screen.
- [ ] Every sentence about backups, undo or Apply is still true after this change (searched).
- [ ] Errors and refusals show in the window, in red, next to their control.
- [ ] If it changes settings by itself, the card, title or its row says so.
- [ ] Headings use `ns.Header`. Spacing is 4, 8, 16 or 24. Groups are further apart than rows.
- [ ] Each row has one main button, the rest in a "..." menu. Delete is last, red, confirmed.
- [ ] The longest real string fits its row without overlap or wrap.
- [ ] No colour outside the table in rule 20.
- [ ] Tooltips follow the tooltip rule and open inside the window.
- [ ] Nothing important is only in a tooltip.
- [ ] Off by default if it acts by itself. Waits out combat.
- [ ] Checks added in `tests/test_<area>.py` and that file run.
