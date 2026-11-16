-- Eye Candy: Steady FPS, a part of the Experimental tab. Off until you turn it on. When FPS stays under
-- your goal, it lowers render scale a little. When FPS comes back well over it, it raises render scale
-- again, never past your own.
--
-- Why it changes so seldom: a change of render scale can hitch. A Blizzard forum report of 2 Sep 2024
-- ("Changing RenderScale causes certain frames to hang") says that after a render scale change, the map,
-- bags and character window hitch the next time they open, and that the game's own slider does it too.
-- That addon changed render scale every 5 seconds. This one changes it only after FPS has been past the
-- goal for 5 seconds (SUSTAIN), at most once every 30 seconds (GAP), 5% at a time (STEP), never under
-- 70% (FLOOR). Those numbers are a choice, not measured.
--
-- The game has its own one, hidden: the DynamicRenderScale setting. Its own text says it is in beta and
-- "may cause hitching" (Ketho's BlizzardInterfaceResources, branch forever, CVars.lua). So the page names
-- it as another way, with no switch.
--
-- A step that didn't help (FPS less than 3% better 3 to 8 seconds after it) means render scale isn't what
-- holds FPS back here. Then it stops lowering, puts that step back once the gap is over, and says so. A
-- loading screen lets it try again. A raise that drops FPS under the goal again is undone once, and then
-- it stops raising there, so it never goes up and down all day.
--
-- Goals go up to 300, the common screen rates (144, 165, 180, 240, 300) after the usual ones.
--
-- FPS limits. The game has an FPS limit for the front (useMaxFPS and maxFPS: default off and 120) and one for
-- the back (useMaxFPSBk and maxFPSBk: default on and 30); the defaults are from Ketho's CVars.lua, branch
-- forever. The live values are read at each reading (ns.GetInfo), not Config.wtf. A front limit under the goal
-- is the goal (and the page says so). In the back, FPS sits at the back limit whatever render scale is, so
-- lowering would find "didn't help" and stop for the session. There is no API for window focus (none is
-- documented; the Alt-Tab Toggle addon infers it from OnUpdate stopping, or from low FPS in a window), so
-- this infers it: the back limit is on, it is under the low line of the goal, and FPS sits at it or just
-- under it (SF.CAP_NEAR, and then up to the same distance over it). Then nothing changes and nothing is
-- judged, and the page says why. Back in front, FPS is not read for SF.SETTLE seconds, because the smoothed
-- FPS still holds the low readings. A real FPS of exactly the back limit in front is taken as the back:
-- a guess that costs a missed lowering, never a wrong one.
--
-- Target FPS (targetFPS, useTargetFPS: default 60 and on) is the game's own: "Dynamic actions will be taken
-- if you fall below the FPS target" (Ketho's CVars.lua). What those actions are isn't documented, and
-- nothing found (16 Nov 2026) says it sets RenderScale, so it is not held back, but that is a guess. What is
-- documented is DynamicRenderScale ("Lowers render scale if GPU bound to hit Target FPS ... May cause
-- hitching", same file): that one moves render scale too, so while it is on, this waits.
--
-- It never changes anything in a fight, or while Autotune, Compare, Peek, photo mode or the eye test is on.
-- Backups, presets, Back and the patch warning see your own render scale, not the lowered one
-- (ns.SituationValue). Logging out puts your own back, so the game saves yours.
--
-- Render scale can be set in a fight (RenderScale isn't a secure setting on Forever: Ketho's CVars.lua),
-- but Eye Candy doesn't change settings in a fight.

local _, ns = ...
local SF = {}
ns.SteadyFPS = SF

SF.LOW, SF.HIGH = 0.9, 1.25   -- under 90% of the goal is low; over 125% is room to raise one step
SF.SUSTAIN = 5                -- seconds past the goal before it changes anything
SF.GAP = 30                   -- seconds, at least, between two changes
SF.STEP, SF.FLOOR = 0.05, 0.7 -- one step of render scale, and the lowest it goes
SF.SKIP, SF.JUDGE, SF.HELP = 3, 5, 0.03 -- after a step down: skip 3 s, then 5 s of FPS must be 3% better
SF.HITCH_FOR = 2              -- seconds after a change in which the longest frame is its hitch
SF.CAP_NEAR = 0.97            -- FPS this close to a cap is held there by the cap
SF.SETTLE = 3                 -- seconds after the game comes back to the front before FPS is read again
SF.GOALS = { 30, 45, 60, 75, 90, 120, 144, 165, 180, 240, 300 }
SF.GOAL = 60
SF.PER_ROW = 6                -- goal buttons in one row on the page

local function Round(x) return math.floor(x * 100 + 0.5) / 100 end

----------------------------------------------------------------------
-- The steps (pure)
----------------------------------------------------------------------

-- A fresh state, at your own render scale.
function SF.New(own)
	return { own = own, scale = own, clock = 0, lowFor = 0, highFor = 0, lowFrames = 0, lowTime = 0, changes = 0 }
end

local function Changed(s, to, why, now)
	s.scale, s.last, s.lastWhy = to, s.clock, why
	s.changes = s.changes + 1
	s.lowFor, s.highFor, s.lowFrames, s.lowTime = 0, 0, 0, 0
	s.hitchFor, s.hitch, s.hitchNormal = SF.HITCH_FOR, 0, now and now > 0 and 1 / now or nil
	return to, why
end

-- One reading. r: { now (smoothed FPS), raw, frames, seconds, long (longest frame), goal, free (nothing holds
-- it back), top (an FPS limit, or nil), bk (the background FPS limit, or nil), vsync }. Returns the render scale to set and why ("lower", "raise",
-- "back"), or nil.
function SF.Step(s, r)
	local t = r.seconds or 0
	s.clock = s.clock + t
	-- The hitch from the last change.
	if s.hitchFor then
		s.hitch = math.max(s.hitch or 0, r.long or 0)
		s.hitchFor = s.hitchFor - t
		if s.hitchFor <= 0 then
			s.hitchFor = nil
			s.lastHitch = s.hitch
			if not s.biggest or s.hitch > s.biggest then s.biggest, s.normal = s.hitch, s.hitchNormal end
		end
	end
	-- The game in the background, held at its background FPS limit: that FPS says nothing about render scale.
	-- It is held at the limit when FPS sits at it or just under it (once it does, any FPS up to just over the
	-- limit keeps it so), and the limit is under the low line of the goal.
	local goal0 = r.goal or SF.GOAL
	if r.top and r.top < goal0 then goal0 = r.top end
	local bk = r.bk and r.bk > 0 and r.bk < goal0 * SF.LOW and r.bk or nil
	local raw = r.raw or r.now or 0
	local wasBk = s.bk
	s.bk = bk ~= nil and raw <= bk / SF.CAP_NEAR and (wasBk or raw >= bk * SF.CAP_NEAR) or false
	s.top = r.top
	-- Back in front: the smoothed FPS still holds the low readings, so it is not read for a moment.
	if wasBk and not s.bk then s.settle = SF.SETTLE end
	local free = r.free
	if s.bk then
		free = false
	elseif s.settle and s.settle > 0 then
		s.settle = s.settle - t
		free = false
	else
		s.settle = nil
	end
	-- Did the last step down help?
	local j = s.judge
	if j then
		if not free then
			s.judge = nil -- held back: what it would measure isn't the step
		elseif j.skip > 0 then
			j.skip = j.skip - t
		else
			j.frames, j.time = j.frames + (r.frames or 0), j.time + t
			if j.time >= SF.JUDGE then
				s.judge = nil
				if j.frames / j.time < j.before * (1 + SF.HELP) then
					s.stuck, s.back = true, j.from
				end
			end
		end
	end
	if not free then
		s.lowFor, s.highFor, s.lowFrames, s.lowTime = 0, 0, 0, 0
		return nil
	end
	-- With an FPS limit under the goal, the limit is as good as it gets. With a cap (a limit, or Vertical
	-- Sync), FPS held at it is room to raise.
	local goal = r.goal or SF.GOAL
	if r.top and r.top < goal then goal = r.top end
	local highAt = goal * SF.HIGH
	if r.top then highAt = math.min(highAt, r.top * SF.CAP_NEAR) end
	if r.vsync then highAt = math.min(highAt, goal * SF.CAP_NEAR) end
	local now = r.now or 0
	if now < goal * SF.LOW then
		s.lowFor, s.lowFrames, s.lowTime = s.lowFor + t, s.lowFrames + (r.frames or 0), s.lowTime + t
	else
		s.lowFor, s.lowFrames, s.lowTime = 0, 0, 0
	end
	s.highFor = now >= highAt and s.highFor + t or 0
	if s.last and s.clock - s.last < SF.GAP then return nil end
	if s.back then
		local to = s.back
		s.back = nil
		if math.abs(to - s.scale) > 0.001 then return Changed(s, to, "back", now) end
	end
	local floor = SF.FLOOR
	if s.lowFor >= SF.SUSTAIN and not s.stuck and s.scale > floor + 0.001 then
		local from, before = s.scale, s.lowTime > 0 and s.lowFrames / s.lowTime or now
		local to = Round(math.max(floor, s.scale - SF.STEP))
		if s.lastWhy == "raise" then s.ceiling = to end
		s.judge = { from = from, before = before, skip = SF.SKIP, frames = 0, time = 0 }
		return Changed(s, to, "lower", now)
	end
	local top = s.own
	if s.ceiling and s.ceiling < top then top = s.ceiling end
	if s.highFor >= SF.SUSTAIN and s.scale < top - 0.001 then
		return Changed(s, Round(math.min(top, s.scale + SF.STEP)), "raise", now)
	end
	return nil
end

-- Someone else set render scale (you, a preset, Autotune): that is your own now. It counts as a change.
function SF.Adopt(s, scale)
	s.own, s.scale, s.last = scale, scale, s.clock
	s.ceiling, s.back, s.judge, s.stuck, s.lastWhy = nil, nil, nil, nil, nil
	s.lowFor, s.highFor, s.lowFrames, s.lowTime = 0, 0, 0, 0
end

-- A loading screen: a new place, so it may try lowering and raising again.
function SF.NewPlace(s)
	s.stuck, s.ceiling, s.judge, s.lastWhy = nil, nil, nil, nil
	s.lowFor, s.highFor, s.lowFrames, s.lowTime = 0, 0, 0, 0
end

----------------------------------------------------------------------
-- In the game
----------------------------------------------------------------------

local state -- SF.New(...) while it is on
local session = { changes = 0 } -- this session: changes made, biggest hitch and a normal frame then
local busy = false -- true while it sets render scale itself

local function Refresh()
	if ns.RefreshUI then ns.RefreshUI() end
end

local function DB()
	ns.db.steady = type(ns.db.steady) == "table" and ns.db.steady or {}
	return ns.db.steady
end

local function Scale()
	return tonumber((GetCVar("RenderScale")))
end

local function Num(cvar)
	return ns.Exists(cvar) and tonumber((ns.GetInfo(cvar))) or nil
end

function SF.Goal()
	local g = ns.db and type(ns.db.steady) == "table" and tonumber(ns.db.steady.goal)
	for _, x in ipairs(SF.GOALS) do
		if x == g then return g end
	end
	return SF.GOAL
end

function SF.IsOn() return state ~= nil end
function SF.State() return state end

-- What holds it back now, as words for "Waiting: ...", or nil. fight: true when that is a fight.
function SF.HeldBy()
	if InCombatLockdown() then return "you are in a fight", true end
	local AT = ns.Autotune
	if AT and AT.IsRunning and AT.IsRunning() then return "Autotune is running" end
	if ns.IsComparing and ns.IsComparing() then return "Compare is on" end
	if ns.PhotoMode and ns.PhotoMode.IsOn() then return "photo mode is on" end
	if ns.EyeTest and ns.EyeTest.IsOn() then return "the eye test is on" end
	if ns.IsPeeking and ns.IsPeeking() then return "Peek is on" end
	local db = ns.db or {}
	if db.autotune then return "Autotune has your settings until you keep or undo its result" end
	if db.photo then return "photo mode has your settings" end
	if db.eyeTest then return "the eye test has your settings" end
	return nil
end

-- Sets render scale, and keeps what the game took (it may clamp it).
local function Set(to)
	busy = true
	SetCVar("RenderScale", ns.ClampRenderScale and ns.ClampRenderScale(to) or to)
	busy = false
	return Scale() or to
end

local function Is(a, b)
	a, b = tonumber(a), tonumber(b)
	return a ~= nil and b ~= nil and math.abs(a - b) < 0.001
end

-- Autotune, photo mode, the eye test and Compare saved the settings to put back when they end. Where
-- they saved the lowered render scale, they put back your own instead.
local function MendSaved(set, own)
	local db = ns.db or {}
	for _, saved in ipairs({ db.autotune and db.autotune.before, db.photo and db.photo.before,
		db.eyeTest and db.eyeTest.before, db.compare and db.compare.now }) do
		if type(saved) == "table" and Is(saved.RenderScale, set) then saved.RenderScale = tostring(own) end
	end
end

local PutBack

-- Your own goes back once what held it puts the lowered value back (Compare keeps its own copy).
local function WaitToPutBack()
	if ns.FPS then ns.FPS.Watch("steadyBack", function()
		if SF.HeldBy() then return end
		ns.FPS.Unwatch("steadyBack")
		PutBack()
	end) end
end

-- Your own render scale back. Not in a fight. Returns true when it is back (or was never lowered).
PutBack = function()
	local db = ns.db and ns.db.steady
	if not (type(db) == "table" and db.set) then return true end
	if InCombatLockdown() then
		db.afterCombat = true
		return false
	end
	local own, set, cur = tonumber(db.own), tonumber(db.set), Scale()
	if own then MendSaved(set, own) end
	if Is(cur, set) then
		if own then Set(own) end
	elseif SF.HeldBy() then
		-- Autotune, photo mode or another has render scale for now: the value is theirs. Wait for them.
		WaitToPutBack()
		return false
	end
	-- Otherwise someone set another value since: that one is yours.
	db.set, db.afterCombat = nil, nil
	if state and own then state.scale = Scale() or own end
	return true
end

local function OnReading(now, raw, frames, seconds, long)
	local s = state
	if not s then return ns.FPS.Unwatch("steady") end
	local db = DB()
	-- The game's own Dynamic Render Scale also moves render scale to chase Target FPS: not at the same time.
	local dyn = Num("DynamicRenderScale") == 1
	local free = SF.HeldBy() == nil and not dyn
	local cur = Scale()
	-- Changed by someone else: yours now. Only while nothing holds it back: Autotune, photo mode and the
	-- others put theirs back when they end.
	if free and cur and math.abs(cur - s.scale) > 0.001 then
		SF.Adopt(s, cur)
		db.own, db.set = cur, nil
		Refresh()
		return
	end
	local top = Num("useMaxFPS") == 1 and Num("maxFPS") or nil
	if top and top <= 0 then top = nil end
	local bk = Num("useMaxFPSBk") == 1 and Num("maxFPSBk") or nil
	local vsync = Num("vsync") == 1
	local hitch, stuck, held, wasBk, wasTop, wasDyn = s.biggest, s.stuck, s.held, s.bk, s.top, s.dyn
	s.held, s.dyn = SF.HeldBy(), dyn
	local to, why = SF.Step(s, { now = now, raw = raw, frames = frames, seconds = seconds, long = long,
		goal = SF.Goal(), free = free, top = top, bk = bk, vsync = vsync })
	if s.biggest ~= hitch and (not session.biggest or s.biggest > session.biggest) then
		session.biggest, session.normal = s.biggest, s.normal
	end
	-- The page says when it stopped, or waits, and the biggest hitch: redraw when one of them changes.
	if not to then
		if s.stuck ~= stuck or s.held ~= held or s.biggest ~= hitch or s.bk ~= wasBk or s.top ~= wasTop
			or s.dyn ~= wasDyn then Refresh() end
		return
	end
	local got = Set(to)
	s.scale = got
	session.changes = session.changes + 1
	if math.abs(got - (tonumber(db.own) or got)) > 0.001 then db.set = got else db.set = nil end
	Refresh()
end

-- atLogin: turning itself back on at login, when it can't wait to be asked again.
function SF.TurnOn(atLogin)
	if state then return true end
	local cur = Scale()
	if not cur then return nil, "This game has no render scale setting." end
	local held, fight = SF.HeldBy()
	-- Their render scale isn't yours: it would be taken as yours.
	if held and not fight and not atLogin then return nil, "Can't turn on while " .. held .. ". Try again after." end
	local db = DB()
	db.on, db.afterCombat = true, nil
	if ns.FPS then ns.FPS.Unwatch("steadyBack") end
	local own = cur
	if db.set and Is(cur, db.set) and tonumber(db.own) then
		-- Still lowered from before: that isn't yours. Yours goes back, or, in a fight, it carries on from there.
		own = tonumber(db.own)
		if not InCombatLockdown() then
			cur = Set(own)
			db.set = nil
		end
	else
		db.set = nil
	end
	db.own = own
	state = SF.New(own)
	state.scale = cur
	ns.FPS.Watch("steady", OnReading)
	Refresh()
	return true
end

function SF.TurnOff()
	local db = DB()
	db.on = nil
	state = nil
	if ns.FPS then ns.FPS.Unwatch("steady") end
	PutBack()
	Refresh()
	return true
end

-- Backups, presets, Back and the patch warning take your own render scale, not the lowered one.
local situationValue = ns.SituationValue
ns.SituationValue = function(cvar, value)
	if situationValue then value = situationValue(cvar, value) end
	if cvar == "RenderScale" and value ~= nil and not busy then
		local db = ns.db and ns.db.steady
		local set = type(db) == "table" and tonumber(db.set)
		if set and tonumber(value) and math.abs(tonumber(value) - set) < 0.001 and tonumber(db.own) then
			return tostring(db.own)
		end
	end
	return value
end

-- A preset that sets render scale sets yours, even to the very value it had lowered to.
local noteOnPreset = ns.NoteOnPreset
if noteOnPreset then
	ns.NoteOnPreset = function(p, ...)
		noteOnPreset(p, ...)
		local values = state and type(p) == "table" and p.id and ns.PresetValues and ns.PresetValues(p.id)
		local cur = Scale()
		if type(values) == "table" and values.RenderScale ~= nil and cur and not SF.HeldBy() then
			SF.Adopt(state, cur)
			local db = DB()
			db.own, db.set = cur, nil
			Refresh()
		end
	end
end

-- The FPS a preset gave isn't measured while render scale is lowered, or just after a change.
if ns.FPS and ns.FPS.Still then
	local still = ns.FPS.Still
	ns.FPS.Still = function(...)
		local db = ns.db and ns.db.steady
		if type(db) == "table" and db.set then return false end
		if state and state.last and state.clock - state.last < SF.SKIP then return false end
		return still(...)
	end
end

local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(_, event, isLogin, isReload)
	local db = ns.db and ns.db.steady
	if type(db) ~= "table" then return end
	if event == "PLAYER_LOGOUT" then
		PutBack()
	elseif event == "PLAYER_LEAVING_WORLD" then
		if state then SF.NewPlace(state) end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if db.afterCombat and not state then PutBack() end
	elseif event == "PLAYER_ENTERING_WORLD" and (isLogin or isReload) then
		-- Still lowered at login (a crash, or a logout in a fight): your own back first.
		state = nil
		if db.on then
			SF.TurnOn(true)
		elseif db.set then
			PutBack()
		end
	end
end)
for _, event in ipairs({ "PLAYER_LOGOUT", "PLAYER_LEAVING_WORLD", "PLAYER_REGEN_ENABLED", "PLAYER_ENTERING_WORLD" }) do
	pcall(events.RegisterEvent, events, event)
end

----------------------------------------------------------------------
-- Steady FPS's part of the Experimental tab
----------------------------------------------------------------------

local W = ns.ROW_W - 16
local GREY, GOLD, WHITE, RED = "|cff9d9d9d", "|cffffd100", "|cffffffff", "|cffff4040"
local ROW = 4

local function Text(c, font)
	local fs = ns.Label(c, "", font)
	fs:SetWidth(W)
	return fs
end

local function Under(f, prev, dx, gap)
	f:SetPoint("TOPLEFT", prev, "BOTTOMLEFT", dx or 0, -(gap or ROW))
end

local function TextH(fs, text)
	local m = tonumber((fs.GetStringHeight and fs:GetStringHeight()))
	if m and m > 0 then return m end
	if not text or text == "" then return 0 end
	local _, breaks = text:gsub("\n", "")
	return (breaks + 1) * 14
end

local function Pct(x) return math.floor(x * 100 + 0.5) .. "%" end

SF.WHY = "When FPS stays under your goal, it lowers render scale a little. When FPS comes back, it raises it again, up to your own."
SF.HOW = "It waits for 5 seconds under or well over the goal, changes 5% at a time, at most once every 30 seconds, "
	.. "and never goes under 70%. Nothing changes in a fight. The game has its own one, Dynamic Render Scale, "
	.. "but the game says it may cause hitching, so Eye Candy doesn't turn it on."

-- The lines under the button.
function SF.Status()
	if not state then return "Off." .. (SF.refused and ("\n" .. RED .. SF.refused .. "|r") or "") end
	local s = state
	local lines = {}
	local now = s.scale
	if math.abs(now - s.own) < 0.001 then
		lines[1] = "On. Render scale is yours, " .. Pct(s.own) .. ". Goal: " .. SF.Goal() .. " FPS."
	else
		lines[1] = "On. Render scale " .. Pct(now) .. " now. Yours is " .. Pct(s.own) .. ". Goal: " .. SF.Goal() .. " FPS."
	end
	if s.own <= SF.FLOOR + 0.001 then
		lines[#lines + 1] = "Your render scale is " .. Pct(SF.FLOOR) .. " or lower already, so there's nothing to lower."
	end
	if s.stuck then
		lines[#lines + 1] = s.back and "Lowering didn't help here, so it stopped. It puts that step back soon."
			or "Lowering didn't help here, so it stopped. It tries again after a loading screen."
	end
	if s.ceiling then
		lines[#lines + 1] = "Raising past " .. Pct(s.ceiling) .. " dropped FPS too far here, so it won't go above that here."
	end
	local held = SF.HeldBy()
	if held then lines[#lines + 1] = GREY .. "Waiting: " .. held .. ".|r" end
	if s.dyn then
		lines[#lines + 1] = GREY .. "Waiting: the game's Dynamic Render Scale is on, and it moves render scale too.|r"
	end
	if s.bk then
		lines[#lines + 1] = GREY .. "Waiting: the game is in the background, so FPS is held at its background limit ("
			.. (Num("maxFPSBk") or "?") .. ").|r"
	end
	-- An FPS limit under the goal is the real goal.
	local goal = SF.Goal()
	if s.top and s.top < goal then
		lines[#lines + 1] = "Your FPS limit is " .. s.top .. ", so it aims for " .. s.top .. "."
	end
	-- It can't tell FPS held by Vertical Sync from FPS held by the graphics card, so it would lower once for
	-- nothing (and put it back) with a goal over the screen's refresh rate.
	if Num("vsync") == 1 then
		lines[#lines + 1] = "Vertical Sync is on, so FPS stops at your screen's refresh rate. Pick a goal at or under it."
	end
	local hitch = session.biggest
	local hitchText = hitch and string.format(" Biggest hitch from a change: %d ms", math.floor(hitch * 1000 + 0.5))
		.. (session.normal and string.format(" (a normal frame then: %d ms).", math.floor(session.normal * 1000 + 0.5)) or ".")
		or ""
	lines[#lines + 1] = "Changes this session: " .. session.changes .. "." .. hitchText
	return table.concat(lines, "\n")
end

local function Build(page, holder)
	local c = ns.ScrollPage(holder, 0)
	c:SetHeight(200)
	local e = { content = c }
	page.steady = e
	e.head, e.headH = ns.Header(c, "Steady FPS", "Experimental")
	e.head:SetPoint("TOPLEFT", 0, 0)
	e.why = Text(c)
	e.why:SetText(SF.WHY)
	Under(e.why, e.head, 4)
	e.how = Text(c, "GameFontDisableSmall")
	e.how:SetText(SF.HOW)
	Under(e.how, e.why, 0, 8)
	e.goalLabel = Text(c)
	e.goalLabel:SetText("Goal:")
	Under(e.goalLabel, e.how, 0, 8)
	e.goals = {}
	local prev, rowStart
	for i, g in ipairs(SF.GOALS) do
		local b = ns.Button(c, g .. " FPS", 66, function()
			DB().goal = g
			Refresh()
		end)
		if i == 1 then
			Under(b, e.goalLabel, 0, 4)
			rowStart = b
		elseif (i - 1) % SF.PER_ROW == 0 then
			Under(b, rowStart, 0, 4) -- the next row
			rowStart = b
		else
			b:SetPoint("LEFT", prev, "RIGHT", 4, 0)
		end
		ns.Tooltip(b, g .. " FPS", "Lower render scale when FPS stays under " .. math.floor(g * SF.LOW + 0.5) .. ".")
		e.goals[i], prev = b, b
	end
	e.toggle = ns.Button(c, "Turn on", 110, function()
		SF.refused = nil
		if state then
			SF.TurnOff()
		else
			local ok, err = SF.TurnOn()
			if not ok then
				SF.refused = err
				Refresh()
			end
		end
	end)
	Under(e.toggle, rowStart, 0, 8) -- under the last row of goals
	ns.Tooltip(e.toggle, "Steady FPS", "Off until you turn it on. Turning it off puts your own render scale back.")
	e.status = Text(c)
	Under(e.status, e.toggle, 0, 8)
end

local function Refresh_(page)
	local e = page.steady
	local goal = SF.Goal()
	for i, b in ipairs(e.goals) do
		b:SetText((SF.GOALS[i] == goal and GOLD or WHITE) .. SF.GOALS[i] .. " FPS|r") -- gold: picked, as on Autotune's page
	end
	e.toggle:SetText(state and "Turn off" or "Turn on")
	local status = SF.Status()
	e.status:SetText(status)
	local rows = math.ceil(#SF.GOALS / SF.PER_ROW)
	local height = e.headH + ROW + TextH(e.why, SF.WHY) + 8 + TextH(e.how, SF.HOW) + 8 + 14 + 4 + rows * 24 + (rows - 1) * 4 + 8 + 24 + 8
		+ TextH(e.status, status)
	e.content:SetHeight(height + 16)
end

if ns.AddExperiment then
	ns.AddExperiment({
		key = "steady", name = "Steady FPS", build = Build, refresh = Refresh_,
		tip = "Lowers render scale a little when FPS stays low, and raises it again when FPS comes back.",
	})
end
