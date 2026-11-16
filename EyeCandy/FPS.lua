-- Eye Candy: the FPS reader (ns.FPS), the live FPS number on the main window's bottom bar, and the FPS
-- each preset gave last time.
--
-- The reader counts frames on its own frame's OnUpdate, and only while someone watches it. Each frame
-- costs two additions and a compare. Twice a second (FPS.EVERY) it makes one reading and calls every
-- watcher with it. With no watcher its frame is hidden, so it costs nothing at all.
--
--   ns.FPS.Watch(key, fn)  start watching. fn(now, raw, frames, seconds, longest) runs at each reading:
--                          now = smoothed FPS, raw = this reading's FPS (frames / seconds), longest = the
--                          longest frame in it, in seconds (a hitch shows here). Watching again with the same
--                          key replaces fn. fn may unwatch itself; it must not watch a new key.
--   ns.FPS.Unwatch(key)    stop. The last watcher out stops the reader.
--   ns.FPS.Now()           the smoothed FPS, or nil while nobody watches (or before the first reading).
--   ns.FPS.Smooth(prev, raw), ns.FPS.Shown(shown, now)   the pure parts, for a number of your own.
--
-- A preset applied (ns.NoteOnPreset, Presets.lua) starts one measurement: once you stand still out of a
-- fight and FPS settles, 4 seconds of frames give the FPS it gave, kept with the zone in
-- EyeCandyDB.presetFPS[id] = { fps, zone, at }. The preset's tooltip shows it (ns.FPS.PresetLine).

local _, ns = ...

local FPS = {}
ns.FPS = FPS

FPS.EVERY = 0.5   -- seconds in one reading
FPS.SMOOTH = 0.5  -- each reading moves the smoothed number this share of the way to the new one
FPS.STEP = 0.75   -- the shown number moves once the smoothed one is this far from it

-- The smoothed FPS after one more reading. The first reading stands alone.
function FPS.Smooth(prev, raw)
	if not prev then return raw end
	return prev + (raw - prev) * FPS.SMOOTH
end

-- The whole number to show. It stays put until the smoothed number is FPS.STEP away, so 62.4, 62.6,
-- 62.4 never flickers between 62 and 63, and a steady 120 still reaches 120.
function FPS.Shown(shown, now)
	if not now then return nil end
	if shown and math.abs(now - shown) < FPS.STEP then return shown end
	return math.floor(now + 0.5)
end

----------------------------------------------------------------------
-- The reader
----------------------------------------------------------------------

local watchers, count = {}, 0
local frames, spent, longest = 0, 0, 0
local frame = CreateFrame("Frame")
frame:Hide()
FPS.frame = frame

function FPS.Tick(elapsed)
	elapsed = tonumber(elapsed) or 0
	frames, spent = frames + 1, spent + elapsed
	if elapsed > longest then longest = elapsed end
	if spent < FPS.EVERY then return end
	local n, t, long = frames, spent, longest
	frames, spent, longest = 0, 0, 0
	local raw = n / t
	FPS.now = FPS.Smooth(FPS.now, raw)
	local now = FPS.now
	for _, fn in pairs(watchers) do fn(now, raw, n, t, long) end
end
frame:SetScript("OnUpdate", function(_, elapsed) FPS.Tick(elapsed) end)

function FPS.Watch(key, fn)
	if watchers[key] == nil then
		count = count + 1
		if count == 1 then
			frames, spent, longest, FPS.now = 0, 0, 0, nil
			frame:Show()
		end
	end
	watchers[key] = fn
end

function FPS.Unwatch(key)
	if watchers[key] == nil then return end
	watchers[key] = nil
	count = count - 1
	if count == 0 then
		frame:Hide()
		FPS.now = nil
	end
end

function FPS.Now() return FPS.now end

function FPS.IsWatching(key)
	if key then return watchers[key] ~= nil end
	return count > 0
end

----------------------------------------------------------------------
-- The live number on the bottom bar
----------------------------------------------------------------------

-- Shows "63 FPS" in text while window is open. The string is built only when the number changes.
-- fits (optional): false hides the number for now (the shrunk bar's title can need the room).
function FPS.ShowOn(text, window, fits)
	local shown
	local function Draw(now)
		local n = FPS.Shown(shown, now)
		if n ~= shown then
			shown = n
			text:SetText(n and (n .. " FPS") or "")
		end
		if fits then text:SetShown(fits() ~= false) end
	end
	local function On()
		shown = nil
		text:SetText("")
		FPS.Watch("bar", Draw)
	end
	-- Alt+Z hides the window's parent, so the window still counts as shown: keep reading.
	local function Off(self)
		if self:IsShown() then return end
		FPS.Unwatch("bar")
	end
	window:HookScript("OnShow", On)
	window:HookScript("OnHide", Off)
	if window:IsShown() then On() end
end

----------------------------------------------------------------------
-- The FPS a preset gave last time
----------------------------------------------------------------------

-- Settling and hitches as Autotune judges them (Autotune.lua): two readings within 3% after at least
-- SETTLE_MIN seconds, at most SETTLE_MAX. A long frame (over 50 ms and 4 x the others) is left out, as
-- long as no more than 1% of the frames are. GIVE_UP: a measurement not done by then is dropped.
local AT = ns.Autotune or {}
FPS.SETTLE_MIN, FPS.SETTLE_MAX = 3, 10
FPS.AGREE = AT.SETTLE_AGREE or 0.03
FPS.SAMPLE = AT.SAMPLE or 4
FPS.HITCH, FPS.TRIM = AT.HITCH or 0.05, AT.TRIM or 4
FPS.GIVE_UP = 60

function FPS.NewMeasure(id)
	return { id = id, phase = "settle", waited = 0, total = 0, frames = 0, spent = 0, cut = 0, cutTime = 0 }
end

-- One reading into measurement m. still: you stood still, out of a fight, for all of it.
-- Returns nil (carry on), "done" (m.fps is the result) or "gave up".
function FPS.MeasureStep(m, raw, n, t, long, still)
	m.total = m.total + t
	if not still then
		-- Start again from the settling: what came before measured something else.
		m.phase, m.waited, m.prev = "settle", 0, nil
		m.frames, m.spent, m.cut, m.cutTime = 0, 0, 0, 0
		return m.total >= FPS.GIVE_UP and "gave up" or nil
	end
	if m.phase == "settle" then
		m.waited = m.waited + t
		local agree = m.prev and m.prev > 0 and math.abs(raw - m.prev) / m.prev <= FPS.AGREE
		m.prev = raw
		if (agree and m.waited >= FPS.SETTLE_MIN) or m.waited >= FPS.SETTLE_MAX then
			m.phase = "sample"
		end
		return m.total >= FPS.GIVE_UP and "gave up" or nil
	end
	m.frames, m.spent = m.frames + n, m.spent + t
	if n > 1 and long > math.max(FPS.HITCH, FPS.TRIM * (t - long) / (n - 1)) then
		m.cut, m.cutTime = m.cut + 1, m.cutTime + long
	end
	if m.spent >= FPS.SAMPLE then
		local trim = m.cut <= math.max(1, math.floor(m.frames * 0.01))
		m.fps = trim and (m.frames - m.cut) / (m.spent - m.cutTime) or m.frames / m.spent
		return "done"
	end
	return m.total >= FPS.GIVE_UP and "gave up" or nil
end

local function Call(f, ...)
	if type(f) ~= "function" then return nil end
	local ok, a = pcall(f, ...)
	if ok then return a end
end

-- Standing still, out of a fight, with nothing else moving the settings: what Autotune refuses, looked
-- at twice a second. Holding the left button counts as moving (dragging the camera, or a slider).
function FPS.Still(m)
	if InCombatLockdown() then return false end
	if Call(IsPlayerMoving) then return false end
	if SettingsPanel and SettingsPanel.IsShown and SettingsPanel:IsShown() then return false end
	if Call(IsMouselooking) or Call(IsMouseButtonDown, "LeftButton") then return false end
	if ns.IsComparing and ns.IsComparing() then return false end
	if AT.IsRunning and AT.IsRunning() then return false end
	local still = true
	local facing, zoom = Call(GetPlayerFacing), Call(GetCameraZoom)
	if type(facing) == "number" then
		if m.facing and math.abs(facing - m.facing) > 0.05 then still = false end
		m.facing = facing
	end
	if type(zoom) == "number" then
		if m.zoom and math.abs(zoom - m.zoom) > 1 then still = false end
		m.zoom = zoom
	end
	return still
end

-- The subzone (Goldshire), or the zone where there is none.
function FPS.Where()
	for _, f in ipairs({ GetSubZoneText, GetRealZoneText, GetZoneText }) do
		local s = Call(f)
		if type(s) == "string" and s ~= "" then return s end
	end
end

local measure

local function Store(m)
	-- Only if the preset is still on, with nothing changed since.
	if ns.OnPreset then
		local p, changed = ns.OnPreset()
		if not p or p.id ~= m.id or (changed or 0) > 0 then return end
	end
	ns.db.presetFPS = type(ns.db.presetFPS) == "table" and ns.db.presetFPS or {}
	ns.db.presetFPS[m.id] = { fps = math.floor(m.fps + 0.5), zone = FPS.Where(), at = time() }
end

local function OnReading(_, raw, n, t, long)
	local m = measure
	if not m then return FPS.Unwatch("preset") end
	local result = FPS.MeasureStep(m, raw, n, t, long, FPS.Still(m))
	if not result then return end
	measure = nil
	FPS.Unwatch("preset")
	if result == "done" then Store(m) end
end

-- Measure what preset id gives. A new preset starts over.
function FPS.Measure(id)
	measure = FPS.NewMeasure(id)
	FPS.Watch("preset", OnReading)
end

function FPS.Measuring() return measure and measure.id end

function FPS.StopMeasure()
	measure = nil
	FPS.Unwatch("preset")
end

-- "Last time: 63 FPS in Goldshire." for the preset's tooltip, or nil.
function FPS.PresetLine(id)
	local all = ns.db and ns.db.presetFPS
	local r = type(all) == "table" and all[id]
	local fps = type(r) == "table" and tonumber(r.fps)
	if not fps then return nil end
	if type(r.zone) == "string" and r.zone ~= "" then
		return string.format("Last time: %d FPS in %s.", fps, r.zone)
	end
	return string.format("Last time: %d FPS.", fps)
end

-- Every preset applied, built-in or yours (Presets.lua records it here).
local note = ns.NoteOnPreset
if note then
	ns.NoteOnPreset = function(p, ...)
		note(p, ...)
		if type(p) == "table" and p.id then FPS.Measure(p.id) end
	end
end

-- A deleted preset's number goes with it.
local delete = ns.DeletePreset
if delete then
	ns.DeletePreset = function(id, ...)
		local ok, err = delete(id, ...)
		if ok and ns.db and type(ns.db.presetFPS) == "table" then ns.db.presetFPS[id] = nil end
		return ok, err
	end
end

-- A loading screen ends a measurement: the place it measured is gone.
local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(_, event)
	if event == "PLAYER_LEAVING_WORLD" and measure then FPS.StopMeasure() end
end)
pcall(events.RegisterEvent, events, "PLAYER_LEAVING_WORLD")
