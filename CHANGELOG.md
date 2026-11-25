# Eye Candy changelog

## 1.1.4

- **The bug report covers the minimap button.** `/ec report` says if the button is set to hidden, if it shows now and what it sits on. It also says if your saved settings loaded when you logged in.

## 1.1.3

- **The bug report lists recent setting changes.** `/ec report` shows the last 15 graphics settings that changed since you logged in, who changed them and where the loading screens fell. It also says which of Eye Candy's own switches are on. This helps find out why the picture can change after a flight or a loading screen.

## 1.1.2

- **The bug report shows the render scale hold.** `/ec report` says if the game's hold on render scale was there when Eye Candy loaded, if it is there now, and if the last logout cleared it. This helps find out why render scale can stay at 100% after a restart.

## 1.1.1

- **Bug reports can go on CurseForge too.** `/ec report` says you can paste the report in a comment on Eye Candy's CurseForge page, as well as on GitHub. Either way the maintainer sees all of it.

## 1.1.0

- **Render scale goes up to 200% again.** Since the 14 November patch the game holds render scale at 100%. Restart the game and it can go to 200%. Until then, the window says it's held. Nothing to turn on.
- **The window fades further.** With the mouse away it fades to about a third, so the world shows through. `/ec fade` turns this off.
- **Plainer words.** Buttons, tooltips and chat messages say what they do in fewer words. The city switch under Capital city is now "Lower settings in capital cities".
- **Fixed: a quality level after a Look kept the Look's render scale.** High after Moody now looks and runs like High. Render scale override, resample filter, sharpness and character detail you set yourself on the Hidden tab still stay.
- **A warning when the game changes your settings.** If a patch changes your graphics settings while you're logged out, a small window lists what changed. Put them back, or keep the changes.
- **Help me pick.** On the Presets tab, by Quality levels. Pick Prettier or Faster and it suggests one preset and shows what it changes. Nothing changes until you press Apply. Let Eye Candy pick opens Autotune instead.
- **Live FPS on the window.** The bottom bar shows your FPS, so you can watch it move as you drag a slider.
- **Each preset remembers its FPS.** A few seconds after you apply one and stand still, its tooltip says "Last time you used it: 63 FPS in Goldshire."
- **Steadier frames in big fights.** Off until you tick "Lower settings in dungeons, raids, battlegrounds and arenas" under Raid & PvP, or type `/ec instance`. In a dungeon, raid, battleground or arena, settings higher than Raid & PvP's come down until you leave. Never in a fight.
- **A name that can't be used stays in its box.** When you save or rename a preset, the reason shows in red under the name, and you can fix it there.
- **The Experimental tab has parts.** Buttons at its top pick one, and it remembers your last.
- **Eye test (experimental).** Like at the optician: which is better, 1 or 2? Each round shows one setting two ways. Pick one, or say they look the same. Your answers make a preset of your own.
- **More than one step back.** The Presets tab lists what you did today, newest first. Back on any step puts your settings back to just before it, after asking. A restore from the Backups tab can be undone too. `/ec back` undoes the newest step.
- **Photo mode (experimental).** One button hides the UI and takes a photo, with your settings as they are or with a screenshot preset. Each screenshot preset has a Change button and a "..." menu. Keep up to 10 of your own. The photo goes in the Screenshots folder in `World of Warcraft\_forever_`.
- **Steady FPS (experimental).** Off until you turn it on. Pick an FPS goal. When FPS stays under it, render scale comes down a little, and goes back up when FPS recovers. Never under 70%, never in a fight. The Presets card says while it has render scale lowered.

## 1.0.1

- **A tidy-up.** Old code from before 1.0.0 is gone. Nothing you use changes.

## 1.0.0

### What's new

- **One window, five tabs.** Presets, Standard, Hidden, Backups and Experimental. Presets opens first.
- **Standard tab.** The game's own Graphics menu, in one place, with the game's own names and help text. Each value shows once, settings you can only change in the game's menu are grey and say so, and a line explains the gold dot.
- **Presets.** Save your own, rename, duplicate and delete them. Four new built-in presets for a job: Raid & PvP, Laptop, Screenshot and Capital city. They sit in their own group, Situations.
- **Steadier frames in cities, by itself.** Tick "Switch in cities by itself" under Capital city on the Presets tab, or type `/ec city`. In a capital city Eye Candy lowers view distance, environment detail, fog and far-away character detail, on top of your own settings and only where yours are higher. When you leave they go back. Anything you change yourself while in the city stays as you set it. It never switches in combat, and it takes no backup. Off until you turn it on.
- **Share a preset.** Share makes a short code. A friend pastes it into Import a preset on the Presets tab and sees what it changes. Import saves it as a new preset, marked New, and changes nothing until they press Apply on it. Only graphics settings from Eye Candy's own list can be set by a code. Anything else is skipped and shown.
- **See what you are on.** The top of the Presets tab and the window's title show the preset you are on, and how many settings you have changed since. They also say when Autotune or the city switch has your settings. Back and Restore say what they did right where you clicked, not in chat.
- **Backups.** A dated list instead of one slot. Original (your settings from before Eye Candy, kept for good) and your own named backups. Eye Candy never adds one by itself, so the list holds only what you chose to keep. On the Backups tab the Original is listed first, each row shows your character's name and how many settings differ from now, and Restore shows how many settings change and asks first.
- **Back to before.** After a preset, a "Back to before <name>" button on the Presets tab undoes it. `/ec back` does the same. It goes back one step, and only until you change something else.
- **Sliders** for every number setting, with a typed box, arrows, a tick at the game's default and a reset arrow. Hold Shift for fine steps. Render scale runs in 1% steps from 33% up to the most the game allows, 200%. Sharpness has an Off position.
- **Autotune (experimental),** on its own Experimental tab. Pick a goal (30, 60, 75, 120, 144, 165, 180 or 240 FPS, or Best balance), then what to tune for: Best look, Raid ready (a lot more spare FPS, so your goal holds in a big fight), Smooth (judged by your slowest frames), Sharpest picture (render scale, textures, anti-aliasing, sharpening and view distance first) or Cool and quiet (FPS capped at your goal, for less heat and noise). Then where to start: the lowest settings, or any preset (a quality level, a Look or your own). From a preset, it keeps what makes that preset itself, like Moody's fog and ambient occlusion, and lowers the rest one step at a time until your goal holds. Press Start. It measures your FPS, tries settings one at a time, and keeps only what holds the goal, the slowest frames included. It notices when Vertical Sync holds FPS at your screen's rate, or your CPU sets the limit, and measures the result again at the end. Stand still for about 3 to 7 minutes (Smooth takes 4 to 10). Moving, turning, dragging or zooming the camera, a loading screen or opening Options stops it and puts your settings back. A fight stops it too, and your settings come back when the fight ends. At the end, Save as preset keeps the result as your own preset, with where it was tested and your field of view and camera distance in its tooltip, or Back to before Autotune undoes it.
- **Search box** for the Standard and Hidden tabs, and a gold dot on any setting you have changed from the game default.
- **Minimap button** (right-click opens Backups) and an Eye Candy entry in the game's Options > AddOns list. `/ec minimap` hides or shows the button.
- **Truer tooltips.** Each tooltip quotes Blizzard's own help text first, then says it in plain words. Where Blizzard has none, it says so. Eight descriptions were wrong or incomplete and are fixed. The big one: Depth Effects is soft particles, not depth of field. Resample filter says when the game ignores it.
- **Peek and Compare.** `/ec peek` hides the game's UI and Eye Candy's windows so you can see the picture, with one small Back button (Esc also brings it back). `/ec compare` flips the world between the settings from before your last preset and now, so you can judge a change in the same spot. `/ec compare stop` ends it on "now". Both have buttons on the window's bottom bar too. While comparing, the button says what a click shows next, and the window's title says what is on screen. Right-click Compare, or close Eye Candy, to end on "now". While peeking, the small bar has its own Show before / Show now button, so you can flip with the UI hidden. Compare needs a preset to compare against, so apply one first. Both end on their own if combat starts, and neither starts in combat. Compare also ends on "now" if you reload.
- **Move and resize every window.** Drag a window to move it. Drag the grip in its bottom-right corner to make it bigger or smaller, from 60% to 130%. Right-click the grip to go back to 100%. Eye Candy remembers where each window is and how big, for each account.
- **Shrink the window.** The minus button next to close rolls the main window up to a small bar with Apply, Compare and Peek. The plus opens it again.
- **The window fades a little** when the mouse is away, so more of the world shows. It comes back as soon as the mouse does. `/ec fade` turns this off.
- **`/ec` opens the window.** If another addon also uses `/ec`, the game may open that one instead. Eye Candy then says so once when you log in, and `/eyecandy` always opens Eye Candy.
- **`/ec report`** opens a box with a bug report. Copy it and paste it into the bug form on GitHub.
