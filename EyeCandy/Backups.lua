-- Eye Candy: dated backups of every setting the addon manages.
-- Kinds: "original" (your settings before Eye Candy, kept forever) and "manual" (named by you).
-- Nothing else is listed. Back to before (Presets.lua) and Compare keep one record of their own,
-- EyeCandyDB.lastBefore, replaced by each preset (ns.NoteBeforePreset) and never shown as a backup.
-- Backups are account-wide (EyeCandyDB is account-wide) and record the character that made them.

local ADDON, ns = ...

local function List()
	return ns.db.backups
end

local function Find(id)
	for _, b in ipairs(List()) do
		if b.id == id then return b end
	end
end

function ns.OriginalBackup()
	if not (ns.db and ns.db.backups) then return nil end
	for _, b in ipairs(List()) do
		if b.kind == "original" then return b end
	end
end

-- Your own value for a setting the city switch has lowered (Situations.lua), else value as it is.
local function Own(cvar, value)
	if value ~= nil and ns.SituationValue then return ns.SituationValue(cvar, value) end
	return value
end

-- Every setting on the addon's list, as it is now. In a city, your own values, not the lowered ones.
local function Capture()
	local values = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local value = Own(cvar, ns.GetInfo(cvar))
		if value ~= nil then values[cvar] = tostring(value) end
	end
	return values
end

local function Copy(t)
	local out = {}
	for k, v in pairs(t or {}) do out[k] = v end
	return out
end

-- What Eye Candy itself had chosen, so a restore also puts the tiers, Extras, dials and Look back.
local function CaptureState()
	return { tiers = Copy(ns.db.tiers), extras = Copy(ns.db.extras), advanced = Copy(ns.db.advanced), look = ns.db.look }
end

-- The choices that were last applied. The tier buttons and Extras change ns.db before Apply is pressed,
-- so ns.db is not "before" at that moment: a backup stores these instead.
local applied

function ns.NoteApplied()
	applied = CaptureState()
	-- The first apply after a preset's "before" record (ns.NoteBeforePreset) is the preset itself:
	-- keep what it left, so /ec back (Presets.lua) can tell when anything has changed since,
	-- even a dial or a Standard row. Only that apply: a record loaded at login, or one from an older
	-- version, is never filled with whatever the game is at now.
	local last = ns.awaitingAfter
	ns.awaitingAfter = nil
	if last and last == ns.db.lastBefore then last.after = Capture() end
end

-- Has any managed setting changed from these values (a Capture())?
function ns.ChangedSince(values)
	for cvar, value in pairs(Capture()) do
		local was = values[cvar]
		if was ~= nil and not ns.Same(value, was) then return true end
	end
	return false
end

-- One Extra was applied on its own (the Standard tab sets it at once): record only that key, so tier
-- choices made but not yet applied stay out of the snapshot. value nil = the Extra was cleared.
-- Only an Extra in force (in the snapshot) or chosen now (in ns.db) is recorded, so the Standard tab
-- may call this for every Extra on a setting it changes. That covers an Extra set back to "Use tier"
-- but not applied yet: the snapshot still holds the old value, and now holds what the game is at.
-- With no snapshot yet, backups read ns.db as it is.
function ns.NoteAppliedExtra(key, value)
	if not applied then return end
	if applied.extras[key] ~= nil or ns.db.extras[key] ~= nil then applied.extras[key] = value end
end

-- Dials apply the moment they move, so those come from now.
local function AppliedState()
	local s = applied or CaptureState()
	return { tiers = Copy(s.tiers), extras = Copy(s.extras), advanced = Copy(ns.db.advanced), look = s.look }
end

-- CVars that Eye Candy's choices in force set: a tier row, an Extra or a dial.
local function ChosenCVars()
	local s = AppliedState()
	local chosen = {}
	for _, cat in ipairs(ns.CATEGORIES) do
		local tier = s.tiers[cat.key]
		if tier and tier > 0 then
			for _, row in ipairs(cat.cvars) do
				if row[3][tier] ~= nil then chosen[row[1]] = true end
			end
		end
	end
	for _, ex in ipairs(ns.EXTRAS) do
		if s.extras[ex.key] ~= nil then chosen[ex.cvar] = true end
	end
	for cvar in pairs(s.advanced) do chosen[cvar] = true end
	return chosen
end

-- The value from before Eye Candy, as best we can tell: the current value, unless one of
-- Eye Candy's choices already sets it, then the game default.
local function BeforeValue(cvar, chosen)
	local value, default = ns.GetInfo(cvar)
	if value == nil then return nil end
	if chosen[cvar] and default ~= nil then return tostring(default) end
	return tostring(value)
end

local function NewEntry(kind, label, values, state)
	local id = ns.db.nextBackupId
	ns.db.nextBackupId = id + 1
	local entry = {
		id = id, kind = kind, label = label, time = date("%Y-%m-%d %H:%M"), stamp = time(),
		character = ns.CharacterName and ns.CharacterName() or "", values = values, state = state,
	}
	local list = List()
	list[#list + 1] = entry
	return entry
end

-- The Original: your settings from before Eye Candy first changed anything. Made once, kept forever.
-- Settings that newer Eye Candy versions start managing are merged in with their value at that time.
-- Returns true if anything was added.
function ns.TakeBackup()
	local original = ns.OriginalBackup()
	local chosen = ChosenCVars()
	if not original then
		local values = {}
		for _, cvar in ipairs(ns.AllManagedCVars()) do
			values[cvar] = BeforeValue(cvar, chosen)
		end
		ns.FixDistantBackup(values)
		NewEntry("original", "Original settings", values, { tiers = {}, extras = {}, advanced = {} })
		ns.Print("saved your graphics settings from before Eye Candy as the Original backup. Type /reload once so it is saved for good.")
		return true
	end
	local added = false
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		if original.values[cvar] == nil then
			local value = BeforeValue(cvar, chosen)
			if value ~= nil then
				original.values[cvar] = value
				added = true
			end
		end
	end
	ns.FixDistantBackup(original.values)
	return added
end

----------------------------------------------------------------------
-- The API the Backups tab calls
----------------------------------------------------------------------

-- kind: "manual" only. Returns the new entry, or nil and a plain reason.
function ns.CreateBackup(kind, label)
	if kind ~= "manual" then
		return nil, "Only named backups can be made. The Original is made once, by itself."
	end
	ns.TakeBackup()
	label = ns.CleanName and ns.CleanName(label) or label
	if not label or label == "" then label = "Backup " .. date("%Y-%m-%d %H:%M") end
	local entry = NewEntry("manual", label, Capture(), AppliedState())
	if ns.RefreshUI then ns.RefreshUI() end
	return entry
end

-- Newest first. The Original is always in the list once made.
function ns.ListBackups()
	local out = {}
	for _, b in ipairs(List()) do out[#out + 1] = b end
	table.sort(out, function(a, b)
		if (a.stamp or 0) ~= (b.stamp or 0) then return (a.stamp or 0) > (b.stamp or 0) end
		return a.id > b.id
	end)
	return out
end

-- How many of a record's settings differ from now.
local function CountChanges(b)
	local managed = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do managed[cvar] = true end
	local n = 0
	for cvar, value in pairs(b.values or {}) do
		if managed[cvar] then
			local now = Own(cvar, ns.GetInfo(cvar))
			if now ~= nil and not ns.Same(now, value) then n = n + 1 end
		end
	end
	return n
end

function ns.CountBackupChanges(id)
	local b = Find(id)
	return b and CountChanges(b) or 0
end

-- Puts a backup, or the "before" record, back: settings and Eye Candy's own choices. Takes no
-- backup of where you are now, so a restore never adds a row. Returns how many settings changed,
-- or nil and a plain reason.
local function Restore(b)
	if type(b.values) ~= "table" then return nil, "That backup is damaged, so it can't be restored." end
	-- No chat here: the window shows the result where you clicked, and the slash commands print it.
	if InCombatLockdown() then
		return nil, "Can't restore in combat. Try again after the fight."
	end
	-- One step back only: after any restore, Back has nothing to return to, so it never undoes this.
	ns.db.lastBefore = nil
	ns.awaitingAfter = nil
	ns.TakeBackup()
	local changes = CountChanges(b)
	-- In a city, what the restore raises past the switch's caps is lowered again (Situations.lua).
	if ns.KeepSituationLowered then
		ns.KeepSituationLowered(ns.ApplyValues, b.values, false)
	else
		ns.ApplyValues(b.values, false)
	end
	local state = type(b.state) == "table" and b.state or {}
	wipe(ns.db.tiers)
	wipe(ns.db.extras)
	wipe(ns.db.advanced)
	for k, v in pairs(state.tiers or {}) do ns.db.tiers[k] = v end
	for k, v in pairs(state.extras or {}) do ns.db.extras[k] = v end
	for k, v in pairs(state.advanced or {}) do ns.db.advanced[k] = v end
	ns.db.look = state.look
	ns.NoteApplied()
	ns.SaveMirror()
	if ns.RefreshUI then ns.RefreshUI() end
	return changes
end

-- One line saying what a restore did, for the window and the slash commands.
function ns.RestoredLine(changes, b)
	return string.format("Restored %d %s from \"%s\" (%s).", changes, changes == 1 and "setting" or "settings",
		tostring(b and b.label or "backup"), tostring(b and b.time or "earlier"))
end

function ns.RestoreBackupById(id)
	local b = Find(id)
	if not b then return nil, "No such backup." end
	return Restore(b)
end

----------------------------------------------------------------------
-- The one "before" record: Back to before and Compare
----------------------------------------------------------------------

-- Called just before a preset (built-in, your own or an import) changes anything. Replaces the
-- last record, so there is only ever one step back. The preset's own apply then fills in .after
-- (ns.NoteApplied). Saved with EyeCandyDB, so Back still works after a /reload.
function ns.NoteBeforePreset(name)
	name = tostring(name or "your last preset")
	ns.db.lastBefore = {
		name = name, label = "Before " .. name, time = date("%Y-%m-%d %H:%M"), stamp = time(),
		values = Capture(), state = AppliedState(),
	}
	ns.awaitingAfter = ns.db.lastBefore
	return ns.db.lastBefore
end

-- The record, if it can still be restored (nil otherwise).
function ns.BeforeRecord()
	local last = ns.db and ns.db.lastBefore
	if type(last) == "table" and type(last.values) == "table" then return last end
end

-- Puts back the settings from just before the last preset. Presets.lua checks first that nothing
-- has changed since (BackTarget). Returns the count restored, or nil and a plain reason.
function ns.RestoreBefore()
	local last = ns.BeforeRecord()
	if not last then return nil, "Nothing to go back to. Apply a preset first." end
	return Restore(last)
end

-- The Original can never be deleted.
function ns.DeleteBackup(id)
	local b = Find(id)
	if not b then return nil, "No such backup." end
	if b.kind == "original" then return nil, "The Original backup is kept for good, so it can't be deleted." end
	local list = List()
	for i = #list, 1, -1 do
		if list[i].id == id then table.remove(list, i) end
	end
	if ns.RefreshUI then ns.RefreshUI() end
	return true
end

-- /ec restore: put back the settings from before Eye Candy (the Original).
function ns.RestoreBackup()
	local original = ns.OriginalBackup()
	if not original then
		ns.Print("no backup saved yet.")
		return
	end
	local n, err = ns.RestoreBackupById(original.id)
	ns.Print(n and ns.RestoredLine(n, original) or err)
	return n, err
end

----------------------------------------------------------------------
-- Saved data
----------------------------------------------------------------------

-- Test builds of 1.0.0 made an automatic backup before every preset, Apply, import and restore.
-- They are removed: nobody chose to keep them, they were already thrown away after 20, and keeping
-- them would leave the clutter this change is for. Back's record still points at one of them by id,
-- so its settings are copied into the record first, and Back keeps working across the update.
local function DropAutomatic(db)
	local last = db.lastBefore
	local n = 0
	for i = #db.backups, 1, -1 do
		local b = db.backups[i]
		if type(b) ~= "table" then
			table.remove(db.backups, i) -- a damaged entry: nothing in it could be restored
		elseif b.kind == "auto" then
			if type(last) == "table" and last.id ~= nil and last.id == b.id and type(last.values) ~= "table" then
				last.values, last.state = b.values, b.state
				last.label, last.time, last.stamp = b.label, b.time, b.stamp
			end
			table.remove(db.backups, i)
			n = n + 1
		end
	end
	if type(last) == "table" then
		last.id = nil
		if type(last.values) ~= "table" then db.lastBefore = nil end
	elseif last ~= nil then
		db.lastBefore = nil
	end
	if n > 0 then
		ns.Print(string.format("removed %d automatic backups. Eye Candy no longer makes them. Your Original and named backups are kept.", n))
	end
	return n
end

-- Called from ns.LoadDB.
function ns.LoadBackups()
	local db = ns.db
	db.backups = db.backups or {}
	db.nextBackupId = db.nextBackupId or 1
	DropAutomatic(db)
	local original = ns.OriginalBackup()
	if original and ns.FixDistantBackup(original.values) > 0 then
		ns.Print("corrected your Restore backup: Distant Detail will now restore to the Graphics menu's values.")
	end
	-- At load, the saved choices are what is in force (the login re-apply puts them back).
	ns.NoteApplied()
end

-- First install: save the Original once the game has settled after login.
local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:SetScript("OnEvent", function(_, event, isLogin, isReload)
	if event == "PLAYER_ENTERING_WORLD" and (isLogin or isReload) and ns.db and not ns.OriginalBackup() then
		-- Same delay as the login re-apply: account settings from the server can land a moment after login.
		C_Timer.After(4, function()
			if not ns.OriginalBackup() then ns.TakeBackup() end
		end)
	end
end)

----------------------------------------------------------------------
-- Slash commands: /ec backups, backup [name], restore <number>
----------------------------------------------------------------------

function ns.BackupSlash(msg, raw)
	local verb = msg:match("^(%S+)")
	local rest = raw:match("^%S+%s+(.+)$")
	-- Numbers are each backup's own id, so a backup added in between never shifts them.
	if verb == "backups" then
		for _, b in ipairs(ns.ListBackups()) do
			-- The same words, in the same order, as the Backups tab rows: the count first. Chat has room,
			-- so it gives the full Name-Realm the row keeps for its tooltip.
			local n = ns.CountBackupChanges(b.id)
			local kind = b.kind == "original" and "Original, kept for good" or "Manual"
			local label = (b.label and b.label ~= "") and b.label or kind
			ns.Print(string.format("%d. %s  (%s, %s, %s%s)", b.id, label,
				n == 0 and "matches now" or (n == 1 and "1 setting differs" or (n .. " settings differ")),
				kind,
				b.time or "?",
				(b.character and b.character ~= "") and (", " .. b.character) or ""))
		end
		ns.Print("restore one with /ec restore <number>")
		return true
	elseif verb == "backup" then
		local b, err = ns.CreateBackup("manual", rest)
		ns.Print(b and ("made a backup: \"" .. b.label .. "\".") or (err or "couldn't make a backup."))
		return true
	elseif verb == "restore" and rest then
		local n = tonumber(rest)
		if not (n and Find(n)) then
			ns.Print("no backup number " .. tostring(rest) .. ". See /ec backups")
			return true
		end
		local changes, err = ns.RestoreBackupById(n)
		ns.Print(changes and ns.RestoredLine(changes, Find(n)) or err)
		return true
	end
	return false
end
