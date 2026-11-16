-- Eye Candy: photo mode, a part of the Experimental tab. One button takes a photo with no UI. A choice says
-- which settings it uses (EyeCandyDB.photoChoice): "mine" (your settings as they are: nothing changes, only
-- the game's UI hides) or "screenshot" (the default): the photo settings go on, the UI hides, the game takes
-- a photo, and your settings and UI come back. The photo settings are the picked screenshot preset: Default
-- (Eye Candy's Screenshot preset, which can't be changed or deleted) or one you saved (EyeCandyDB.photoPresets,
-- each with every setting on Eye Candy's list; EyeCandyDB.photoPick says which).
--
-- Change: your settings are saved first (EyeCandyDB.photo, as for a photo, with Eye Candy's own choices:
-- levels, Extras, dials, Look), the screenshot preset goes on, and you adjust it on the Standard and Hidden
-- tabs. Save screenshot preset keeps what is on (in the one you changed, or in a new one for Default), Cancel
-- keeps nothing; either puts your settings and choices back. Backups, presets, Back and restores end the edit
-- first (Cancel), so they never see it. A fight, a loading screen or /reload cancels it too, and a copy still
-- saved at the next login is put back. Closing the window does not end it: the title says it is on.
--
-- Screenshot() is what the game's own screenshot key calls. Addons may call it: Memento (CurseForge, for the
-- retail game of Nov 2026) takes one by itself after a boss kill or an achievement. Not tested on Forever
-- itself. The game fires SCREENSHOT_SUCCEEDED or SCREENSHOT_FAILED once it is done, and saves the file as
-- WoWScrnShot_ and the date and time, in the Screenshots folder of the game's own folder
-- (World of Warcraft\_forever_\Screenshots), as JPEG unless the screenshotFormat setting says otherwise
-- (warcraft.wiki.gg, Screenshot and SCREENSHOT_SUCCEEDED).
--
-- How many frames until the new settings show: nothing in the game says. The frames after a big change are
-- slow and uneven while the game loads what it now needs. So photo mode waits, as Autotune does after a
-- render scale change (Autotune.lua, at least 2 seconds, at most 6), until two half-second windows agree:
-- frame rate within 10%, and no frame in either more than 2.5 times the window's average (a long frame
-- is the game still loading). Those two numbers are a rule of thumb, not measured. It counts the frames it
-- waited and says so on the tab, so a photo that still looks half-loaded can be matched to the count.
--
-- Your settings from before are saved in EyeCandyDB.photo first. A fight, a loading screen, Esc or any other
-- Eye Candy change stops a photo and puts them back. It never changes settings in a fight. With "My settings
-- now" nothing is saved or changed, so there is nothing to put back but the UI.

local _, ns = ...
local PM = {}
ns.PhotoMode = PM

PM.PRESET = "look:screenshot"
PM.MIN, PM.MAX, PM.WINDOW, PM.AGREE, PM.SPIKE = 2, 6, 0.5, 0.1, 2.5
PM.SHOT_WAIT = 5 -- seconds to wait for the game to say the photo is saved
PM.MINE_WAIT = 0.3 -- with your own settings nothing changes: a moment for the UI to hide
PM.FOLDER = "World of Warcraft\\_forever_\\Screenshots"

local shot -- nil, or { phase = "settle" | "shot", waited, frames, wn, wt, prevFps, left, mine }
local edit = false -- true while the photo settings are on for you to adjust (Change it)
local noted = false -- an apply ran during the edit: Backups' record of the choices in force is renewed after
local busy = false -- true while photo mode itself sets values, so its own guard lets them through
local situationsWaiting = false -- a zone change came during the photo: the switch looks again after it

local frame = CreateFrame("Frame")
frame:Hide()
PM.frame = frame

local function Refresh()
	if ns.RefreshUI then ns.RefreshUI() end
end

-- The status line. kind: "done" (normal), "waiting" (grey) or "refused" (red).
local function Say(kind, text)
	PM.message, PM.messageKind = text, kind
end

-- Chat only when photo mode isn't in front of the player: it says it there.
local function Tell(msg)
	local m = _G.EyeCandyMainFrame
	if m and m.IsShown and m:IsShown() and not m.shrunk and m.tab == "autotune"
		and ns.ExperimentPart and ns.ExperimentPart() == "photo" then return end
	ns.Print(msg)
end

local function SetValues(values)
	busy = true
	for cvar, v in pairs(values) do
		if ns.Exists(cvar) and not ns.Same(ns.GetInfo(cvar), v) then SetCVar(cvar, v) end
	end
	busy = false
end

local function Copy(t)
	local out = {}
	for k, v in pairs(t or {}) do out[k] = v end
	return out
end

-- Eye Candy's own choices (levels, Extras, dials, Look): the Hidden and Standard tabs write them as you adjust,
-- so an edit saves them with your settings and gives them back.
local function CaptureChoices()
	local db = ns.db
	return { tiers = Copy(db.tiers), extras = Copy(db.extras), advanced = Copy(db.advanced), look = db.look,
		presetExtras = db.presetExtras and Copy(db.presetExtras) or nil, keepApplied = db.keepApplied }
end

local function RestoreChoices(state)
	if type(state) ~= "table" then return end
	local db = ns.db
	db.tiers, db.extras, db.advanced = Copy(state.tiers), Copy(state.extras), Copy(state.advanced)
	db.look = state.look
	db.presetExtras = state.presetExtras and Copy(state.presetExtras) or nil
	-- "Keep my settings applied" can be ticked during the edit too. An older copy has no keepApplied: leave it.
	if state.keepApplied ~= nil then db.keepApplied = state.keepApplied end
	if ns.SaveMirror then pcall(ns.SaveMirror) end
	-- Backups keeps its own record of the choices in force: renew it if the edit applied anything.
	if noted and ns.NoteApplied then pcall(ns.NoteApplied) end
	noted = false
end

-- Puts back the settings from before, menu values before hidden ones (a menu value can reset hidden ones),
-- then anything left over. In a fight it waits. Returns true when they are back now.
local function PutBack()
	local saved = ns.db and ns.db.photo
	if not saved then return true end
	if InCombatLockdown() then
		saved.afterCombat = true
		return false
	end
	busy = true
	local ok, err = pcall(ns.ApplyValues, saved.before, false)
	busy = false
	SetValues(saved.before)
	-- An edit that wasn't saved gives back the pick from before it (Save clears pickBefore first).
	if type(saved.pickBefore) == "table" then
		ns.db.photoPick, ns.db.photoChoice = saved.pickBefore.pick, saved.pickBefore.choice
	end
	ns.db.photo = nil
	RestoreChoices(saved.state)
	-- The city or instance switch waited while the photo had your settings: it looks again now.
	if situationsWaiting then
		situationsWaiting = false
		if ns.UpdateSituations then ns.UpdateSituations() end
	end
	if not ok then error(err, 0) end
	return true
end

function PM.IsOn() return shot ~= nil end

-- One frame of the wait for the new settings. s: { waited, frames, wn, wt, wlong, prevFps, prevEven }.
-- Returns true once two half-second windows in a row are even (no frame over PM.SPIKE times the average)
-- with frame rates within PM.AGREE, after PM.MIN seconds; or once PM.MAX seconds have gone.
function PM.Settle(s, elapsed)
	s.waited, s.frames = s.waited + elapsed, s.frames + 1
	s.wn, s.wt = s.wn + 1, s.wt + elapsed
	s.wlong = math.max(s.wlong or 0, elapsed)
	if s.wt >= PM.WINDOW then
		local fps = s.wn / s.wt
		local even = s.wlong <= PM.SPIKE * s.wt / s.wn
		local agree = s.prevFps and math.abs(fps - s.prevFps) / s.prevFps <= PM.AGREE
		local done = agree and even and s.prevEven and s.waited >= PM.MIN
		s.prevFps, s.prevEven, s.wn, s.wt, s.wlong = fps, even, 0, 0, 0
		if done then return true end
	end
	return s.waited >= PM.MAX
end

local function Waited(s)
	return string.format("It waited %d frames (%.1f seconds) for the new settings.", s.frames, s.waited)
end

-- Ends the peek and puts your settings back. Returns the closing words: what came back, or what waits.
local function Restore()
	local uiBack = true
	if ns.IsPeeking and ns.IsPeeking() then uiBack = ns.TogglePeek() and true or false end
	local back = PutBack()
	if back and uiBack then return "Your settings and UI are back as they were.", true end
	if back then return "Your settings are back. Press Esc or Alt+Z for the UI.", false end
	return "Your settings come back when the fight ends.", false
end

-- Ends the photo. result: "saved", "failed" or "unknown".
local function Finish(result)
	local s = shot
	shot = nil
	frame:Hide()
	local closing, all = Restore()
	PM.last = { frames = s.frames, seconds = s.waited, result = result }
	local ui = s.uiShown and " The UI came back before the photo, so it may be in it." or ""
	if result == "saved" then
		Say(all and "done" or "waiting", "Photo saved at " .. date("%H:%M:%S") .. ", in " .. PM.FOLDER
			.. " where the game is installed." .. (s.mine and "" or " " .. Waited(s)) .. ui .. " " .. closing)
	elseif result == "failed" then
		Say("refused", "The game couldn't save the photo. " .. closing)
	else
		Say("waiting", "The game didn't say whether the photo was saved. Look in " .. PM.FOLDER
			.. " where the game is installed." .. ui .. " " .. closing)
	end
	Tell(PM.message)
	Refresh()
end

-- What the photo uses: "mine" or "screenshot" (the default).
function PM.Choice()
	return (ns.db and ns.db.photoChoice == "mine") and "mine" or "screenshot"
end

-- A pick while a photo is being taken says to wait. Returns true when nothing is in the way, else nil and why.
local function FreeToPick()
	if shot then
		Say("waiting", "Photo mode is taking a photo. Wait a few seconds, then pick.")
		Refresh()
		return nil, "Photo mode is taking a photo. Wait a few seconds."
	end
	if edit then return nil, "Save or cancel the screenshot preset you are adjusting first." end
	return ns.db ~= nil
end

function PM.SetChoice(choice)
	if not FreeToPick() then return nil end
	ns.db.photoChoice = choice == "mine" and "mine" or "screenshot"
	Refresh()
	return true
end

-- Screenshot presets: Default (Eye Candy's Screenshot preset, PM.PRESET, which can't be changed or deleted)
-- and the ones you save (EyeCandyDB.photoPresets, a list of { name, values, saved }). EyeCandyDB.photoPick
-- says which one a photo uses: 0 (or nothing) for Default, else its place in the list.
PM.DEFAULT = "Default"
PM.MAX_PRESETS, PM.MAX_NAME = 10, 30

-- Your saved screenshot presets. A single set saved before the list existed (EyeCandyDB.photoSettings)
-- becomes the first one, and is picked as it was used.
function PM.Presets()
	local db = ns.db
	if not db then return {} end
	if type(db.photoPresets) ~= "table" then db.photoPresets = {} end
	local list = db.photoPresets
	local old = db.photoSettings
	if old ~= nil then
		db.photoSettings = nil
		if type(old) == "table" and type(old.values) == "table" and next(old.values) then
			table.insert(list, 1, { name = "My photo settings", values = old.values, saved = old.saved })
			db.photoPick = 1
		end
	end
	for i = #list, 1, -1 do
		local p = list[i]
		if type(p) ~= "table" or type(p.name) ~= "string" or type(p.values) ~= "table" then
			table.remove(list, i)
			local pick = tonumber(db.photoPick)
			if pick == i then db.photoPick = 0 elseif pick and pick > i then db.photoPick = pick - 1 end
		end
	end
	return list
end

-- Which screenshot preset a photo uses: 0 for Default, else its place in the list.
function PM.Pick()
	local n = #PM.Presets()
	local i = tonumber(ns.db and ns.db.photoPick) or 0
	if i < 1 or i > n or i ~= math.floor(i) then return 0 end
	return i
end

-- The name of screenshot preset i (0 is Default), or nil.
function PM.Name(i)
	if i == 0 then return PM.DEFAULT end
	local p = PM.Presets()[i]
	return p and p.name
end

-- Picks the screenshot preset a photo uses, and the Screenshot preset choice with it.
function PM.SetPick(i)
	if not FreeToPick() then return nil end
	if not PM.Name(i) then return nil end
	ns.db.photoPick, ns.db.photoChoice = i, "screenshot"
	Refresh()
	return true
end

-- The values screenshot preset i puts on (the picked one when i is nil), and what to call it.
-- Returns values, name; or nil and a plain reason.
function PM.PhotoValues(i)
	i = i or PM.Pick()
	if i > 0 then
		local p = PM.Presets()[i]
		if p then return Copy(p.values), "\"" .. p.name .. "\"" end
	end
	local values = ns.PresetValues and ns.PresetValues(PM.PRESET)
	if not values then return nil, "The Screenshot preset is missing." end
	return values, "The Screenshot preset"
end

-- A name for a new screenshot preset that no other has.
function PM.NewName()
	local taken = {}
	for _, p in ipairs(PM.Presets()) do taken[p.name:lower()] = true end
	local n = 1
	while taken[("Photo preset " .. n):lower()] do n = n + 1 end
	return "Photo preset " .. n
end

-- A typed name, trimmed, or nil and a plain reason. except: the place of the preset being renamed.
local function CheckName(name, except)
	name = tostring(name or ""):gsub("^%s+", ""):gsub("%s+$", "")
	if name == "" then return nil, "Type a name first." end
	-- Letters, not bytes: an accented letter is two or more bytes, and only the first doesn't start with 10.
	local _, letters = name:gsub("[^\128-\191]", "")
	if letters > PM.MAX_NAME then return nil, "That name is too long. Keep it to " .. PM.MAX_NAME .. " letters." end
	if name:lower() == PM.DEFAULT:lower() then return nil, "Default is Eye Candy's own. Pick another name." end
	for i, p in ipairs(PM.Presets()) do
		if i ~= except and p.name:lower() == name:lower() then
			return nil, "You already have a screenshot preset called \"" .. p.name .. "\". Pick another name."
		end
	end
	return name
end

-- Every setting on Eye Candy's list, and any extra in values, as they are now: the way back.
local function Before(values)
	local before = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local v = ns.GetInfo(cvar)
		if v ~= nil then before[cvar] = v end
	end
	for cvar in pairs(values) do
		if before[cvar] == nil and ns.Exists(cvar) then before[cvar] = ns.GetInfo(cvar) end
	end
	return before
end

-- What stops photo mode taking a photo or opening an edit, as a plain reason, or nil. Ends a Compare.
local function Blocked(what)
	if shot then return "Photo mode is already taking a photo." end
	if edit then return "A screenshot preset is on for you to adjust. Save it or press Cancel first." end
	if InCombatLockdown() then return "Not in a fight. Try again after it." end
	if ns.db.photo then return "Photo mode is still putting your settings back. It waits for the fight to end." end
	if ns.EyeTest and ns.EyeTest.IsOn() then return "The eye test is on. Finish or stop it first." end
	local AT = ns.Autotune
	if AT and AT.IsRunning() then return "Autotune is running. Stop it first." end
	-- Its result is on until you keep or undo it, and an undo then would be taken back by the way back.
	if ns.db.autotune then return "Autotune has your settings. Keep or undo its result first." end
	if ns.IsPeeking and ns.IsPeeking() then return "Peek is on. Press Back first." end
	if ns.IsComparing and ns.IsComparing() then
		local ok, err = ns.StopCompare()
		if not ok then return err end
	end
	return nil
end

-- Takes the photo. Returns true (it carries on by itself for a few seconds), or nil and a plain reason.
function PM.Take()
	if not shot and not edit and InCombatLockdown() then return nil, "Not in a fight. Try again after it." end
	if not shot and not edit and type(Screenshot) ~= "function" then return nil, "This game doesn't let addons take a photo." end
	local blocked = Blocked()
	if blocked then return nil, blocked end
	local mine = PM.Choice() == "mine"
	local values, name
	if not mine then
		values, name = PM.PhotoValues()
		if not values then return nil, name end
		-- Saved first, so the way back covers every setting.
		ns.db.photo = { before = Before(values) }
	end
	shot = { phase = "settle", waited = 0, frames = 0, wn = 0, wt = 0, mine = mine }
	if not mine then
		busy = true
		local ok, err = pcall(ns.ApplyValues, values, true)
		busy = false
		if not ok then
			shot = nil
			pcall(PutBack) -- it sets each value back itself even when the apply fails again
			return nil, name .. " couldn't go on, so no photo was taken. Your settings are back. (" .. tostring(err) .. ")"
		end
	end
	local hid, why = ns.PeekWithoutBar()
	if not hid then
		shot = nil
		PutBack()
		return nil, (why or "Couldn't hide the game's UI.") .. (mine and " No photo was taken." or " No photo was taken, and your settings are back.")
	end
	Say(nil, nil)
	frame:Show()
	return true
end

function PM.IsEditing() return edit end

local editing = 0 -- which screenshot preset is on for you to adjust: 0 for Default, else its place in the list
local editGen = 0 -- counts edits, so a name box from an edit that is over saves nothing

-- Which edit is on (a number), or nil: the name box checks it is still the same one.
function PM.EditToken()
	if edit then return editGen end
end

-- Room for one more screenshot preset: true, or nil and a plain reason.
function PM.RoomForNew()
	if #PM.Presets() >= PM.MAX_PRESETS then
		return nil, "You have " .. PM.MAX_PRESETS .. " screenshot presets. Cancel, delete one, then try again."
	end
	return true
end

-- The name of the screenshot preset on for you to adjust, or nil.
function PM.EditingName()
	if edit then return PM.Name(editing) or PM.DEFAULT end
end

-- Which screenshot preset is on for you to adjust (0 for Default), or nil.
function PM.EditingIndex()
	if edit then return editing end
end

-- Change: your settings are saved, screenshot preset i (the picked one when i is nil) goes on, and you
-- adjust it on the Standard and Hidden tabs. It is picked for photos too. Returns true, or nil and a plain reason.
function PM.Change(i)
	local blocked = Blocked()
	if blocked then return nil, blocked end
	i = i or PM.Pick()
	if not PM.Name(i) then return nil, "That screenshot preset is gone." end
	local values, name = PM.PhotoValues(i)
	if not values then return nil, name end
	-- The pick from before goes back with Cancel (PutBack), so Cancel keeps nothing.
	local pickBefore = { pick = ns.db.photoPick, choice = ns.db.photoChoice }
	ns.db.photoPick, ns.db.photoChoice, editing = i, "screenshot", i
	-- The Original backup is made first if it is missing, so it holds your settings and not the photo's.
	if ns.TakeBackup then ns.TakeBackup(false) end
	ns.db.photo = { before = Before(values), state = CaptureChoices(), editing = true, pickBefore = pickBefore }
	edit, noted = true, false
	editGen = editGen + 1
	busy = true
	local ok, err = pcall(ns.ApplyValues, values, true)
	busy = false
	if not ok then
		edit = false
		pcall(PutBack)
		return nil, name .. " couldn't go on, so nothing changed. Your settings are back. (" .. tostring(err) .. ")"
	end
	Say(nil, nil)
	Refresh()
	return true
end

-- Ends the edit and puts your settings and choices back. Returns the closing words.
local function EndEdit()
	edit = false
	if PutBack() then return "Your settings are back as they were.", true end
	return "Your settings come back when the fight ends.", false
end

-- Save screenshot preset: every setting on Eye Candy's list, as it is now, is kept in the preset being
-- adjusted, or in a new one called name when asNew is true (always for Default, which can't change). The
-- saved preset is picked for photos. Then your own settings come back. Returns true, or nil and a plain
-- reason (the edit stays on).
function PM.SavePreset(asNew, name)
	if not edit then return nil end
	local list = PM.Presets()
	local into = (not asNew and editing > 0 and list[editing]) or nil
	if not into then
		local why
		name, why = CheckName(name)
		if not name then return nil, why end
		local room
		room, why = PM.RoomForNew()
		if not room then return nil, why end
	end
	-- A setting still as it was before the edit (the photo settings don't set it, and it wasn't adjusted) may be
	-- one the city or instance switch, or Steady FPS, lowered: it is kept as your own value (ns.SituationValue,
	-- as backups and presets do), so a photo outside the city isn't taken with the city's lowered values.
	local before = ns.db.photo and ns.db.photo.before or {}
	local values = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local v = ns.GetInfo(cvar)
		if v ~= nil and ns.SituationValue and before[cvar] ~= nil and ns.Same(v, before[cvar]) then
			v = ns.SituationValue(cvar, v)
		end
		if v ~= nil then values[cvar] = tostring(v) end
	end
	if into then
		into.values, into.saved = values, date("%d %b")
	else
		into = { name = name, values = values, saved = date("%d %b") }
		list[#list + 1] = into
		ns.db.photoPick = #list
	end
	ns.db.photoChoice = "screenshot"
	-- Saved: the pick stays on it, not on the one from before the edit.
	if ns.db.photo then ns.db.photo.pickBefore = nil end
	local closing, all = EndEdit()
	Say(all and "done" or "waiting", "Saved as \"" .. into.name .. "\". A photo now uses it. " .. closing)
	Refresh()
	return true
end

-- Renames saved screenshot preset i. Returns true, or nil and a plain reason.
function PM.RenamePreset(i, name)
	local free, busyWhy = FreeToPick()
	if not free then return nil, busyWhy end
	local p = PM.Presets()[i]
	if not p then return nil, i == 0 and "Default can't be renamed." or "That screenshot preset is gone." end
	local why
	name, why = CheckName(name, i)
	if not name then return nil, why end
	local old = p.name
	p.name = name
	Say("done", "Renamed \"" .. old .. "\" to \"" .. name .. "\".")
	Refresh()
	return true
end

-- Deletes saved screenshot preset i. A photo then uses Default if it used this one.
function PM.DeletePreset(i)
	local free, busyWhy = FreeToPick()
	if not free then return nil, busyWhy end
	local list = PM.Presets()
	local p = list[i]
	if not p then return nil, i == 0 and "Default can't be deleted." or "That screenshot preset is gone." end
	local pick = PM.Pick()
	table.remove(list, i)
	if pick == i then ns.db.photoPick = 0 elseif pick > i then ns.db.photoPick = pick - 1 end
	Say("done", "Deleted \"" .. p.name .. "\"." .. (pick == i and " A photo now uses Default." or ""))
	Refresh()
	return true
end

-- Cancel, or an end from outside (a fight, a loading screen): nothing is saved, your own come back.
-- why: shown to the player, nil for the Cancel button.
function PM.CancelEdit(why)
	if not edit then return end
	local closing, all = EndEdit()
	local lead = why and ("The screenshot preset was not saved: " .. why .. ". ") or "Cancelled. Nothing was saved. "
	Say(all and "done" or "waiting", lead .. closing)
	Tell(PM.message)
	Refresh()
end

-- One short line for the window's title and the Presets card while a screenshot preset is on, or nil.
function PM.Note()
	if edit then return "Screenshot preset on: save it in Photo mode" end
	local saved = ns.db and ns.db.photo
	if saved and saved.afterCombat then return "Photo mode puts your settings back after the fight" end
end

local runningNote = ns.RunningNote
ns.RunningNote = function(...)
	local note = PM.Note()
	if note then return note end
	if runningNote then return runningNote(...) end
end

-- Stops it and puts your settings back. why: shown to the player.
function PM.Stop(why)
	if not shot then return end
	local before = shot.phase == "settle"
	shot = nil
	frame:Hide()
	local closing, all = Restore()
	local lead = "Photo mode stopped: " .. why .. ". " .. (before and "No photo was taken. " or "")
	Say(all and "done" or "waiting", lead .. closing)
	Tell(PM.message)
	Refresh()
end

frame:SetScript("OnUpdate", function(self, elapsed)
	if not shot then
		self:Hide()
		return
	end
	if shot.phase == "settle" then
		-- Esc or Alt+Z brought the UI back (Peek.lua ends the peek): no photo.
		if not (ns.IsPeeking and ns.IsPeeking()) then return PM.Stop("the UI came back") end
		-- Your own settings: nothing changed, so only a moment for the UI to hide.
		local ready
		if shot.mine then
			shot.waited, shot.frames = shot.waited + elapsed, shot.frames + 1
			ready = shot.waited >= PM.MINE_WAIT
		else
			ready = PM.Settle(shot, elapsed)
		end
		if ready then
			shot.phase, shot.left = "shot", PM.SHOT_WAIT
			if not pcall(Screenshot) then return Finish("failed") end
		end
	else
		-- Esc or Alt+Z while the game takes it: the UI may be in the photo, and the result says so.
		if not (ns.IsPeeking and ns.IsPeeking()) then shot.uiShown = true end
		shot.left = shot.left - elapsed
		if shot.left <= 0 then Finish("unknown") end
	end
end)

-- Any other Eye Candy change stops a photo first, so the way back stays right (as the eye test, EyeTest.lua):
-- an apply, a backup, a preset's step (NoteBeforePreset), Back on a step (RestoreStep), /ec back (GoBack)
-- and a restore. An edit of the photo settings lets the three the Standard and Hidden tabs use through (an
-- apply, and the Original backup they make sure of); the rest end it first, so they hold your settings.
local ALLOWED_IN_EDIT = { ApplyAll = true, ApplyValues = true, TakeBackup = true }
for _, name in ipairs({ "ApplyAll", "ApplyValues", "CreateBackup", "TakeBackup", "NoteBeforePreset",
	"RestoreStep", "GoBack", "RestoreBackupById" }) do
	local orig = ns[name]
	if orig then
		ns[name] = function(...)
			if not busy then
				if shot then PM.Stop("another setting changed") end
				if edit and not ALLOWED_IN_EDIT[name] then PM.CancelEdit("another setting changed") end
			end
			return orig(...)
		end
	end
end

-- During the edit the city and instance switch waits (it looks again once yours are back), so an apply on the
-- Standard or Hidden tab must not be lowered by it either: that would cap the photo settings and write the
-- edited value into the switch's record of your own (Situations.lua).
local keepLowered = ns.KeepSituationLowered
if keepLowered then
	ns.KeepSituationLowered = function(fn, ...)
		if edit then return fn(...) end
		return keepLowered(fn, ...)
	end
end

-- Save my settings as a preset (the Presets tab, /ec save) would save the photo settings while they are on.
local saveCurrent = ns.SaveCurrentAsPreset
if saveCurrent then
	ns.SaveCurrentAsPreset = function(...)
		if edit then return nil, "A screenshot preset is on. Save it or press Cancel in Photo mode first." end
		return saveCurrent(...)
	end
end

-- Backups keeps a record of the choices in force. An apply during the edit changes it: renewed once yours are back.
for _, name in ipairs({ "NoteApplied", "NoteAppliedExtra" }) do
	local orig = ns[name]
	if orig then
		ns[name] = function(...)
			if edit then noted = true end
			return orig(...)
		end
	end
end

-- Compare, Autotune and the eye test change settings too: none starts while it takes a photo, or while
-- the photo settings are on for you to adjust.
local REFUSE = "Photo mode is taking a photo. Wait a few seconds."
local REFUSE_EDIT = "A screenshot preset is on. Save it or press Cancel in Photo mode first."
local function Refuse() return shot and REFUSE or (edit and REFUSE_EDIT) or nil end
local toggleCompare = ns.ToggleCompare
if toggleCompare then
	ns.ToggleCompare = function(...)
		local why = Refuse()
		if why then return nil, why end
		return toggleCompare(...)
	end
end
if ns.Autotune then
	local start = ns.Autotune.Start
	ns.Autotune.Start = function(...)
		local why = Refuse()
		if why then return false, why end
		return start(...)
	end
end
if ns.EyeTest then
	local start = ns.EyeTest.Start
	ns.EyeTest.Start = function(...)
		local why = Refuse()
		if why then return nil, why end
		return start(...)
	end
end

-- The city and instance switch (Situations.lua) waits while the photo has your settings, and looks again
-- once they are back: otherwise it would lower the photo's values and then lose track of yours.
if ns.UpdateSituations then
	local update = ns.UpdateSituations
	ns.UpdateSituations = function(...)
		if ns.db and ns.db.photo then
			situationsWaiting = true
			return
		end
		return update(...)
	end
end

-- The patch warning's copy at logout and the FPS reader's preset measure take your settings, not the photo's.
if ns.PatchWatch and ns.PatchWatch.Own then
	local own = ns.PatchWatch.Own
	ns.PatchWatch.Own = function(cvar, value)
		local saved = ns.db and ns.db.photo
		if value ~= nil and saved and type(saved.before) == "table" and saved.before[cvar] ~= nil then
			value = saved.before[cvar]
		end
		return own(cvar, value)
	end
end
if ns.FPS and ns.FPS.Still then
	local still = ns.FPS.Still
	ns.FPS.Still = function(...)
		if shot or edit then return false end
		return still(...)
	end
end

local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(_, event, isLogin, isReload)
	local saved = ns.db and ns.db.photo
	if event == "SCREENSHOT_SUCCEEDED" or event == "SCREENSHOT_FAILED" then
		if shot and shot.phase == "shot" then Finish(event == "SCREENSHOT_SUCCEEDED" and "saved" or "failed") end
	elseif event == "PLAYER_REGEN_DISABLED" then
		-- Lockdown starts just after this event, so settings can still go back here.
		if shot then PM.Stop("a fight started") end
		if edit then PM.CancelEdit("a fight started") end
	elseif event == "PLAYER_LEAVING_WORLD" or event == "PLAYER_LOGOUT" then
		if shot then PM.Stop("a loading screen") end
		if edit then PM.CancelEdit("a loading screen") end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if saved and saved.afterCombat and not shot and not edit and PutBack() then
			Say("done", "Photo mode: the fight is over, so your settings are back as they were.")
			Tell(PM.message)
			Refresh()
		end
	elseif event == "PLAYER_ENTERING_WORLD" then
		-- Still saved at login (saved variables are only written at logout or /reload): put them back.
		if (isLogin or isReload) and saved and not shot and not edit and PutBack() then
			Say("done", "Photo mode didn't finish last time, so your settings went back as they were.")
			Tell(PM.message)
		end
	end
end)
for _, event in ipairs({ "SCREENSHOT_SUCCEEDED", "SCREENSHOT_FAILED", "PLAYER_ENTERING_WORLD", "PLAYER_LEAVING_WORLD",
	"PLAYER_LOGOUT", "PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED" }) do
	pcall(events.RegisterEvent, events, event)
end

----------------------------------------------------------------------
-- Photo mode's part of the Experimental tab
----------------------------------------------------------------------

local W = ns.ROW_W - 16
local GREY, RED = "|cff9d9d9d", "|cffff4040"
local ROW = 4

local function Text(c, font)
	local fs = ns.Label(c, "", font)
	fs:SetWidth(W)
	return fs
end

local function Under(f, prev, dx, gap)
	f:SetPoint("TOPLEFT", prev, "BOTTOMLEFT", dx or 0, -(gap or ROW))
end

local function TextH(fs, text)
	local m = tonumber((fs.GetStringHeight and fs:GetStringHeight()))
	if m and m > 0 then return m end
	if not text or text == "" then return 0 end
	local _, breaks = text:gsub("\n", "")
	return (breaks + 1) * 14
end

local GOLD, WHITE = "|cffffd100", "|cffffffff"

PM.WHY = "One click takes a photo with no UI on the screen. Pick what it uses: your settings as they are, or a screenshot preset."
PM.HOW = "Stand where you want the photo and point the camera first. It hides the UI, waits a few seconds if settings change, "
	.. "takes the photo and puts everything back. Expect low FPS for those seconds. A fight, a loading screen or Esc stops it."
PM.EDIT = "Change its settings on the Standard and Hidden tabs. Then come back here and press Save screenshot preset. "
	.. "Cancel puts your own settings back and saves nothing. A fight or a loading screen cancels it too."
PM.EDIT_DEFAULT = "Default stays as it is: saving makes a new screenshot preset with a name you pick."

-- What the photo uses now, in a line.
local function ChoiceText()
	if PM.Choice() == "mine" then
		return "The photo uses your settings as they are now. Nothing changes. Only the UI hides."
	end
	return "The photo uses \"" .. PM.Name(PM.Pick()) .. "\". Your settings come back after. "
		.. "Click a name to use another. Change puts one on so you can adjust it."
end

-- Save screenshot preset, or Save as new: a new one asks for its name first.
local function AskName()
	local room, why = PM.RoomForNew()
	if not room then
		Say("refused", why)
		return Refresh()
	end
	local token = PM.EditToken()
	ns.Ask({ title = "Save screenshot preset", text = "Name for the new screenshot preset:", edit = PM.NewName(), accept = "Save",
		onAccept = function(name)
			-- A fight or a loading screen ended the edit while the box was open, or another edit started.
			if token == nil or PM.EditToken() ~= token then
				Say("refused", "That change is over, so nothing was saved. Press Change to start again.")
				return Refresh()
			end
			local ok, err = PM.SavePreset(true, name)
			if not ok and err then Say("refused", err) end
			Refresh()
		end })
end

local function Said(ok, err)
	if not ok and err then Say("refused", err) end
	Refresh()
end

local LIST_ROW = 28

-- Row i of the screenshot preset list (0 is Default): the name to pick it, Change, and for yours Rename and Delete.
local function PresetRow(e, i)
	e.rows = e.rows or {}
	local r = e.rows[i]
	if r then return r end
	r = CreateFrame("Frame", nil, e.content)
	r:SetSize(W, LIST_ROW - ROW)
	r.pick = ns.Button(r, "", 260, function() PM.SetPick(i) end)
	r.pick:SetPoint("LEFT", 0, 0)
	ns.Tooltip(r.pick, function() return PM.Name(i) or "" end, function()
		if i == 0 then return "Eye Candy's own Screenshot preset. It can't be renamed or deleted. Click to use it for photos." end
		local p = PM.Presets()[i]
		return "Your screenshot preset" .. (p and p.saved and (", saved " .. p.saved) or "") .. ". Click to use it for photos."
	end)
	r.change = ns.Button(r, "Change", 80, function() Said(PM.Change(i)) end)
	r.change:SetPoint("LEFT", r.pick, "RIGHT", ROW, 0)
	ns.Tooltip(r.change, "Change", "Puts this screenshot preset on so you can adjust it on the Standard and Hidden tabs. Your settings are saved first and come back when you save or cancel.")
	if i > 0 then
		r.rename = ns.Button(r, "Rename", 80, function()
			local name = PM.Name(i)
			if not name then return end
			ns.Ask({ title = "Rename screenshot preset", text = "New name for \"" .. name .. "\":", edit = name, accept = "Rename",
				onAccept = function(text) Said(PM.RenamePreset(i, text)) end })
		end)
		r.rename:SetPoint("LEFT", r.change, "RIGHT", ROW, 0)
		r.delete = ns.Button(r, "Delete", 70, function()
			local name = PM.Name(i)
			if not name then return end
			ns.Ask({ title = "Delete screenshot preset", text = "Delete \"" .. name .. "\"? This can't be undone.", accept = "Delete",
				onAccept = function() Said(PM.DeletePreset(i)) end })
		end)
		r.delete:SetPoint("LEFT", r.rename, "RIGHT", ROW, 0)
	end
	e.rows[i] = r
	return r
end

local function Build(page, holder)
	local c = ns.ScrollPage(holder, 0)
	c:SetHeight(200)
	local e = { content = c }
	page.photo = e
	e.head, e.headH = ns.Header(c, "Photo mode", "Experimental")
	e.head:SetPoint("TOPLEFT", 0, 0)
	e.why = Text(c)
	e.why:SetText(PM.WHY)
	Under(e.why, e.head, 4)
	e.how = Text(c, "GameFontDisableSmall")
	e.how:SetText(PM.HOW)
	Under(e.how, e.why, 0, 8)
	-- The choice: what the photo uses.
	e.mine = ns.Button(c, "My settings now", 130, function() PM.SetChoice("mine") end)
	ns.Tooltip(e.mine, "My settings now", "The photo uses your settings as they are. No setting changes. Only the UI hides.")
	e.mine.label = "My settings now"
	e.shotChoice = ns.Button(c, "Screenshot preset", 130, function() PM.SetChoice("screenshot") end)
	e.shotChoice:SetPoint("LEFT", e.mine, "RIGHT", ROW, 0)
	ns.Tooltip(e.shotChoice, "Screenshot preset", "The photo uses the screenshot preset picked in the list below. Your settings come back after.")
	e.shotChoice.label = "Screenshot preset"
	e.choiceText = Text(c, "GameFontDisableSmall")
	e.listHead = Text(c, "GameFontNormal")
	e.listHead:SetText("Screenshot presets")
	e.take = ns.Button(c, "Take photo", 110, function()
		local ok, err = PM.Take()
		if not ok and err then
			Say("refused", err)
			Refresh()
		end
	end)
	ns.Tooltip(e.take, "Take photo", "Hides the UI and takes a photo with what you picked above. Your settings and UI come back after.")

	-- While a screenshot preset is on for you to adjust.
	e.bigText = Text(c, "GameFontNormalHuge")
	e.editText = Text(c)
	e.save = ns.Button(c, "Save screenshot preset", 190, function()
		if (PM.EditingIndex() or 0) == 0 then return AskName() end
		Said(PM.SavePreset(false))
	end)
	ns.Tooltip(e.save, "Save screenshot preset", function()
		if (PM.EditingIndex() or 0) == 0 then return "Saves every setting on Eye Candy's list, as it is now, as a new screenshot preset. You pick its name. Then your own settings come back." end
		return "Keeps every setting on Eye Candy's list, as it is now, in this screenshot preset. Then your own settings come back."
	end)
	e.saveNew = ns.Button(c, "Save as new", 110, AskName)
	e.saveNew:SetPoint("LEFT", e.save, "RIGHT", ROW, 0)
	ns.Tooltip(e.saveNew, "Save as new", "Saves what is on now as a new screenshot preset with a name you pick. The one you changed stays as it was.")
	e.cancel = ns.Button(c, "Cancel", 90, function() PM.CancelEdit() end)
	ns.Tooltip(e.cancel, "Cancel", "Saves nothing. Your own settings come back as they were.")
	e.status = Text(c)
end

local function StatusText()
	local text = PM.message or ""
	if text == "" then return "" end
	if PM.messageKind == "refused" then return RED .. text .. "|r" end
	if PM.messageKind == "waiting" then return GREY .. text .. "|r" end
	return text
end

local function Refresh_(page)
	local e = page.photo
	local status = StatusText()
	e.status:SetText(status)
	local editing = PM.IsEditing()
	local mine = PM.Choice() == "mine"
	local list = PM.Presets()
	local pick = PM.Pick()
	local changing = PM.EditingIndex() or 0
	for _, f in ipairs({ e.mine, e.shotChoice, e.choiceText, e.take }) do f:SetShown(not editing) end
	e.listHead:SetShown(not editing and not mine)
	for _, f in ipairs({ e.bigText, e.editText, e.save, e.cancel }) do f:SetShown(editing and true or false) end
	-- Save as new only when a saved one is being adjusted: Default's Save already makes a new one.
	e.saveNew:SetShown(editing and changing > 0)
	-- The choice made is gold (rule 20: the selected thing).
	e.mine:SetText((mine and GOLD or WHITE) .. e.mine.label .. "|r")
	e.shotChoice:SetText((mine and WHITE or GOLD) .. e.shotChoice.label .. "|r")
	e.mine.chosen, e.shotChoice.chosen = mine, not mine
	for i, r in pairs(e.rows or {}) do
		if i > #list then r:Hide() end
	end
	local height = e.headH + ROW + TextH(e.why, PM.WHY) + 8 + TextH(e.how, PM.HOW) + 8
	local last
	if editing then
		for _, r in pairs(e.rows or {}) do r:Hide() end
		local big = "Screenshot preset is on: " .. (PM.EditingName() or PM.DEFAULT)
		e.bigText:SetText(big)
		local text = PM.EDIT .. (changing == 0 and ("\n" .. PM.EDIT_DEFAULT) or "")
		e.editText:SetText(text)
		for _, f in ipairs({ e.bigText, e.editText, e.save, e.cancel }) do f:ClearAllPoints() end
		Under(e.bigText, e.how, 0, 12)
		Under(e.editText, e.bigText, 0, 8)
		Under(e.save, e.editText, 0, 10)
		e.cancel:SetPoint("LEFT", changing > 0 and e.saveNew or e.save, "RIGHT", ROW, 0)
		last = e.save
		height = height + 4 + TextH(e.bigText, big) + 8 + TextH(e.editText, text) + 10 + 24
	else
		local text = ChoiceText()
		e.choiceText:SetText(text)
		for _, f in ipairs({ e.mine, e.choiceText, e.listHead, e.take }) do f:ClearAllPoints() end
		Under(e.mine, e.how, 0, 8)
		Under(e.choiceText, e.mine, 0, 8)
		height = height + 24 + 8 + TextH(e.choiceText, text)
		local above = e.choiceText
		if mine then
			for _, r in pairs(e.rows or {}) do r:Hide() end
		else
			Under(e.listHead, above, 0, 10)
			above = e.listHead
			height = height + 10 + TextH(e.listHead, "Screenshot presets")
			for i = 0, #list do
				local r = PresetRow(e, i)
				local name = ns.ShortName(PM.Name(i), 34)
				r.pick:SetText((i == pick and GOLD or WHITE) .. name .. "|r")
				r.pick.chosen = i == pick
				r:ClearAllPoints()
				Under(r, above, 0, ROW)
				r:Show()
				above = r
				height = height + LIST_ROW
			end
		end
		Under(e.take, above, 0, 10)
		last = e.take
		height = height + 10 + 24
	end
	e.status:ClearAllPoints()
	Under(e.status, last, 0, 8)
	height = height + 8 + TextH(e.status, status)
	e.content:SetHeight(height + 16)
end

if ns.AddExperiment then
	ns.AddExperiment({
		key = "photo", name = "Photo mode", build = Build, refresh = Refresh_,
		tip = "One click: a photo with no UI, using your settings or a screenshot preset, then everything back.",
	})
end
