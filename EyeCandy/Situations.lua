-- Eye Candy: switch for a Situation by itself. Off until you turn it on (/ec city, /ec instance).
--
-- In a capital city (Capital city) or a dungeon, raid, battleground or arena (Raid & PvP), the settings
-- in that Situation's auto.caps (Data.lua) come down on top of your own, and only where yours are higher.
-- Nothing else changes and no backup is taken. When you leave, each one goes back to what it was, unless
-- you changed it yourself while you were there. Never in combat: a switch waits until the fight ends.
-- It also waits while Autotune is testing settings.
--
-- Saved: EyeCandyDB.autoSituations[key] = true (on), EyeCandyDB.situationActive = { key, place, set } where
-- set[cvar] = { was = your value, now = the value Eye Candy set }, and place is the instance type for
-- Raid & PvP. Kept across a reload or logout, so a logout in a city or a dungeon still puts your settings
-- back on the next login outside it.
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

-- The instance types Raid & PvP switches in, and the words for them. IsInInstance gives
-- (inInstance, instanceType) (InstanceDocumentation.lua, forever branch). Forever's own UI also checks
-- "neighborhood" and "interior" (player housing) and the game has "scenario": none of those is a fight
-- this is for, so only these four count.
local PLACES = {
	party = { a = "a dungeon", the = "the dungeon" },
	raid = { a = "a raid", the = "the raid" },
	pvp = { a = "a battleground", the = "the battleground" },
	arena = { a = "an arena", the = "the arena" },
}

-- The instance type when in a dungeon, raid, battleground or arena, else false.
function ns.InstanceType()
	if not IsInInstance then return false end
	local inside, kind = IsInInstance()
	if inside and PLACES[kind] then return kind end
	return false
end

-- The game's own Raid and Battleground settings (Options > Graphics, "Enable Raid and Battleground
-- Settings", RAIDsettingsEnabled). Its tooltip: "an alternate graphic setting for Raids and
-- Battlegrounds". When it is on, the game uses its raidGraphics twin of each of these graphics menu
-- settings in a raid or a battleground (Blizzard_Settings_Shared/Mainline/GraphicsOverrides.lua, forever
-- branch), so Eye Candy leaves them to the game there. Dungeons are not covered (players report it), and
-- arenas are unconfirmed, so there Eye Candy lowers them as usual: if the game swaps after all, the
-- lowered value just goes unused and goes back when you leave.
local GAME_RAID_TWINS = {
	graphicsShadowQuality = true, graphicsLiquidDetail = true, graphicsPBRLiquidDetail = true,
	graphicsParticleDensity = true, graphicsSSAO = true, graphicsDepthEffects = true,
	graphicsComputeEffects = true, graphicsOutlineMode = true, graphicsTextureResolution = true,
	graphicsSpellDensity = true, graphicsProjectedTextures = true, graphicsLightMode = true,
	graphicsViewDistance = true, graphicsEnvironmentDetail = true, graphicsGroundClutter = true,
}
local GAME_RAID_PLACES = { raid = true, pvp = true }

local function GameRaidOn(place)
	return GAME_RAID_PLACES[place] == true and GetCVarBool ~= nil and GetCVarBool("RAIDsettingsEnabled") == true
end

local TESTS = { city = ns.InCapitalCity, instance = ns.InstanceType }

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

-- Its key ("city", "raid"), or nil.
function ns.ActiveSituationKey()
	local st = Active()
	return st and Find(st.key) and st.key or nil
end

-- One short line for the card and the title while a switch has lowered settings, or nil.
function ns.SituationNote()
	local st = Active()
	if not (st and Find(st.key)) then return nil end
	local place = PLACES[st.place]
	return "In " .. (place and place.a or "a city") .. ": some settings lowered"
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
-- only (optional): a set of CVars to look at. place: the instance type, so the game's own raid settings
-- are left to the game.
local function Lower(s, set, only, place)
	local n = 0
	local gameRaid = GameRaidOn(place)
	for cvar, cap in pairs(s.auto.caps) do
		local now = ns.GetInfo(cvar)
		if tonumber(now) and tonumber(now) > cap + 0.001 and (not only or only[cvar])
			and not (gameRaid and GAME_RAID_TWINS[cvar]) then
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

local function Enter(s, place)
	local set = {}
	local n = Lower(s, set, nil, place)
	ns.db.situationActive = { key = s.key, place = place, set = set }
	if n > 0 then
		local where = PLACES[place]
		if where then
			ns.Print(string.format("In %s: lowered %d %s to %s's for steadier frames. %s back when you leave.%s",
				where.a, n, Plural(n, "setting", "settings"), s.name, Plural(n, "It goes", "They go"),
				GameRaidOn(place) and " The game's own Raid and Battleground settings look after the rest." or ""))
		else
			ns.Print(string.format("%s: lowered %d %s for steadier frames. %s back when you leave.",
				s.name, n, Plural(n, "setting", "settings"), Plural(n, "It goes", "They go")))
		end
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
		local where = PLACES[st.place]
		if where then
			ns.Print(string.format("Left %s: put back %d %s.", where.the, back, Plural(back, "setting", "settings")))
		else
			ns.Print(string.format("%s over: put back %d %s.", name, back, Plural(back, "setting", "settings")))
		end
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
local autotuneArmed = false -- waiting for Autotune to finish

-- true while a switch waits for a fight to end (the tick boxes say so).
function ns.SituationWaiting()
	return pending
end

local function AutotuneRunning()
	return ns.Autotune ~= nil and ns.Autotune.IsRunning ~= nil and ns.Autotune.IsRunning() == true
end

-- Works out where you are and switches to match.
function ns.UpdateSituations()
	if not ns.db then return end
	if InCombatLockdown() then
		if not pending then
			pending = true
			if ns.RefreshUI then ns.RefreshUI() end
		end
		return
	end
	if pending then
		pending = false
		if ns.RefreshUI then ns.RefreshUI() end
	end
	-- Autotune is testing your settings: step aside, and look again once it is done.
	if AutotuneRunning() then
		if not autotuneArmed then
			autotuneArmed = true
			C_Timer.After(5, function()
				autotuneArmed = false
				ns.UpdateSituations()
			end)
		end
		return
	end
	local st = Active()
	local want, wantPlace, unsure
	local result = {}
	for _, s in ipairs(ns.SITUATIONS or {}) do
		if s.auto and ns.IsAutoSituationOn(s.key) and TESTS[s.auto.test] then
			local r = TESTS[s.auto.test]()
			result[s.key] = r
			if r == nil then
				unsure = true
			elseif r then
				want = s
				wantPlace = type(r) == "string" and r or nil
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
		-- Stay as you are while the switch you are in can't tell. One that can (you are out of the
		-- dungeon) or was turned off ends now.
		if not st or (ns.IsAutoSituationOn(st.key) and result[st.key] == nil) then return end
	else
		retries = 0
	end
	if st and want and want.key == st.key and wantPlace == st.place then return end
	if not st and not want then return end
	-- A Compare showing "before" ends first, so the switch reads, lowers and puts back your real settings.
	if ns.IsComparing and ns.IsComparing() and ns.StopCompare then ns.StopCompare() end
	if st then Leave() end
	if want then Enter(want, wantPlace) end
end

local function Pack(...)
	return { n = select("#", ...), ... }
end

-- Runs fn(...) and, while a switch is on, lowers again only what it raised: a setting you raised yourself
-- before it, which fn left as it was, stays yours. The raised value is remembered as your newest one.
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
		if next(raised) and Lower(s, st.set, raised, st.place) > 0 and ns.RefreshUI then ns.RefreshUI() end
	end
	if not res[1] then error(res[2], 0) end
	return unpack(res, 2, res.n)
end

-- Eye Candy re-applied your choices (a preset, Apply, or the quiet re-apply at login and after Options).
local coreApplyAll = ns.ApplyAll
function ns.ApplyAll(...)
	return ns.KeepSituationLowered(coreApplyAll, ...)
end

-- Turn the switch on or off. Called by the Presets tab, /ec city and /ec instance.
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
		-- After a loading screen (every way into or out of an instance has one), once the map is known.
		-- Eye Candy's own login re-apply (4 seconds, Core.lua) goes through the ApplyAll wrapper above, so
		-- it can't undo a switch.
		retries = 0
		C_Timer.After(2, ns.UpdateSituations)
	else
		SoonAfterZone()
	end
end)

----------------------------------------------------------------------
-- /ec city and /ec instance
----------------------------------------------------------------------

local SLASH = {
	city = {
		key = "city",
		on = "In a capital city, Eye Candy now lowers view distance, environment detail, fog and far-away character detail, and puts them back when you leave. /ec city turns it off.",
		off = "Eye Candy no longer changes settings in capital cities.",
		help = "/ec city  lower the costly settings in capital cities by itself, and put them back when you leave",
	},
	instance = {
		key = "raid",
		on = "In dungeons, raids, battlegrounds and arenas, Eye Candy now lowers costly settings to Raid & PvP's, and puts them back when you leave. /ec instance turns it off.",
		off = "Eye Candy no longer changes settings in dungeons, raids, battlegrounds and arenas.",
		help = "/ec instance  lower the costly settings to Raid & PvP's in dungeons, raids, battlegrounds and arenas by itself, and put them back when you leave",
	},
}

local coreSlash = SlashCmdList.EYECANDY
SlashCmdList.EYECANDY = function(msg)
	local m = (msg or ""):lower():gsub("^%s+", ""):gsub("%s+$", "")
	local word, arg = m:match("^(%a+)%s*(%a*)$")
	local cmd = word and SLASH[word]
	if cmd and (arg == "" or arg == "on" or arg == "off") then
		local on
		if arg == "" then on = not ns.IsAutoSituationOn(cmd.key) else on = (arg == "on") end
		if not ns.SetAutoSituation(cmd.key, on) then return end
		ns.Print(on and cmd.on or cmd.off)
		return
	end
	coreSlash(msg)
	if m == "help" then
		ns.Print(SLASH.city.help)
		ns.Print(SLASH.instance.help)
	end
end
