-- Eye Candy: the Experimental tab. It holds several parts (ns.EXPERIMENTS): Autotune first, then each part
-- another file adds with ns.AddExperiment. A row of buttons at the top picks the part on show, remembered per
-- account in EyeCandyDB.experimentPart. Each part has its own scrolling page.
-- Autotune (Autotune.lua): pick a goal, a way of tuning and where to start, press Start, stand still. All
-- three are remembered per account in EyeCandyDB.autotuneGoal =
-- { mode, goal, style, from (a preset's id; nil is the lowest settings) }.
-- Built to docs/ui-rules.md: ns.Header headings, each part anchored under the one before (so a long
-- line pushes the rest down instead of overlapping it), and only the colours in rule 20.

local _, ns = ...
local AT = ns.Autotune

local W = ns.ROW_W - 16
local GREY, RED, GOLD, WHITE = "|cff9d9d9d", "|cffff4040", "|cffffd100", "|cffffffff"
local ROW, GROUP = 4, 16 -- spacing inside a group, and before the next heading

-- The goal picked. One no longer offered (90 FPS, before 15 Nov 2026) falls back to Best balance, so the
-- page always shows the goal Start would use.
local function Offered(goal)
	for _, g in ipairs(AT.GOALS) do
		if g == goal then return true end
	end
	return false
end

-- The goal, the way of tuning and the preset to start from picked. A goal saved before the ways of tuning
-- (no style) is Best look. A preset that has gone since (deleted) falls back to the lowest settings.
local function Goal()
	local g = ns.db.autotuneGoal
	local style = type(g) == "table" and AT.STYLE[g.style] and g.style or "look"
	local from = type(g) == "table" and g.from and ns.FindPreset and ns.FindPreset(g.from) and g.from or nil
	if type(g) == "table" and (g.mode == "balance" or (g.mode == "target" and Offered(tonumber(g.goal)))) then
		return g.mode, tonumber(g.goal), style, from
	end
	return "balance", nil, style, from
end

-- Remembers a pick, keeping the rest of what was picked.
local function Pick(field, value, field2, value2)
	local mode, goal, style, from = Goal()
	local g = { mode = mode, goal = goal, style = style, from = from }
	g[field] = value
	if field2 then g[field2] = value2 end
	ns.db.autotuneGoal = g
	ns.RefreshUI()
end

-- What each way of tuning does, in its tooltip and the line under the buttons.
local STYLE_TEXT = {
	look = "The best look that holds your goal.",
	raid = "Keeps a lot more spare FPS, so your goal holds in a big fight. Tune in a quiet spot.",
	smooth = "Judged by your slowest frames, not the average. Fewer hitches, a little less detail.",
	sharp = "Spends spare FPS on a clear picture first: render scale, textures, anti-aliasing, sharpening and view distance. Shadows and effects come after.",
	cool = "Caps FPS at your goal so your graphics card works less: less heat, noise and power. Looks stay as high as they can.",
}

local function StyleText(mode, style)
	local text = STYLE_TEXT[style]
	if AT.STYLE[style].capAtGoal and mode ~= "target" then
		text = text .. "\n" .. AT.STYLE[style].name .. " needs an FPS goal. Pick one above."
	end
	return text
end

-- The presets to start from, in the Presets tab's order: the quality levels, Looks and Situations, then yours.
local function FromList()
	local list = ns.ListPresets and ns.ListPresets() or { builtin = {}, user = {} }
	local out = {}
	for _, p in ipairs(list.builtin or {}) do out[#out + 1] = p end
	for _, p in ipairs(list.user or {}) do out[#out + 1] = p end
	return out
end

-- "a, b and c".
local function List(words)
	if #words < 2 then return words[1] or "" end
	return table.concat(words, ", ", 1, #words - 1) .. " and " .. words[#words]
end

-- The line under Start from: what is kept and what goes. mode, style: Best balance lowers a little more
-- once 60 holds, and Sharpest picture lowers the clear settings last.
local function FromText(from, mode, style)
	local p = from and ns.FindPreset(from)
	if not p then return "Builds up from the lowest settings, one setting at a time." end
	local values = ns.PresetValues(from) or {}
	local keep, labels = AT.Essence(from, values), {}
	for _, def in ipairs(AT.KNOBS) do
		if keep[def.key] and values[def.cvar] ~= nil then labels[#labels + 1] = AT.Label(def.cvar) end
	end
	local kept = #labels > 0 and ("its " .. List(labels) .. ", and every setting Autotune doesn't tune")
		or "every setting Autotune doesn't tune"
	local text = "Starts from " .. p.name .. " and keeps " .. kept .. ". Lowers the rest one step at a time, the least look for its cost first, until your goal holds. Never raises anything."
	if mode == "balance" then
		text = text .. " Best balance then lowers a little more where that gains a lot of FPS."
	end
	if AT.STYLE[style] and AT.STYLE[style].clearFirst then
		text = text .. " " .. AT.STYLE[style].name .. " lowers the settings that make the picture clear last."
	end
	return text
end

-- Where to stand and how long it takes. Raid ready keeps its own spare, so a quiet spot is fine; Smooth
-- measures longer and never stops a passing sample early (6 s against 4 s a measurement).
local function HowText(style)
	local where = style == "raid" and "Stand anywhere, even somewhere quiet: Raid ready keeps the spare a big fight needs."
		or "Stand somewhere busy, like a city, so the result holds up in play."
	local long = style == "smooth" and "4 to 10" or "3 to 7"
	return where .. " Press Start, then let go of the mouse and keys for about " .. long .. " minutes. Autotune changes your settings while it runs.\n"
		.. "Moving, turning, dragging or zooming the camera, a loading screen or opening Options stops it and puts your settings back. A fight stops it too, and your settings come back when the fight ends."
end

-- One line in the result: how it was tuned. nil for Best look.
local function StyleResult(r)
	local st = AT.STYLE[r.style or "look"]
	if not st or st.key == "look" then return nil end
	local what
	if st.headroom and r.cap then
		what = "it couldn't keep spare here, because FPS stays at " .. r.cap .. "."
	elseif st.headroom then
		what = string.format("it keeps %d%% spare FPS for a big fight.", math.floor((st.headroom - 1) * 100 + 0.5))
	elseif st.slowFirst then
		what = "judged by your slowest frames."
	elseif st.clearFirst then
		what = "the settings that make the picture clear went first."
	elseif st.capAtGoal then
		if r.capKept then
			what = string.format("FPS isn't capped. The game kept the cap at %d, under your goal of %d, so your own cap is back as it was.",
				r.capKept, r.capAsked or r.goal)
		elseif not r.fpsCap then
			what = "but this game has no FPS cap setting, so FPS isn't capped."
		else
			what = string.format("FPS is capped at %d. Change it on the Standard tab: Max Foreground FPS.", r.fpsCap)
		end
	end
	return "Tuned for " .. st.name .. ": " .. what
end

local function PCText()
	local m = AT.Machine()
	local lines = {}
	if m.gpu then
		lines[#lines + 1] = "Graphics card: " .. m.gpu .. (m.lowPower and " (power saving)" or "")
	else
		lines[#lines + 1] = "Graphics card: the game didn't say."
	end
	local size = m.width and string.format("Game window: %d x %d.", m.width, m.height or 0) or ""
	if m.scaleMin and m.scaleMax then
		size = size .. string.format(" Render scale can go from %d%% to %d%%.",
			math.floor(m.scaleMin * 100 + 0.5), math.floor(m.scaleMax * 100 + 0.5))
	end
	if size ~= "" then lines[#lines + 1] = (size:gsub("^ ", "")) end
	if m.lowPower then
		lines[#lines + 1] = "This looks like a laptop's power-saving graphics chip. 60 FPS is a good goal."
	end
	if m.vsync then
		lines[#lines + 1] = "Vertical Sync is on, so FPS stops at your screen's refresh rate. A goal above that can't be reached."
	end
	lines[#lines + 1] = GREY .. "The game doesn't tell addons your CPU, memory or screen refresh rate, so Autotune measures instead.|r"
	return table.concat(lines, "\n")
end

-- style: the spare kept depends on the way of tuning (Raid ready keeps more).
local function GoalText(mode, goal, style)
	if mode == "balance" then
		return "Each setting goes up only while it's worth what it costs. Never under " .. AT.BALANCE_MIN .. " FPS."
	end
	local spare = math.floor(((AT.STYLE[style or "look"].headroom or AT.HEADROOM) - 1) * 100 + 0.5)
	return "The best look that stays over " .. goal .. " FPS here, with " .. spare .. "% to spare for busier places."
end

local function StatusText()
	local p = AT.progress
	if AT.IsRunning() and p then
		local what
		if p.check then
			what = "Measuring the settings kept so far again, in case your PC has slowed."
		elseif p.again then
			what = "Close call, so measuring again."
		elseif p.phase == "now" then
			what = "Measuring your settings as they are."
		elseif p.phase == "floor" then
			what = "Measuring the lowest settings."
		elseif p.capTest then
			what = "Checking whether something holds FPS at a limit, like Vertical Sync."
		elseif p.phase == "base" then
			what = "Measuring the preset you start from."
		elseif p.try and p.try.trim then
			what = "Lowering " .. AT.Label(p.try.cvar) .. " to " .. AT.ValueText(p.try.cvar, p.try.value) .. "."
		elseif p.try then
			what = "Trying " .. AT.Label(p.try.cvar) .. " at " .. AT.ValueText(p.try.cvar, p.try.value) .. "."
		else
			what = "Measuring."
		end
		return string.format("Autotune is changing your settings to test them. Measurement %d of up to %d. %s Don't touch the mouse or keys.",
			p.count, p.max, what)
	end
	local text = AT.message or ""
	if text == "" then return "" end
	if AT.messageKind == "refused" then return RED .. text .. "|r" end
	if AT.messageKind == "waiting" then return GREY .. text .. "|r" end
	return text
end

local function ResultText(r)
	local goal = r.mode == "balance" and ("best balance, never under " .. AT.BALANCE_MIN .. " FPS") or ("over " .. r.goal .. " FPS")
	local lines = {
		"Autotune's settings are on now. Save as preset keeps them as \"" .. r.name .. "\". Back to before Autotune undoes them.",
		string.format("%d FPS before, %d FPS now. Goal: %s.", math.floor(r.before or 0), math.floor(r.after or 0), goal),
	}
	if r.from then lines[#lines + 1] = "Started from " .. r.from .. ". Each change below is from " .. r.from .. "'s value." end
	local style = StyleResult(r)
	if style then lines[#lines + 1] = style end
	local place = AT.PlaceText(r.place)
	if place then lines[#lines + 1] = place end
	if r.time then lines[#lines + 1] = "It stopped at " .. AT.MAX_TRIES .. " measurements, so some settings weren't tried." end
	if r.cap then
		lines[#lines + 1] = "FPS stays at " .. r.cap .. " here, which looks like Vertical Sync or another limit. Autotune can't leave spare room above it."
	end
	if r.cpuBound then
		lines[#lines + 1] = "Your CPU sets the limit here, so most graphics settings cost little. Busy places can still run slower."
	end
	if r.texturesHint then lines[#lines + 1] = "If it stutters when flying, lower Texture Resolution." end
	if #r.changes == 0 then
		lines[#lines + 1] = r.from and (r.from .. " already holds your goal here, so nothing was lowered.")
			or "Nothing changed. Your settings were already the best fit here."
	end
	for _, c in ipairs(r.changes) do
		local line = string.format("%s: %s to %s", AT.Label(c.cvar), AT.ValueText(c.cvar, c.before), AT.ValueText(c.cvar, c.after))
		local fps = AT.CostFPS(c.ms, r.after)
		if fps and fps >= 1 then line = line .. GREY .. string.format(", costs about %d FPS", math.floor(fps + 0.5)) .. "|r" end
		lines[#lines + 1] = line
	end
	return table.concat(lines, "\n")
end

-- Puts f under prev, dx to the right of prev's left edge, gap pixels lower.
local function Under(f, prev, dx, gap)
	f:SetPoint("TOPLEFT", prev, "BOTTOMLEFT", dx or 0, -(gap or ROW))
end

local function Text(c, font)
	local fs = ns.Label(c, "", font)
	fs:SetWidth(W)
	return fs
end

-- How tall a text is. A long line wraps at W, so it is measured; 14px a line is only the fallback
-- when the game gives no height.
local function TextH(fs, text)
	local m = tonumber((fs.GetStringHeight and fs:GetStringHeight()))
	if m and m > 0 then return m end
	if not text or text == "" then return 0 end
	local _, breaks = text:gsub("\n", "")
	return (breaks + 1) * 14
end

-- How tall a frame is, or its built size when the game gives none.
local function FrameH(f, built)
	local h = tonumber((f.GetHeight and f:GetHeight()))
	return (h and h > 0) and h or built
end

local function BuildAutotune(page, holder)
	local c = ns.ScrollPage(holder, 0)
	c:SetHeight(640)
	page.content = c

	-- Each heading's height, for the page height (every block below is chained under the one above).
	page.headH = {}
	page.head, page.headH.head = ns.Header(c, "Autotune", "Experimental")
	page.head:SetPoint("TOPLEFT", 0, 0)
	page.why = Text(c)
	page.whyText = "Finds the best look your PC can hold at the frame rate you pick. It measures as it goes, one setting at a time."
	page.why:SetText(page.whyText)
	Under(page.why, page.head, 4)

	page.pcHead, page.headH.pc = ns.Header(c, "Your PC")
	Under(page.pcHead, page.why, -4, GROUP)
	page.pc = Text(c)
	Under(page.pc, page.pcHead, 4)

	page.goalHead, page.headH.goal = ns.Header(c, "Goal")
	Under(page.goalHead, page.pc, -4, GROUP)
	page.goals = {}
	local choices = {}
	-- Nine goals on one line: 66px for each FPS goal (8 x 70 + 110 fits the 708px row).
	for _, g in ipairs(AT.GOALS) do choices[#choices + 1] = { "target", g, g .. " FPS", 66 } end
	choices[#choices + 1] = { "balance", nil, "Best balance", 110 }
	local prev, x = nil, 0
	for i, ch in ipairs(choices) do
		local mode, goal, label = ch[1], ch[2], ch[3]
		local b = ns.Button(c, label, ch[4], function() Pick("mode", mode, "goal", goal) end)
		if prev then b:SetPoint("LEFT", prev, "RIGHT", ROW, 0) else Under(b, page.goalHead, 4) end
		-- Buttons on the right half open their tooltip to the left, so it stays inside the window.
		ns.Tooltip(b, label, function() return GoalText(mode, goal, (select(3, Goal()))) end, x > W / 2 and "ANCHOR_LEFT" or nil)
		x = x + ch[4] + ROW
		b.mode, b.goal, b.label = mode, goal, label
		page.goals[i] = b
		prev = b
	end
	page.goalText = Text(c, "GameFontDisableSmall")
	Under(page.goalText, page.goals[1], 0, 8)

	-- The ways of tuning, on one line: 90 + 100 + 80 + 140 + 130 and the gaps fit the row.
	page.styleHead, page.headH.style = ns.Header(c, "Tune for")
	Under(page.styleHead, page.goalText, -4, GROUP)
	page.styles = {}
	local widths = { look = 90, raid = 100, smooth = 80, sharp = 140, cool = 130 }
	prev, x = nil, 0
	for i, st in ipairs(AT.STYLES) do
		local key, w = st.key, widths[st.key] or 120
		local b = ns.Button(c, st.name, w, function() Pick("style", key) end)
		if prev then b:SetPoint("LEFT", prev, "RIGHT", ROW, 0) else Under(b, page.styleHead, 4) end
		ns.Tooltip(b, st.name, STYLE_TEXT[key], x > W / 2 and "ANCHOR_LEFT" or nil)
		x = x + w + ROW
		b.style, b.label = key, st.name
		page.styles[i] = b
		prev = b
	end
	page.styleText = Text(c, "GameFontDisableSmall")
	Under(page.styleText, page.styles[1], 0, 8)

	-- Where it starts: the lowest settings (it builds up), or any preset (it keeps that preset's look and
	-- lowers the rest). A dropdown, or in a client without one, a "< name >" stepper.
	page.fromHead, page.headH.from = ns.Header(c, "Start from")
	Under(page.fromHead, page.styleText, -4, GROUP)
	page.fromMenu = function(_, root)
		local function Item(text, id)
			root:CreateRadio(text, function() return (select(4, Goal())) == id end, function() Pick("from", id) end)
		end
		Item("Lowest settings", nil)
		for _, p in ipairs(FromList()) do Item(p.name, p.id) end
	end
	local ok, dd = pcall(CreateFrame, "DropdownButton", nil, c, "WowStyle1DropdownTemplate")
	if ok and dd and dd.SetupMenu then
		dd:SetWidth(240)
		dd:SetupMenu(page.fromMenu)
		page.fromDropdown = dd
		page.fromPick = dd
	else
		local f = CreateFrame("Frame", nil, c)
		f:SetSize(240, 24)
		local function Step(dir)
			local ids, at = { false }, 1
			for _, p in ipairs(FromList()) do ids[#ids + 1] = p.id end
			local now = select(4, Goal())
			for i, id in ipairs(ids) do if id == (now or false) then at = i end end
			local id = ids[math.min(math.max(at + dir, 1), #ids)]
			Pick("from", id or nil)
		end
		page.fromPrev = ns.Button(f, "<", 24, function() Step(-1) end)
		page.fromPrev:SetPoint("LEFT")
		page.fromNext = ns.Button(f, ">", 24, function() Step(1) end)
		page.fromNext:SetPoint("RIGHT")
		-- Between the buttons, on one line: a long name is cut.
		page.fromName = ns.Label(f, "")
		page.fromName:SetPoint("CENTER")
		page.fromName:SetWidth(184)
		if page.fromName.SetWordWrap then page.fromName:SetWordWrap(false) end
		page.fromStep = Step
		page.fromPick = f
	end
	Under(page.fromPick, page.fromHead, 4)
	ns.Tooltip(page.fromPick, "Start from", "Lowest settings builds up as far as your goal allows. A preset keeps its look and lowers the rest until your goal holds.")
	page.fromText = Text(c, "GameFontDisableSmall")
	Under(page.fromText, page.fromPick, 0, 8)

	page.start = ns.Button(c, "Start", 120, function()
		if AT.IsRunning() then
			AT.Stop("you pressed Stop")
			return
		end
		local mode, goal, style, from = Goal()
		local ok, err = AT.Start(mode, goal, style, from)
		if not ok and err then
			AT.Say("refused", err)
			ns.RefreshUI()
		end
	end)
	Under(page.start, page.fromText, 0, 8)
	ns.Tooltip(page.start, function() return AT.IsRunning() and "Stop" or "Start" end, function()
		return AT.IsRunning() and "Stops now and puts your settings back as they were."
			or "Changes your settings while it measures. Yours are saved first, and come back if it stops."
	end)
	page.status = Text(c)
	Under(page.status, page.start, 0, 8)

	page.how = Text(c, "GameFontDisableSmall")
	Under(page.how, page.status, 0, 8)

	page.resultHead, page.headH.result = ns.Header(c, "Result")
	Under(page.resultHead, page.how, -4, GROUP)
	-- The buttons sit right under the heading, so a long list of changes never pushes them out of reach.
	-- One main button. Back to before Autotune is the smaller, second choice.
	page.keep = ns.Button(c, "Save as preset", 130, function() AT.Keep() end)
	Under(page.keep, page.resultHead, 4)
	page.result = Text(c)
	Under(page.result, page.keep, 0, 8)
	page.putBack = ns.Button(c, "Back to before Autotune", 150, function() AT.PutBack() end)
	page.putBack:SetHeight(20)
	if page.putBack.SetNormalFontObject then page.putBack:SetNormalFontObject("GameFontNormalSmall") end
	page.putBack:SetPoint("LEFT", page.keep, "RIGHT", 8, 0)
	ns.Tooltip(page.keep, "Save as preset", function()
		return "Saves Autotune's settings as your preset \"" .. (AT.result and AT.result.name or "Autotune") .. "\" and keeps them on, like any preset. Back to before on the Presets tab undoes it."
	end)
	ns.Tooltip(page.putBack, "Back to before Autotune", "Puts your settings back as they were before Autotune.")
end

local function RefreshAutotune(page)
	local mode, goal, style, from = Goal()
	local running = AT.IsRunning()
	local pcText = PCText()
	page.pc:SetText(pcText)
	-- The chosen goal and way of tuning are gold (rule 20: gold is the selected thing), the rest white.
	local function Mark(b, chosen)
		b:SetText((chosen and GOLD or running and GREY or WHITE) .. b.label .. "|r")
		b.chosen = chosen
		b:SetEnabled(not running)
	end
	for _, b in ipairs(page.goals) do Mark(b, b.mode == mode and b.goal == goal) end
	for _, b in ipairs(page.styles) do Mark(b, b.style == style) end
	local goalText, styleText, statusText = GoalText(mode, goal, style), StyleText(mode, style), StatusText()
	page.goalText:SetText(goalText)
	page.styleText:SetText(styleText)
	local fromText = FromText(from, mode, style)
	page.fromText:SetText(fromText)
	if page.fromDropdown then
		if page.fromDropdown.GenerateMenu then page.fromDropdown:GenerateMenu() end
		if page.fromDropdown.SetEnabled then page.fromDropdown:SetEnabled(not running) end
	else
		local p = from and ns.FindPreset(from)
		page.fromName:SetText(p and (ns.ShortName and ns.ShortName(p.name, 26) or p.name) or "Lowest settings")
		page.fromPrev:SetEnabled(not running)
		page.fromNext:SetEnabled(not running)
	end
	page.howText = HowText(style)
	page.how:SetText(page.howText)
	page.start:SetText(running and "Stop" or "Start")
	page.status:SetText(statusText)
	local r = AT.result
	page.resultHead:SetShown(r ~= nil)
	page.result:SetShown(r ~= nil)
	page.keep:SetShown(r ~= nil)
	page.putBack:SetShown(r ~= nil)
	local text = r and ResultText(r) or ""
	page.result:SetText(text)
	-- The page is as tall as everything on it, so it scrolls to the result's last line. Every block is
	-- chained under the one above, so a wrapped line anywhere (your PC, the goal, the way of tuning, the
	-- status, the how-to note or the result) pushes the rest down; each one is measured, not assumed.
	local H = page.headH
	local height = H.head + ROW + TextH(page.why, page.whyText)
		+ GROUP + H.pc + ROW + TextH(page.pc, pcText)
		+ GROUP + H.goal + ROW + FrameH(page.goals[1], 24)
		+ 8 + TextH(page.goalText, goalText)
		+ GROUP + H.style + ROW + FrameH(page.styles[1], 24)
		+ 8 + TextH(page.styleText, styleText)
		+ GROUP + H.from + ROW + FrameH(page.fromPick, 24)
		+ 8 + TextH(page.fromText, fromText)
		+ 8 + FrameH(page.start, 24)
		+ 8 + TextH(page.status, statusText)
		+ 8 + TextH(page.how, page.howText)
	if r then
		height = height + GROUP + H.result + ROW + FrameH(page.keep, 24) + 8 + TextH(page.result, text)
	end
	page.content:SetHeight(height + 16) -- room under the last line
end

----------------------------------------------------------------------
-- The parts of the tab, and the row of buttons that picks one
----------------------------------------------------------------------

-- { key, name, tip, build(page, holder), refresh(page) }, in the order the buttons show. build gets the
-- tab's page (to keep its frames on) and the part's own frame (under the buttons) to build in.
ns.EXPERIMENTS = ns.EXPERIMENTS or {}
local PART = {}

-- Adds a part to the tab. Files load before the tab is built, so every part has its button.
function ns.AddExperiment(part)
	if PART[part.key] then return end
	PART[part.key] = part
	ns.EXPERIMENTS[#ns.EXPERIMENTS + 1] = part
end

ns.AddExperiment({
	key = "autotune", name = "Autotune", build = BuildAutotune, refresh = RefreshAutotune,
	tip = "Finds the best look your PC can hold at the frame rate you pick.",
})

-- The part on show: the one picked last, or Autotune.
function ns.ExperimentPart()
	local key = ns.db and ns.db.experimentPart
	return PART[key] and key or "autotune"
end

-- Shows a part of the Experimental tab, and the tab if the window is open on another.
function ns.ShowExperiment(key)
	if not PART[key] then return end
	ns.db.experimentPart = key
	ns.RefreshUI()
end

local PICK_W, PICK_H = 110, 32 -- each button, and the row with the gap under it

ns.TAB_BUILD.autotune = function(page)
	page.parts, page.partButtons = {}, {}
	local prev, x = nil, 0
	for i, part in ipairs(ns.EXPERIMENTS) do
		local b = ns.Button(page, part.name, PICK_W, function() ns.ShowExperiment(part.key) end)
		if prev then b:SetPoint("LEFT", prev, "RIGHT", ROW, 0) else b:SetPoint("TOPLEFT", 0, 0) end
		ns.Tooltip(b, part.name, part.tip, x > W / 2 and "ANCHOR_LEFT" or nil)
		x = x + PICK_W + ROW
		b.key, b.label = part.key, part.name
		page.partButtons[i] = b
		prev = b
		local holder = CreateFrame("Frame", nil, page)
		holder:SetPoint("TOPLEFT", 0, -PICK_H)
		holder:SetPoint("BOTTOMRIGHT", 0, 0)
		page.parts[part.key] = holder
		part.build(page, holder)
	end
end

ns.TAB_REFRESH.autotune = function(page)
	local key = ns.ExperimentPart()
	-- The part on show is gold (rule 20: the selected thing), the rest white.
	for _, b in ipairs(page.partButtons) do
		b.chosen = b.key == key
		b:SetText((b.chosen and GOLD or WHITE) .. b.label .. "|r")
	end
	for k, holder in pairs(page.parts) do holder:SetShown(k == key) end
	PART[key].refresh(page)
end
