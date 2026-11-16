-- Eye Candy: named presets (built-in and your own) and share strings.
-- A share string is "!EC1!" + Base64(Deflate(CBOR(payload))), built with the game's C_EncodingUtil.
-- Import safety: only CVars on ns.AllManagedCVars() are ever applied. Anything else is skipped and listed.

local ADDON, ns = ...

local PREFIX = "!EC1!"
local FORMAT = 1
local NAME_MAX = 40
local DESC_MAX = 400      -- longest note read from a share code (Autotune's is about 200)
local VALUE_MAX = 24      -- longest value string accepted from a share string
local TEXT_MAX = 16000    -- longest share string accepted (a real one is a few hundred characters)
local ENTRIES_MAX = 3000  -- most settings read from one share string

----------------------------------------------------------------------
-- Helpers
----------------------------------------------------------------------

-- Keep only whole UTF-8 characters (stray bytes are dropped), at most max bytes.
local function CutUTF8(s, max)
	local out, len, i = {}, 0, 1
	while i <= #s do
		local c = s:byte(i)
		local n = (c < 128 and 1) or (c >= 194 and c <= 223 and 2) or (c >= 224 and c <= 239 and 3) or (c >= 240 and c <= 244 and 4) or 0
		local ch = n > 0 and s:sub(i, i + n - 1) or ""
		local valid = n > 0 and #ch == n
		for j = 2, n do
			local b = ch:byte(j)
			if not b or b < 128 or b > 191 then valid = false end
		end
		if valid then
			if len + n > max then break end
			out[#out + 1] = ch
			len = len + n
			i = i + n
		else
			i = i + 1
		end
	end
	return table.concat(out)
end

-- Names and other text from a share string: no colour codes, no escape sequences, no control characters.
local function CleanText(s, max)
	if type(s) ~= "string" then return nil end
	s = s:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""):gsub("|", ""):gsub("%c", " ")
	s = s:gsub("^%s+", ""):gsub("%s+$", "")
	s = CutUTF8(s, max):gsub("%s+$", "")
	return s
end
ns.CleanName = function(name) return CleanText(name, NAME_MAX) end

function ns.CharacterName()
	local name = (type(UnitName) == "function" and UnitName("player")) or "Unknown"
	local realm = (type(GetRealmName) == "function" and GetRealmName()) or ""
	realm = realm:gsub("%s", "")
	return realm ~= "" and (name .. "-" .. realm) or name
end

local function GameVersion()
	local version = GetBuildInfo()
	return tostring(version or "")
end

local function ManagedSet()
	local set = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do set[cvar] = true end
	return set
end

-- Graphics menu CVars and visible extras are set before hidden ones (the menu values can reset hidden ones).
-- rank: category rows in order, then Extras, then everything else (the same order ns.ApplyAll uses).
local function OptsByCVar()
	local opts, visible, rank, r = {}, {}, {}, 0
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, row in ipairs(cat.cvars) do
			opts[row[1]] = row
			if not row.hidden then visible[row[1]] = true end
			r = r + 1
			rank[row[1]] = rank[row[1]] or r
		end
	end
	for _, ex in ipairs(ns.EXTRAS) do
		if not ex.hidden then visible[ex.cvar] = true end
		opts[ex.cvar] = opts[ex.cvar] or ex
		r = r + 1
		rank[ex.cvar] = rank[ex.cvar] or r
	end
	return opts, visible, rank
end

-- Set a table of CVar values. Only CVars on the addon's list that exist in this client are touched.
-- useOpts: step Graphics menu values down to what the GPU supports and clamp render scale (for presets).
-- Returns how many values were set, and the ApplyOne-style result when useOpts is on.
function ns.ApplyValues(values, useOpts)
	local managed = ManagedSet()
	local opts, visible, rank = OptsByCVar()
	local result = { applied = 0, skipped = {}, changed = {} }
	local n = 0
	for _, wantVisible in ipairs({ true, false }) do
		local names = {}
		for cvar in pairs(values) do
			if managed[cvar] and (visible[cvar] == true) == wantVisible then names[#names + 1] = cvar end
		end
		table.sort(names, function(a, b)
			local ra, rb = rank[a] or math.huge, rank[b] or math.huge
			if ra ~= rb then return ra < rb end
			return a < b
		end)
		for _, cvar in ipairs(names) do
			local value = values[cvar]
			if ns.Exists(cvar) then
				if useOpts then
					local o = opts[cvar] or {}
					local wanted = (o.menu or o.scale) and tonumber(value) or value
					local before = result.applied
					ns.ApplyOne(cvar, (o[2] or o.name or cvar), wanted, o, result)
					if result.applied > before then n = n + 1 end
				elseif ns.Same(ns.GetInfo(cvar), value) or SetCVar(cvar, value) ~= false then
					n = n + 1
				end
			end
		end
	end
	return n, result
end

----------------------------------------------------------------------
-- Built-in presets (read-only)
----------------------------------------------------------------------

local function TierName(index)
	return index > #ns.TIERS and "Showcase" or ns.TIERS[index]
end

local function Builtins()
	local list = {}
	for i = 1, #ns.TIERS + 1 do
		local name = TierName(i)
		local desc = (i > #ns.TIERS)
			and "Everything pushed: Cinematic on every system, plus the Showcase values for the Hidden tab's settings."
			or ("Every system at " .. name .. ".")
		list[#list + 1] = { id = "tier" .. i, name = name, group = "Tiers", desc = desc, builtin = true, index = i }
	end
	for _, look in ipairs(ns.LOOKS) do
		list[#list + 1] = { id = "look:" .. look.key, name = look.name, group = "Looks", desc = look.desc, builtin = true, look = look }
	end
	for _, s in ipairs(ns.SITUATIONS or {}) do
		list[#list + 1] = { id = "look:" .. s.key, name = s.name, group = "Situations", desc = s.desc, builtin = true, look = s }
	end
	return list
end

-- Your value from before Eye Candy (the Original backup), else the game default.
local function BeforeValue(cvar)
	local b = ns.OriginalBackup and ns.OriginalBackup()
	local v = b and b.values and b.values[cvar]
	if v == nil then
		local _, default = ns.GetInfo(cvar)
		v = default
	end
	return v ~= nil and tostring(v) or nil
end

-- The values a built-in sets, worked out without applying it. Tier rows, then Extras, then dials
-- (the same order ns.SetPreset uses, so later ones win). Hidden rows and dials the built-in hands back
-- get your value from before Eye Candy, as ns.SetPreset does. Extras it leaves alone are left out.
local function BuiltinValues(p)
	local index = p.index or p.look.base
	local look = p.look
	local tier = math.min(index, #ns.TIERS)
	local values = {}
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, row in ipairs(cat.cvars) do
			if row[3][tier] ~= nil then
				values[row[1]] = tostring(row[3][tier])
			elseif row.hidden then
				values[row[1]] = BeforeValue(row[1])
			end
		end
	end
	local extras = {}
	if index > #ns.TIERS then
		for key, value in pairs(ns.SHOWCASE_EXTRAS) do extras[key] = value end
	end
	if look then
		for key, value in pairs(look.extras or {}) do extras[key] = value end
	end
	for _, ex in ipairs(ns.EXTRAS) do
		if extras[ex.key] ~= nil then values[ex.cvar] = tostring(extras[ex.key]) end
	end
	for _, group in ipairs(ns.ADVANCED or {}) do
		for _, d in ipairs(group.rows) do
			local v = d.p and d.p[index]
			if v ~= nil then
				values[d[1]] = tostring(v)
			elseif values[d[1]] == nil then
				-- ns.ResetAdvanced hands it to its tier row (already in values), else your own value.
				values[d[1]] = BeforeValue(d[1])
			end
		end
	end
	if look then
		for cvar, value in pairs(look.dials or {}) do values[cvar] = tostring(value) end
	end
	return values
end

----------------------------------------------------------------------
-- Finding and naming
----------------------------------------------------------------------

local function UserList()
	return ns.db.presets
end

function ns.FindPreset(id)
	for _, p in ipairs(Builtins()) do
		if p.id == id then return p end
	end
	for _, p in ipairs(UserList()) do
		if p.id == id then return p end
	end
end

-- Case-insensitive. Built-ins first.
function ns.FindPresetByName(name)
	name = (ns.CleanName(name) or ""):lower()
	if name == "" then return nil end
	for _, p in ipairs(Builtins()) do
		if p.name:lower() == name then return p end
	end
	for _, p in ipairs(UserList()) do
		if p.name:lower() == name then return p end
	end
end

local function NameTaken(name, exceptId)
	local p = ns.FindPresetByName(name)
	return p ~= nil and p.id ~= exceptId, p
end

-- "Moody" -> "Moody (2)", "Moody (3)" ... A name that already ends in " (n)" is numbered from its base.
local function UniqueName(name)
	if not NameTaken(name) then return name end
	local base = name:gsub(" %(%d+%)$", "")
	for n = 2, 9999 do
		local suffix = " (" .. n .. ")"
		local candidate = CutUTF8(base, NAME_MAX - #suffix) .. suffix
		if not NameTaken(candidate) then return candidate end
	end
end

local function CheckNewName(name, exceptId)
	name = ns.CleanName(name)
	if not name or name == "" then
		return nil, "Give the preset a name."
	end
	local taken, other = NameTaken(name, exceptId)
	if taken then
		if other.builtin then
			return nil, "\"" .. other.name .. "\" is a built-in preset. Pick another name."
		end
		return nil, "You already have a preset called \"" .. other.name .. "\"."
	end
	return name
end

local function NewUserPreset(name, values, author, date_, gameVersion)
	local id = "u" .. ns.db.nextPresetId
	ns.db.nextPresetId = ns.db.nextPresetId + 1
	local p = {
		id = id, name = name, group = "Yours", builtin = false, values = values,
		author = author or ns.CharacterName(), date = date_ or date("%Y-%m-%d %H:%M"),
		gameVersion = gameVersion or GameVersion(),
	}
	local list = UserList()
	list[#list + 1] = p
	if ns.RefreshUI then ns.RefreshUI() end
	return p
end

----------------------------------------------------------------------
-- The API the Presets tab calls
----------------------------------------------------------------------

function ns.ListPresets()
	local user = {}
	for _, p in ipairs(UserList()) do user[#user + 1] = p end
	table.sort(user, function(a, b) return a.name:lower() < b.name:lower() end)
	return { builtin = Builtins(), user = user }
end

-- Every value a preset asks for, without applying it (built-ins worked out, yours as saved), as a copy
-- the caller may change. nil and "missing" if no such preset, nil and "damaged" if yours has no values
-- (only a hand-edited saved file does that). A built-in's hidden rows come from your before-Eye-Candy
-- values, else the game default. Applying it may land some lower: a menu setting is stepped down to
-- what the GPU supports, and the game may keep less of others (render scale, zoom).
-- Autotune starts from one this way: applying it would add a step to today's list and trip
-- Autotune's stop-on-change guard.
function ns.PresetValues(id)
	local p = ns.FindPreset(id)
	if not p then return nil, "missing" end
	local source = p.builtin and BuiltinValues(p) or p.values
	if type(source) ~= "table" then return nil, "damaged" end
	local values = {}
	for cvar, value in pairs(source) do values[cvar] = value end
	return values
end

-- Every setting on the addon's list, as it is now. In a city, your own values, not the ones the city
-- switch lowered (Situations.lua).
local function Snapshot()
	local values = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local value = ns.GetInfo(cvar)
		if value ~= nil and ns.SituationValue then value = ns.SituationValue(cvar, value) end
		if value ~= nil then values[cvar] = tostring(value) end
	end
	return values
end

function ns.SaveCurrentAsPreset(name)
	local clean, err = CheckNewName(name)
	if not clean then return nil, err end
	return NewUserPreset(clean, Snapshot())
end

function ns.RenamePreset(id, name)
	local p = ns.FindPreset(id)
	if not p then return nil, "No such preset." end
	if p.builtin then return nil, "Built-in presets can't be renamed. Duplicate it first." end
	local clean, err = CheckNewName(name, id)
	if not clean then return nil, err end
	p.name = clean
	if ns.RefreshUI then ns.RefreshUI() end
	return true
end

-- Works on built-ins too: the copy holds the values the built-in sets.
function ns.DuplicatePreset(id)
	local p = ns.FindPreset(id)
	if not p then return nil, "No such preset." end
	local values = ns.PresetValues(id)
	if not values then return nil, "That preset is damaged, so it can't be copied." end
	local copy = NewUserPreset(UniqueName(p.name), values)
	-- Your preset's note (Autotune's says where it was tested) goes with the copy.
	if not p.builtin and type(p.desc) == "string" then copy.desc = p.desc end
	return copy
end

function ns.DeletePreset(id)
	local p = ns.FindPreset(id)
	if not p then return nil, "No such preset." end
	if p.builtin then return nil, "Built-in presets can't be deleted." end
	local list = UserList()
	for i = #list, 1, -1 do
		if list[i].id == id then table.remove(list, i) end
	end
	if ns.RefreshUI then ns.RefreshUI() end
	return true
end

-- Applies straight away. Keeps it as one of today's steps first (no backup row), so Back to before can undo it.
function ns.ApplyPresetById(id)
	local p = ns.FindPreset(id)
	if not p then
		ns.Print("no such preset.")
		return false
	end
	if p.builtin then
		-- SetPreset and SetLook add their own step to today's list, refuse in combat, and (wrapped below)
		-- record the preset you are on.
		local ok
		if p.look then ok = ns.SetLook(p.look.key) == true
		elseif p.index > #ns.TIERS then ok = ns.ApplyShowcase() == true
		else ok = ns.SetPreset(p.index) == true end
		if ok and ns.RefreshUI then ns.RefreshUI() end
		return ok
	end
	if InCombatLockdown() then
		ns.Print("can't change presets in combat. Try again after the fight.")
		return false
	end
	-- The record first, so a Compare showing "before" ends before anything reads the settings.
	if ns.NoteBeforePreset then ns.NoteBeforePreset(p.name) end
	ns.TakeBackup(false)
	-- Your preset is a set of values, not tiers: clear the tiers, Extras and Look so nothing re-applies over it.
	wipe(ns.db.tiers)
	wipe(ns.db.extras)
	wipe(ns.db.advanced)
	ns.db.look = nil
	local scaleBefore = ns.GetInfo("RenderScale")
	local n, result
	local function Apply()
		n, result = ns.ApplyValues(p.values, true)
		-- Hidden values (not in the Graphics menu) that differ from the game default are kept applied, so
		-- closing Options (which can reset them) puts them back. ns.ApplyAdvanced re-applies any CVar in
		-- db.advanced, dial or not. The value kept is the one the client accepted.
		local _, visible = OptsByCVar()
		local managed = ManagedSet()
		for cvar in pairs(p.values) do
			if managed[cvar] and not visible[cvar] then
				local now, default = ns.GetInfo(cvar)
				if tonumber(now) and not ns.Same(now, default) then
					ns.db.advanced[cvar] = tonumber(now)
				end
			end
		end
		if ns.NoteApplied then ns.NoteApplied() end
	end
	-- In a city, what the preset raised past the switch's caps is lowered again, after the values above
	-- are kept as yours (Situations.lua).
	if ns.KeepSituationLowered then ns.KeepSituationLowered(Apply) else Apply() end
	ns.SaveMirror()
	ns.Print(string.format("applied your preset \"%s\" (%d settings).", p.name, n))
	for _, s in ipairs(result.skipped) do ns.Print("  " .. s) end
	for _, c in ipairs(result.changed) do ns.Print("  " .. c) end
	if scaleBefore and not ns.Same(scaleBefore, ns.GetInfo("RenderScale")) then
		ns.Print("Render scale changed. If the picture doesn't change, restart the game so it takes effect.")
	end
	ns.NoteOnPreset(p)
	if ns.RefreshUI then ns.RefreshUI() end
	return true
end

----------------------------------------------------------------------
-- The preset you are on, for the Presets tab's highlight
----------------------------------------------------------------------

-- ns.db.onPreset = { id, after = every managed setting as the preset left it }. The values the
-- game kept are recorded, so a value the client refused (render scale above what it allows) never
-- makes the preset look changed.
-- A restore clears it (Backups.lua), so a backup is never the preset you are on. Each of today's
-- steps keeps the one from before it, so Back puts it back.
function ns.NoteOnPreset(p)
	ns.db.onPreset = { id = p.id, after = Snapshot() }
end

-- A tier, Look or Showcase set from chat (/ec preset 3, /ec look moody) or the Hidden
-- tab skips ApplyPresetById, so the record is made here, after it worked. Core.lua loads first.
for _, fn in ipairs({ "SetPreset", "SetLook", "ApplyShowcase" }) do
	local core = ns[fn]
	if core then
		ns[fn] = function(a, ...)
			local ok = core(a, ...)
			if ok == true then
				local id
				if fn == "SetLook" then id = "look:" .. tostring(a)
				elseif fn == "ApplyShowcase" then id = "tier" .. (#ns.TIERS + 1)
				elseif select("#", ...) == 0 or (...) == nil then id = "tier" .. tostring(a) end -- SetPreset(i, look) is a Look's base
				local p = id and ns.FindPreset(id)
				if p then ns.NoteOnPreset(p) end
			end
			return ok
		end
	end
end

-- Returns the preset you are on and how many settings have changed since it was applied
-- (p, changed), or nil when there is none. In a city the lowered values count as yours
-- (ns.SituationValue), so the city switch never makes a preset look changed.
function ns.OnPreset()
	local on = ns.db.onPreset
	if ns.db.look and not (type(on) == "table" and on.id == "look:" .. ns.db.look) then
		local p = ns.FindPreset("look:" .. ns.db.look)
		if p then return p, 0 end
	end
	if type(on) ~= "table" or not on.id then return nil end
	local p = ns.FindPreset(on.id)
	if not p then return nil end -- deleted since
	local changed = 0
	for cvar, was in pairs(on.after or {}) do
		local now = ns.GetInfo(cvar)
		if now ~= nil and ns.SituationValue then now = ns.SituationValue(cvar, now) end
		if now ~= nil and not ns.Same(now, was) then changed = changed + 1 end
	end
	return p, changed
end

----------------------------------------------------------------------
-- Share strings
----------------------------------------------------------------------

local function Encoder()
	local E = C_EncodingUtil
	if type(E) ~= "table" or not (E.SerializeCBOR and E.CompressString and E.EncodeBase64
		and E.DeserializeCBOR and E.DecompressString and E.DecodeBase64) then
		return nil
	end
	return E
end

-- Only the settings that differ from the game default go in the string.
function ns.ExportPreset(id)
	local p = ns.FindPreset(id)
	if not p then return nil, "No such preset." end
	local E = Encoder()
	if not E then return nil, "This game version can't make share codes." end
	local source = p.builtin and BuiltinValues(p) or p.values
	local values = {}
	for cvar, value in pairs(source) do
		local _, default = ns.GetInfo(cvar)
		if default == nil or not ns.Same(value, default) then values[cvar] = tostring(value) end
	end
	local payload = {
		v = FORMAT, name = p.name, author = ns.CharacterName(), date = date("%Y-%m-%d %H:%M"),
		gameVersion = GameVersion(), values = values,
		-- Your preset's note travels with it. An older Eye Candy ignores the extra field.
		desc = (not p.builtin and type(p.desc) == "string" and p.desc ~= "") and p.desc or nil,
	}
	local ok, cbor = pcall(E.SerializeCBOR, payload)
	if not ok or type(cbor) ~= "string" then return nil, "Couldn't build the share code." end
	local ok2, packed = pcall(E.CompressString, cbor)
	if not ok2 or type(packed) ~= "string" then return nil, "Couldn't build the share code." end
	local ok3, text = pcall(E.EncodeBase64, packed)
	if not ok3 or type(text) ~= "string" or text == "" then return nil, "Couldn't build the share code." end
	return PREFIX .. text
end

local DAMAGED = "This string is damaged or cut short. Copy it again."

-- Open a share string. Returns the payload table, or nil and a reason.
local function Decode(text)
	if type(text) ~= "string" then return nil, "Paste an Eye Candy share code first." end
	if #text > TEXT_MAX then return nil, "This string is too long to be an Eye Candy preset." end
	text = text:gsub("%s+", "")
	if text == "" then return nil, "Paste an Eye Candy share code first." end
	local version = text:match("^!EC(%d+)!")
	if not version then return nil, "This isn't an Eye Candy share code." end
	if tonumber(version) > FORMAT then
		return nil, "This string was made by a newer Eye Candy. Update the addon to import it."
	end
	if tonumber(version) ~= FORMAT then return nil, "This isn't an Eye Candy share code." end
	local E = Encoder()
	if not E then return nil, "This game version can't read share codes." end
	local body = text:sub(#PREFIX + 1)
	local ok, packed = pcall(E.DecodeBase64, body)
	if not ok or type(packed) ~= "string" or packed == "" then return nil, DAMAGED end
	local ok2, cbor = pcall(E.DecompressString, packed)
	if not ok2 or type(cbor) ~= "string" or cbor == "" then return nil, DAMAGED end
	local ok3, payload = pcall(E.DeserializeCBOR, cbor)
	if not ok3 or type(payload) ~= "table" then return nil, DAMAGED end
	if type(payload.v) == "number" and payload.v > FORMAT then
		return nil, "This string was made by a newer Eye Candy. Update the addon to import it."
	end
	if payload.v ~= FORMAT then return nil, DAMAGED end
	if type(payload.name) ~= "string" or type(payload.values) ~= "table" then return nil, DAMAGED end
	local name = ns.CleanName(payload.name)
	if not name or name == "" then return nil, DAMAGED end
	return payload, nil, name
end

-- What a share string may set each CVar to. Graphics menu rows: whole numbers 0 to 10. Render scale:
-- the game's own limits. Dials: their slider range (or choice list, or 0/1). Extras: their options.
-- Other tier rows: between the lowest and highest tier value. Anything else on the list: +/-100000.
local function Limits()
	local lim = {}
	local function widen(cvar, v)
		v = tonumber(v)
		if not v then return end
		local l = lim[cvar] or {}
		l.lo, l.hi = math.min(l.lo or v, v), math.max(l.hi or v, v)
		lim[cvar] = l
	end
	local lo = (type(GetMinRenderScale) == "function") and GetMinRenderScale() or 0.33
	local hi = (type(GetMaxRenderScale) == "function") and GetMaxRenderScale() or 2
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, row in ipairs(cat.cvars) do
			if row.menu then
				lim[row[1]] = { lo = 0, hi = 10, int = true, fixed = true }
			elseif row.scale then
				lim[row[1]] = { lo = lo, hi = hi, fixed = true }
			else
				for t = 1, #ns.TIERS do widen(row[1], row[3][t]) end
			end
		end
	end
	for _, ex in ipairs(ns.EXTRAS) do
		if ex.scale then
			lim[ex.cvar] = { lo = lo, hi = hi, fixed = true }
		elseif not (lim[ex.cvar] and lim[ex.cvar].fixed) then
			for _, o in ipairs(ex.options) do widen(ex.cvar, o[1]) end
		end
	end
	for _, group in ipairs(ns.ADVANCED or {}) do
		for _, d in ipairs(group.rows) do
			if not (lim[d[1]] and lim[d[1]].fixed) then
				if d.kind == "toggle" then
					lim[d[1]] = { lo = 0, hi = 1, int = true }
				elseif d.kind == "choice" then
					lim[d[1]] = { set = d.values }
				else
					lim[d[1]] = { lo = d[3], hi = d[4] }
				end
			end
		end
	end
	return lim
end

local function GoodValue(cvar, value, lim)
	if type(value) ~= "string" and type(value) ~= "number" then return nil end
	local s = tostring(value)
	if #s > VALUE_MAX then return nil end
	if not (s:match("^%-?%d+%.?%d*$") or s:match("^%-?%.%d+$")) then return nil end
	local n = tonumber(s)
	if not n then return nil end
	local _, default = ns.GetInfo(cvar)
	if default ~= nil and ns.Same(n, default) then return s end
	local l = lim[cvar] or { lo = -100000, hi = 100000 }
	if l.set then
		for _, v in ipairs(l.set) do
			if ns.Same(v, n) then return s end
		end
		return nil
	end
	if n < l.lo - 1e-6 or n > l.hi + 1e-6 then return nil end
	if l.int and n ~= math.floor(n) then return nil end
	return s
end

-- Work out what an import would do. Settings the string leaves out are the game default, so the
-- result is the same preset the sharer had. Nothing is changed here.
local function Plan(text)
	local payload, err, name = Decode(text)
	if not payload then return nil, err end
	local managed = ManagedSet()
	local lim = Limits()
	local given, skipped, count = {}, {}, 0
	for key, value in pairs(payload.values) do
		count = count + 1
		if count > ENTRIES_MAX then return nil, "This string holds too many settings to be an Eye Candy preset." end
		local label = (type(key) == "string" or type(key) == "number") and CleanText(tostring(key), 60) or "(bad entry)"
		local good = type(key) == "string" and managed[key] and GoodValue(key, value, lim)
		if type(key) == "string" and managed[key] and good then
			given[key] = good
		else
			skipped[#skipped + 1] = label
		end
	end
	table.sort(skipped)
	local values, missing, changes = {}, {}, 0
	for cvar in pairs(managed) do
		local now, default = ns.GetInfo(cvar)
		if now ~= nil then
			local value = given[cvar] or (default ~= nil and tostring(default) or nil)
			if value ~= nil then
				values[cvar] = value
				if not ns.Same(now, value) then changes = changes + 1 end
			end
		elseif given[cvar] then
			missing[#missing + 1] = cvar
		end
	end
	table.sort(missing)
	local clash = ns.FindPresetByName(name)
	return {
		ok = true, name = name, author = CleanText(payload.author, 60) or "", date = CleanText(payload.date, 20) or "",
		gameVersion = CleanText(payload.gameVersion, 20) or "", desc = CleanText(payload.desc, DESC_MAX), changes = changes, skipped = skipped, missing = missing,
		clash = clash ~= nil, clashBuiltin = clash ~= nil and clash.builtin == true, values = values,
	}
end

-- { ok, err, name, author, date, gameVersion, desc, changes, skipped = { cvar, ... }, missing = { cvar, ... }, clash }
function ns.PreviewImport(text)
	local plan, err = Plan(text)
	if not plan then return { ok = false, err = err } end
	local preview = {}
	for k, v in pairs(plan) do
		if k ~= "values" then preview[k] = v end
	end
	return preview
end

-- mode: "replace" overwrites your preset with the same name; "keep" saves it as "Name (2)".
-- A built-in is never replaced. Saves the preset only: nothing changes until you press Apply on it,
-- so it works in combat too. Returns the saved preset, or nil and a reason.
function ns.ImportPreset(text, mode)
	local plan, err = Plan(text)
	if not plan then return nil, err end
	local existing = ns.FindPresetByName(plan.name)
	local p
	if existing and mode == "replace" and not existing.builtin then
		existing.values = plan.values
		existing.author, existing.date, existing.gameVersion = plan.author, plan.date, plan.gameVersion
		p = existing
	else
		p = NewUserPreset(UniqueName(plan.name), plan.values, plan.author, plan.date, plan.gameVersion)
	end
	p.desc = plan.desc ~= "" and plan.desc or nil
	if #plan.skipped > 0 then
		ns.Print(string.format("skipped %d settings that aren't on Eye Candy's graphics list: %s", #plan.skipped, table.concat(plan.skipped, ", ")))
	end
	ns.Print(string.format("imported \"%s\" as a new preset. Press Apply on it to use it.", p.name))
	if ns.RefreshUI then ns.RefreshUI() end
	return p
end

----------------------------------------------------------------------
-- Slash commands: /ec presets, save <name>, use <name>, share <name>
----------------------------------------------------------------------

-- What a step is called after "Back to before" and in Back's question: "Moody", "your own changes",
-- "you restored "Raid night"".
local function BackTarget(step)
	if step.kind == "own" then return "your own changes" end
	if step.kind == "restore" then return "you restored \"" .. tostring(step.name) .. "\"" end
	return tostring(step.name or "your last preset")
end
ns.BackTarget = BackTarget

-- A step's name on its row: what it was.
function ns.StepName(step)
	if step.kind == "restore" then return "Restored \"" .. tostring(step.name) .. "\"" end
	return tostring(step.name or "")
end

-- A step's grey line: what kind and when.
function ns.StepLine(step)
	local at = tostring(step.time or "")
	if step.kind == "own" then return "Settings you changed yourself after " .. at .. "." end
	if step.kind == "restore" then return "Backup restored at " .. at .. "." end
	return "Preset applied at " .. at .. "."
end

-- Back to before a step from today's list: a step from ns.BackSteps, its place there, or the newest
-- when nil. Puts back the settings from just before it; it and every newer step leave the list
-- (Backups.lua). You are back on the preset you were on before it. One line says what it did or why
-- it couldn't (the Presets card and /ec back both show it). Returns the change count or nil, then the line.
function ns.GoBack(step)
	if type(step) ~= "table" then step = ns.BackSteps()[step or 1] end
	if not step then return nil, "Nothing to go back to today. Apply a preset first." end
	local n, err = ns.RestoreStep(step)
	if not n then return nil, err end
	-- Your own changes undone: you are back where the newest step left you, so the preset you are on stays.
	if not step.live then ns.db.onPreset = step.on end
	if ns.RefreshUI then ns.RefreshUI() end
	return n, string.format("Back to before %s: %d %s put back.", BackTarget(step), n, n == 1 and "setting" or "settings")
end

function ns.PresetSlash(msg, raw)
	local verb = msg:match("^(%S+)")
	local rest = raw:match("^%S+%s+(.+)$")
	if verb == "back" and not rest then
		local _, line = ns.GoBack()
		ns.Print(line)
		return true
	elseif verb == "presets" and not rest then
		local all = ns.ListPresets()
		local names = {}
		for _, p in ipairs(all.builtin) do names[#names + 1] = p.name end
		ns.Print("built-in presets: " .. table.concat(names, ", "))
		names = {}
		for _, p in ipairs(all.user) do names[#names + 1] = p.name end
		ns.Print("your presets: " .. (#names > 0 and table.concat(names, ", ") or "none yet. Save one with /ec save <name>"))
		return true
	elseif verb == "save" and rest then
		local p, err = ns.SaveCurrentAsPreset(rest)
		ns.Print(p and ("saved your current settings as \"" .. p.name .. "\".") or err)
		return true
	elseif (verb == "use" or verb == "share") and rest then
		local p = ns.FindPresetByName(rest)
		if not p then
			ns.Print("no preset called \"" .. (ns.CleanName(rest) or "") .. "\". See /ec presets")
			return true
		end
		if verb == "use" then
			ns.ApplyPresetById(p.id)
			return true
		end
		local text, err = ns.ExportPreset(p.id)
		if not text then
			ns.Print(err)
			return true
		end
		ns.ShowText(text)
		-- Read the string straight back, so a fault in the game's encoder shows up here, not on a friend's PC.
		local check = ns.PreviewImport(text)
		if check.ok and check.name == p.name then
			ns.Print(string.format("share code for \"%s\": %d characters. It reads back correctly. Copy it from the box.", p.name, #text))
		else
			ns.Print("the share code did not read back (" .. tostring(check.err) .. "). Please report this with /ec report.")
		end
		return true
	end
	return false
end
