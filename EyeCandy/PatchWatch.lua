-- Eye Candy: a warning when settings change while the game is closed (a game patch, say: the one on
-- 14 November 2026 held render scale at 100%).
--
-- At logout and /reload (PLAYER_LOGOUT, just before saved data is written: warcraft.wiki.gg) it keeps a
-- copy of every setting on Eye Candy's list, as your own values: Compare's "now", not "before"; the
-- settings from before Autotune, not its test values; your own values, not the city switch's lowered ones.
-- At the next login it compares. A change made during play is already in the copy, so only a change made
-- while the game was closed counts. If there is none, nothing shows. If there are some, one small window
-- lists them, with Put them back and Keep the game's. Put them back never runs in a fight and takes no
-- backup. It reads each one back and says, in red, any the game kept.
--
-- No false alarms (each checked, see tests/test_patch_watch.py):
--   first login after install   no copy yet: nothing shows
--   another PC                  saved data is on each PC, so its copy is its own. A copied settings folder
--                               on a PC with another graphics card: nothing shows
--   another WoW account         graphics settings are shared by the PC's accounts. The copy carries a token,
--                               also kept in a registered CVar (it lasts across a relog, not a game close:
--                               warcraft.wiki.gg C_CVar.RegisterCVar). Another token there: another account
--                               logged out last, so nothing shows
--   stored on the server        a setting that follows the account or character (C_CVar.GetCVarInfo's third
--                               and fourth returns) can change on another PC: never counted
--   rewritten at every start    the same change as last time (by the game or another addon at start):
--                               shown once, then never again
--   a /reload before the check  the old copy is kept, and the reload checks instead
-- Unconfirmed: whether the game keeps a setting changed in a session that ended in a crash. Saved data is
-- only written on logout or /reload, so the copy is older then, and such a change may show once.
--
-- Saved: EyeCandyDB.patchWatch = { snap = { values, machine, token }, seen = { [cvar] = { was, now } },
-- pending = true while the login check hasn't run }.

local _, ns = ...

local PW = {}
ns.PatchWatch = PW

local TOKEN_CVAR = "eyeCandyWatch"
-- After Eye Candy's login re-apply (4 s, Core.lua), the city switch (2 s, Situations.lua) and Compare's
-- second put-back (4 s, Compare.lua), so what is compared is what stays.
PW.WAIT = 8
PW.MAX_LINES = 8

if C_CVar and C_CVar.RegisterCVar then pcall(C_CVar.RegisterCVar, TOKEN_CVAR, "") end

local function DB()
	if not ns.db then return nil end
	if type(ns.db.patchWatch) ~= "table" then ns.db.patchWatch = {} end
	return ns.db.patchWatch
end

local function Plural(n, one, many)
	return n == 1 and one or many
end

-- Your own value for a setting: Compare's "now" while "before" shows, the value from before Autotune
-- while it has your settings, and your value under the city switch's lowered one.
function PW.Own(cvar, value)
	if value == nil then return nil end
	local db = ns.db or {}
	local cmp, at = db.compare, db.autotune
	if type(cmp) == "table" and type(cmp.now) == "table" and cmp.now[cvar] ~= nil then
		value = cmp.now[cvar]
	elseif type(at) == "table" and type(at.before) == "table" and at.before[cvar] ~= nil then
		value = at.before[cvar]
	end
	if ns.SituationValue then value = ns.SituationValue(cvar, value) end
	return tostring(value)
end

-- Every setting on Eye Candy's list, as your own values.
function PW.Values()
	local values = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local v = PW.Own(cvar, (ns.GetInfo(cvar)))
		if v ~= nil then values[cvar] = v end
	end
	return values
end

-- The graphics cards, so a copy from another PC is never compared with this one.
function PW.Machine()
	local names = {}
	local get = C_VideoOptions and C_VideoOptions.GetGxAdapterInfo
	local ok, list = false, nil
	if type(get) == "function" then ok, list = pcall(get) end
	if ok and type(list) == "table" then
		for _, a in ipairs(list) do
			if type(a) == "table" and a.name then names[#names + 1] = tostring(a.name) end
		end
	end
	table.sort(names)
	return table.concat(names, "|")
end

-- A setting stored on the server follows the account or character, so it can change on another PC.
local function OnServer(cvar)
	if not (C_CVar and C_CVar.GetCVarInfo) then return false end
	local ok, _, _, account, character = pcall(C_CVar.GetCVarInfo, cvar)
	return ok and (account == true or character == true)
end

-- old, now: { [cvar] = value }. order: the cvars to look at, in order (a repeat is skipped).
-- seen: the changes found last time. skip(cvar): true to leave a setting out.
-- Returns the changes to show, in order ({ cvar, was, now }), and every change found ({ [cvar] = { was, now } }).
function PW.Diff(old, now, order, seen, skip)
	local show, all, done = {}, {}, {}
	for _, cvar in ipairs(order) do
		local was, is = old[cvar], now[cvar]
		if not done[cvar] and was ~= nil and is ~= nil and not ns.Same(was, is) and not (skip and skip(cvar)) then
			done[cvar] = true
			all[cvar] = { was = was, now = is }
			local s = type(seen) == "table" and seen[cvar]
			if not (type(s) == "table" and ns.Same(s.was, was) and ns.Same(s.now, is)) then
				show[#show + 1] = { cvar = cvar, was = was, now = is }
			end
		end
	end
	return show, all
end

----------------------------------------------------------------------
-- Names and values, as the tabs show them
----------------------------------------------------------------------

function PW.Name(cvar)
	local row = ns.StandardRow and ns.StandardRow(cvar)
	local text = row and row.label and ns.StandardText and ns.StandardText(row.label)
	if text then return text end
	local d = ns.ADVANCED_BY_CVAR and ns.ADVANCED_BY_CVAR[cvar]
	if d then return d[2] end
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, r in ipairs(cat.cvars) do
			if r[1] == cvar then return r[2] end
		end
	end
	for _, ex in ipairs(ns.EXTRAS) do
		if ex.cvar == cvar then return ex.name end
	end
	return cvar
end

function PW.Format(cvar, value)
	local row = ns.StandardRow and ns.StandardRow(cvar)
	if row and row.kind ~= "info" and ns.FormatStandard then return ns.FormatStandard(row, value) end
	local d = ns.ADVANCED_BY_CVAR and ns.ADVANCED_BY_CVAR[cvar]
	if d and d.kind == "toggle" then return ns.Same(value, 1) and "On" or "Off" end
	return ns.FormatNumber(tonumber(value) or value)
end

----------------------------------------------------------------------
-- The window
----------------------------------------------------------------------

local frame
local LINE_H = 16

local function Build(n)
	local height = 32 + 24 + n * LINE_H + 8 + 2 * LINE_H + 8 + 38
	frame = ns.MakeWindow("EyeCandyPatchFrame", 420, height, "Eye Candy")
	frame.head = ns.Label(frame, "", "GameFontHighlight")
	frame.head:SetPoint("TOPLEFT", 18, -32)
	frame.head:SetWidth(384)
	frame.lines = {}
	frame.result = ns.Label(frame, "")
	frame.result:SetWidth(384)
	frame.result:SetWordWrap(false)
	frame.refused = ns.Label(frame, "")
	frame.refused:SetPoint("TOPLEFT", frame.result, "BOTTOMLEFT", 0, -4)
	frame.refused:SetWidth(384)
	frame.refused:SetWordWrap(false)

	frame.keep = ns.Button(frame, "Keep the game's", 130, function() PW.Keep() end)
	frame.keep:SetPoint("BOTTOMRIGHT", -16, 14)
	ns.Tooltip(frame.keep, "Keep the game's", "Changes nothing. The settings stay as the game set them.", "ANCHOR_LEFT")
	frame.back = ns.Button(frame, "Put them back", 130, function() PW.PutBack() end)
	frame.back:SetPoint("RIGHT", frame.keep, "LEFT", -8, 0)
	ns.Tooltip(frame.back, "Put them back",
		"Sets each one back to what it was when you last logged out. Takes no backup.", "ANCHOR_LEFT")
	frame.close = ns.Button(frame, "Close", 100, function() frame:Hide() end)
	frame.close:SetPoint("BOTTOMRIGHT", -16, 14)
	frame.close:Hide()

	if ns.PEEK_WINDOWS then tinsert(ns.PEEK_WINDOWS, "EyeCandyPatchFrame") end
end

local function Line(i)
	local fs = frame.lines[i]
	if not fs then
		fs = ns.Label(frame, "")
		fs:SetPoint("TOPLEFT", 26, -32 - 24 - (i - 1) * LINE_H)
		fs:SetWidth(376)
		fs:SetWordWrap(false)
		frame.lines[i] = fs
	end
	return fs
end

-- kind: "done" (normal), "waiting" (grey). refused: names the game kept, shown in red under it.
local function Say(kind, text, refused)
	frame.result:SetText(text and (kind == "waiting" and ("|cff9d9d9d" .. text .. "|r") or text) or "")
	frame.refused:SetText(refused and ("|cffff4040" .. refused .. "|r") or "")
end

function PW.Show(list)
	PW.list, PW.queued = list, false
	local n = #list
	local listed = math.min(n, PW.MAX_LINES + (n == PW.MAX_LINES + 1 and 1 or 0))
	local rows = listed + (n > listed and 1 or 0)
	if not frame then Build(rows) else frame:SetSize(420, 32 + 24 + rows * LINE_H + 8 + 2 * LINE_H + 8 + 38) end
	frame.head:SetText(string.format("The game changed %d %s since you last played. %s",
		n, Plural(n, "setting", "settings"), Plural(n, "Put it back?", "Put them back?")))
	for _, fs in ipairs(frame.lines) do fs:Hide() end
	for i = 1, listed do
		local c = list[i]
		local fs = Line(i)
		fs:SetText(string.format("%s: was %s, now %s", ns.ShortName(PW.Name(c.cvar), 32),
			PW.Format(c.cvar, c.was), PW.Format(c.cvar, c.now)))
		fs:Show()
	end
	if n > listed then
		local fs = Line(listed + 1)
		fs:SetText(string.format("And %d more.", n - listed))
		fs:Show()
	end
	frame.result:SetPoint("TOPLEFT", 18, -32 - 24 - rows * LINE_H - 8)
	Say(nil, nil, nil)
	frame.back:SetText(Plural(n, "Put it back", "Put them back"))
	frame.back:Show()
	frame.keep:Show()
	frame.close:Hide()
	frame:Show()
	frame:Raise()
end

function PW.Keep()
	PW.queued = false
	PW.list = nil
	if frame then frame:Hide() end
end

-- Sets each change back, reads it back, and says how many went back and which the game kept.
function PW.PutBack()
	local list = PW.list
	if not (list and frame) then return false end
	if InCombatLockdown() then
		PW.queued = true
		frame.back:Hide()
		Say("waiting", "Waiting for the fight to end. Then " .. Plural(#list, "it goes", "they go") .. " back.")
		return false
	end
	PW.queued = false
	local values = {}
	for _, c in ipairs(list) do values[c.cvar] = c.was end
	-- Menu values step down to what the graphics card supports and render scale stays in the game's range
	-- (ns.ApplyValues with its options). In a city, the switch lowers again what this raised.
	local function Go() ns.ApplyValues(values, true) end
	if ns.KeepSituationLowered then ns.KeepSituationLowered(Go) else Go() end
	local back, kept = 0, {}
	for _, c in ipairs(list) do
		local now = PW.Own(c.cvar, (ns.GetInfo(c.cvar)))
		if now ~= nil and ns.Same(now, c.was) then
			back = back + 1
		else
			kept[#kept + 1] = PW.Name(c.cvar) .. " at " .. (now ~= nil and PW.Format(c.cvar, now) or "nothing")
		end
	end
	PW.list = nil
	Say("done", back > 0 and string.format("Put back %d %s.", back, Plural(back, "setting", "settings")) or nil,
		#kept > 0 and ("The game kept " .. table.concat(kept, ", ") .. ".") or nil)
	frame.back:Hide()
	frame.keep:Hide()
	frame.close:Show()
	frame:Show()
	if ns.RefreshUI then ns.RefreshUI() end
	return true
end

----------------------------------------------------------------------
-- Login and logout (called from Core.lua's events)
----------------------------------------------------------------------

local due = false -- the check waits for a fight to end

-- Compares the copy from the last logout with now. Returns the changes shown, or nil.
function PW.Check()
	local db = DB()
	if not db then return nil end
	db.pending = nil
	local snap = db.snap
	if type(snap) ~= "table" or type(snap.values) ~= "table" then return nil end
	if snap.machine and snap.machine ~= PW.Machine() then return nil end
	local token = GetCVar(TOKEN_CVAR)
	if token and token ~= "" and snap.token and token ~= snap.token then return nil end
	local show, all = PW.Diff(snap.values, PW.Values(), ns.AllManagedCVars(), db.seen, OnServer)
	db.seen = all
	if #show > 0 then PW.Show(show) end
	return show
end

local function CheckSoon(delay)
	C_Timer.After(delay, function()
		if InCombatLockdown() then
			due = true
		else
			PW.Check()
		end
	end)
end

function ns.PatchWatchLogin(isLogin, isReload)
	local db = DB()
	if not db then return end
	if isLogin then db.pending = true end
	if db.pending and (isLogin or isReload) then CheckSoon(PW.WAIT) end
end

function ns.PatchWatchLogout()
	local db = DB()
	if not db then return end
	-- The login check hasn't run (a /reload in the first seconds): keep the copy it compares with.
	if db.pending and db.snap then return end
	local token = tostring(time()) .. "-" .. tostring(math.random(100000, 999999))
	db.snap = { values = PW.Values(), machine = PW.Machine(), token = token }
	if C_CVar and C_CVar.SetCVar then pcall(C_CVar.SetCVar, TOKEN_CVAR, token) end
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:SetScript("OnEvent", function()
	if due then
		due = false
		-- After Autotune puts your settings back once the fight ends (Autotune.lua).
		CheckSoon(2)
	end
	if PW.queued then PW.PutBack() end
end)
