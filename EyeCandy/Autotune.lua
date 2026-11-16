-- Eye Candy: Autotune (experimental). Finds the best look the PC can hold at a frame rate goal, by measuring.
--
-- How it works: measure your settings now, then drop every setting it uses to its lowest and measure again.
-- If even that misses the goal, it stops and says so. If FPS sits at a refresh rate there (Vertical Sync), a
-- goal at that rate is judged just under it, and a goal above it can't be reached. Next, render scale at 100%:
-- hardly slower than the lowest means the CPU sets the limit, and the settings that load the CPU keep more
-- spare. Then it raises one setting at a time and keeps a raise only if the goal still holds, the slowest 5% of
-- frames included.
--   A goal (30 to 240 FPS): the setting with the best look for its cost goes to the end of its best stretch
--   of steps; a miss comes back down one step at a time.
--   Best balance: render scale to 100% first if it holds 60 FPS, then one step at a time; a step stays only
--   while it costs little for the look it adds.
-- Render scale over 100% is tried last, after every other setting. After every 8 tries, and at the end unless
-- the last try passed, the kept settings are measured again; if a warm PC no longer holds them, the newest
-- raises go, one at a time, until they hold.
-- A measurement leaves out a long frame or two (a shader compile), and is taken again once if it had one.
-- Ways of tuning (AT.STYLES, "Tune for" on the tab): Best look is the above. Raid ready keeps much more spare,
-- Smooth judges by the slowest frames, Sharpest picture tries the clarity settings first, and Cool and quiet
-- turns the game's FPS cap on at the goal when it is done.
-- Start from (on the tab): instead of the lowest settings, any preset. Its values go on, and while the goal
-- misses, one setting at a time goes one step lower, the least look for its cost first. What makes it that
-- preset is never lowered (AT.LOOK_KEEP, AT.Essence), and nothing goes above the preset.
--
-- The game tells an addon the GPU's name and which values it supports, but not the CPU, memory, video memory or
-- refresh rate (checked 15 Nov 2026 in Ketho's GlobalAPI.lua and Blizzard's Graphics.lua, forever branch). So it
-- measures. Each setting's order comes from a guess at how much it costs and how much it adds (see KNOBS); the
-- measured cost of every change is shown at the end.
--
-- Pure logic: AT.Stats, AT.Verdict, AT.Cap, AT.Line, AT.Early, AT.NewRun, AT.Step, AT.Values, AT.Changes,
-- AT.CostFPS (tests/test_autotune.py).
-- The run in the game: AT.Start, AT.Stop, AT.Keep, AT.PutBack. Never in combat; moving, a fight, a loading
-- screen, opening Options or another Eye Candy change stops it and puts the settings from before back.

local _, ns = ...

local AT = {}
ns.Autotune = AT

-- The goals offered (15 Nov 2026): common refresh rates, plus 30 for a laptop.
AT.GOALS = { 30, 60, 75, 120, 144, 165, 180, 240 }
AT.HEADROOM = 1.1      -- a goal needs 10% to spare: cities and fights run slower than a quiet spot
AT.CPU_HEADROOM = 1.25 -- on a PC whose CPU sets the limit, the settings that load the CPU need more: a crowd
                       -- costs CPU (how much more is a guess)
AT.CPU_BOUND = 1.1     -- frames at 100% render scale less than 10% slower than at the lowest: the CPU sets the limit
AT.CLOSE = 0.03        -- within 3% of the line: measure once more and average
AT.CLOSE_DROP = 0.25   -- best balance: a drop within a quarter of what's allowed (at least 1 point) is a close call
AT.BALANCE_MIN = 60    -- best balance never goes under this
AT.BALANCE_RATE = 0.04 -- best balance: a step may cost 4% FPS for each point of look it adds
AT.MAX_TRIES = 60      -- measurements in one run, at most
AT.SLOW_SHARE = 0.85   -- the slowest 5% of frames must run at 85% of the goal or better
-- Settling: after a change, wait until two half-second windows agree within 3%, at least SETTLE_MIN seconds
-- (SETTLE_MIN_SLOW after render scale or texture changes), at most SETTLE_MAX.
AT.SETTLE_MIN, AT.SETTLE_MIN_SLOW, AT.SETTLE_MAX = 1, 2, 6
AT.SETTLE_WINDOW, AT.SETTLE_AGREE = 0.5, 0.03
AT.SAMPLE = 4          -- seconds of frames in one measurement
AT.EARLY_AFTER = 1.5   -- a sample more than EARLY_MARGIN from the line stops after this many seconds
AT.EARLY_MARGIN = 0.15
AT.HITCH = 0.05        -- a frame over 50 ms, and over TRIM x the middle frame, is a hitch: the sample is taken again once
AT.TRIM = 4
-- A cap: FPS within 1.5% of a common refresh rate with frames this even (0.5%, or 5% with Vertical Sync on:
-- with it off, only a frame limiter is that even, and a PC that happens to run near 90 must not count).
-- Then a goal at the cap is judged against 97% of it (the slow frames against 90%), since nothing can pass it.
AT.REFRESH = { 50, 60, 75, 85, 90, 100, 120, 144, 165, 180, 200, 240, 280, 360 }
AT.CAP_NEAR, AT.CAP_SPREAD, AT.CAP_SPREAD_VSYNC = 0.015, 0.005, 0.05
AT.CAP_LINE, AT.CAP_SLOW = 0.97, 0.9
AT.RECHECK = 8         -- after this many measurements, measure the kept settings again: a PC warms up and slows,
                       -- so that measurement is the new baseline, and if they no longer hold, the newest raise goes

-- The settings Autotune moves, each with its steps from the lowest it uses (Performance's value) to the
-- top. Each step after the first: { value, look, cost }. Look is how much the step adds to the picture and
-- cost how much FPS it is expected to take, both in rough points. Both only set the order; they are guesses
-- from the 15 Nov 2026 research (kami-labs' Forever measurements put render scale, compute effects, secondary
-- lighting and shadows as the most costly; texture resolution, liquid and view distance near free).
-- Left out: anything needing a restart or a window reset, spell density and projected textures (combat
-- effects), and the hidden distance values (the Looks set those).
-- slow: wait longer after it changes. after: only tried once that setting is at its top and every other
-- setting is done. cpu: it loads the CPU more than the graphics card (more to draw far away, more objects).
-- free: in Best balance it is judged on the FPS line alone; a blurry picture is never worth saving FPS for.
-- clear: it makes the picture clearer (Sharpest picture tries these first). only: used by that way of tuning
-- alone; anti-aliasing and sharpening are otherwise left as you have them.
-- Anti-aliasing: 0 none, 1 and 2 FXAA low and high, 3 CMAA, 4 CMAA 2 (Blizzard's Graphics.lua, forever).
AT.KNOBS = {
	{ key = "textures", cvar = "graphicsTextureResolution", slow = true, clear = true, steps = { { 1 }, { 2, 3, 0.2 } } },
	{ key = "filtering", cvar = "textureFilteringMode", clear = true, steps = { { 3 }, { 4, 1, 0.1 }, { 5, 1, 0.1 } } },
	{ key = "aa", cvar = "ffxAntiAliasingMode", clear = true, only = "sharp", steps = { { 0 }, { 1, 1, 0.1 }, { 2, 0.5, 0.1 }, { 3, 0.5, 0.2 }, { 4, 0.5, 0.2 } } },
	{ key = "sharpen", cvar = "ResampleAlwaysSharpen", clear = true, only = "sharp", steps = { { 0 }, { 1, 1, 0.1 } } },
	{ key = "light", cvar = "graphicsLightMode", steps = { { 0 }, { 1, 4, 1.5 }, { 2, 2, 1.5 }, { 3, 1.5, 3 } } },
	{ key = "compute", cvar = "graphicsComputeEffects", steps = { { 1 }, { 2, 2, 1 }, { 3, 1.5, 1.5 }, { 4, 1, 3 } } },
	{ key = "shadows", cvar = "graphicsShadowQuality", steps = { { 1 }, { 2, 1.5, 0.5 }, { 3, 1.5, 0.5 }, { 4, 1, 0.7 }, { 5, 0.5, 1 } } },
	{ key = "ssao", cvar = "graphicsSSAO", steps = { { 1 }, { 2, 1.5, 0.5 }, { 3, 1, 0.5 }, { 4, 0.5, 0.7 } } },
	{ key = "depth", cvar = "graphicsDepthEffects", steps = { { 1 }, { 2, 0.5, 0.2 }, { 3, 0.5, 0.2 } } },
	{ key = "liquid", cvar = "graphicsLiquidDetail", steps = { { 1 }, { 2, 0.5, 0.1 }, { 3, 0.5, 0.2 } } },
	{ key = "pbr", cvar = "graphicsPBRLiquidDetail", steps = { { 0 }, { 1, 1, 0.3 }, { 2, 0.5, 0.3 } } },
	{ key = "view", cvar = "graphicsViewDistance", cpu = true, clear = true, steps = { { 3 }, { 5, 1.5, 0.3 }, { 7, 1, 0.3 }, { 9, 0.5, 0.4 } } },
	{ key = "environment", cvar = "graphicsEnvironmentDetail", cpu = true, steps = { { 3 }, { 5, 1.5, 0.5 }, { 7, 1, 0.5 }, { 9, 0.5, 0.7 } } },
	{ key = "clutter", cvar = "graphicsGroundClutter", cpu = true, steps = { { 3 }, { 5, 1, 0.5 }, { 7, 1, 0.5 }, { 9, 0.5, 0.7 } } },
	{ key = "particles", cvar = "graphicsParticleDensity", cpu = true, steps = { { 1 }, { 2, 0.5, 0.2 }, { 3, 0.5, 0.2 }, { 4, 0.5, 0.3 }, { 5, 0.3, 0.4 } } },
	{ key = "vrs", cvar = "vrsValar", steps = { { 2 }, { 1, 0.5, 0.3 }, { 0, 0.5, 0.3 } } },
	{ key = "scale", cvar = "RenderScale", slow = true, free = true, clear = true, steps = { { 0.6 }, { 0.7, 5, 1.5 }, { 0.8, 5, 1.5 }, { 0.9, 4, 1.5 }, { 1, 4, 1.5 } } },
	{ key = "scaleUp", cvar = "RenderScale", slow = true, clear = true, after = "scale", steps = { { 1 }, { 1.25, 0.7, 2 }, { 1.5, 0.7, 3 } } },
}
-- The first setting for each CVar (render scale's is "scale").
AT.KNOB_BY_CVAR = {}
for _, def in ipairs(AT.KNOBS) do AT.KNOB_BY_CVAR[def.cvar] = AT.KNOB_BY_CVAR[def.cvar] or def end

-- The ways of tuning ("Tune for" on the tab). Every field is optional; a missing one keeps the rule above.
-- headroom, cpuHeadroom: the spare, instead of HEADROOM and CPU_HEADROOM. slowShare: how fast the slowest 5%
-- of frames must run, against the goal (instead of SLOW_SHARE). lowShare: the slowest 1% as well.
-- slowFirst: a close call is judged on the slow frames, and a pass never stops a sample early (the slow
-- frames need the whole sample). sample: seconds in one measurement. clearFirst: the clear settings go
-- first, render scale over 100% straight after them. capAtGoal: when done, the game's FPS cap goes on at the
-- goal (maxFPS: "Set FPS limit. Min 8", Ketho's CVars.lua, forever); it needs an FPS goal.
-- Raid ready's spare is a guess: players report big fights at about half a quiet spot's FPS, mostly CPU.
AT.STYLES = {
	{ key = "look", name = "Best look" },
	{ key = "raid", name = "Raid ready", headroom = 1.5, cpuHeadroom = 1.8, slowShare = 1 },
	{ key = "smooth", name = "Smooth", slowShare = 1, lowShare = 0.7, slowFirst = true, sample = 6 },
	{ key = "sharp", name = "Sharpest picture", clearFirst = true },
	{ key = "cool", name = "Cool and quiet", capAtGoal = true },
}
AT.STYLE = {}
for _, s in ipairs(AT.STYLES) do AT.STYLE[s.key] = s end

-- Starting from a preset ("Start from" on the tab): the preset's values go on first, and if they miss the
-- goal, settings go down one step at a time, the least look for its cost first, until it holds. Nothing is
-- ever raised above the preset. The settings Autotune doesn't tune (colour, glow, field of view, the grass
-- dials) are the preset's and never change. What else is kept, untrimmed, is the preset's essence:
-- a Look keeps the settings its own description names (Data.lua), anything else the settings it has clearly
-- higher than its others (AT.Essence).
AT.LOOK_KEEP = {
	beautiful = { "ssao", "depth" },           -- natural ambient occlusion, soft edges on smoke and spells
	painterly = { "depth", "textures" },       -- soft edges, ground textures that show
	crisp = { "scale", "filtering", "textures" }, -- maximum clarity
	moody = { "ssao", "depth", "compute" },    -- deeper ambient occlusion, soft edges, fog and sun rays
	classic = {},                              -- its character is all in the settings Autotune doesn't tune
}
AT.STAND_OUT = 0.25 -- a setting this far above the preset's middle share of its scale is the point of it

-- Where a value sits among steps (low to high, or high to low like VRS), as a share from 0 to 1.
local function Share(steps, v)
	local n = #steps
	if n < 2 then return 0 end
	local dir = steps[n][1] >= steps[1][1] and 1 or -1
	local at = 0
	for i, s in ipairs(steps) do
		if (v - s[1]) * dir >= -1e-9 then at = i end
	end
	if at == 0 then return 0 end
	if at >= n then return 1 end
	local a, b = steps[at][1], steps[at + 1][1]
	return (at - 1 + (v - a) / (b - a)) / (n - 1)
end

-- The settings (knob keys, as a set) a preset keeps untrimmed. id: the preset's id; values: its values.
function AT.Essence(id, values)
	local keep = {}
	local look = type(id) == "string" and id:match("^look:(.+)$")
	if look and AT.LOOK_KEEP[look] then
		for _, key in ipairs(AT.LOOK_KEEP[look]) do keep[key] = true end
		return keep
	end
	local shares, list = {}, {}
	for _, def in ipairs(AT.KNOBS) do
		local v = tonumber((values or {})[def.cvar])
		if v and not def.after and not def.only then
			shares[def.key] = Share(def.steps, v)
			list[#list + 1] = shares[def.key]
		end
	end
	if #list == 0 then return keep end
	table.sort(list)
	local middle = #list % 2 == 1 and list[(#list + 1) / 2] or (list[#list / 2] + list[#list / 2 + 1]) / 2
	for key, s in pairs(shares) do
		if s > middle + AT.STAND_OUT then keep[key] = true end
	end
	return keep
end

-- FPS limits that would spoil a measurement. Lifted while measuring and put back after. The background limit
-- too: a moment in another window would measure the background rate.
-- Vsync is left alone: changing it resets the game window (its flag in Blizzard's Graphics.lua). A cap it
-- makes is found by measuring (AT.Cap).
AT.CAPS = { useMaxFPS = 0, useTargetFPS = 0, useMaxFPSBk = 0 }

----------------------------------------------------------------------
-- Pure logic
----------------------------------------------------------------------

-- One measurement from a list of frame times in seconds.
-- fps: frames over time, leaving out a few long frames (a shader compile or a texture loading once is not what
-- the settings cost). Only up to 1% of the frames are left out; more than that is how the settings run.
-- low: the 1% low (the 99th percentile frame time, as FPS, of every frame). slow: the 95th percentile, as FPS.
-- spread: how uneven the frames are (0 is perfectly even; a refresh-rate cap is under 0.02).
-- hitch: a frame over HITCH seconds and TRIM x the middle frame. steady: the slow frames are not far off the rest.
function AT.Stats(times)
	local n = #times
	if n == 0 then return { fps = 0, low = 0, slow = 0, spread = 0, frames = 0, steady = false } end
	local sorted = {}
	for i = 1, n do sorted[i] = times[i] end
	table.sort(sorted)
	local cut = math.max(AT.HITCH, AT.TRIM * sorted[math.ceil(n / 2)])
	local over = 0
	for i = n, 1, -1 do
		if sorted[i] > cut then over = over + 1 else break end
	end
	local kept = over <= math.max(1, math.floor(n * 0.01)) and n - over or n
	local sum, sq = 0, 0
	for i = 1, kept do sum, sq = sum + sorted[i], sq + sorted[i] * sorted[i] end
	if sum <= 0 then return { fps = 0, low = 0, slow = 0, spread = 0, frames = n, steady = false } end
	local mean = sum / kept
	local fps = kept / sum
	local p99 = sorted[math.max(1, math.ceil(n * 0.99))]
	local p95 = sorted[math.max(1, math.ceil(kept * 0.95))]
	local low = p99 > 0 and 1 / p99 or fps
	return {
		fps = fps, low = low, slow = p95 > 0 and 1 / p95 or fps,
		spread = math.sqrt(math.max(0, sq / kept - mean * mean)) / mean,
		hitch = over > 0, frames = n, steady = low >= fps * 0.4,
	}
end

-- "pass", "fail" or "again" (too close to call, or jerky: measure once more).
-- target: fps must clear the line (goal x HEADROOM), and the slow frames (m.slow) goal x SLOW_SHARE.
-- balance: the same with goal = BALANCE_MIN, and the drop from the last kept measurement (last) must be no more
-- than BALANCE_RATE for each point of look (worth) the step adds.
-- o: { line, slowLine } to judge against instead (a cap, or a CPU-bound PC), and free = true to skip the drop.
-- o.lowLine: the slowest 1% (m.low) must clear it too. o.slowFirst: slow frames near their line are a close call.
-- m.again: this is already the second look, so judge it as it is.
function AT.Verdict(mode, goal, m, last, worth, o)
	o = o or {}
	if not m.steady and not m.again then return "again" end
	local line = o.line or goal * AT.HEADROOM
	local slowLine = o.slowLine or goal * AT.SLOW_SHARE
	local close = math.abs(m.fps - line) / line < AT.CLOSE
	if o.slowFirst then
		if m.slow and slowLine > 0 then close = close or math.abs(m.slow - slowLine) / slowLine < AT.CLOSE end
		if m.low and o.lowLine and o.lowLine > 0 then close = close or math.abs(m.low - o.lowLine) / o.lowLine < AT.CLOSE end
	end
	local pass = m.fps >= line and (m.slow == nil or m.slow >= slowLine)
		and (o.lowLine == nil or m.low == nil or m.low >= o.lowLine)
	if mode == "balance" and last and last.fps > 0 and not o.free then
		local drop = (last.fps - m.fps) / last.fps
		local allowed = AT.BALANCE_RATE * (worth or 0)
		pass = pass and drop <= allowed
		-- A free step (no drop) is not a close call: the band is a share of what's allowed, at least 1 point.
		close = close or math.abs(drop - allowed) < math.max(0.01, AT.CLOSE_DROP * allowed)
	end
	if close and not m.again then return "again" end
	return pass and "pass" or "fail"
end

-- The FPS cap a measurement shows, or nil: frames this even, at a common refresh rate (Vertical Sync, or a
-- limit Autotune can't lift). vsync: Vertical Sync is on, so frames may be a little less even.
function AT.Cap(m, vsync)
	if not (m and m.fps and m.fps > 0 and m.spread) then return nil end
	if m.spread > (vsync and AT.CAP_SPREAD_VSYNC or AT.CAP_SPREAD) then return nil end
	for _, r in ipairs(AT.REFRESH) do
		if math.abs(m.fps - r) / r <= AT.CAP_NEAR then return r end
	end
end

-- The FPS line, the slow-frame line and the slowest-1% line (nil: not judged) a try of kn is judged against
-- (kn nil: the kept settings), by the run's way of tuning. A CPU-bound PC keeps more spare for the settings
-- that load the CPU. A goal at a cap is judged just under it.
function AT.Line(run, kn)
	local st = run.style or AT.STYLE.look
	local cpu = run.cpuBound and kn and kn.def.cpu
	local head = cpu and (st.cpuHeadroom or AT.CPU_HEADROOM) or (st.headroom or AT.HEADROOM)
	local line, slow = run.goal * head, run.goal * (st.slowShare or AT.SLOW_SHARE)
	local low = st.lowShare and run.goal * st.lowShare or nil
	if run.cap and run.goal <= run.cap * (1 + AT.CAP_NEAR) then
		line = math.min(line, run.cap * AT.CAP_LINE)
		slow = math.min(slow, run.cap * AT.CAP_SLOW)
		if low then low = math.min(low, run.cap * AT.CAP_SLOW) end
	end
	return line, slow, low
end

-- What a measurement of kn (nil: the kept settings) is judged against, for AT.Verdict. loose: a check on the
-- way allows the 3% a close call would.
local function Judge(run, kn, loose)
	local line, slow, low = AT.Line(run, kn)
	local k = loose and (1 - AT.CLOSE) or 1
	return { line = line * k, slowLine = slow * k, lowLine = low and low * k, free = kn and kn.def.free,
		slowFirst = run.style.slowFirst }
end

-- Can a try's sample stop early? m: the frames so far. A clear miss always can. A clear pass can with a goal,
-- or for a free setting (Best balance's drop test needs the full sample), unless the slow frames decide.
function AT.Early(run, m)
	if not (run.try and m and (m.frames or 0) >= 30) then return false end
	local kn = run.try.knob
	local line, slowLine = AT.Line(run, kn)
	if m.fps < line * (1 - AT.EARLY_MARGIN) then return true end
	if m.fps > line * (1 + AT.EARLY_MARGIN) and (m.slow == nil or m.slow >= slowLine)
		and (run.mode == "target" or kn.def.free) and not run.style.slowFirst then
		return true
	end
	return false
end

-- A run from a preset: each setting's steps run from Autotune's lowest up to the preset's value, which is
-- the top (a value between steps, like 75% render scale, is a step of its own). Render scale's steps over
-- 100% are part of it here: a preset may start there. A setting the preset doesn't name is left alone.
local function FromKnobs(run, env, from)
	for _, def in ipairs(AT.KNOBS) do
		local v = tonumber(from.values[def.cvar])
		if v and not def.after and (not def.only or def.only == run.style.key) and env.exists(def.cvar) then
			local all = {}
			for _, s in ipairs(def.steps) do all[#all + 1] = s end
			for _, d2 in ipairs(AT.KNOBS) do
				if d2.after == def.key then
					for i = 2, #d2.steps do all[#all + 1] = d2.steps[i] end
				end
			end
			local dir = all[#all][1] >= all[1][1] and 1 or -1
			local steps = {}
			for _, s in ipairs(all) do
				if (v - s[1]) * dir >= -1e-9 and env.supported(def.cvar, s[1]) then steps[#steps + 1] = s end
			end
			local top = steps[#steps]
			if (not top or math.abs(top[1] - v) > 1e-9) and env.supported(def.cvar, v) then
				-- Its look and cost are those of the step it sits under.
				local above
				for _, s in ipairs(all) do
					if not above and (s[1] - v) * dir > 1e-9 then above = s end
				end
				above = above or all[#all]
				steps[#steps + 1] = { v, above[2] or 0, above[3] or 0 }
			end
			if #steps > 0 then
				local kn = { def = def, steps = steps, lo = #steps, hi = #steps, before = steps[#steps][1] }
				-- The preset's own value, as it wrote it, while the setting is at its start.
				if math.abs(steps[#steps][1] - v) < 1e-9 then kn.raw = from.values[def.cvar] end
				kn.kept = from.keep and from.keep[def.key] or nil
				kn.settled = #steps == 1 or kn.kept or false
				run.knobs[#run.knobs + 1] = kn
				run.byKey[def.key] = kn
			end
		end
	end
end

-- env: exists(cvar), supported(cvar, value), current = { cvar = value as it is now }, vsync = true if on.
-- style: the way of tuning's key (AT.STYLES); nil is Best look. from: a preset to start from, { values (every
-- value it asks for), keep (AT.Essence) }; nil builds up from the lowest settings.
function AT.NewRun(mode, goal, env, style, from)
	local run = {
		mode = mode, goal = mode == "balance" and AT.BALANCE_MIN or goal, vsync = env.vsync,
		knobs = {}, byKey = {}, count = 0, kept = {}, sinceCheck = 0, style = AT.STYLE[style] or AT.STYLE.look,
	}
	if from then
		run.from = from
		FromKnobs(run, env, from)
		return run
	end
	for _, def in ipairs(AT.KNOBS) do
		local dep = def.after and run.byKey[def.after]
		if env.exists(def.cvar) and (not def.after or dep) and (not def.only or def.only == run.style.key) then
			local steps = {}
			for i, s in ipairs(def.steps) do
				-- The first step of an "after" setting is its partner's top, already known good.
				if (i == 1 and def.after) or env.supported(def.cvar, s[1]) then steps[#steps + 1] = s end
			end
			-- No lowest value means nothing to start from; an "after" setting must still start where its partner ends.
			local usable = steps[1] == def.steps[1] and (not dep or dep.steps[#dep.steps][1] == steps[1][1])
			if usable and #steps > 0 then
				local kn = { def = def, steps = steps, lo = 1, hi = #steps, before = tonumber((env.current or {})[def.cvar]) }
				kn.settled = #steps == 1
				run.knobs[#run.knobs + 1] = kn
				run.byKey[def.key] = kn
			end
		end
	end
	return run
end

-- Every setting at its lowest ("after" settings start where their partner ends, so they add nothing here).
local function FloorValues(run)
	local set = {}
	for _, kn in ipairs(run.knobs) do
		if not kn.def.after then set[kn.def.cvar] = kn.steps[1][1] end
	end
	return set
end

-- How much look a setting adds for its cost, and the step to try: the next step (balance), or the best stretch
-- of steps from where it is (a goal). The best stretch, not every step left, so a good first step isn't buried
-- under a costly top, and a costly top isn't taken before other settings' good steps. A tie goes to the longer.
local function Score(run, kn)
	local look, cost, best, at = 0, 0, 0, kn.lo + 1
	local last = run.mode == "balance" and kn.lo + 1 or kn.hi
	for i = kn.lo + 1, last do
		look, cost = look + (kn.steps[i][2] or 0), cost + (kn.steps[i][3] or 0)
		local s = look / math.max(cost, 0.01)
		if s >= best * 0.999 then best, at = math.max(best, s), i end
	end
	return best, at
end

-- Asks for kn at step index to be measured. set: values to change as well (a revert).
local function Try(run, kn, index, set)
	kn.tried = true
	run.try = { knob = kn, index = index }
	local value = kn.steps[index][1]
	set[kn.def.cvar] = value
	return { set = set, measure = true, slow = kn.def.slow, try = { key = kn.def.key, cvar = kn.def.cvar, value = value } }
end

-- Picks the next setting and value to try, or nil when every setting is done.
-- Best balance tries the free settings first (render scale up to 100%), Sharpest picture the clear ones, then
-- by score. An "after" setting waits for every other setting, or with Sharpest picture, every clear one.
local function Next(run, set)
	local clearFirst = run.style.clearFirst
	local othersOpen = false
	for _, kn in ipairs(run.knobs) do
		if not kn.settled and not kn.def.after and (kn.def.clear or not clearFirst) then othersOpen = true end
	end
	local best, bestScore, bestFree, bestAt
	for _, kn in ipairs(run.knobs) do
		if not kn.settled and kn.def.after and not othersOpen then
			-- Its partner must have reached its top; if not, there is nothing to build on.
			local dep = run.byKey[kn.def.after]
			if dep.lo ~= #dep.steps then kn.settled = true end
		end
		if not kn.settled and not (kn.def.after and othersOpen) then
			local free = ((run.mode == "balance" and kn.def.free) or (clearFirst and kn.def.clear)) and true or false
			local score, at = Score(run, kn)
			if not best or (free and not bestFree) or (free == bestFree and score > bestScore) then
				best, bestScore, bestFree, bestAt = kn, score, free, at
			end
		end
	end
	if not best then return nil end
	return Try(run, best, bestAt, set)
end

-- Render scale at 100%, measured straight after the lowest settings. Its time against the lowest's says whether
-- the CPU or the graphics card sets the limit. It is also render scale's first try.
local function Probe(run)
	local kn = run.byKey.scale
	if not kn or kn.settled then return nil end
	for i = kn.hi, kn.lo + 1, -1 do
		if kn.steps[i][1] == 1 then
			run.phase = "probe"
			return Try(run, kn, i, {})
		end
	end
end

-- Measures the kept settings again. final: the last measurement before the result.
local function Check(run, set, final)
	run.checking, run.final, run.sinceCheck = true, final, 0
	return { set = set, measure = true, check = true }
end

-- Is any setting still to be tried? (An "after" setting only once its partner is at its top.)
local function AnyOpen(run)
	for _, kn in ipairs(run.knobs) do
		if not kn.settled then
			local dep = kn.def.after and run.byKey[kn.def.after]
			if not dep or dep.lo == #dep.steps or not dep.settled then return true end
		end
	end
	return false
end

-- After a measurement: measure the kept settings again after every RECHECK tries, then the next try. Once
-- there is nothing left to try, or time is nearly up, a last check, unless the last measurement was a try of
-- the kept settings that passed (a check on the way is judged more loosely, so it doesn't count).
-- One measurement is held back for it.
local function Continue(run, set)
	local open = AnyOpen(run)
	if open and run.count >= AT.MAX_TRIES - 1 then run.outOfTime = true end
	if open and not run.outOfTime and run.sinceCheck >= AT.RECHECK and #run.kept > 0 then return Check(run, set, false) end
	local action = not run.outOfTime and Next(run, set)
	if action then return action end
	if run.lastWasKept and not run.lastLoose and next(set) == nil then
		run.finalDone = true
		return { done = run.outOfTime and "time" or "finished", set = set }
	end
	return Check(run, set, true)
end

-- From a preset: the value of kn at step i (the preset's own, as it wrote it, at the start).
local function Val(kn, i)
	if i == #kn.steps and kn.raw ~= nil then return kn.raw end
	return kn.steps[i][1]
end

-- From a preset: every value it asks for, with the tuned settings at their start.
local function BaseValues(run)
	local set = {}
	for cvar, v in pairs(run.from.values) do set[cvar] = v end
	for _, kn in ipairs(run.knobs) do set[kn.def.cvar] = Val(kn, #kn.steps) end
	return set
end

-- From a preset: the setting to lower next, or nil when none is left. The step with the least look for its
-- cost goes first; Sharpest picture lowers every other setting before a clear one. prune: Best balance's look
-- for a step worth lowering, which never lowers render scale (a blurry picture is never worth the FPS).
local function TrimPick(run, prune)
	local best, bestR, bestClear
	for _, kn in ipairs(run.knobs) do
		if not kn.settled and kn.lo > 1 and not (prune and kn.def.free) then
			local s = kn.steps[kn.lo]
			local r = (s[2] or 0) / math.max(s[3] or 0, 0.01)
			local clear = (run.style.clearFirst and kn.def.clear) and true or false
			if not best or (bestClear and not clear) or (clear == bestClear and r < bestR) then
				best, bestR, bestClear = kn, r, clear
			end
		end
	end
	return best
end

-- From a preset: asks for kn one step lower to be measured.
local function Trim(run, kn)
	run.try = { knob = kn, index = kn.lo - 1 }
	local value = Val(kn, kn.lo - 1)
	return { set = { [kn.def.cvar] = value }, measure = true, slow = kn.def.slow,
		try = { key = kn.def.key, cvar = kn.def.cvar, value = value, trim = true } }
end

-- From a preset: the run after its first measurement (the "now" one). Every measurement is of the settings
-- as they stand, so there are no checks on the way: a trim stays, and the next is measured from there.
local function FromStep(run, m, Again, limit)
	if run.phase == "now" then
		run.phase = "base"
		return { set = BaseValues(run), measure = true, base = true }
	end
	if run.phase == "prune" then
		-- Best balance: a step down stays only if it gains more than its look is worth.
		local kn, index = run.try.knob, run.try.index
		local gain = (m.fps - run.last.fps) / run.last.fps
		local allowed = AT.BALANCE_RATE * (kn.steps[index + 1][2] or 0)
		if not m.again and math.abs(gain - allowed) < math.max(0.01, AT.CLOSE_DROP * allowed) then
			local again = Again("again")
			if again then return again end
		end
		local set = {}
		if gain > allowed then
			kn.lo = index
			run.last = m
		else
			set[kn.def.cvar] = Val(kn, kn.lo)
			kn.settled = true
		end
		if kn.lo <= 1 then kn.settled = true end
		run.try = nil
		local nextKn = run.count < limit and TrimPick(run, true)
		if nextKn then
			local action = Trim(run, nextKn)
			for cvar, v in pairs(set) do action.set[cvar] = action.set[cvar] or v end
			return action
		end
		return { done = "finished", set = set }
	end

	-- The preset as it is, or after a trim: does the goal hold?
	local set = {}
	-- A cap (Vertical Sync, a frame limiter): a heavy preset may just happen to run at an even 60, and a
	-- cheap step gains next to nothing, so neither proves one. After a step lower that gains nothing, with
	-- frames even at a refresh rate, the cap is tested: one measurement with every setting it may lower at
	-- its lowest. Still there, it is a cap, and the step goes back (it bought nothing). Else the step stays,
	-- and that rate never counts as a cap again.
	if run.capProbe then
		local probe = run.capProbe
		run.capProbe = nil
		set = probe.back
		local kn = probe.knob
		if AT.Cap(m, run.vsync) == probe.at and m.fps <= probe.at * (1 + AT.CAP_NEAR) then
			-- A cap: the step that gained nothing goes back.
			run.cap = probe.at
			kn.settled = true
		else
			-- Not a cap: the step was just cheap, and stays (small gains add up).
			run.notCap[probe.at] = true
			kn.lo = probe.index
			if kn.lo <= 1 then kn.settled = true end
			set[kn.def.cvar] = Val(kn, kn.lo)
			run.trimmed = true
		end
		-- The settings are back as they were before the test, so the measurement before it is theirs.
		m = {}
		for k, v in pairs(run.last) do m[k] = v end
		m.again = true
	else
		local tried = run.try and run.try.knob
		local capNow = tried and run.last and m.fps <= run.last.fps * (1 + AT.CAP_NEAR) and AT.Cap(m, run.vsync)
		run.notCap = run.notCap or {}
		if capNow and not run.notCap[capNow] and run.cap ~= capNow then
			local index = run.try.index
			run.try = nil
			run.last = m
			local test, back = {}, { [tried.def.cvar] = Val(tried, tried.lo) }
			for _, kn in ipairs(run.knobs) do
				if not kn.kept and kn.lo > 1 then
					test[kn.def.cvar] = kn.steps[1][1]
					back[kn.def.cvar] = back[kn.def.cvar] or Val(kn, kn.lo)
				end
			end
			test[tried.def.cvar] = tried.steps[1][1]
			run.capProbe = { at = capNow, back = back, knob = tried, index = index }
			return { set = test, measure = true, capTest = true }
		elseif capNow then
			-- At a cap already known: the step bought nothing, so it goes back.
			set[tried.def.cvar] = Val(tried, tried.lo)
			tried.settled = true
		elseif tried then
			tried.lo = run.try.index
			if tried.lo <= 1 then tried.settled = true end
			run.trimmed = true
		end
		run.try = nil
	end
	if run.cap and run.goal > run.cap * (1 + AT.CAP_NEAR) then
		return { done = "unreachable", set = set, best = m.fps, cap = run.cap, partly = run.trimmed }
	end
	local verdict = AT.Verdict("target", run.goal, m, nil, nil, Judge(run))
	local again = Again(verdict)
	if again then
		again.set = set
		return again
	end
	run.last = m
	local function With(action)
		for cvar, v in pairs(set) do action.set[cvar] = action.set[cvar] or v end
		return action
	end
	if verdict == "pass" then
		if run.mode == "balance" then
			run.phase = "prune"
			local kn = run.count < limit and TrimPick(run, true)
			if kn then return With(Trim(run, kn)) end
		end
		return { done = "finished", set = set }
	end
	run.phase = "trim"
	local kn = TrimPick(run)
	if kn and run.count < limit then return With(Trim(run, kn)) end
	-- Nothing left to lower (or out of measurements) and still short: it can't be reached from this preset.
	-- trimmed: something was lowered on the way (a preset already at its lowest, or all kept, wasn't).
	return { done = "unreachable", set = set, best = m.fps, cap = run.cap, trimmed = not kn and run.trimmed or nil,
		outOfTime = kn and true or nil }
end

-- Feeds in a measurement (nil to begin) and returns what to do next:
--   { set = { cvar = value }, measure = true, try = {...}, again = true?, check = true? }: change these,
--   settle, measure. check: it measures the kept settings again.
--   { done = "finished" | "time" | "unreachable", set = {...}, best = fps, cap = fps? }: stop. A "finished" or
--   "time" run leaves the kept values on once set is applied; "unreachable" means put the settings from
--   before back. cap: the FPS cap the lowest settings ran at, if any.
function AT.Step(run, m)
	if run.phase == nil then
		run.phase = "now"
		return { set = {}, measure = true }
	end
	if run.pending then
		local p = run.pending
		m = {
			fps = (p.fps + m.fps) / 2, low = math.min(p.low or 0, m.low or 0),
			slow = (p.slow and m.slow) and math.min(p.slow, m.slow) or nil,
			spread = math.max(p.spread or 0, m.spread or 0), frames = (p.frames or 0) + (m.frames or 0),
			steady = m.steady, again = true,
		}
		run.pending = nil
	end
	run.count = run.count + 1
	local limit = AT.MAX_TRIES + (run.checking and 5 or 0) -- a last check may run a little over

	if run.phase == "now" then
		run.before = m
		if run.from then return FromStep(run, m) end
		run.phase = "floor"
		return { set = FloorValues(run), measure = true }
	end

	local function Again(verdict)
		if verdict == "again" and run.count < limit then
			run.pending = m
			return { set = {}, measure = true, again = true, check = run.checking or nil }
		end
	end
	if run.from then return FromStep(run, m, Again, limit) end

	if run.phase == "floor" then
		run.cap = AT.Cap(m, run.vsync)
		if run.cap and run.goal > run.cap * (1 + AT.CAP_NEAR) then
			run.floor = m
			return { done = "unreachable", set = {}, best = m.fps, cap = run.cap }
		end
		local verdict = AT.Verdict("target", run.goal, m, nil, nil, Judge(run))
		local again = Again(verdict)
		if again then return again end
		run.floor = m
		if verdict ~= "pass" then return { done = "unreachable", set = {}, best = m.fps, cap = run.cap } end
		run.last, run.lastWasKept = m, true
		local probe = Probe(run)
		if probe then return probe end
		run.phase = "climb"
		return Continue(run, {})
	end

	if run.checking then
		-- These settings passed already, so a check on the way allows the 3% a close call would, and is judged
		-- as it is: it is there to catch a PC that slowed, not to measure twice. The last check is what you get,
		-- so it is judged like any try.
		if not run.final then m.again = true end
		local verdict = AT.Verdict("target", run.goal, m, nil, nil, Judge(run, nil, not run.final))
		local again = Again(verdict)
		if again then return again end
		run.checking = false
		if verdict == "pass" or #run.kept == 0 then
			-- The freshest measurement of the kept settings is the baseline from now on (the PC may have warmed up).
			run.last, run.lastWasKept, run.lastLoose = m, true, not run.final
			run.checkedDepth = #run.kept
			if run.final then
				run.finalDone = true
				return { done = run.outOfTime and "time" or "finished", set = {} }
			end
			return Continue(run, {})
		end
		-- They no longer hold: undo the newest kept raise, and measure again. Out of measurements, go back to
		-- the settings the last passing check measured instead, so one bad moment can't undo raise after raise.
		local set = {}
		local function Undo()
			local top = table.remove(run.kept)
			local kn = top.knob
			kn.lo, kn.hi, kn.settled, kn.ms, kn.cost = top.prev, top.prev, true, top.ms, top.cost
			set[kn.def.cvar] = kn.steps[kn.lo][1]
		end
		Undo()
		run.lastWasKept = false
		if run.count >= limit and #run.kept > (run.checkedDepth or 0) then
			while #run.kept > (run.checkedDepth or 0) do Undo() end
		end
		if run.count >= limit then
			run.finalDone = false
			return { done = "time", set = set }
		end
		return Check(run, set, run.final)
	end

	local kn, index = run.try.knob, run.try.index
	if run.phase == "probe" then
		-- Hardly slower at 100% than at the lowest: the CPU sets the limit. A cap hides it, so not then.
		run.cpuBound = not run.cap and m.fps * AT.CPU_BOUND >= run.floor.fps
	end
	local worth = 0
	for i = kn.lo + 1, index do worth = worth + (kn.steps[i][2] or 0) end
	local verdict = AT.Verdict(run.mode, run.goal, m, run.last, worth, Judge(run, kn))
	local again = Again(verdict)
	if again then return again end
	if verdict == "again" then verdict = "fail" end
	run.phase = "climb"

	local set = {}
	if verdict == "pass" then
		run.kept[#run.kept + 1] = { knob = kn, prev = kn.lo, ms = kn.ms, cost = kn.cost }
		-- The cost in time a frame: it adds up fairly from one setting to the next, where FPS doesn't.
		kn.ms = (kn.ms or 0) + 1000 / m.fps - 1000 / run.last.fps
		kn.cost = (kn.cost or 0) + run.last.fps - m.fps
		kn.lo = index
		run.last, run.lastWasKept, run.lastLoose = m, true, false
	else
		kn.hi = index - 1
		set[kn.def.cvar] = kn.steps[kn.lo][1]
		run.lastWasKept = false
	end
	if kn.lo >= kn.hi then kn.settled = true end
	run.try = nil
	run.sinceCheck = run.sinceCheck + 1
	return Continue(run, set)
end

-- The values the run has kept, per CVar.
function AT.Values(run)
	local values = {}
	for _, kn in ipairs(run.knobs) do
		if not kn.def.after or kn.lo > 1 then values[kn.def.cvar] = kn.steps[kn.lo][1] end
	end
	return values
end

-- Each setting the run changed: { cvar, key, before, after, cost (FPS its kept raises took, or nil),
-- ms (the time a frame they took, or nil) }.
function AT.Changes(run)
	local list, row = {}, {}
	for _, kn in ipairs(run.knobs) do
		local cvar = kn.def.cvar
		if not kn.def.after or kn.lo > 1 then
			local r = row[cvar]
			if not r then
				r = { cvar = cvar, key = kn.def.key, before = kn.before }
				row[cvar] = r
				list[#list + 1] = r
			end
			r.after = kn.steps[kn.lo][1]
			-- Render scale is two settings here (up to 100%, then over): their costs add up.
			if kn.cost then r.cost = (r.cost or 0) + kn.cost end
			if kn.ms then r.ms = (r.ms or 0) + kn.ms end
		end
	end
	local out = {}
	for _, r in ipairs(list) do
		if r.before == nil or not ns.Same(r.before, r.after) then out[#out + 1] = r end
	end
	return out
end

----------------------------------------------------------------------
-- The PC, as far as the game tells
----------------------------------------------------------------------

local function Call(f, ...)
	if type(f) ~= "function" then return nil end
	local ok, a, b = pcall(f, ...)
	if ok then return a, b end
end

-- { gpu, lowPower, external, width, height, vsync, scaleMin, scaleMax }. Any of them may be nil.
-- The GPU shown is the one the gxAdapter CVar names, or with it on auto, the first that isn't a low-power chip.
-- That the game picks that one on auto is a guess.
function AT.Machine()
	local info = {}
	local vo = C_VideoOptions or {}
	local adapters = Call(vo.GetGxAdapterInfo)
	if type(adapters) == "table" then
		local want = GetCVar and GetCVar("gxAdapter") or ""
		local pick
		for _, a in ipairs(adapters) do
			if want ~= "" and a.name == want then pick = a end
		end
		if not pick then
			for _, a in ipairs(adapters) do
				if not a.isLowPower then pick = pick or a end
			end
		end
		pick = pick or adapters[1]
		if pick then
			info.gpu, info.lowPower, info.external = pick.name, pick.isLowPower, pick.isExternal
		end
	end
	local size = Call(vo.GetCurrentGameWindowSize, tonumber(GetCVar and GetCVar("gxMonitor")) or 0,
		GetCVarBool and GetCVarBool("gxMaximize"))
	if type(size) == "table" and size.x then info.width, info.height = size.x, size.y end
	info.vsync = ns.Exists("vsync") and ns.Same(ns.GetInfo("vsync"), 1) or false
	info.scaleMin, info.scaleMax = Call(GetMinRenderScale), Call(GetMaxRenderScale)
	return info
end

-- Can this PC use this value? Render scale within the game's range; menu values by the game's own check.
local function Supported(cvar, value)
	if cvar == "RenderScale" then
		local lo, hi = Call(GetMinRenderScale) or 0.33, Call(GetMaxRenderScale) or 2
		return value >= lo - 0.001 and value <= hi + 0.001
	end
	if cvar:find("^graphics") then return ns.IsSupported(cvar, value) end
	-- CMAA and CMAA 2 only where the game offers them: AntiAliasingSupported() gives fxaa, cmaa, cmaa2
	-- (Blizzard's Graphics.lua, forever). If the game doesn't say, neither is tried.
	if cvar == "ffxAntiAliasingMode" and tonumber(value) and tonumber(value) >= 3 then
		local ok, _, cmaa, cmaa2 = pcall(AntiAliasingSupported)
		if not ok then return false end
		if tonumber(value) == 3 then return cmaa and true or false end
		return cmaa2 and true or false
	end
	return true
end
AT.Supported = Supported

----------------------------------------------------------------------
-- Words
----------------------------------------------------------------------

-- The setting's name in the game's own words where Eye Candy has them.
function AT.Label(cvar)
	local row = ns.StandardRow and ns.StandardRow(cvar)
	local text = row and ns.StandardText and ns.StandardText(row.label)
	if text then return text end
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, r in ipairs(cat.cvars) do
			if r[1] == cvar then return r[2] end
		end
	end
	return cvar
end

function AT.ValueText(cvar, value)
	if value == nil then return "?" end
	if cvar == "RenderScale" then return math.floor(tonumber(value) * 100 + 0.5) .. "%" end
	local row = ns.StandardRow and ns.StandardRow(cvar)
	if row and ns.FormatStandard then
		local ok, text = pcall(ns.FormatStandard, row, value)
		if ok and text then return text end
	end
	return ns.FormatNumber(tonumber(value) or value)
end

-- What a setting costs in FPS at the result's rate: the FPS you'd gain without its ms a frame. nil if unknown.
function AT.CostFPS(ms, fps)
	if not (ms and fps and fps > 0) then return nil end
	local without = 1000 / fps - ms
	if without <= 0 then return nil end
	return 1000 / without - fps
end

function AT.GoalName(mode, goal)
	if mode == "balance" then return "best balance" end
	return goal .. " FPS"
end

----------------------------------------------------------------------
-- The run in the game
----------------------------------------------------------------------

local run, state, restoring
local frame = CreateFrame("Frame")
frame:Hide()
AT.frame = frame

local function Refresh()
	if ns.RefreshUI then ns.RefreshUI() end
end

-- The tab's status line. kind: "done" (normal), "waiting" (grey) or "refused" (red).
local function Say(kind, text)
	AT.message, AT.messageKind = text, kind
end
AT.Say = Say

-- Chat only when the Experimental tab isn't in front of the player: the tab says it there.
local function Tell(msg)
	local m = _G.EyeCandyMainFrame
	if m and m.IsShown and m:IsShown() and not m.shrunk and m.tab == "autotune" then return end
	ns.Print(msg)
end

local function SetValues(values)
	restoring = true
	for cvar, v in pairs(values) do
		if ns.Exists(cvar) and not ns.Same(ns.GetInfo(cvar), v) then SetCVar(cvar, v) end
	end
	restoring = false
end

-- Puts back every setting saved at the start. A menu value can reset hidden values (Data.lua), so the
-- whole list was saved, and ns.ApplyValues sets menu values before hidden ones. The second pass catches what
-- isn't on Eye Candy's list (the FPS limits); values already right are not touched again.
local function PutBefore(saved)
	if not (saved and saved.before) then return end
	restoring = true
	local ok, err = pcall(ns.ApplyValues, saved.before, false)
	restoring = false
	SetValues(saved.before)
	if not ok then error(err, 0) end
end

-- Puts the settings from before back and forgets them, or in a fight, waits for it to end (Eye Candy never
-- changes settings in combat). msg: said in chat once they are back. Returns true when they are back now.
local function Restore(msg)
	local saved = ns.db.autotune
	if not saved then return true end
	if InCombatLockdown() then
		saved.afterCombat = msg
		saved.result = nil
		return false
	end
	PutBefore(saved)
	ns.db.autotune = nil
	return true
end

local function PutCaps(saved)
	if not (saved and saved.before) then return end
	local caps = {}
	for cvar in pairs(AT.CAPS) do caps[cvar] = saved.before[cvar] end
	SetValues(caps)
end

function AT.IsRunning() return run ~= nil end

-- One short line for the window's title and the Presets card while Autotune has your settings, or nil.
function ns.AutotuneNote()
	if run then return "Autotune is testing settings" end
	local saved = ns.db and ns.db.autotune
	if saved and saved.afterCombat then return "Autotune puts your settings back after the fight" end
	if AT.result then return "Autotune's settings are on, not saved yet" end
end

-- Which way you face, in radians: 0 is north, counterclockwise (warcraft.wiki.gg). nil in an instance.
local function Facing()
	local ok, f = pcall(GetPlayerFacing)
	if ok and type(f) == "number" then return f end
end

-- The camera's distance (GetCameraZoom ignores walls the camera bumps into, so it holds still while you do).
local function Zoom()
	local z = Call(GetCameraZoom)
	if type(z) == "number" then return z end
end

-- The camera being dragged round: right-drag (mouse look), or the left button held over the world for more
-- than DRAG_HOLD seconds (a quick click to pick a target is not a drag; the game hides the cursor while it
-- turns the camera, so its position can't tell). Over the world, GetMouseFoci gives the world frame or an
-- empty list (warcraft.wiki.gg); over a button it gives the button. dt: seconds since the last look.
AT.DRAG_HOLD = 0.3
local held = 0
local function DraggingCamera(dt)
	if Call(IsMouselooking) then return true end
	local foci = Call(IsMouseButtonDown, "LeftButton") and Call(GetMouseFoci)
	if type(foci) == "table" and (foci[1] == nil or foci[1] == WorldFrame) then
		held = held + (dt or 0)
	else
		held = 0
	end
	return held > AT.DRAG_HOLD
end

-- Where and how a run measured: zone, subzone, map position (0 to 100), facing, field of view and camera
-- distance. A part the game doesn't give (an instance hides the position and facing) is left out.
function AT.Place()
	local p = {}
	local zone = Call(GetRealZoneText) or Call(GetZoneText)
	if type(zone) == "string" and zone ~= "" then p.zone = zone end
	local sub = Call(GetSubZoneText)
	if type(sub) == "string" and sub ~= "" and sub ~= p.zone then p.subzone = sub end
	local map = C_Map and Call(C_Map.GetBestMapForUnit, "player")
	local pos = map and C_Map and Call(C_Map.GetPlayerMapPosition, map, "player")
	if type(pos) == "table" and pos.GetXY then
		local ok, x, y = pcall(pos.GetXY, pos)
		if ok and type(x) == "number" and type(y) == "number" and (x > 0 or y > 0) then
			p.x, p.y = x * 100, y * 100
		end
	end
	p.facing = Facing()
	p.fov = ns.Exists("cameraFov") and tonumber((ns.GetInfo("cameraFov"))) or nil
	p.zoom = Zoom()
	return p
end

local COMPASS = { "north", "north-west", "west", "south-west", "south", "south-east", "east", "north-east" }

-- One line for a preset's description, or nil if the game gave nothing.
function AT.PlaceText(p)
	if not p then return nil end
	local parts = {}
	local where = p.zone and ((p.subzone and (p.subzone .. ", ") or "") .. p.zone)
	if where then
		if p.x then where = where .. string.format(" at %.1f, %.1f", p.x, p.y) end
		if p.facing then
			local i = math.floor(p.facing / (math.pi / 4) + 0.5) % 8 + 1
			where = where .. ", facing " .. COMPASS[i]
		end
		parts[#parts + 1] = "Tested in " .. where .. "."
	end
	local cam = {}
	if p.fov then cam[#cam + 1] = string.format("field of view %d", math.floor(p.fov + 0.5)) end
	if p.zoom then cam[#cam + 1] = string.format("camera distance %d", math.floor(p.zoom + 0.5)) end
	if #cam > 0 then
		local s = table.concat(cam, ", ")
		parts[#parts + 1] = s:sub(1, 1):upper() .. s:sub(2) .. "."
	end
	if #parts == 0 then return nil end
	if #cam > 0 then parts[#parts + 1] = "A wider view or a camera further out draws more." end
	return table.concat(parts, " ")
end

-- Why the run must stop now, or nil. dt: seconds since the last look (for a held mouse button).
function AT.Interrupted(dt)
	if InCombatLockdown() then return "a fight started" end
	if type(IsPlayerMoving) == "function" and IsPlayerMoving() then return "you moved" end
	if SettingsPanel and SettingsPanel.IsShown and SettingsPanel:IsShown() then return "Options opened" end
	if state and state.facing then
		local now = Facing()
		local ok, turned = pcall(function() return now and math.abs(now - state.facing) > 0.05 end)
		if ok and turned then return "you turned" end
	end
	if DraggingCamera(dt) then return "you moved the camera" end
	if state and state.zoom then
		local now = Zoom()
		local ok, zoomed = pcall(function() return now and math.abs(now - state.zoom) > 1 end)
		if ok and zoomed then return "you zoomed the camera" end
	end
end

local Finish

local function Do(action)
	local set = action.set
	if action.base then
		-- A preset's values go on as a preset's do: menu values before hidden ones (Presets.lua). Then only
		-- the tuned settings again: set in any order, the base quality slider could reset them.
		restoring = true
		local ok = pcall(ns.ApplyValues, action.set, false)
		restoring = false
		if ok then
			set = {}
			for cvar, v in pairs(action.set) do
				if AT.KNOB_BY_CVAR[cvar] then set[cvar] = v end
			end
		end
	end
	if set then SetValues(set) end
	-- A menu value can reset hidden values (Data.lua): the preset's own go back on after each change, menu
	-- values before hidden ones, as a preset puts them on. Values already right are not touched.
	if run.fromRest and action.set and next(action.set) ~= nil and not action.base then
		restoring = true
		pcall(ns.ApplyValues, run.fromRest, false)
		restoring = false
	end
	if action.done then return Finish(action) end
	local slow = false
	for cvar in pairs(action.set or {}) do
		for _, def in ipairs(AT.KNOBS) do
			if def.cvar == cvar and def.slow then slow = true end
		end
	end
	state = {
		phase = "settle", min = slow and AT.SETTLE_MIN_SLOW or AT.SETTLE_MIN, waited = 0, wn = 0, wt = 0,
		times = {}, facing = state and state.facing, zoom = state and state.zoom,
	}
	AT.progress = { count = run.count + 1, max = AT.MAX_TRIES, try = action.try, phase = run.phase,
		again = action.again, check = action.check, capTest = action.capTest }
	Refresh()
end

-- Starts a run. mode: "target" (goal = 30 to 240) or "balance". style: the way of tuning (AT.STYLES; nil is
-- Best look). fromId: a preset to start from (any of ns.ListPresets); nil builds up from the lowest settings.
-- Returns true, or false and why.
function AT.Start(mode, goal, style, fromId)
	local st = AT.STYLE[style] or AT.STYLE.look
	if run then return false, "Autotune is already running." end
	if st.capAtGoal and mode ~= "target" then return false, st.name .. " needs an FPS goal. Pick one above." end
	local from
	if fromId then
		local values, why = ns.PresetValues(fromId)
		local p = ns.FindPreset(fromId)
		if not (values and p) then
			return false, (why == "damaged" and "That preset is damaged" or "That preset is gone")
				.. ", so Autotune can't start from it. Pick another."
		end
		-- FPS limits are never a preset's (Autotune lifts them while it measures).
		for cvar in pairs(AT.CAPS) do values[cvar] = nil end
		values.maxFPS = nil
		from = { id = fromId, name = p.name, values = values, keep = AT.Essence(fromId, values) }
	end
	if InCombatLockdown() then return false, "Autotune can't start in a fight. Try again after it." end
	if type(IsPlayerMoving) == "function" and IsPlayerMoving() then return false, "Stand still first, then press Start." end
	AT.pending = nil
	-- A result still waiting for Keep or Put back goes back first, so "before" is your own settings.
	if ns.db.autotune then AT.PutBack(true) end

	local before = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local v = ns.GetInfo(cvar)
		if v ~= nil then before[cvar] = v end
	end
	for _, def in ipairs(AT.KNOBS) do
		if ns.Exists(def.cvar) then before[def.cvar] = ns.GetInfo(def.cvar) end
	end
	for cvar in pairs(AT.CAPS) do
		if ns.Exists(cvar) then before[cvar] = ns.GetInfo(cvar) end
	end
	-- The cap's number too: Cool and quiet changes it, and Back to before Autotune puts it back.
	if ns.Exists("maxFPS") then before.maxFPS = ns.GetInfo("maxFPS") end
	-- And anything else the preset sets, so Back to before Autotune puts all of it back.
	for cvar in pairs(from and from.values or {}) do
		if before[cvar] == nil and ns.Exists(cvar) then before[cvar] = ns.GetInfo(cvar) end
	end
	-- Saved, so a reload or a crash mid-run still puts them back at the next login.
	ns.db.autotune = { before = before, mode = mode, goal = goal, style = st.key, from = fromId }
	AT.result, AT.message, AT.messageKind = nil, nil, nil
	SetValues(AT.CAPS)

	run = AT.NewRun(mode, goal, { exists = ns.Exists, supported = Supported, current = before, vsync = AT.Machine().vsync }, st.key, from)
	if from then
		-- The preset's values Autotune doesn't tune: put back on after each change (Do). Not the base quality
		-- slider (Standard.lua's master row): set again, it would reset the settings just lowered.
		run.fromRest = {}
		for cvar, v in pairs(from.values) do
			if not AT.KNOB_BY_CVAR[cvar] and cvar ~= "graphicsQuality" then run.fromRest[cvar] = v end
		end
	end
	-- The camera distance is read once the first settle is over: a camera still easing after a scroll of the
	-- wheel would otherwise look like a zoom.
	state = { facing = Facing() }
	-- Where it measured, for the result and the preset: the result holds for this spot and this camera.
	run.place = AT.Place()
	frame:Show()
	Do(AT.Step(run, nil))
	return true
end

local function Clear()
	run, state, AT.progress = nil, nil, nil
	frame:Hide()
end

-- Stops a run and puts the settings from before back. why: shown to the player.
function AT.Stop(why)
	if not run then return end
	Clear()
	if Restore("Autotune: the fight is over, so your settings are back as they were.") then
		Say("done", "Autotune stopped: " .. why .. ". Your settings are back as they were.")
	else
		Say("waiting", "Autotune stopped: " .. why .. ". Your settings come back when the fight ends.")
	end
	Tell(AT.message)
	Refresh()
end

Finish = function(action)
	local saved = ns.db.autotune
	local goalName = AT.GoalName(run.mode, run.goal)
	local st = run.style
	if action.done == "unreachable" then
		Restore("Autotune: your settings are back as they were.")
		local best, goalFPS = math.floor((action.best or 0) + 0.5), run.goal .. " FPS"
		-- How low it went: the lowest settings, or from a preset, as low as its look allows.
		local from, kept = run.from, false
		for _ in pairs(from and from.keep or {}) do kept = true end
		local lead = "even at the lowest settings"
		if from and action.trimmed then
			lead = kept and ("even with everything but " .. from.name .. "'s look lowered") or ("even with " .. from.name .. " lowered as far as it goes")
		elseif from then
			lead = "with " .. from.name .. (action.partly and " partly lowered" or "")
		end
		local msg
		if action.outOfTime then
			msg = string.format("Autotune ran out of time before %s held from %s here. It reached %d FPS.", goalFPS, from and from.name or "your settings", best)
		elseif st.headroom then
			-- Raid ready: the lowest settings may beat the goal itself, but not the spare it keeps.
			msg = string.format("Autotune: %s this spot ran at %d FPS. %s keeps spare for a big fight, so %s needs %d FPS here.",
				lead, best, st.name, goalFPS, math.floor(AT.Line(run) + 0.5))
		else
			msg = string.format("Autotune: %s this spot ran at %d FPS, so %s can't be reached here.", lead, best, goalFPS)
			if st.slowFirst then msg = msg .. " " .. st.name .. " needs your slowest frames at " .. goalFPS .. " or better." end
		end
		if from and kept and not action.cap and not action.outOfTime then
			msg = msg .. " Start from Lowest settings to lower " .. from.name .. "'s look too."
		end
		if action.cap then
			msg = msg .. " FPS stayed at " .. action.cap .. ", which looks like Vertical Sync or another limit."
		elseif AT.Machine().vsync then
			msg = msg .. " Vertical Sync is on, which holds FPS at your screen's refresh rate."
		end
		Say("done", msg .. " Your settings are back as they were.")
		Tell(AT.message)
		Clear()
		Refresh()
		return
	end
	PutCaps(saved)
	-- Cool and quiet: the game's FPS cap goes on at the goal. Read back, since the game may hold it lower.
	local fpsCap, capAsked, capKept
	if st.capAtGoal and run.mode == "target" and ns.Exists("maxFPS") and ns.Exists("useMaxFPS") then
		SetValues({ useMaxFPS = 1, maxFPS = run.goal })
		capAsked = run.goal
		local kept = tonumber((ns.GetInfo("maxFPS")))
		if kept and math.abs(kept - run.goal) < 0.5 then
			fpsCap = kept
		else
			-- The game kept another number: a cap under the goal would undo the tune, so yours goes back.
			capKept = kept
			SetValues({ useMaxFPS = saved.before.useMaxFPS, maxFPS = saved.before.maxFPS })
		end
	end
	saved.result = true
	local changes = AT.Changes(run)
	-- Video memory: the game doesn't say how much there is. A power-saving chip shares the PC's memory, so
	-- high-resolution textures may stutter when a lot loads at once (flying). A guess, so only a hint.
	local textures = false
	for _, c in ipairs(changes) do
		if c.key == "textures" and tonumber(c.after) and tonumber(c.after) > (tonumber(c.before) or 0) then textures = true end
	end
	AT.result = {
		-- The way of tuning goes in the name, but not Best look's ("Autotune 60 FPS cool and quiet"). From a
		-- preset, it is named for the preset ("Moody for 120 FPS").
		mode = run.mode, goal = run.goal, style = st.key, fpsCap = fpsCap, capAsked = capAsked, capKept = capKept,
		name = (run.from and (run.from.name .. " for ") or "Autotune ") .. goalName .. (st.key ~= "look" and (" " .. st.name:lower()) or ""),
		from = run.from and run.from.name, fromValues = run.from and run.from.values,
		before = run.before and run.before.fps, after = run.last and run.last.fps,
		changes = changes, time = action.done == "time", cpuBound = run.cpuBound, place = run.place,
		-- The cap, only when it lowered the line: a 60 goal under a 144 cap was judged as usual. The way of
		-- tuning's own spare counts (Raid ready's 50% under a 144 cap is not 50%).
		cap = run.cap and run.cap * AT.CAP_LINE < run.goal * (st.headroom or AT.HEADROOM) and run.cap or nil,
		texturesHint = textures and AT.Machine().lowPower or nil,
	}
	Tell(string.format("Autotune is done: %d FPS before, %d FPS now. Save as preset or Back to before Autotune, on the Experimental tab.",
		math.floor(AT.result.before or 0), math.floor(AT.result.after or 0)))
	Clear()
	Refresh()
end

-- Keeps the result: saves it as one of your presets and applies that, so it stays on like any preset.
function AT.Keep()
	local saved = ns.db.autotune
	if not (AT.result and saved) then return false end
	if InCombatLockdown() then
		AT.pending = "keep"
		Say("waiting", "Waiting for the fight to end, then Autotune's settings are saved as your preset.")
		Refresh()
		return false
	end
	AT.pending = nil
	local name, n = AT.result.name, 1
	while ns.FindPresetByName(name) do
		n = n + 1
		name = AT.result.name .. " (" .. n .. ")"
	end
	local p = ns.SaveCurrentAsPreset(name)
	if not p then
		Say("refused", "Autotune couldn't save the preset. Autotune's settings are still on.")
		Refresh()
		return false
	end
	-- Where it was tested, in the preset's tooltip on the Presets tab. A Cool and quiet cap is your own
	-- setting, not the preset's (presets never hold FPS limits, so a shared one can't reset yours), so the
	-- note leaves it out: it goes with a copy and a share code, where it wouldn't be true.
	local cap = AT.result.fpsCap
	local fromValues = AT.result.fromValues
	local place = AT.PlaceText(AT.result.place)
	p.desc = AT.result.from and ("Started from " .. AT.result.from .. "." .. (place and (" " .. place) or "")) or place
	-- The tuned settings on top of everything else as it was: a menu value may have reset a hidden one
	-- during the run, and the preset keeps yours. In a city with the city switch on, yours is the value
	-- from before the switch lowered it (Situations.lua). From a preset, everything else is the preset's.
	local tuned = {}
	for _, def in ipairs(AT.KNOBS) do tuned[def.cvar] = true end
	for cvar, v in pairs(fromValues or saved.before) do
		if not tuned[cvar] and not AT.CAPS[cvar] and p.values[cvar] ~= nil then
			if not fromValues and ns.SituationValue then v = ns.SituationValue(cvar, v) end
			p.values[cvar] = tostring(v)
		end
	end
	-- Back to before first, so the preset's step in today's list holds your old settings.
	PutBefore(saved)
	ns.db.autotune = nil
	AT.result = nil
	if ns.ApplyPresetById(p.id) then
		if cap then SetValues({ useMaxFPS = 1, maxFPS = cap }) end
		Say("done", "Autotune's settings are saved as your preset \"" .. name .. "\" and on now."
			.. (cap and (" FPS is capped at " .. cap .. ", as your own setting, not part of the preset. Change it on the Standard tab: Max Foreground FPS.") or ""))
	else
		Say("refused", "Autotune saved your preset \"" .. name .. "\", but it couldn't be put on. Your settings are back as they were. Pick it on the Presets tab to try again.")
	end
	Refresh()
	return true
end

-- Throws the result away and puts the settings from before back. quiet: no chat line.
function AT.PutBack(quiet)
	local saved = ns.db.autotune
	if not saved then return false end
	if InCombatLockdown() then
		if not quiet then
			AT.pending = "putback"
			Say("waiting", "Waiting for the fight to end, then your settings go back as they were.")
			Refresh()
		end
		return false
	end
	AT.pending = nil
	if run then Clear() end
	Restore()
	AT.result = nil
	if not quiet then
		Say("done", "Autotune: your settings are back as they were.")
		Tell(AT.message)
	end
	Refresh()
	return true
end

frame:SetScript("OnUpdate", function(self, elapsed)
	if not run then self:Hide() return end
	local why = AT.Interrupted(elapsed)
	if why then return AT.Stop(why) end
	if state.phase == "settle" then
		-- Settled once two half-second windows agree, after the least wait; never longer than SETTLE_MAX.
		state.waited, state.wn, state.wt = state.waited + elapsed, state.wn + 1, state.wt + elapsed
		if state.wt >= AT.SETTLE_WINDOW then
			local fps = state.wn / state.wt
			local agree = state.prevFps and math.abs(fps - state.prevFps) / state.prevFps <= AT.SETTLE_AGREE
			state.prevFps, state.wn, state.wt = fps, 0, 0
			if (agree and state.waited >= state.min) or state.waited >= AT.SETTLE_MAX then
				state.phase, state.sampled, state.times, state.nextEarly = "sample", 0, {}, AT.EARLY_AFTER
				if not state.zoom then
					state.zoom = Zoom()
					if run.place then run.place.zoom = state.zoom or run.place.zoom end
				end
			end
		end
		return
	end
	state.times[#state.times + 1] = elapsed
	state.sampled = state.sampled + elapsed
	local enough = state.sampled >= (run.style.sample or AT.SAMPLE)
	-- A try far from its line can stop early. Looked at four times a second, not every frame.
	if not enough and state.sampled >= state.nextEarly then
		state.nextEarly = state.sampled + 0.25
		enough = AT.Early(run, AT.Stats(state.times))
	end
	if not enough then return end
	local m = AT.Stats(state.times)
	if m.hitch and not state.retook then
		-- A long frame (a shader compile, a texture loading): take the sample once more.
		state.retook, state.sampled, state.times, state.nextEarly = true, 0, {}, AT.EARLY_AFTER
		return
	end
	Do(AT.Step(run, m))
end)

-- Any other Eye Candy change during a run stops it first, so the measurement and the way back stay right.
-- The backup calls are here too: a preset takes its backup before it applies, and that backup must hold your
-- settings, not the run's.
for _, name in ipairs({ "ApplyAll", "ApplyValues", "CreateBackup", "TakeBackup" }) do
	local orig = ns[name]
	if orig then
		ns[name] = function(...)
			if run and not restoring then AT.Stop("another setting changed") end
			return orig(...)
		end
	end
end

local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(_, event, isLogin, isReload)
	local saved = ns.db and ns.db.autotune
	if event == "PLAYER_ENTERING_WORLD" then
		-- A run or a result left over from before a reload: put the settings from before back.
		if (isLogin or isReload) and saved and not run then
			local msg = saved.result and "Autotune: you didn't save its result, so your settings went back as they were."
				or "Autotune didn't finish last time, so your settings went back as they were."
			AT.result, AT.pending = nil, nil
			if Restore(msg) then
				Say("done", msg)
				Tell(msg)
			else
				Say("waiting", "Autotune: your settings from before come back when the fight ends.")
			end
		end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if saved and saved.afterCombat and not run then
			local msg = saved.afterCombat
			if Restore() then
				Say("done", msg)
				Tell(msg)
				Refresh()
			end
		elseif AT.pending and not run then
			local what = AT.pending
			AT.pending = nil
			-- The waiting line goes, even if there is nothing left to save or put back by now.
			if AT.messageKind == "waiting" then Say(nil, nil) end
			if what == "keep" then AT.Keep() else AT.PutBack() end
		end
	elseif run then
		AT.Stop(event == "PLAYER_REGEN_DISABLED" and "a fight started"
			or event == "PLAYER_STARTED_MOVING" and "you moved" or "a loading screen")
	end
end)
-- One at a time: an event this client doesn't know must not stop the others.
for _, event in ipairs({ "PLAYER_ENTERING_WORLD", "PLAYER_REGEN_ENABLED", "PLAYER_REGEN_DISABLED",
	"PLAYER_STARTED_MOVING", "PLAYER_LEAVING_WORLD" }) do
	pcall(events.RegisterEvent, events, event)
end
