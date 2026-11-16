-- Eye Candy: today's steps on the Presets tab. Backups.lua keeps them (ns.BackSteps), Presets.lua
-- goes back (ns.GoBack). A "Today" group at the top of the list, newest first: one row a step, with
-- what it was, when, and its own Back. Back asks first and says how many settings it changes. The
-- newest three show; Show all shows every one. UI.lua's RefreshPresetList places the rows.

local ADDON, ns = ...

local STEPS_SHOWN = 3
-- The same sizes as a preset row (UI.lua), so the groups line up.
local ROW_H, ROW_GAP, NAME_X, NAME_W, NAME_CHARS = 34, 4, 14, 180, 26
local NOTE = "Newest first. Back goes back to just before that step. Newer steps are undone too."

-- What the list shows now, so a timed check can tell when to redraw. "" with no steps.
function ns.StepsKey(steps)
	steps = steps or (ns.BackSteps and ns.BackSteps()) or {}
	local top = steps[1]
	if not top then return "" end
	return #steps .. ":" .. tostring(ns.StepsVersion and ns.StepsVersion() or top.stamp) .. (top.live and ":live" or "")
end

local function Plural(n, word)
	return n .. " " .. word .. (n == 1 and "" or "s")
end

-- Back on a step: asks first, with how many settings change and how many newer steps go too.
-- Compare ends first, so the count is against your own settings.
function ns.AskBack(page, step)
	if ns.IsComparing and ns.IsComparing() and ns.StopCompare then ns.StopCompare() end
	local newer = 0
	for i, s in ipairs(ns.BackSteps()) do
		if s == step or (s.live and step.live) then newer = i - 1 end
	end
	local n = ns.CountStepChanges(step)
	local text = n == 0 and string.format("Put back your settings from just before %s? No setting changes: they are already as they were then.", ns.BackTarget(step))
		or string.format("Put back your settings from just before %s? This changes %s.", ns.BackTarget(step), Plural(n, "setting"))
	local steps = newer == 1 and "step" or "steps"
	if newer > 0 and n == 0 then
		text = text .. string.format(" The %d newer %s above it %s the list.", newer, steps, newer == 1 and "leaves" or "leave")
	elseif newer > 0 then
		text = text .. string.format(" It also undoes the %d newer %s above it.", newer, steps)
	end
	ns.Ask({ title = "Back to before", text = text, accept = "Back", onAccept = function()
		local done, line = ns.GoBack(step)
		page.cardMsg = line and ((done and "|cff7cff7c" or "|cffff4040") .. line .. "|r") or nil
		page.cardMsgKey = nil
		ns.RefreshUI()
	end })
end

local function FitName(fs, name)
	local n = NAME_CHARS
	fs:SetText(ns.ShortName(name, n))
	local get = fs.GetUnboundedStringWidth or fs.GetStringWidth
	while (tonumber((get(fs))) or 0) > NAME_W and n > 6 do
		n = n - 1
		fs:SetText(ns.ShortName(name, n))
	end
end

local function StepRow(content)
	local row = CreateFrame("Frame", nil, content)
	row:SetSize(ns.ROW_W, ROW_H)
	row.bg = row:CreateTexture(nil, "BACKGROUND")
	row.bg:SetAllPoints()
	row.bg:SetColorTexture(1, 1, 1, 0.05)
	row.name = ns.Label(row, "", "GameFontHighlight")
	row.name:SetPoint("LEFT", NAME_X, 0)
	row.name:SetWidth(NAME_W)
	if row.name.SetWordWrap then row.name:SetWordWrap(false) end
	row.back = ns.Button(row, "Back", 70, function() ns.AskBack(row.page, row.step) end)
	row.back:SetPoint("RIGHT", -4, 0)
	ns.Tooltip(row.back, function() return "Back to before " .. ns.BackTarget(row.step or {}) end,
		"Puts your settings back as they were just before this step. Asks first, and says how many settings change.", "ANCHOR_LEFT")
	row.line = ns.Label(row, "", "GameFontHighlightSmall")
	row.line:SetPoint("LEFT", NAME_X + NAME_W + 10, 0)
	row.line:SetPoint("RIGHT", row.back, "LEFT", -10, 0)
	row.line:SetTextColor(0.62, 0.62, 0.62)
	if row.line.SetWordWrap then row.line:SetWordWrap(false) end
	return row
end

-- The list entries for the Today group (none with no steps today).
function ns.StepEntries(page)
	local steps = ns.BackSteps and ns.BackSteps() or {}
	page.stepsKey = ns.StepsKey(steps)
	page.stepsUsed = 0
	if #steps == 0 then return {} end
	local out = { { header = "What you did today", note = NOTE, opts = { steps = #steps } } }
	local shown = page.showAllSteps and #steps or math.min(#steps, STEPS_SHOWN)
	for i = 1, shown do out[#out + 1] = { step = steps[i] } end
	return out
end

-- Show all, on the Today heading, only when there are more than the rows shown.
function ns.PlaceStepsMore(page, header, total)
	if not page.stepsMore then
		page.stepsMore = ns.Button(header, "Show all", 110, function()
			page.showAllSteps = not page.showAllSteps
			ns.RefreshUI()
		end)
	end
	local b = page.stepsMore
	b:SetParent(header)
	b:ClearAllPoints()
	b:SetPoint("TOPRIGHT", -4, -6)
	b:SetText(page.showAllSteps and "Show fewer" or ("Show all " .. total))
	b:SetShown(total > STEPS_SHOWN)
end

-- One step's row at y. Returns the y under it.
function ns.PlaceStepRow(page, e, y)
	page.stepRows = page.stepRows or {}
	page.stepsUsed = (page.stepsUsed or 0) + 1
	local row = page.stepRows[page.stepsUsed]
	if not row then
		row = StepRow(page.content)
		page.stepRows[page.stepsUsed] = row
	end
	row.page, row.step = page, e.step
	FitName(row.name, ns.StepName(e.step))
	row.line:SetText(ns.StepLine(e.step))
	row:ClearAllPoints()
	row:SetPoint("TOPLEFT", 0, -y)
	row:Show()
	return y + ROW_H + ROW_GAP
end

-- Hides the rows not used this time, and Show all with no Today group.
function ns.EndStepRows(page)
	for i = (page.stepsUsed or 0) + 1, #(page.stepRows or {}) do page.stepRows[i]:Hide() end
	if page.stepsMore and (page.stepsUsed or 0) == 0 then page.stepsMore:Hide() end
end
