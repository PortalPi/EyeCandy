-- Eye Candy: photo mode, a part of the Experimental tab. One button: the Screenshot preset goes on, the
-- game's UI hides, the game takes a photo, and your settings and UI come back.
--
-- Screenshot() is what the game's own screenshot key calls. Addons may call it: Memento (CurseForge, for the
-- retail game of Nov 2026) takes one by itself after a boss kill or an achievement. Not tested on Forever
-- itself. The game fires SCREENSHOT_SUCCEEDED or SCREENSHOT_FAILED once it is done, and saves the file as
-- WoWScrnShot_ and the date and time, in the Screenshots folder of the game's own folder
-- (World of Warcraft\_forever_\Screenshots), as JPEG unless the screenshotFormat setting says otherwise
-- (warcraft.wiki.gg, Screenshot and SCREENSHOT_SUCCEEDED).
--
-- How many frames until the new settings show: nothing in the game says. The frames after a big change are
-- slow while the game loads what it now needs, so photo mode waits as Autotune does after a render scale
-- change (Autotune.lua): until two half-second windows of frame rate agree within 3%, at least 2 seconds,
-- at most 6. It counts the frames it waited and says so on the tab.
--
-- Your settings from before are saved in EyeCandyDB.photo first. A fight, a loading screen, Esc or any other
-- Eye Candy change stops it and puts them back. It never changes settings in a fight.

local _, ns = ...
local PM = {}
ns.PhotoMode = PM

PM.PRESET = "look:screenshot"
PM.MIN, PM.MAX, PM.WINDOW, PM.AGREE = 2, 6, 0.5, 0.03
PM.SHOT_WAIT = 5 -- seconds to wait for the game to say the photo is saved
PM.FOLDER = "World of Warcraft\\_forever_\\Screenshots"

local shot -- nil, or { phase = "settle" | "shot", waited, frames, wn, wt, prevFps, left }
local busy = false -- true while photo mode itself sets values, so its own guard lets them through

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
	ns.db.photo = nil
	if not ok then error(err, 0) end
	return true
end

function PM.IsOn() return shot ~= nil end

-- One frame of the wait for the new settings. s: { waited, frames, wn, wt, prevFps }. Returns true once
-- two half-second windows agree within PM.AGREE after PM.MIN seconds, or PM.MAX seconds have gone.
function PM.Settle(s, elapsed)
	s.waited, s.frames = s.waited + elapsed, s.frames + 1
	s.wn, s.wt = s.wn + 1, s.wt + elapsed
	if s.wt >= PM.WINDOW then
		local fps = s.wn / s.wt
		local agree = s.prevFps and math.abs(fps - s.prevFps) / s.prevFps <= PM.AGREE
		s.prevFps, s.wn, s.wt = fps, 0, 0
		if agree and s.waited >= PM.MIN then return true end
	end
	return s.waited >= PM.MAX
end

local function Waited(s)
	return string.format("It waited %d frames (%.1f seconds) for the new settings.", s.frames, s.waited)
end

-- Ends the photo: the UI and your settings come back. result: "saved", "failed" or "unknown".
local function Finish(result)
	local s = shot
	shot = nil
	frame:Hide()
	if ns.IsPeeking and ns.IsPeeking() then ns.TogglePeek() end
	PutBack()
	PM.last = { frames = s.frames, seconds = s.waited, result = result }
	if result == "saved" then
		Say("done", "Photo saved at " .. date("%H:%M:%S") .. ", in " .. PM.FOLDER .. ". " .. Waited(s)
			.. " Your settings and UI are back.")
	elseif result == "failed" then
		Say("refused", "The game couldn't save the photo. Your settings and UI are back.")
	else
		Say("waiting", "The game didn't say whether the photo was saved. Look in " .. PM.FOLDER
			.. ". Your settings and UI are back.")
	end
	Tell(PM.message)
	Refresh()
end

-- Takes the photo. Returns true (it carries on by itself for a few seconds), or nil and a plain reason.
function PM.Take()
	if shot then return nil, "Photo mode is already taking a photo." end
	if InCombatLockdown() then return nil, "Not in a fight. Try again after it." end
	if type(Screenshot) ~= "function" then return nil, "This game doesn't let addons take a photo." end
	if ns.EyeTest and ns.EyeTest.IsOn() then return nil, "The eye test is on. Finish or stop it first." end
	local AT = ns.Autotune
	if AT and AT.IsRunning() then return nil, "Autotune is running. Stop it first." end
	if ns.IsPeeking and ns.IsPeeking() then return nil, "Peek is on. Press Back first." end
	if ns.IsComparing and ns.IsComparing() then
		local ok, err = ns.StopCompare()
		if not ok then return nil, err end
	end
	local values = ns.PresetValues and ns.PresetValues(PM.PRESET)
	if not values then return nil, "The Screenshot preset is missing." end
	-- Every setting on Eye Candy's list, and the preset's, so the way back covers them all.
	local before = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local v = ns.GetInfo(cvar)
		if v ~= nil then before[cvar] = v end
	end
	for cvar in pairs(values) do
		if before[cvar] == nil and ns.Exists(cvar) then before[cvar] = ns.GetInfo(cvar) end
	end
	ns.db.photo = { before = before }
	shot = { phase = "settle", waited = 0, frames = 0, wn = 0, wt = 0 }
	busy = true
	local ok, err = pcall(ns.ApplyValues, values, true)
	busy = false
	if not ok then
		shot = nil
		PutBack()
		error(err, 0)
	end
	local hid, why = ns.PeekWithoutBar()
	if not hid then
		shot = nil
		PutBack()
		return nil, (why or "Couldn't hide the game's UI.") .. " No photo was taken, and your settings are back."
	end
	Say(nil, nil)
	frame:Show()
	return true
end

-- Stops it and puts your settings back. why: shown to the player.
function PM.Stop(why)
	if not shot then return end
	local before = shot.phase == "settle"
	shot = nil
	frame:Hide()
	if ns.IsPeeking and ns.IsPeeking() then ns.TogglePeek() end
	local back = PutBack()
	local lead = "Photo mode stopped: " .. why .. ". " .. (before and "No photo was taken. " or "")
	if back then
		Say("done", lead .. "Your settings are back as they were.")
	else
		Say("waiting", lead .. "Your settings come back when the fight ends.")
	end
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
		if PM.Settle(shot, elapsed) then
			shot.phase, shot.left = "shot", PM.SHOT_WAIT
			if not pcall(Screenshot) then return Finish("failed") end
		end
	else
		shot.left = shot.left - elapsed
		if shot.left <= 0 then Finish("unknown") end
	end
end)

-- Any other Eye Candy change stops it first, so the way back stays right (as the eye test, EyeTest.lua).
for _, name in ipairs({ "ApplyAll", "ApplyValues", "CreateBackup", "TakeBackup", "NoteBeforePreset",
	"RestoreBefore", "RestoreBackupById", "UndoLastPreset" }) do
	local orig = ns[name]
	if orig then
		ns[name] = function(...)
			if shot and not busy then PM.Stop("another setting changed") end
			return orig(...)
		end
	end
end

-- Compare, Autotune and the eye test change settings too: none starts while it takes a photo.
local REFUSE = "Photo mode is taking a photo. Wait a few seconds."
local toggleCompare = ns.ToggleCompare
if toggleCompare then
	ns.ToggleCompare = function(...)
		if shot then return nil, REFUSE end
		return toggleCompare(...)
	end
end
if ns.Autotune then
	local start = ns.Autotune.Start
	ns.Autotune.Start = function(...)
		if shot then return false, REFUSE end
		return start(...)
	end
end
if ns.EyeTest then
	local start = ns.EyeTest.Start
	ns.EyeTest.Start = function(...)
		if shot then return nil, REFUSE end
		return start(...)
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
		if shot then return false end
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
	elseif event == "PLAYER_LEAVING_WORLD" or event == "PLAYER_LOGOUT" then
		if shot then PM.Stop("a loading screen") end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if saved and saved.afterCombat and not shot and PutBack() then
			Say("done", "Photo mode: the fight is over, so your settings are back as they were.")
			Tell(PM.message)
			Refresh()
		end
	elseif event == "PLAYER_ENTERING_WORLD" then
		-- Still saved at login (saved variables are only written at logout or /reload): put them back.
		if (isLogin or isReload) and saved and not shot and PutBack() then
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

PM.WHY = "One click takes a photo with the Screenshot preset and no UI on the screen. Then your settings and UI come back."
PM.HOW = "Stand where you want the photo and point the camera first. It hides the UI, waits a few seconds for the new settings, "
	.. "takes the photo and puts everything back. Expect low FPS for those seconds. A fight, a loading screen or Esc stops it."

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
	e.take = ns.Button(c, "Take photo", 110, function()
		local ok, err = PM.Take()
		if not ok and err then
			Say("refused", err)
			Refresh()
		end
	end)
	Under(e.take, e.how, 0, 8)
	ns.Tooltip(e.take, "Take photo", "Puts the Screenshot preset on, hides the UI, takes a photo, then puts your settings and UI back.")
	e.status = Text(c)
	Under(e.status, e.take, 0, 8)
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
	local height = e.headH + ROW + TextH(e.why, PM.WHY) + 8 + TextH(e.how, PM.HOW) + 8 + 24 + 8 + TextH(e.status, status)
	e.content:SetHeight(height + 16)
end

if ns.AddExperiment then
	ns.AddExperiment({
		key = "photo", name = "Photo mode", build = Build, refresh = Refresh_,
		tip = "One click: a photo with the Screenshot preset and no UI, then everything back.",
	})
end
