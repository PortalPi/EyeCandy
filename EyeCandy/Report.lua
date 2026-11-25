-- Eye Candy: /ec report
-- Builds one text block a player can paste into the GitHub bug form or a CurseForge comment: addon version,
-- game build, current settings (the same text as /ec export) and the recent
-- Lua errors that mention Eye Candy.
--
-- Errors are caught by wrapping the game's error handler (geterrorhandler /
-- seterrorhandler). Checked in Gethe/wow-ui-source, branch "forever", on 15 Nov 2026:
-- Blizzard_ScriptErrors installs its own handler with seterrorhandler at start-up
-- (before any addon loads), and Blizzard code still calls geterrorhandler(). Both are
-- plain globals with no secure check. Messages can be secret values when code is
-- tainted, so we test them before touching them.
--
-- Limits, said in the report itself: errors from before Eye Candy loaded are not seen,
-- and an error addon that replaces the handler after us without passing errors on
-- hides them from us.
local _, ns = ...

local MAX_ERRORS = 10      -- distinct errors kept
local MAX_MESSAGE = 600    -- characters kept per message
local MAX_STACK_LINES = 6  -- stack lines kept per error

local errors = {}          -- newest last: { text = "...", count = n }
local installed = false
local handler = nil        -- our wrapper, so the report can say if it is still the game's handler
local seen = 0             -- every error the handler was given
local unreadable = 0       -- of those, secret or not text

local function Readable(v)
	if type(issecretvalue) == "function" and issecretvalue(v) then return false end
	if type(canaccessvalue) == "function" and not canaccessvalue(v) then return false end
	return true
end

local function Mentions(text)
	local lower = text:lower()
	return lower:find("eyecandy", 1, true) ~= nil or lower:find("eye candy", 1, true) ~= nil
end

local function ShortStack()
	if type(debugstack) ~= "function" then return "" end
	-- Ask for plenty of lines: the first few are our own wrapper, dropped below.
	local ok, stack = pcall(debugstack, 2, 20, 0)
	if not ok or type(stack) ~= "string" or not Readable(stack) then return "" end
	-- Our own wrapper is on the stack of every error, so drop its lines. Otherwise every
	-- addon's error would look like ours.
	local kept = {}
	for line in stack:gmatch("[^\n]+") do
		local lower = line:lower()
		local ours = lower:find("eyecandy[\\/]report%.lua") ~= nil
		local pcallFrame = lower:find("^%[c%]:.-pcall") ~= nil
		if not ours and not pcallFrame and #kept < MAX_STACK_LINES then kept[#kept + 1] = line end
	end
	return table.concat(kept, "\n")
end

-- Called with the text of every Lua error. Never raises.
function ns.RecordError(message)
	seen = seen + 1
	pcall(function()
		if type(message) ~= "string" or not Readable(message) then
			unreadable = unreadable + 1
			return
		end
		local stack = ShortStack()
		if not (Mentions(message) or Mentions(stack)) then return end
		local text = message:sub(1, MAX_MESSAGE)
		if stack ~= "" then text = text .. "\n" .. stack end
		for i, e in ipairs(errors) do
			if e.text == text then
				e.count = e.count + 1
				table.remove(errors, i)
				errors[#errors + 1] = e
				return
			end
		end
		errors[#errors + 1] = { text = text, count = 1 }
		if #errors > MAX_ERRORS then table.remove(errors, 1) end
	end)
end

function ns.InstallErrorCapture()
	if installed then return true end
	if type(geterrorhandler) ~= "function" or type(seterrorhandler) ~= "function" then return false end
	local ok = pcall(function()
		local previous = geterrorhandler()
		handler = function(message, ...)
			ns.RecordError(message)
			if previous then return previous(message, ...) end
		end
		seterrorhandler(handler)
	end)
	installed = ok
	return ok
end

function ns.CapturedErrors()
	return errors
end

-- One line saying whether capture is working: is our wrapper still the game's error
-- handler, and how many errors did it get. A "no" means another addon replaced it.
local function CaptureCheck()
	local ok, current = pcall(geterrorhandler)
	local ours = ok and handler ~= nil and current == handler
	return string.format("  Check: Eye Candy is still the game's error handler: %s. Errors it was given: %d (%d unreadable).",
		ours and "yes" or "NO", seen, unreadable)
end

local function AddonVersion()
	local get = (C_AddOns and C_AddOns.GetAddOnMetadata) or GetAddOnMetadata
	local ok, version = false, nil
	if type(get) == "function" then ok, version = pcall(get, "EyeCandy", "Version") end
	return (ok and version) or "unknown"
end

----------------------------------------------------------------------
-- Settings that changed since login, and who changed them
----------------------------------------------------------------------
-- A picture that goes wrong after a loading screen could be the game, or Eye Candy changing a setting
-- by itself on the way. hooksecurefunc on SetCVar and C_CVar.SetCVar sees every change made from Lua
-- (Eye Candy's, the game menu's, other addons') without tainting the callers. The game engine's own
-- changes don't go through Lua, so they are not seen; the report says so.

local MAX_CHANGES = 15
local changes = {}         -- newest last: { at = seconds, cvar = name, value = text, ours = bool } or { at, loading = true }
local hooked = false
local started = nil
local watched = nil        -- set of CVar names the report lists, built on first use (Data.lua loads later)

local function Now()
	if type(GetTime) ~= "function" then return 0 end
	local ok, t = pcall(GetTime)
	if not ok or type(t) ~= "number" then return 0 end
	started = started or t
	return t - started
end

local function Watched(cvar)
	-- CVar names ignore case in the game, so the lists are kept in lower case.
	if not watched then
		if not ns.CATEGORIES then return false end -- Data.lua not loaded yet: build the list later
		watched = {}
		for _, cat in ipairs(ns.CATEGORIES) do
			for _, row in ipairs(cat.cvars or {}) do watched[row[1]:lower()] = true end
		end
		for _, ex in ipairs(ns.EXTRAS or {}) do if ex.cvar then watched[ex.cvar:lower()] = true end end
		for _, cvar in ipairs(ns.EXPORT_EXTRA or {}) do watched[cvar:lower()] = true end
	end
	local lower = cvar:lower()
	if watched[lower] then return true end
	if ns.db and type(ns.db.advanced) == "table" then
		for name in pairs(ns.db.advanced) do
			if type(name) == "string" and name:lower() == lower then return true end
		end
	end
	return false
end

-- true when Eye Candy (not this file) is on the stack of the change.
local function OursOnStack()
	if type(debugstack) ~= "function" then return false end
	local ok, stack = pcall(debugstack, 2, 30, 0)
	if not ok or type(stack) ~= "string" or not Readable(stack) then return false end
	for line in stack:gmatch("[^\n]+") do
		local lower = line:lower()
		if lower:find("eyecandy[\\/]") and not lower:find("eyecandy[\\/]report%.lua") then return true end
	end
	return false
end

local function Add(entry)
	changes[#changes + 1] = entry
	if #changes > MAX_CHANGES then table.remove(changes, 1) end
end

local function OnSet(cvar, value)
	pcall(function()
		if type(cvar) ~= "string" or not Readable(cvar) or not Readable(value) or not Watched(cvar) then return end
		local text = tostring(value)
		local at = Now()
		-- SetCVar may call C_CVar.SetCVar, so one change can be seen twice.
		local last = changes[#changes]
		if last and last.cvar == cvar and last.value == text and at - last.at < 1 then return end
		Add({ at = at, cvar = cvar, value = text, ours = OursOnStack() })
	end)
end

function ns.WatchSettingChanges()
	if hooked or type(hooksecurefunc) ~= "function" then return hooked end
	Now()
	local okA = type(SetCVar) == "function" and pcall(hooksecurefunc, "SetCVar", OnSet)
	local okB = type(C_CVar) == "table" and type(C_CVar.SetCVar) == "function" and pcall(hooksecurefunc, C_CVar, "SetCVar", OnSet)
	hooked = (okA or okB) and true or false
	return hooked
end

local loadingFrame = CreateFrame("Frame")
pcall(loadingFrame.RegisterEvent, loadingFrame, "PLAYER_LEAVING_WORLD")
loadingFrame:SetScript("OnEvent", function(_, event)
	if hooked and event == "PLAYER_LEAVING_WORLD" then pcall(Add, { at = Now(), loading = true }) end
end)

local function OnOff(v) return v and "on" or "off" end

local function ChangesSection(buf)
	buf[#buf + 1] = "--- Settings changed since login (newest last) ---"
	local db = ns.db or {}
	local steady = ns.SteadyFPS and ns.SteadyFPS.IsOn and ns.SteadyFPS.IsOn()
	buf[#buf + 1] = string.format("  Eye Candy by itself: keep applied %s, city switch %s, instance switch %s, Steady FPS %s. Lowered now: %s.",
		OnOff(db.keepApplied), OnOff(ns.IsAutoSituationOn and ns.IsAutoSituationOn("city")),
		OnOff(ns.IsAutoSituationOn and ns.IsAutoSituationOn("raid")), OnOff(steady),
		(ns.ActiveSituationName and ns.ActiveSituationName()) or "none")
	if not hooked then
		buf[#buf + 1] = "  (not watched: this client has no hooksecurefunc)"
		return
	end
	if #changes == 0 then buf[#buf + 1] = "  (none seen)" end
	for _, c in ipairs(changes) do
		if c.loading then
			buf[#buf + 1] = string.format("  %6ds  loading screen", math.floor(c.at))
		else
			buf[#buf + 1] = string.format("  %6ds  %-30s %-10s by %s", math.floor(c.at), c.cvar, c.value, c.ours and "Eye Candy" or "the game or another addon")
		end
	end
	buf[#buf + 1] = "  Not seen: changes the game engine makes without Lua. Only the last " .. MAX_CHANGES .. " are kept."
end

function ns.BuildReport()
	local buf = {}
	buf[#buf + 1] = "=== Eye Candy bug report ==="
	buf[#buf + 1] = "Addon: Eye Candy " .. tostring(AddonVersion())
	buf[#buf + 1] = ""
	buf[#buf + 1] = "--- Lua errors that mention or pass through Eye Candy (since you logged in) ---"
	if not installed then
		buf[#buf + 1] = "  (error capture is off: this client has no seterrorhandler)"
	elseif #errors == 0 then
		buf[#buf + 1] = "  (none caught)"
	else
		for i = #errors, 1, -1 do
			local e = errors[i]
			buf[#buf + 1] = string.format("  [%dx] %s", e.count, (e.text:gsub("\n", "\n        ")))
		end
	end
	if installed then buf[#buf + 1] = CaptureCheck() end
	buf[#buf + 1] = "  Not seen: errors from before Eye Candy loaded, or hidden by another error addon."
	buf[#buf + 1] = ""
	if ns.RenderCap and ns.RenderCap.ReportLine then
		local ok, line = pcall(ns.RenderCap.ReportLine)
		if ok and line then
			buf[#buf + 1] = line
			buf[#buf + 1] = ""
		end
	end
	if ns.MinimapReportLine then
		local ok, line = pcall(ns.MinimapReportLine)
		if ok and line then
			buf[#buf + 1] = line
			buf[#buf + 1] = ""
		end
	end
	pcall(ChangesSection, buf)
	buf[#buf + 1] = ""
	buf[#buf + 1] = ns.BuildExport(false)
	return table.concat(buf, "\n")
end

function ns.ShowReport()
	ns.ShowText(ns.BuildReport(), ns.REPORT_HINT)
	ns.Print("Bug report ready. Copy it with Ctrl+C, then paste it into the bug form on GitHub or a comment on CurseForge.")
end

ns.InstallErrorCapture()
ns.WatchSettingChanges()
