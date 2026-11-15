-- Eye Candy: Compare. Flips the live settings between "before" (the settings from just before the
-- last preset, the same record Back to before uses) and "now", so you can see the difference in the same spot.
-- It takes no backup per flip and never changes Eye Candy's own choices (ns.db tiers, extras, dials).
-- Ending always lands on "now": StopCompare, combat, logout and /reload. If the game closes while
-- "before" is showing, EyeCandyDB.compare holds "now" and the next load puts it back.

local ADDON, ns = ...

local state -- nil when not comparing: { before, now, shown, label, showing = "before" | "now" }
local pendingFinish = false -- combat had already locked settings when compare had to end

local function Capture()
	local values = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local value = ns.GetInfo(cvar)
		if value ~= nil then values[cvar] = tostring(value) end
	end
	return values
end

local function Copy(t)
	local out = {}
	for k, v in pairs(t or {}) do out[k] = v end
	return out
end

-- How many of a's settings differ from b (settings b doesn't have are not counted).
local function CountDiff(a, b)
	local n = 0
	for cvar, value in pairs(a) do
		if b[cvar] ~= nil and not ns.Same(value, b[cvar]) then n = n + 1 end
	end
	return n
end

-- The "before" record (Backups.lua), if it differs from now, keeping only settings Eye Candy manages
-- today. Returns the record and its values, or nil and whether there was a record at all.
local function FindBefore(now)
	local b = ns.BeforeRecord and ns.BeforeRecord()
	if not b then return nil, false end
	local values = {}
	for cvar, value in pairs(b.values) do
		if now[cvar] ~= nil then values[cvar] = tostring(value) end
	end
	if CountDiff(values, now) > 0 then return b, values end
	return nil, true
end

-- A setting that differs from what Compare last put there was changed by the player (a slider, a
-- preset): it joins "now", so ending compare keeps it.
local function MergeChanges()
	local live = Capture()
	for cvar, value in pairs(live) do
		local shown = state.shown[cvar]
		if shown ~= nil and not ns.Same(value, shown) then state.now[cvar] = value end
	end
end

-- Redraw what shows the compare state: the main window's button and title, and the Peek bar.
local function Changed()
	if ns.RefreshUI then ns.RefreshUI() end
	if ns.RefreshPeekBar then ns.RefreshPeekBar() end
end

local function Show(side)
	ns.ApplyValues(state[side], false)
	state.showing = side
	state.shown = Capture() -- what the game really holds now (it can clamp a value)
	if side == "before" then
		ns.db.compare = { now = Copy(state.now), label = state.label }
	else
		ns.db.compare = nil
	end
	Changed()
end

local function Saved()
	local saved = ns.db and ns.db.compare
	if type(saved) == "table" and type(saved.now) == "table" then return saved end
end

-- Put "now" back and stop: a compare running now, or one left in the saved data when the game
-- closed on "before". Returns false if combat already locked settings (it finishes after the fight).
local function Finish()
	if not state and not Saved() then
		pendingFinish = false
		return true
	end
	if InCombatLockdown() then
		pendingFinish = true
		return false
	end
	pendingFinish = false
	if state then
		MergeChanges()
		if state.showing == "before" then Show("now") end
		state = nil
	else
		ns.ApplyValues(Saved().now, false)
	end
	if ns.db then ns.db.compare = nil end
	Changed()
	return true
end

-- A backup, a preset's "before" record or a restore while "before" is showing would record "before"
-- as your settings. End compare on "now" first. Every caller looks these up on ns when it runs, so
-- wrapping them here covers presets, imports, Back and restores without touching Backups.lua.
-- when (optional) says from the call's own arguments whether to end first.
local function EndFirst(name, when)
	local original = ns[name]
	if type(original) ~= "function" then return end
	ns[name] = function(...)
		if state and (not when or when(...)) then Finish() end
		return original(...)
	end
end
EndFirst("CreateBackup")
EndFirst("RestoreBackupById")
EndFirst("NoteBeforePreset")
EndFirst("RestoreBefore")
-- Back checks nothing changed since the preset, and "before" on screen is a change: end first.
EndFirst("UndoLastPreset")
-- Apply (not the hidden-only re-apply that keeps your settings applied) ends it too, as it did when
-- Apply took a backup.
EndFirst("ApplyAll", function(onlyHidden) return not onlyHidden end)

-- Starts compare on "before", or flips between "before" and "now". Returns true, or nil and a plain reason.
function ns.ToggleCompare()
	if InCombatLockdown() then
		return nil, "Can't compare in combat. Try again after the fight."
	end
	if pendingFinish then Finish() end
	if state then
		MergeChanges()
		Show(state.showing == "before" and "now" or "before")
		return true
	end
	local now = Capture()
	local before, values = FindBefore(now)
	if not before then
		if values then
			return nil, "Nothing to compare: your settings are the same as before your last preset."
		end
		return nil, "Nothing to compare yet. Apply a preset first, then Compare flips between before and after."
	end
	state = {
		before = values, now = now, shown = now,
		label = before.name and ("before " .. before.name) or "before your last preset",
	}
	Show("before")
	return true
end

-- Ends compare on "now". Returns true, or nil and a plain reason (combat: it ends after the fight).
function ns.StopCompare()
	if not Finish() then
		return nil, "Can't change settings in combat. They go back to now after the fight."
	end
	return true
end

function ns.IsComparing()
	return state ~= nil
end

-- "Showing: before Raid & PvP" or "Showing: now". nil when not comparing.
function ns.CompareLabel()
	if not state then return nil end
	if state.showing == "before" then return "Showing: " .. state.label end
	return "Showing: now"
end

function ns.CompareSlash(msg)
	if msg == "compare stop" or msg == "compare off" then
		local wasOn = state ~= nil
		local ok, err = ns.StopCompare()
		if not ok then
			ns.Print(err)
		elseif wasOn then
			ns.Print("compare ended. Showing: now.")
		else
			ns.Print("compare isn't on.")
		end
		return
	end
	local ok, err = ns.ToggleCompare()
	if not ok then
		ns.Print(err)
		return
	end
	ns.Print(ns.CompareLabel() .. ". Type /ec compare to flip, /ec compare stop to end on now.")
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("PLAYER_REGEN_DISABLED")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:RegisterEvent("PLAYER_LOGOUT")
events:SetScript("OnEvent", function(_, event)
	if event == "PLAYER_LOGIN" then
		-- The game closed (or /reload'ed in combat) while "before" was showing: put "now" back at once,
		-- and again once the game settles, because account settings from the server can land a moment
		-- after login (the same 4 second wait as Core.lua's login re-apply). The flag stays until then.
		-- In combat it all waits for PLAYER_REGEN_ENABLED.
		-- Not covered: a crash while "before" shows. Saved data is only written on logout or /reload,
		-- so "now" is lost then (unconfirmed whether the game keeps the "before" values after a crash).
		local saved = not state and Saved()
		if saved and not InCombatLockdown() then
			ns.ApplyValues(saved.now, false)
			C_Timer.After(4, function()
				if not state and Saved() and Finish() then
					ns.Print("put your settings back to now. Compare was still showing before when the game closed.")
				end
			end)
		elseif saved then
			pendingFinish = true
		end
	elseif event == "PLAYER_REGEN_DISABLED" then
		-- Lockdown starts just after this event, so settings can still change here.
		if state then
			if Finish() then
				ns.Print("combat started, so compare ended. Showing: now.")
			else
				ns.Print("combat started, so compare ends after the fight.")
			end
		end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if pendingFinish then Finish() end
	elseif event == "PLAYER_LOGOUT" then
		-- Logout and /reload. In combat the saved "now" stays, with any change made since, and the
		-- next load puts it back.
		if state and InCombatLockdown() then
			MergeChanges()
			if state.showing == "before" then ns.db.compare = { now = Copy(state.now), label = state.label } end
		elseif state then
			Finish()
		end
	end
end)
