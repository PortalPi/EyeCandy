-- Eye Candy: Help me pick. A button on the Presets tab's Quality levels heading opens a strip under it
-- with one question: Prettier, Faster, or Let Eye Candy pick.
--   Prettier and Faster each suggest one built-in preset, a step up or down a ladder from where you
--   are, and say what it changes. Nothing changes until you press its Apply, which is the row's own
--   Apply (ns.PresetAction), so Back to before undoes it like any preset. In a fight the Apply waits
--   for the fight to end and says so; closing the strip, or leaving the tab, drops the wait.
--   Let Eye Candy pick opens the Experimental tab with Best balance and Best look picked. It starts
--   nothing: the player presses Start.
-- It never opens by itself: no popup, no line at login, nothing in chat. Only the button opens it.
-- UI.lua places the button and the strip (RefreshPresetList); everything else is here.
-- Checks in tests/test_helper.py.

local _, ns = ...

local H = {}
ns.Helper = H

local GREY, RED, GOLD = "|cff9d9d9d", "|cffff4040", "|cffffd100"

----------------------------------------------------------------------
-- Which preset each answer gives
----------------------------------------------------------------------

-- The ladder, cheapest first. Prettier is the next step up from where you are, Faster the next step down.
-- Why these: the quality levels are the plain steps between Laptop (the cheapest built-in) and Showcase
-- (the most). Cinematic is left out for Beautiful, which is Cinematic's cost with Showcase's far
-- detail, at 150% render scale with gentler sharpening: the Look made as the happy medium. The other
-- Looks are styles rather than steps, so they are never offered, only placed (H.NEAR).
H.LADDER = { "look:laptop", "tier1", "tier2", "tier3", "tier4", "look:beautiful", "tier6" }

-- Built-ins off the ladder, at the step they cost about the same as (from their base level and render
-- scale in Data.lua). A new built-in that is in neither is placed by measuring its settings.
H.NEAR = {
	tier5 = 6,                 -- Cinematic: Beautiful's level
	["look:painterly"] = 6, ["look:classic"] = 6, ["look:moody"] = 6, -- Cinematic or Showcase at 150%
	["look:crisp"] = 7, ["look:screenshot"] = 7,                        -- Showcase at the highest render scale
	["look:raid"] = 4, ["look:city"] = 4,                               -- High with a few things lowered
}

-- Render scale counts four times: it costs and shows more than any one menu setting.
H.SCALE_WEIGHT = 4
-- Settings this close to a step (in quality levels) are on it.
H.MARGIN = 0.1

-- The settings measured: every Graphics menu row in Data.lua and render scale, with each value's place
-- on the quality levels (a value two levels share sits between them). Rows that never change are left out.
local rows
local function Rows()
	if rows then return rows end
	rows = {}
	for _, cat in ipairs(ns.CATEGORIES) do
		for _, row in ipairs(cat.cvars) do
			if row.menu or row.scale then
				local sum, count, order = {}, {}, {}
				for i = 1, #ns.TIERS do
					local v = row[3][i]
					if v ~= nil then
						if not sum[v] then order[#order + 1], sum[v], count[v] = v, 0, 0 end
						sum[v], count[v] = sum[v] + i, count[v] + 1
					end
				end
				if #order >= 2 then
					table.sort(order)
					local pts = {}
					for _, v in ipairs(order) do pts[#pts + 1] = { v, sum[v] / count[v] } end
					rows[#rows + 1] = { cvar = row[1], label = row[2], pts = pts, scale = row.scale, weight = row.scale and H.SCALE_WEIGHT or 1 }
				end
			end
		end
	end
	return rows
end

-- Where a value sits on a row's quality levels: between two points it is worked out in proportion;
-- past either end it carries on at the end's slope.
local function Place(pts, v)
	local i = 1
	while i < #pts - 1 and v > pts[i + 1][1] do i = i + 1 end
	local a, b = pts[i], pts[i + 1]
	local at = a[2] + (v - a[1]) * (b[2] - a[2]) / (b[1] - a[1])
	return math.max(0, math.min(#ns.TIERS + 2, at))
end

-- Render scale as the game would keep it: a preset asking for more than the game allows gets the most.
local function Kept(row, v)
	if not row.scale then return v end
	if GetMaxRenderScale then v = math.min(v, tonumber((GetMaxRenderScale())) or v) end
	if GetMinRenderScale then v = math.max(v, tonumber((GetMinRenderScale())) or v) end
	return v
end

-- Your value now. In a city, yours, not the one the city switch lowered (Situations.lua).
local function Now(cvar)
	local v = ns.GetInfo(cvar)
	if v ~= nil and ns.SituationValue then v = ns.SituationValue(cvar, v) end
	return v
end
H.Now = Now

-- How high a set of settings sits, in quality levels (1 = Performance, 5 = Cinematic). values is a
-- table of cvar = value; nil measures your settings now. Settings it lacks are left out.
function H.Level(values)
	local total, weight = 0, 0
	for _, row in ipairs(Rows()) do
		local v
		if values then v = tonumber(values[row.cvar]) else v = tonumber(Now(row.cvar)) end
		if v then
			total = total + Place(row.pts, Kept(row, v)) * row.weight
			weight = weight + row.weight
		end
	end
	return weight > 0 and total / weight or 0
end

-- A built-in's step on the ladder, or nil.
function H.Step(id)
	for i, ladderId in ipairs(H.LADDER) do
		if ladderId == id then return i end
	end
	return H.NEAR[id]
end

-- The step you are on: a built-in you have not changed since. nil when you are on your own settings
-- (no preset, your own preset, or a built-in changed since), which are placed by measuring them.
-- Also returns the preset you are on, if any.
function H.Where()
	local p, changed = nil, 0
	if ns.OnPreset then p, changed = ns.OnPreset() end
	if p and p.builtin and (changed or 0) == 0 then
		local step = H.Step(p.id)
		if step then return step, p end
	end
	return nil, p
end

local function NoneText(up, p)
	if up then
		if p then return "You're on " .. p.name .. ", the top of Eye Candy's presets. None is prettier." end
		return "Your settings are as high as Eye Candy's presets go. None is prettier."
	end
	if p then return "You're on " .. p.name .. ", the fastest of Eye Candy's presets. None is faster." end
	return "Your settings are as low as Eye Candy's presets go. None is faster."
end

-- The preset an answer ("prettier" or "faster") gives, or nil and a line saying why there is none.
function H.Pick(answer)
	local up = answer == "prettier"
	local step, onP = H.Where()
	local target
	if step then
		target = up and step + 1 or step - 1
	else
		local now = H.Level()
		local lv = {}
		for i, id in ipairs(H.LADDER) do lv[i] = H.Level(ns.PresetValues(id) or {}) end
		-- The nearest step; on a tie (render scale held at 100% makes the top steps measure the same),
		-- the lower one.
		local best
		for i = 1, #lv do
			if not best or math.abs(lv[i] - now) < math.abs(lv[best] - now) - 1e-9 then best = i end
		end
		if best and math.abs(lv[best] - now) <= H.MARGIN then
			target = up and best + 1 or best - 1
		elseif up then
			for i = 1, #lv do
				if lv[i] > now then target = i; break end
			end
		else
			for i = #lv, 1, -1 do
				if lv[i] < now then target = i; break end
			end
		end
		onP = nil -- not on a step: the line says "your settings"
	end
	local id = target and H.LADDER[target]
	local p = id and ns.FindPreset(id)
	if not p then return nil, NoneText(up, onP) end
	return p
end

----------------------------------------------------------------------
-- What a pick changes
----------------------------------------------------------------------

-- "Shadow quality" -> "shadow quality", for the middle of a sentence. "SSAO" stays as it is.
function H.Lower(s)
	if s:sub(2, 2):match("%l") then return s:sub(1, 1):lower() .. s:sub(2) end
	return s
end

-- "a, b, c and 2 more"
function H.List(words)
	local n = #words
	if n == 0 then return "" end
	if n == 1 then return words[1] end
	if n <= 3 then return table.concat(words, ", ", 1, n - 1) .. " and " .. words[n] end
	return table.concat(words, ", ", 1, 3) .. " and " .. (n - 3) .. " more"
end

-- How many of your settings a preset would change, and which menu settings (and render scale) it
-- raises and lowers, by name in Data.lua's order. A menu setting may land lower on a graphics card
-- that can't take it, and render scale may be held by the game, so the count is "up to".
function H.Changes(id)
	local values = ns.PresetValues(id)
	local ups, downs = {}, {}
	if not values then return 0, ups, downs end
	-- A render scale override of yours stays through a quality level, and ns.PresetValues says so.
	local n = 0
	for cvar, want in pairs(values) do
		if ns.Exists(cvar) then
			local now = Now(cvar)
			if now ~= nil and not ns.Same(now, want) then n = n + 1 end
		end
	end
	for _, row in ipairs(Rows()) do
		local now, want = tonumber(Now(row.cvar)), tonumber(values[row.cvar])
		if now and want then
			want = Kept(row, want)
			if want > now + 1e-6 then ups[#ups + 1] = H.Lower(row.label)
			elseif want < now - 1e-6 then downs[#downs + 1] = H.Lower(row.label) end
		end
	end
	return n, ups, downs
end

local KIND = { Tiers = "a quality level", Looks = "a Look", Situations = "a Situation" }

local function PickText(p)
	local lines = {}
	local line = ns.PresetLine and ns.PresetLine(p) or ""
	lines[#lines + 1] = p.name .. ", " .. (KIND[p.group] or "a preset") .. ". " .. line
	local n, ups, downs = H.Changes(p.id)
	if #ups > 0 then lines[#lines + 1] = "Higher: " .. H.List(ups) .. "." end
	if #downs > 0 then lines[#lines + 1] = "Lower: " .. H.List(downs) .. "." end
	lines[#lines + 1] = string.format("Up to %d of your settings change. Back to before undoes it.", n)
	return table.concat(lines, "\n")
end

----------------------------------------------------------------------
-- Let Eye Candy pick
----------------------------------------------------------------------

-- Why Best balance: the game tells addons nothing about the screen's refresh rate, so a fixed FPS goal
-- could sit under it. Best balance raises a setting only while it is worth its cost, never under 60 FPS.
-- It replaces the goal, way of tuning and start point picked before: the player asked Eye Candy to pick,
-- and the line names all three.
-- Where to stand and how long is the tab's own text (HowText in AutotuneTab.lua); this line only says
-- what was picked. It goes once the goal is changed on the tab, so it never names an old pick.
H.AUTO_LINE = "Help me pick chose Best balance and Best look, from the lowest settings. Press Start when you're ready."

local picked -- the goal table Let Eye Candy pick set, while its line is showing

function H.LetEyeCandyPick()
	local AT = ns.Autotune
	local running = AT and AT.IsRunning and AT.IsRunning()
	if not running then
		picked = { mode = "balance", style = "look" }
		ns.db.autotuneGoal = picked
	end
	ns.ShowTab("autotune")
	if AT and AT.Say and not running then
		AT.Say("done", H.AUTO_LINE)
		ns.RefreshUI()
	end
end

-- The tab's Pick() saves a new goal table, so a goal changed since is a different table: the line goes.
local tabRefresh = ns.TAB_REFRESH and ns.TAB_REFRESH.autotune
if tabRefresh then
	ns.TAB_REFRESH.autotune = function(page, ...)
		local AT = ns.Autotune
		if AT and AT.message == H.AUTO_LINE and ns.db.autotuneGoal ~= picked then
			AT.message, AT.messageKind = nil, nil
		end
		return tabRefresh(page, ...)
	end
end

----------------------------------------------------------------------
-- The strip
----------------------------------------------------------------------

local QUESTION = "What matters more to you?"
local ASK_TEXT = "Prettier and Faster suggest one preset and show what it changes. Nothing changes until you press Apply. Let Eye Candy pick opens Autotune on the Experimental tab."

local waiting -- { page, p } while an Apply waits for a fight to end

local function Strip(page) return page and page.helperStrip end

-- Open on the question, or close (the button does both). Closing drops a waiting Apply.
function H.Set(page, state, p, text)
	local s = Strip(page)
	if s then s.state, s.p, s.text = state, p, text end
	if waiting and waiting.page == page and state ~= "waiting" then waiting = nil end
	ns.RefreshUI()
end

-- Open, for UI.lua's layout: the strip goes under the Quality levels heading.
function ns.HelperOpen(page)
	local s = Strip(page)
	return s ~= nil and s.state ~= nil
end

local function Applied(page, p)
	local on = ns.OnPreset and ns.OnPreset()
	if on and on.id == p.id then
		H.Set(page, "done", p, "Back on " .. p.name .. " under Today, at the top of the list, undoes it.")
	else
		-- The row's Apply puts a refusal's reason on the card; say it here too, where it was pressed.
		local why = page and page.cardMsg and page.cardMsg:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
		H.Set(page, "none", p, RED .. p.name .. " didn't go on." .. (why and why ~= "" and (" " .. why) or "") .. "|r")
	end
end

local function Apply(page, p)
	if InCombatLockdown() then
		H.Set(page, "waiting", p, GREY .. "Waiting for the fight to end. " .. p.name .. " goes on then. Close this to cancel.|r")
		waiting = { page = page, p = p }
		return
	end
	ns.PresetAction(p, "apply")
	Applied(page, p)
end

local function Answer(page, answer)
	local p, why = H.Pick(answer)
	local s = Strip(page)
	if s then s.word = answer == "prettier" and "Prettier" or "Faster" end
	if p then H.Set(page, "pick", p, PickText(p)) else H.Set(page, "none", nil, why) end
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:SetScript("OnEvent", function()
	local w = waiting
	waiting = nil
	if w and Strip(w.page) and Strip(w.page).state == "waiting" then
		ns.PresetAction(w.p, "apply")
		Applied(w.page, w.p)
	end
end)

local function Build(page)
	local s = CreateFrame("Frame", nil, page.content)
	s:SetSize(ns.ROW_W, 80)
	s.h = 80
	local bg = s:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(1, 1, 1, 0.04)
	s.title = ns.Label(s, "", "GameFontNormal")
	s.title:SetPoint("TOPLEFT", 14, -8)
	s.title:SetWidth(ns.ROW_W - 120)
	s.title:SetJustifyH("LEFT")
	s.title:SetWordWrap(false)
	s.body = ns.Label(s, "", "GameFontHighlightSmall")
	s.body:SetPoint("TOPLEFT", 20, -28)
	s.body:SetWidth(ns.ROW_W - 40)
	s.body:SetJustifyH("LEFT")

	s.prettier = ns.Button(s, "Prettier", 100, function() Answer(page, "prettier") end)
	ns.Tooltip(s.prettier, "Prettier", "Suggests the next preset up from where you are, and shows what it changes. Nothing changes yet.")
	s.faster = ns.Button(s, "Faster", 100, function() Answer(page, "faster") end)
	ns.Tooltip(s.faster, "Faster", "Suggests the next preset down from where you are, and shows what it changes. Nothing changes yet.")
	s.auto = ns.Button(s, "Let Eye Candy pick", 150, function() H.LetEyeCandyPick() end)
	ns.Tooltip(s.auto, "Let Eye Candy pick", "Opens Autotune on the Experimental tab with Best balance picked. It starts only when you press Start.")
	s.apply = ns.Button(s, "Apply", 160, function() if s.p then Apply(page, s.p) end end)
	ns.Tooltip(s.apply, function() return s.apply:GetText() or "Apply" end, "Applies this preset now. Back to before undoes it.")
	s.again = ns.Button(s, "Ask again", 90, function() H.Set(page, "ask") end)
	s.again:SetHeight(22)
	s.close = ns.Button(s, "Close", 80, function() H.Set(page, nil) end)
	s.close:SetHeight(22)
	-- The strip hides with its page (leaving the tab, closing the window): it closes, and a waiting
	-- Apply goes with it, so nothing changes where the player can't see it said.
	s:SetScript("OnHide", function(self)
		self.state, self.p, self.text = nil, nil, nil
		if waiting and waiting.page == page then waiting = nil end
	end)
	s:Hide()
	page.helperStrip = s
	return s
end

-- Lay the strip out for its state, size it, and return it (UI.lua anchors it).
function ns.HelperStrip(page)
	local s = Strip(page) or Build(page)
	local state = s.state
	local title, body
	if state == "ask" then
		title, body = QUESTION, GREY .. ASK_TEXT .. "|r"
	elseif state == "pick" then
		title, body = s.word .. ": " .. s.p.name, s.text
	elseif state == "waiting" then
		title, body = s.word .. ": " .. s.p.name, PickText(s.p) .. "\n" .. s.text
	elseif state == "done" then
		title, body = "Now on " .. s.p.name, s.text
	else
		title, body = s.word or "", s.text or ""
	end
	s.title:SetText(GOLD .. title .. "|r")
	s.title.text = title -- what it says, without the colour, for the checks
	s.body:SetText(body)
	local used = math.ceil(tonumber((s.body:GetStringHeight())) or 0)
	if used <= 0 then
		local _, breaks = body:gsub("\n", "")
		used = (breaks + 1) * 12
	end
	local top = 28 + used + 8
	local asking = state == "ask"
	s.prettier:SetShown(asking)
	s.faster:SetShown(asking)
	s.auto:SetShown(asking)
	s.apply:SetShown(state == "pick")
	s.again:SetShown(not asking)
	if state == "pick" then s.apply:SetText("Apply " .. s.p.name) end
	local first = asking and s.prettier or (state == "pick" and s.apply or s.again)
	first:ClearAllPoints()
	first:SetPoint("TOPLEFT", s, "TOPLEFT", 20, -top)
	if asking then
		s.faster:ClearAllPoints()
		s.faster:SetPoint("LEFT", s.prettier, "RIGHT", 8, 0)
		s.auto:ClearAllPoints()
		s.auto:SetPoint("LEFT", s.faster, "RIGHT", 8, 0)
	elseif state == "pick" then
		s.again:ClearAllPoints()
		s.again:SetPoint("LEFT", s.apply, "RIGHT", 8, 0)
	end
	s.close:ClearAllPoints()
	s.close:SetPoint("TOPRIGHT", s, "TOPRIGHT", -14, -top)
	s.h = top + 24 + 8
	s:SetSize(ns.ROW_W, s.h)
	return s
end

-- The Help me pick button, on the Quality levels heading (UI.lua calls this when it lays the heading out).
function ns.HelperButton(page, header)
	local b = page.helperButton
	if not b then
		b = ns.Button(header, "Help me pick", 120, function()
			if ns.HelperOpen(page) then H.Set(page, nil) else
				if not Strip(page) then Build(page) end
				H.Set(page, "ask")
			end
		end)
		ns.Tooltip(b, "Help me pick", "Asks what matters more to you, then suggests one preset. Nothing changes until you press Apply.", "ANCHOR_LEFT")
		page.helperButton = b
	end
	b.header = header
	b:ClearAllPoints()
	b:SetPoint("TOPRIGHT", header, "TOPRIGHT", -4, -6)
	b:Show()
	return b
end
