-- Eye Candy: /ec report
-- Builds one text block a player can paste into the GitHub bug form: addon version,
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
	buf[#buf + 1] = ns.BuildExport(false)
	return table.concat(buf, "\n")
end

function ns.ShowReport()
	ns.ShowText(ns.BuildReport())
	ns.Print("Bug report ready. Copy it with Ctrl+C, then paste it into the bug form on GitHub.")
end

ns.InstallErrorCapture()
