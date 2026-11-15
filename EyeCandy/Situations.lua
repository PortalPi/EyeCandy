-- Eye Candy: switch for a Situation by itself. Off until you turn it on (/ec city).
--
-- In a capital city, the settings that cost most in a crowd (a Situation's auto.caps in Data.lua) come
-- down on top of your own, and only where yours are higher. Nothing else changes and no backup is taken.
-- When you leave, each one goes back to what it was, unless you changed it yourself while you were there.
-- Never in combat: a switch waits until the fight ends.
--
-- Saved: EyeCandyDB.autoSituations[key] = true (on), EyeCandyDB.situationActive = { key, set } where
-- set[cvar] = { was = your value, now = the value Eye Candy set }. Kept across a reload or logout, so a
-- logout in a city still puts your settings back on the next login outside it.
--
-- Backups, saved presets and Back see your own values, not the lowered ones: ns.SituationValue.

local _, ns = ...

-- Enum.UIMapFlag.IsCityMap (Blizzard_APIDocumentationGenerated/MapConstantsDocumentation.lua, forever
-- branch). There is no "City" map type: a city is a Zone with this flag.
local CITY_FLAG = 1048576
local ZONE_TYPE = 3 -- Enum.UIMapType.Zone; Continent, World and Cosmic are lower

-- Retail map ids for the capitals (warcraft.wiki.gg UiMapID). Unconfirmed in Forever, which may use
-- its own ids: the city flag and "sanctuary" are checked as well.
local KNOWN_CITIES = {
	[84] = true,  -- Stormwind
	[85] = true,  -- Orgrimmar
	[87] = true,  -- Ironforge
	[88] = true,  -- Thunder Bluff
	[89] = true,  -- Darnassus
	[90] = true,  -- Undercity
	[103] = true, -- The Exodar
	[110] = true, -- Silvermoon
	[111] = true, -- Shattrath
	[125] = true, -- Dalaran (Northrend)
	[501] = true, -- Dalaran (Eastern Kingdoms)
}

local function HasFlag(flags, flag)
	flags = tonumber(flags)
	return flags ~= nil and math.floor(flags / flag) % 2 == 1
end

-- true in a capital city, false outside one, nil while the game can't say (just after a loading screen).
-- A "sanctuary" (C_PvP.GetZonePVPInfo; the bare GetZonePVPInfo is gone) counts: those are the big
-- neutral hubs. Unconfirmed which zones Forever marks as one.
function ns.InCapitalCity()
	if IsInInstance and IsInInstance() then return false end
	if C_PvP and C_PvP.GetZonePVPInfo and C_PvP.GetZonePVPInfo() == "sanctuary" then return true end
	if not (C_Map and C_Map.GetBestMapForUnit and C_Map.GetMapInfo) then return false end
	local id = C_Map.GetBestMapForUnit("player")
	if not id then return nil end
	-- A district or building inside a city is its own map: walk up to the zone.
	for _ = 1, 10 do
		if KNOWN_CITIES[id] then return true end
		local info = C_Map.GetMapInfo(id)
		if not info then return false end
		if HasFlag(info.flags, CITY_FLAG) then return true end
		if not info.mapType or info.mapType <= ZONE_TYPE or not info.parentMapID or info.parentMapID == 0 then
			return false
		end
		id = info.parentMapID
	end
	return false
end

local TESTS = { city = ns.InCapitalCity }

local function Find(key)
	for _, s in ipairs(ns.SITUATIONS or {}) do
		if s.key == key and s.auto then return s end
	end
end

local function Active()
	local st = ns.db and ns.db.situationActive
	if type(st) ~= "table" then return nil end
	if type(st.set) ~= "table" then st.set = {} end
	return st
end

function ns.IsAutoSituationOn(key)
	return ns.db ~= nil and type(ns.db.autoSituations) == "table" and ns.db.autoSituations[key] == true
end

-- The name of the Situation switched on by itself right now, or nil.
function ns.ActiveSituationName()
	local st = Active()
	local s = st and Find(st.key)
	return s and s.name or nil
end

-- Your own value for a setting the switch has lowered, else value. Backups, saved presets and Back's
-- "has anything changed" use this, so none of them records the lowered values as yours.
function ns.SituationValue(cvar, value)
	local st = Active()
	local r = st and st.set[cvar]
	if type(r) == "table" and r.was ~= nil and ns.Same(value, r.now) then return r.was end
	return value
end

-- Lowers each cap where the setting is higher. Records what it was, so leaving can put it back.
-- only (optional): a set of CVars to look at.
local function Lower(s, set, only)
	local n = 0
	for cvar, cap in pairs(s.auto.caps) do
		local now = ns.GetInfo(cvar)
		if tonumber(now) and tonumber(now) > cap + 0.001 and (not only or only[cvar]) then
			SetCVar(cvar, cap)
			local after = ns.GetInfo(cvar)
			if not ns.Same(after, now) then
				set[cvar] = { was = now, now = after }
				n = n + 1
			end
		end
	end
	return n
end

local function Plural(n, one, many)
	return n == 1 and one or many
end

local function Enter(s)
	local set = {}
	local n = Lower(s, set)
	ns.db.situationActive = { key = s.key, set = set }
	if n > 0 then
		ns.Print(string.format("%s: lowered %d %s for steadier frames. %s back when you leave.",
			s.name, n, Plural(n, "setting", "settings"), Plural(n, "It goes", "They go")))
	end
	if ns.RefreshUI then ns.RefreshUI() end
end

local function Leave()
	local st = Active()
	if not st then return end
	ns.db.situationActive = nil
	local back, kept = 0, 0
	for cvar, r in pairs(st.set) do
		if type(r) == "table" and r.was ~= nil and ns.Exists(cvar) then
			if ns.Same(ns.GetInfo(cvar), r.now) then
				SetCVar(cvar, r.was)
				back = back + 1
			else
				kept = kept + 1
			end
		end
	end
	local s = Find(st.key)
	local name = s and s.name or "Situation"
	if back > 0 then
		ns.Print(string.format("%s over: put back %d %s.", name, back, Plural(back, "setting", "settings")))
	end
	if kept > 0 then
		ns.Print(string.format("Left %d alone that changed while you were there.", kept))
	end
	if ns.RefreshUI then ns.RefreshUI() end
end

local pending = false -- a switch waits for combat to end
local retries = 0     -- the game didn't know the map yet
local RETRY_LIMIT = 5
local retryArmed = false

-- Works out where you are and switches to match.
function ns.UpdateSituations()
	if not ns.db then return end
	if InCombatLockdown() then
		pending = true
		return
	end
	pending = false
	local st = Active()
	local want, unsure
	for _, s in ipairs(ns.SITUATIONS or {}) do
		if s.auto and ns.IsAutoSituationOn(s.key) and TESTS[s.auto.test] then
			local r = TESTS[s.auto.test]()
			if r == nil then
				unsure = true
			elseif r then
				want = s
				break
			end
		end
	end
	if unsure and not want then
		-- Just after a loading screen the game may not know the map yet: ask again shortly.
		if retries < RETRY_LIMIT and not retryArmed then
			retries = retries + 1
			retryArmed = true
			C_Timer.After(2, function()
				retryArmed = false
				ns.UpdateSituations()
			end)
		end
		-- Stay as you are, unless the switch was turned off.
		if not st or ns.IsAutoSituationOn(st.key) then return end
	else
		retries = 0
	end
	if st and want and want.key == st.key then return end
	if not st and not want then return end
	-- A Compare showing "before" ends first, so the switch reads, lowers and puts back your real settings.
	if ns.IsComparing and ns.IsComparing() and ns.StopCompare then ns.StopCompare() end
	if st then Leave() end
	if want then Enter(want) end
end

local function Pack(...)
	return { n = select("#", ...), ... }
end

-- Runs fn(...) and, in a city, lowers again only what it raised: a setting you raised yourself before
-- it, which fn left as it was, stays yours. The raised value is remembered as your newest one.
-- Every apply (below, and a preset of yours in Presets.lua) and every restore (Backups.lua, Back
-- included) go through this.
function ns.KeepSituationLowered(fn, ...)
	local st, s = Active(), nil
	s = st and Find(st.key)
	local before
	if s and not InCombatLockdown() then
		before = {}
		for cvar in pairs(s.auto.caps) do before[cvar] = ns.GetInfo(cvar) end
	end
	local res = Pack(pcall(fn, ...))
	-- In combat an apply waits too (Core.lua runs it again after the fight, through this wrapper).
	if before and not InCombatLockdown() and Active() == st then
		local raised = {}
		for cvar, was in pairs(before) do
			if not ns.Same(ns.GetInfo(cvar), was) then raised[cvar] = true end
		end
		if next(raised) and Lower(s, st.set, raised) > 0 and ns.RefreshUI then ns.RefreshUI() end
	end
	if not res[1] then error(res[2], 0) end
	return unpack(res, 2, res.n)
end

-- Eye Candy re-applied your choices (a preset, Apply, or the quiet re-apply at login and after Options).
local coreApplyAll = ns.ApplyAll
function ns.ApplyAll(...)
	return ns.KeepSituationLowered(coreApplyAll, ...)
end

-- Turn the switch on or off. Called by the Presets tab and /ec city.
function ns.SetAutoSituation(key, on)
	local s = Find(key)
	if not s or not ns.db then return false end
	if type(ns.db.autoSituations) ~= "table" then ns.db.autoSituations = {} end
	ns.db.autoSituations[key] = on and true or nil
	ns.UpdateSituations()
	if ns.RefreshUI then ns.RefreshUI() end
	return true
end

----------------------------------------------------------------------
-- Events
----------------------------------------------------------------------

-- Several zone events can fire for one step through a gate: only the last one counts.
local generation = 0
local function SoonAfterZone()
	generation = generation + 1
	local mine = generation
	C_Timer.After(1, function()
		if mine == generation then ns.UpdateSituations() end
	end)
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:RegisterEvent("ZONE_CHANGED_NEW_AREA")
events:RegisterEvent("ZONE_CHANGED")
events:RegisterEvent("ZONE_CHANGED_INDOORS")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:SetScript("OnEvent", function(_, event)
	if not ns.db then return end
	if not (Active() or next(ns.db.autoSituations or {})) then return end
	if event == "PLAYER_REGEN_ENABLED" then
		if pending then ns.UpdateSituations() end
	elseif event == "PLAYER_ENTERING_WORLD" then
		-- After a loading screen, once the map is known. Eye Candy's own login re-apply (4 seconds,
		-- Core.lua) goes through the ApplyAll wrapper above, so it can't undo a switch.
		retries = 0
		C_Timer.After(2, ns.UpdateSituations)
	else
		SoonAfterZone()
	end
end)

----------------------------------------------------------------------
-- /ec city
----------------------------------------------------------------------

local coreSlash = SlashCmdList.EYECANDY
SlashCmdList.EYECANDY = function(msg)
	local m = (msg or ""):lower():gsub("^%s+", ""):gsub("%s+$", "")
	if m == "city" or m == "city on" or m == "city off" then
		local on
		if m == "city" then on = not ns.IsAutoSituationOn("city") else on = (m == "city on") end
		if not ns.SetAutoSituation("city", on) then return end
		if on then
			ns.Print("In a capital city, Eye Candy now lowers view distance, environment detail, fog and far-away character detail, and puts them back when you leave. /ec city turns it off.")
		else
			ns.Print("Eye Candy no longer changes settings in capital cities.")
		end
		return
	end
	coreSlash(msg)
	if m == "help" then
		ns.Print("/ec city  lower the costly settings in capital cities by itself, and put them back when you leave")
	end
end
