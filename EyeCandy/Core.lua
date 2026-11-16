-- Eye Candy: core logic (reading, applying, backing up and exporting CVars).

local ADDON, ns = ...

local PREFIX = "|cffffd100Eye Candy:|r "
local MIRROR_CVAR = "eyeCandyMirror"

function ns.Print(msg)
	DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. tostring(msg))
end

----------------------------------------------------------------------
-- CVar helpers
----------------------------------------------------------------------

-- Returns current value, default value. Both nil if the CVar does not exist in this client.
function ns.GetInfo(cvar)
	if C_CVar and C_CVar.GetCVarInfo then
		local ok, value, default = pcall(C_CVar.GetCVarInfo, cvar)
		if ok and value ~= nil then
			return value, default
		end
		return nil, nil
	end
	local value = GetCVar(cvar)
	return value, value and GetCVarDefault(cvar) or nil
end

function ns.Exists(cvar)
	return (ns.GetInfo(cvar)) ~= nil
end

local function Same(a, b)
	local na, nb = tonumber(a), tonumber(b)
	if na and nb then
		return math.abs(na - nb) < 0.001
	end
	return tostring(a) == tostring(b)
end
ns.Same = Same

local function FormatNumber(v)
	if type(v) == "number" then
		if v == math.floor(v) then
			return tostring(v)
		end
		return string.format("%.2f", v)
	end
	return tostring(v)
end
ns.FormatNumber = FormatNumber

-- Display name of an extra's chosen option (nil = its "leave alone" option).
function ns.ExtraLabel(ex, value)
	for _, opt in ipairs(ex.options) do
		if (opt[1] == nil and value == nil) or (opt[1] ~= nil and value ~= nil and Same(opt[1], value)) then
			return opt[2]
		end
	end
	return value == nil and "Leave as is" or FormatNumber(value)
end

-- Is a Graphics menu index supported on this hardware? Uses the client's own check.
local function IsSupported(cvar, value)
	if type(IsGraphicsSettingValueSupported) ~= "function" then
		return true
	end
	local ok, err = pcall(IsGraphicsSettingValueSupported, cvar, value, false)
	if not ok then
		return true -- unknown, let the client decide
	end
	return err == nil or err == 0 or err == false
end
ns.IsSupported = IsSupported

-- Highest supported index at or below the requested one.
function ns.ResolveMenuValue(cvar, wanted)
	-- Menu indices are small whole numbers; never loop on a huge one (a share string could carry one).
	wanted = math.floor(math.min(tonumber(wanted) or 0, 20))
	for v = wanted, 0, -1 do
		if IsSupported(cvar, v) then
			return v
		end
	end
	return nil
end

function ns.ClampRenderScale(value)
	local lo = (type(GetMinRenderScale) == "function") and GetMinRenderScale() or 0.33
	local hi = (type(GetMaxRenderScale) == "function") and GetMaxRenderScale() or 2
	if value > hi then return hi end
	if value < lo then return lo end
	return value
end

----------------------------------------------------------------------
-- Saved state (SavedVariables, with a CVar mirror as a fallback)
----------------------------------------------------------------------

local function DefaultDB()
	return { tiers = {}, extras = {}, advanced = {}, keepApplied = true, backup = nil }
end

local function SerialiseExtras(extras)
	local parts = {}
	for key, value in pairs(extras) do
		parts[#parts + 1] = key .. ":" .. tostring(value)
	end
	table.sort(parts)
	return table.concat(parts, ",")
end

local function ParseExtras(str)
	local extras = {}
	for key, value in string.gmatch(str or "", "(%w+):(%-?[%d%.]+)") do -- sharpness Off is -1
		extras[key] = tonumber(value)
	end
	return extras
end

local function SerialiseTiers(tiers)
	local parts = {}
	for key, tier in pairs(tiers) do
		parts[#parts + 1] = key .. "=" .. tier
	end
	table.sort(parts)
	return table.concat(parts, ",")
end

local function ParseTiers(str)
	local tiers = {}
	for key, tier in string.gmatch(str or "", "(%w+)=(%d+)") do
		tiers[key] = tonumber(tier)
	end
	return tiers
end

function ns.SaveMirror()
	if not (C_CVar and C_CVar.SetCVar) then return end
	pcall(C_CVar.SetCVar, MIRROR_CVAR, SerialiseTiers(ns.db.tiers) .. ";keep=" .. (ns.db.keepApplied and 1 or 0)
		.. ";ex=" .. SerialiseExtras(ns.db.extras))
end

-- Format: "tiers;keep=1;ex=key:value,..." (older versions wrote only "tiers;keep=1").
local function ParseMirror(str)
	local tiers, keep, extras = {}, nil, {}
	for seg in string.gmatch(str, "[^;]+") do
		local k = seg:match("^keep=(%d)$")
		local ex = seg:match("^ex=(.*)$")
		if k then
			keep = k == "1"
		elseif ex then
			extras = ParseExtras(ex)
		else
			tiers = ParseTiers(seg)
		end
	end
	return tiers, keep, extras
end

-- A backup taken after hand-testing the LOD CVars holds the test values, so Restore
-- would put the test values back. Swap those for what the Graphics menu sets at max.
local function FixDistantBackup(values)
	if not (values and ns.DISTANT_MENU_VALUES) then return 0 end
	local cinematic = {}
	for _, cat in ipairs(ns.CATEGORIES) do
		if cat.key == "distant" then
			for _, row in ipairs(cat.cvars) do
				cinematic[row[1]] = row[3][#ns.TIERS]
			end
		end
	end
	local fixed = 0
	for cvar, menuValue in pairs(ns.DISTANT_MENU_VALUES) do
		if values[cvar] ~= nil and cinematic[cvar] ~= nil and Same(values[cvar], cinematic[cvar]) then
			values[cvar] = tostring(menuValue)
			fixed = fixed + 1
		end
	end
	return fixed
end
ns.FixDistantBackup = FixDistantBackup

function ns.LoadDB()
	if type(EyeCandyDB) ~= "table" then
		EyeCandyDB = DefaultDB()
	end
	EyeCandyDB.tiers = EyeCandyDB.tiers or {}
	EyeCandyDB.extras = EyeCandyDB.extras or {}
	EyeCandyDB.advanced = EyeCandyDB.advanced or {} -- SavedVariables only (too long for the mirror CVar)
	if EyeCandyDB.keepApplied == nil then EyeCandyDB.keepApplied = true end
	EyeCandyDB.presets = EyeCandyDB.presets or {} -- your own presets (Presets.lua)
	EyeCandyDB.nextPresetId = EyeCandyDB.nextPresetId or 1
	ns.db = EyeCandyDB

	-- Mirror CVar: survives even if SavedVariables fail to load (seen on the Forever beta).
	if C_CVar and C_CVar.RegisterCVar then
		pcall(C_CVar.RegisterCVar, MIRROR_CVAR, "")
	end
	if next(ns.db.tiers) == nil and next(ns.db.extras) == nil then
		local mirror = GetCVar(MIRROR_CVAR)
		if mirror and mirror ~= "" then
			local tiers, keep, extras = ParseMirror(mirror)
			ns.db.tiers, ns.db.extras = tiers, extras
			if keep ~= nil then ns.db.keepApplied = keep end
			if next(ns.db.tiers) or next(ns.db.extras) then
				ns.Print("restored your choices from the backup copy.")
			end
		end
	end

	-- Backups (Backups.lua): the backups list, and the Original's Distant Detail correction.
	if ns.LoadBackups then ns.LoadBackups() end
end

----------------------------------------------------------------------
-- Backup / restore
----------------------------------------------------------------------

function ns.AllManagedCVars()
	local list = {}
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, row in ipairs(cat.cvars) do
			list[#list + 1] = row[1]
		end
	end
	for _, ex in ipairs(ns.EXTRAS) do
		list[#list + 1] = ex.cvar
	end
	if ns.AdvancedCVars then
		for _, cvar in ipairs(ns.AdvancedCVars()) do
			list[#list + 1] = cvar
		end
	end
	if ns.StandardCVars then
		-- The Standard tab's settings, minus any already listed above.
		local seen = {}
		for _, cvar in ipairs(list) do seen[cvar:lower()] = true end
		for _, cvar in ipairs(ns.StandardCVars()) do
			if not seen[cvar:lower()] then
				seen[cvar:lower()] = true
				list[#list + 1] = cvar
			end
		end
	end
	return list
end

-- ns.TakeBackup, ns.RestoreBackup and the rest of the backups live in Backups.lua.

----------------------------------------------------------------------
-- Applying tiers
----------------------------------------------------------------------

local pendingAfterCombat = false

-- Set one CVar, record what happened in result.
-- opts.menu: Graphics menu index (step down to what the GPU supports); opts.scale: render scale (clamp).
local function ApplyOne(cvar, label, wanted, opts, result)
	if not ns.Exists(cvar) then
		result.skipped[#result.skipped + 1] = label .. " (not in this client)"
		return
	end
	local target = wanted
	if opts.menu then
		target = ns.ResolveMenuValue(cvar, wanted)
	elseif opts.scale then
		target = ns.ClampRenderScale(wanted)
	end
	if target == nil then
		result.skipped[#result.skipped + 1] = label .. " (not supported by your GPU)"
		return
	end
	if not Same(ns.GetInfo(cvar), target) then
		SetCVar(cvar, target)
	end
	local now = ns.GetInfo(cvar)
	if Same(now, target) then
		result.applied = result.applied + 1
		if not Same(target, wanted) then
			-- Render scale's range is the game's (GetMin/GetMaxRenderScale), not the player's PC.
			-- A menu value steps down to the highest the game says it supports (IsGraphicsSettingValueSupported,
			-- which weighs the graphics card and other settings, so neither is named).
			local why = opts.scale and ((target < wanted and "the most" or "the least") .. " the game allows now")
				or "the highest the game supports now"
			result.changed[#result.changed + 1] = string.format("%s: %s (%s, asked %s)", label, FormatNumber(target), why, FormatNumber(wanted))
		end
	else
		result.changed[#result.changed + 1] = string.format("%s: client kept %s (asked %s)", label, tostring(now), FormatNumber(target))
	end
end

ns.ApplyOne = ApplyOne

local function NewResult()
	return { applied = 0, skipped = {}, changed = {} }
end

-- Apply one category at a tier. Returns a result table.
-- pass: "visible" = settings the Graphics menu owns, "hidden" = CVars the menu overwrites.
function ns.ApplyCategory(cat, tier, pass)
	local result = NewResult()
	if not tier or tier == 0 then return result end

	for _, row in ipairs(cat.cvars) do
		local wanted = row[3][tier]
		local inPass = (pass == "hidden") == (row.hidden == true)
		-- The render scale extra owns RenderScale when set; an Advanced dial owns its CVar when set.
		local overridden = (row.scale and ns.db.extras.renderScale ~= nil) or ns.db.advanced[row[1]] ~= nil
		if wanted ~= nil and inPass and not overridden then
			ApplyOne(row[1], row[2], wanted, row, result)
		end
	end
	return result
end

-- Apply one extra toggle. Returns a result table (empty if left alone or not in this pass).
function ns.ApplyExtra(ex, pass)
	local result = NewResult()
	local wanted = ns.db.extras[ex.key]
	local inPass = (pass == "hidden") == (ex.hidden == true)
	if wanted ~= nil and inPass then
		ApplyOne(ex.cvar, ex.name, wanted, ex, result)
	end
	return result
end

function ns.ApplyAll(onlyHidden, quiet)
	if InCombatLockdown() then
		pendingAfterCombat = true
		if not quiet then ns.Print("in combat. Settings will apply when combat ends.") end
		return
	end

	-- Save the Original before anything changes (the login re-apply can run before it exists).
	-- Apply takes no backup and is no step of its own: what it changes shows in today's steps as your
	-- own changes (ns.NoteBeforeStep, Backups.lua).
	ns.TakeBackup(false)

	-- Menu indices first, then hidden values (the menu values can reset hidden ones).
	local passes = onlyHidden and { "hidden" } or { "visible", "hidden" }
	local report = {}
	local total, notes = 0, {}
	local function Record(key, r)
		total = total + r.applied
		for _, s in ipairs(r.skipped) do notes[#notes + 1] = s end
		for _, c in ipairs(r.changed) do notes[#notes + 1] = c end
		local agg = report[key] or { applied = 0, notes = 0 }
		agg.applied = agg.applied + r.applied
		agg.notes = agg.notes + #r.skipped + #r.changed
		report[key] = agg
	end

	for _, pass in ipairs(passes) do
		for _, cat in ipairs(ns.CATEGORIES) do
			local tier = ns.db.tiers[cat.key]
			if tier and tier > 0 then
				Record(cat.key, ns.ApplyCategory(cat, tier, pass))
			end
		end
		-- Extras after tiers, so they win where they overlap.
		for _, ex in ipairs(ns.EXTRAS) do
			if ns.db.extras[ex.key] ~= nil then
				Record("extra:" .. ex.key, ns.ApplyExtra(ex, pass))
			end
		end
		-- Advanced dials are all hidden CVars: re-applied last, after anything the menu resets.
		if pass == "hidden" and ns.ApplyAdvanced and next(ns.db.advanced) then
			Record("advanced", ns.ApplyAdvanced())
		end
	end

	ns.lastReport = report
	if ns.NoteApplied then ns.NoteApplied() end
	if not quiet then
		if total == 0 and #notes == 0 then
			ns.Print("nothing to apply. Pick a level or a setting on the Hidden tab first.")
		else
			ns.Print(string.format("applied %d settings.", total))
			local seen = {}
			for _, n in ipairs(notes) do
				if not seen[n] then
					seen[n] = true
					ns.Print("  " .. n)
				end
			end
		end
	end
	if ns.RefreshUI then ns.RefreshUI() end
end

-- Best-looking setup: every row at the top tier, plus the Showcase extras.
-- Apply a preset: 1 to 5 = that tier everywhere, #TIERS + 1 = Showcase (Cinematic plus the Showcase extras).
-- Also sets the Advanced dials for that preset. Applies straight away.
-- look (optional): a Look table from ns.LOOKS; its Extras and dials are layered on top of the preset.
function ns.SetPreset(index, look)
	if InCombatLockdown() then
		ns.Print("can't change presets in combat. Try again after the fight.")
		return false
	end
	-- One of today's steps, for Back to before and Compare (Backups.lua). No backup row. First, so a
	-- Compare showing "before" ends (Compare.lua) before anything reads the settings.
	if ns.NoteBeforePreset then
		ns.NoteBeforePreset(look and look.name or (index > #ns.TIERS and "Showcase" or ns.TIERS[index]))
	end
	ns.TakeBackup(false)
	local tier = math.min(index, #ns.TIERS)
	for _, cat in ipairs(ns.CATEGORIES) do
		ns.db.tiers[cat.key] = tier
	end
	if index > #ns.TIERS then
		for key, value in pairs(ns.SHOWCASE_EXTRAS) do
			ns.db.extras[key] = value
		end
	end
	if look then
		for key, value in pairs(look.extras or {}) do
			ns.db.extras[key] = value
		end
	end
	-- One of your presets can keep hidden values that have no dial (Presets.lua); a built-in drops them.
	for cvar in pairs(ns.db.advanced) do
		if not (ns.ADVANCED_BY_CVAR and ns.ADVANCED_BY_CVAR[cvar]) then ns.db.advanced[cvar] = nil end
	end
	if ns.ApplyAdvancedPreset then ns.ApplyAdvancedPreset(index) end
	if look then
		for cvar, value in pairs(look.dials or {}) do
			ns.db.advanced[cvar] = value
		end
	end
	ns.db.look = look and look.key or nil
	-- Hidden values this preset leaves alone go back to their value from before Eye Candy, so a lower
	-- preset doesn't keep a higher preset's values (e.g. Cinematic's terrain detail on Performance).
	local original = ns.OriginalBackup and ns.OriginalBackup()
	local backup = original and original.values
	if backup then
		for _, cat in ipairs(ns.CATEGORIES) do
			for _, row in ipairs(cat.cvars) do
				local cvar = row[1]
				if row.hidden and row[3][tier] == nil and ns.db.advanced[cvar] == nil
					and backup[cvar] ~= nil and ns.Exists(cvar) and not Same(ns.GetInfo(cvar), backup[cvar]) then
					SetCVar(cvar, backup[cvar])
				end
			end
		end
	end
	ns.SaveMirror()
	ns.ApplyAll(false, false)
	return true
end

-- Finds a Look or a Situation (Data.lua) by key or name. Situations carry situation = true.
function ns.FindLook(key)
	key = (key or ""):lower()
	for _, look in ipairs(ns.LOOKS) do
		if look.key == key or look.name:lower() == key then return look end
	end
	for _, s in ipairs(ns.SITUATIONS or {}) do
		if s.key == key or s.name:lower() == key then return s end
	end
end

function ns.SetLook(key)
	local look = ns.FindLook(key)
	if not look then
		local names = {}
		for _, l in ipairs(ns.LOOKS) do names[#names + 1] = l.key end
		for _, s in ipairs(ns.SITUATIONS or {}) do names[#names + 1] = s.key end
		ns.Print("unknown look. Use: " .. table.concat(names, ", "))
		return
	end
	local scaleBefore = ns.GetInfo("RenderScale")
	if not ns.SetPreset(look.base, look) then return false end
	if look.back then
		ns.Print(look.name .. " on. When you're done, type /ec back to put your settings back as they were.")
	else
		ns.Print((look.situation and "Preset: " or "Look: ") .. look.name .. ". Fine-tune anything on the Hidden tab. /ec back undoes it.")
	end
	if scaleBefore and not Same(scaleBefore, ns.GetInfo("RenderScale")) then
		ns.Print("Render scale changed. If the picture doesn't change, restart the game so it takes effect.")
	end
	return true
end

function ns.ApplyShowcase()
	local scaleBefore = ns.GetInfo("RenderScale")
	if not ns.SetPreset(#ns.TIERS + 1) then return false end
	ns.Print("Showcase on. If the picture doesn't look sharper, restart the game so the new render scale takes effect.")
	if scaleBefore and not Same(scaleBefore, ns.GetInfo("RenderScale")) then
		ns.Print("Render scale changed. Check your FPS. If it's too low, lower 'Render scale override' on the Hidden tab.")
	end
	return true
end

----------------------------------------------------------------------
-- Export
----------------------------------------------------------------------

local function Bool(fn, ...)
	if type(fn) ~= "function" then return "n/a" end
	local ok, v = pcall(fn, ...)
	if not ok then return "n/a" end
	return v and "yes" or "no"
end

local function Line(buf, cvar, label)
	local value, default = ns.GetInfo(cvar)
	if value == nil then
		buf[#buf + 1] = string.format("  %-30s (not in this client)", cvar)
		return
	end
	local mark = Same(value, default) and "" or "  *changed"
	buf[#buf + 1] = string.format("  %-30s %-8s default %-8s%s%s", cvar, value, tostring(default), mark, label and ("  [" .. label .. "]") or "")
end

function ns.BuildExport(includeAll)
	local buf = {}
	local version, build, buildDate, iface = GetBuildInfo()
	buf[#buf + 1] = "=== Eye Candy graphics export ==="
	buf[#buf + 1] = string.format("Client: %s (%s) %s, interface %s", tostring(version), tostring(build), tostring(buildDate), tostring(iface))
	buf[#buf + 1] = "Exported: " .. date("%Y-%m-%d %H:%M")

	if C_VideoOptions then
		local okA, adapters = pcall(C_VideoOptions.GetGxAdapterInfo)
		if okA and type(adapters) == "table" then
			for _, a in ipairs(adapters) do
				buf[#buf + 1] = "GPU: " .. tostring(a.name) .. (a.isLowPower and " (low power)" or "")
			end
		end
		local okS, size = pcall(C_VideoOptions.GetCurrentGameWindowSize, tonumber(GetCVar("gxMonitor")) or 0, GetCVarBool("gxMaximize"))
		if okS and size then
			buf[#buf + 1] = string.format("Window: %dx%d", size.x or 0, size.y or 0)
		end
		buf[#buf + 1] = "Supports: PBR water " .. Bool(C_VideoOptions.IsPBRWaterSupported)
			.. ", secondary lighting " .. Bool(C_VideoOptions.IsSecondaryLightingSupported)
			.. ", outline mode " .. Bool(C_VideoOptions.IsOutlineModeSupported)
			.. ", linear lighting " .. Bool(C_VideoOptions.IsLinearEnabledOnStart)
		buf[#buf + 1] = "HD textures: available " .. Bool(C_VideoOptions.AreHighResTexturesAvailable)
			.. ", installed " .. Bool(C_BattleNet and C_BattleNet.AreHighResTexturesInstalled)
	end
	if type(GetMinRenderScale) == "function" and type(GetMaxRenderScale) == "function" then
		buf[#buf + 1] = string.format("Render scale range: %s to %s", FormatNumber(GetMinRenderScale()), FormatNumber(GetMaxRenderScale()))
	end
	if C_GameRules and C_GameRules.GetForeverExperiencePreset and Enum and Enum.ForeverExperiencePreset then
		local ok, preset = pcall(C_GameRules.GetForeverExperiencePreset)
		local name = "unknown"
		if ok then
			for k, v in pairs(Enum.ForeverExperiencePreset) do
				if v == preset then name = k end
			end
		end
		buf[#buf + 1] = "Experience preset: " .. name
	end

	buf[#buf + 1] = ""
	buf[#buf + 1] = "--- Eye Candy tiers ---"
	for _, cat in ipairs(ns.CATEGORIES) do
		local tier = ns.db.tiers[cat.key] or 0
		buf[#buf + 1] = string.format("  %-26s %s", cat.name, tier > 0 and ns.TIERS[tier] or "No change")
	end

	local look = ns.db.look and ns.FindLook(ns.db.look)
	buf[#buf + 1] = "  Look: " .. (look and look.name or "none")
	buf[#buf + 1] = ""
	buf[#buf + 1] = "--- Eye Candy extras ---"
	for _, ex in ipairs(ns.EXTRAS) do
		local chosen = ns.ExtraLabel(ex, ns.db.extras[ex.key])
		local value = ns.GetInfo(ex.cvar)
		buf[#buf + 1] = string.format("  %-26s %-14s (%s now %s)", ex.name, chosen, ex.cvar, tostring(value))
	end

	buf[#buf + 1] = ""
	buf[#buf + 1] = "--- Eye Candy advanced overrides ---"
	local advNames = {}
	for cvar in pairs(ns.db.advanced) do advNames[#advNames + 1] = cvar end
	table.sort(advNames, function(a, b) return a:lower() < b:lower() end)
	if #advNames == 0 then buf[#buf + 1] = "  (none)" end
	for _, cvar in ipairs(advNames) do
		buf[#buf + 1] = string.format("  %-30s set %-8s now %s", cvar, tostring(ns.db.advanced[cvar]), tostring(ns.GetInfo(cvar)))
	end

	for _, cat in ipairs(ns.CATEGORIES) do
		buf[#buf + 1] = ""
		buf[#buf + 1] = "--- " .. cat.name .. " ---"
		for _, row in ipairs(cat.cvars) do
			Line(buf, row[1], row[2])
		end
	end

	buf[#buf + 1] = ""
	buf[#buf + 1] = "--- Other display settings ---"
	for _, cvar in ipairs(ns.EXPORT_EXTRA) do
		Line(buf, cvar)
	end

	-- Every Graphics-category CVar the client reports (changed ones only, unless includeAll).
	if type(ConsoleGetAllCommands) == "function" then
		local ok, commands = pcall(ConsoleGetAllCommands)
		if ok and type(commands) == "table" then
			local graphicsCat = (Enum and Enum.ConsoleCategory and Enum.ConsoleCategory.Graphics) or 1
			local cvarType = (Enum and Enum.ConsoleCommandType and Enum.ConsoleCommandType.Cvar) or 0
			local names = {}
			for _, info in ipairs(commands) do
				if info.category == graphicsCat and info.commandType == cvarType then
					local value, default = ns.GetInfo(info.command)
					if value ~= nil and (includeAll or not Same(value, default)) then
						names[#names + 1] = info.command
					end
				end
			end
			table.sort(names, function(a, b) return a:lower() < b:lower() end)
			buf[#buf + 1] = ""
			buf[#buf + 1] = string.format("--- %s graphics CVars (%d) ---", includeAll and "All" or "Changed", #names)
			for _, name in ipairs(names) do
				Line(buf, name)
			end
		end
	end

	return table.concat(buf, "\n")
end

-- Search every console CVar by name and return value, default and the client's own help text.
function ns.BuildFind(word)
	word = (word or ""):lower()
	if word == "" then return "Usage: /ec find <word>   e.g. /ec find shadow" end
	if type(ConsoleGetAllCommands) ~= "function" then return "This client does not expose ConsoleGetAllCommands." end
	local ok, commands = pcall(ConsoleGetAllCommands)
	if not ok or type(commands) ~= "table" then return "Could not read the console command list." end
	local cvarType = (Enum and Enum.ConsoleCommandType and Enum.ConsoleCommandType.Cvar) or 0
	local hits = {}
	for _, info in ipairs(commands) do
		if info.commandType == cvarType and info.command:lower():find(word, 1, true) then
			hits[#hits + 1] = info
		end
	end
	table.sort(hits, function(a, b) return a.command:lower() < b.command:lower() end)
	local buf = { string.format("=== Eye Candy find: \"%s\" (%d CVars) ===", word, #hits) }
	for _, info in ipairs(hits) do
		local value, default = ns.GetInfo(info.command)
		buf[#buf + 1] = string.format("%s = %s (default %s)%s", info.command, tostring(value), tostring(default),
			Same(value, default) and "" or "  *changed")
		buf[#buf + 1] = "    " .. ((info.help and info.help ~= "") and info.help or "(no description)")
	end
	return table.concat(buf, "\n")
end

----------------------------------------------------------------------
-- Events
----------------------------------------------------------------------

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:RegisterEvent("PLAYER_LOGOUT")

-- Anything for Eye Candy to keep applied: a tier, an extra or an Advanced dial.
function ns.HasChoices()
	return next(ns.db.tiers) ~= nil or next(ns.db.extras) ~= nil or next(ns.db.advanced) ~= nil
end

local hookedSettings = false
local function HookSettingsPanel()
	if hookedSettings or not SettingsPanel then return end
	hookedSettings = true
	-- The Graphics menu overwrites grass/weather/far clip. Put ours back when it closes.
	-- Settings the menu shows and you changed there are kept as yours first (Standard.lua).
	SettingsPanel:HookScript("OnShow", function()
		if ns.SnapshotGameMenu then ns.SnapshotGameMenu() end
	end)
	SettingsPanel:HookScript("OnHide", function()
		if ns.KeepGameMenuChanges and ns.db then ns.KeepGameMenuChanges() end
		if ns.db and ns.db.keepApplied and ns.HasChoices() then
			C_Timer.After(0.5, function() ns.ApplyAll(true, true) end)
		end
	end)
end

events:SetScript("OnEvent", function(_, event, arg1, arg2)
	if event == "ADDON_LOADED" and arg1 == ADDON then
		ns.LoadDB()
	elseif event == "PLAYER_ENTERING_WORLD" then
		HookSettingsPanel()
		local isLogin, isReload = arg1, arg2
		if isLogin and ns.SlashClash() then ns.Print(ns.CLASH_LINE) end
		if (isLogin or isReload) and ns.db.keepApplied and ns.HasChoices() then
			-- Delay: account settings from the server can land a moment after login.
			C_Timer.After(4, function() ns.ApplyAll(true, true) end)
		end
		-- Settings changed while the game was closed (PatchWatch.lua).
		if ns.PatchWatchLogin then ns.PatchWatchLogin(isLogin, isReload) end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if pendingAfterCombat then
			pendingAfterCombat = false
			ns.ApplyAll(false, false)
		end
	elseif event == "PLAYER_LOGOUT" then
		ns.SaveMirror()
		if ns.PatchWatchLogout then ns.PatchWatchLogout() end
	end
end)

----------------------------------------------------------------------
-- Slash commands
----------------------------------------------------------------------

-- /ec is the one every message names. /eyecandy is a quiet spare in case another addon takes /ec.
-- The numbers must run on with no gap: the game stops reading at the first missing one.
SLASH_EYECANDY1 = "/ec"
SLASH_EYECANDY2 = "/graphics"
SLASH_EYECANDY3 = "/eyecandy"

-- Another addon that also claims /ec (Easy Controller Forever does): WoW then picks one of the
-- two at random, so Eye Candy says at login, and in help, that /eyecandy always opens it.
ns.CLASH_LINE = "another addon also uses /ec, so /ec may open that one. /eyecandy always opens Eye Candy."
function ns.SlashClash()
	for k, v in pairs(_G) do
		if type(k) == "string" and type(v) == "string" and k:sub(1, 6) == "SLASH_"
			and v:lower() == "/ec" and not k:match("^SLASH_EYECANDY%d+$") then
			return true
		end
	end
	return false
end

SlashCmdList.EYECANDY = function(msg)
	local raw = (msg or ""):gsub("^%s+", ""):gsub("%s+$", "") -- keeps capitals, for preset names
	msg = raw:lower()
	if msg == "export" or msg == "dump" then
		ns.ShowExport(false)
	elseif msg == "export all" or msg == "dump all" then
		ns.ShowExport(true)
	elseif msg:match("^find") then
		ns.ShowText(ns.BuildFind(msg:match("^find%s*(.*)$")))
	elseif msg == "report" then
		ns.ShowReport()
	elseif msg == "peek" then
		ns.PeekSlash() -- Peek.lua
	elseif msg == "compare" or msg == "compare stop" or msg == "compare off" then
		ns.CompareSlash(msg) -- Compare.lua
	elseif msg == "apply" then
		ns.ApplyAll(false, false)
	elseif msg == "restore" then
		ns.RestoreBackup()
	elseif msg == "advanced" or msg == "adv" or msg == "hidden" then
		ns.ToggleAdvanced()
	elseif msg == "fade" then
		ns.db.noFade = not ns.db.noFade or nil
		ns.Print(ns.db.noFade and "the window no longer fades when the mouse is away."
			or "the window fades a little when the mouse is away.")
	elseif msg == "minimap" then
		ns.ToggleMinimapButton()
	elseif msg:match("^look") then
		ns.SetLook(msg:match("^look%s*(%a*)"))
	elseif ns.PresetSlash and ns.PresetSlash(msg, raw) then
		-- presets, save <name>, use <name>, share <name> (Presets.lua)
	elseif ns.BackupSlash and ns.BackupSlash(msg, raw) then
		-- backups, backup [name], restore <number> (Backups.lua)
	elseif msg == "showcase" or msg == "preset showcase" then
		ns.ApplyShowcase()
	elseif msg:match("^preset ") then
		local name = msg:match("^preset (%a+)")
		for i, t in ipairs(ns.TIERS) do
			if t:lower() == name then
				ns.SetPreset(i)
				return
			end
		end
		ns.Print("unknown preset. Use: performance, balanced, high, ultra, cinematic")
	elseif msg == "help" then
		ns.Print("/ec  open the window")
		if ns.SlashClash() then ns.Print(ns.CLASH_LINE) end
		ns.Print("/ec export  copy box with your settings (changed graphics CVars)")
		ns.Print("/ec export all  every graphics CVar the client has")
		ns.Print("/ec preset <performance|balanced|high|ultra|cinematic>  set every system and apply")
		ns.Print("/ec showcase  everything pushed: Cinematic plus the Showcase hidden settings")
		ns.Print("/ec look <beautiful|painterly|crisp|moody|classic>  curated styles")
		ns.Print("/ec look <raid|laptop|screenshot>  presets for a job. /ec back  undo the newest of today's steps")
		ns.Print("/ec presets  list presets. save <name>  save your settings. use <name>  apply one. share <name>  make a share code")
		ns.Print("/ec hidden  open the Hidden tab: system levels and ~60 hidden settings (also: /ec advanced)")
		ns.Print("/ec minimap  show or hide the minimap button")
		ns.Print("/ec fade  turn off (or on) the window fading a little when the mouse is away")
		ns.Print("/ec find <word>  search CVars, with the client's own descriptions")
		ns.Print("/ec report  copy box with a bug report to paste into GitHub")
		ns.Print("/ec peek  hide the game's UI and Eye Candy to see the world. Back or Esc brings it back")
		ns.Print("/ec compare  flip between before your last preset and now. compare stop  end on now")
		ns.Print("/ec apply  re-apply your chosen levels and settings")
		ns.Print("/ec restore  put back the values from before Eye Candy's first apply")
		ns.Print("/ec backups  list backups. backup <name>  make one. restore <number>  restore one")
	else
		ns.ToggleMain()
	end
end
