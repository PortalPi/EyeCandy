-- Eye Candy: the main window (four tabs and a bottom bar), shared widgets, popups and the export box.
-- Tabs: Presets (opens first), Standard (Standard.lua), Hidden (Advanced.lua), Backups.
-- The Presets and Backups tabs use the presets and backups API (Presets.lua, Backups.lua) when it is
-- loaded, and fall back to plain tier and Look buttons and a single backup when it is not.

local _, ns = ...

local WIDTH, HEIGHT = 780, 640
ns.PAGE_W = WIDTH - 24  -- a tab page
ns.ROW_W = WIDTH - 56   -- a row inside a scrolling page
local main, exportFrame, askFrame

local TABS = {
	-- width: sized to the label. The tab row, the search count and the search box share one line
	-- (rule 19), so the tabs may not grow without the count's room shrinking.
	{ key = "presets", label = "Presets", width = 80 },
	{ key = "standard", label = "Standard", width = 80 },
	{ key = "hidden", label = "Hidden", width = 70 },
	{ key = "backups", label = "Backups", width = 80 },
	{ key = "autotune", label = "Experimental", width = 100 }, -- AutotuneTab.lua
}
ns.TAB_BUILD, ns.TAB_REFRESH, ns.TAB_LIST = {}, {}, {}

----------------------------------------------------------------------
-- Shared widgets
----------------------------------------------------------------------

----------------------------------------------------------------------
-- Windows: drag to move, drag the corner grip to scale. Both are remembered per account
-- in EyeCandyDB.windows[name] = { x, y, scale }, x and y being the top-left corner in UIParent
-- units (so the spot is the same whatever the scale). Scaling never changes the layout.
----------------------------------------------------------------------

ns.WINDOW_SCALE_MIN, ns.WINDOW_SCALE_MAX = 0.6, 1.3

local function ClampScale(s)
	s = tonumber(s) or 1
	if s < ns.WINDOW_SCALE_MIN then s = ns.WINDOW_SCALE_MIN end
	if s > ns.WINDOW_SCALE_MAX then s = ns.WINDOW_SCALE_MAX end
	return math.floor(s * 100 + 0.5) / 100
end
ns.ClampWindowScale = ClampScale

-- The scale that puts the window's bottom-right corner under the cursor, with the top-left
-- corner (left, top) fixed. Everything in UIParent units; w and h are the unscaled size.
function ns.ScaleForCorner(left, top, w, h, cx, cy)
	if not (left and top and w and h and cx and cy) or w <= 0 or h <= 0 then return nil end
	return ClampScale(math.max((cx - left) / w, (top - cy) / h))
end

local function WindowState(name, create)
	local db = ns.db
	if not (db and name) then return nil end
	if create then
		db.windows = db.windows or {}
		db.windows[name] = db.windows[name] or {}
	end
	return db.windows and db.windows[name]
end

-- The top-left corner in UIParent units, or nil if the game hasn't placed the frame yet.
local function TopLeft(f)
	local l, t, s = f:GetLeft(), f:GetTop(), f:GetScale()
	if not (tonumber(l) and tonumber(t)) then return nil end
	s = tonumber(s) or 1
	return l * s, t * s
end

local function PlaceAt(f, x, y, s)
	f:SetScale(s)
	f:ClearAllPoints()
	f:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", x / s, y / s)
end

function ns.SaveWindow(f)
	local st = WindowState(f.windowName, true)
	if not st then return end
	local x, y = TopLeft(f)
	if x then st.x, st.y = x, y end
	st.scale = ClampScale(f:GetScale() or st.scale or 1)
end

-- Puts a window where it was last left, at its last scale. A window never moved sits centred.
function ns.PlaceWindow(f)
	local st = WindowState(f.windowName)
	local s = ClampScale(st and st.scale or 1)
	if st and tonumber(st.x) and tonumber(st.y) then
		PlaceAt(f, st.x, st.y, s)
	else
		f:SetScale(s)
		f:ClearAllPoints()
		f:SetPoint("CENTER")
	end
end

-- Sets a window's scale, keeping its top-left corner where it is, and remembers it.
function ns.SetWindowScale(f, s)
	s = ClampScale(s)
	local x, y = TopLeft(f)
	if x then PlaceAt(f, x, y, s) else f:SetScale(s) end
	ns.SaveWindow(f)
end

local function CursorInParent()
	local cx, cy = GetCursorPosition()
	local es = tonumber(UIParent:GetEffectiveScale() or 1) or 1
	if not (tonumber(cx) and tonumber(cy)) or es <= 0 then return nil end
	return cx / es, cy / es
end

local function AddScaleGrip(f, width, height)
	local grip = CreateFrame("Button", nil, f)
	grip:SetSize(14, 14)
	grip:SetPoint("BOTTOMRIGHT", -2, 2)
	grip:SetFrameLevel((tonumber(f:GetFrameLevel() or 0) or 0) + 20)
	grip:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
	grip:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
	grip:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
	grip:RegisterForClicks("RightButtonUp")

	-- Dragging: the top-left corner and how far the press was from the bottom-right corner are
	-- read once, then each frame sets the scale that keeps that gap, so a click alone changes nothing.
	function grip.Drag()
		local cx, cy = CursorInParent()
		local s = cx and ns.ScaleForCorner(grip.left, grip.top, width, height, cx + grip.dx, cy - grip.dy)
		if s and s ~= grip.lastScale then
			grip.lastScale = s
			PlaceAt(f, grip.left, grip.top, s)
		end
	end
	local function EndDrag(self)
		self:SetScript("OnUpdate", nil)
		self:SetButtonState("NORMAL")
		self.left, self.top = nil, nil
		ns.SaveWindow(f)
	end
	grip:SetScript("OnMouseDown", function(self, button)
		if button ~= "LeftButton" then return end
		local x, y = TopLeft(f)
		local cx, cy = CursorInParent()
		if not (x and cx) then return end
		local s = tonumber(f:GetScale() or 1) or 1
		self.left, self.top, self.lastScale = x, y, s
		self.dx, self.dy = x + width * s - cx, cy - (y - height * s)
		self:SetButtonState("PUSHED", true)
		self:SetScript("OnUpdate", self.Drag)
	end)
	grip:SetScript("OnMouseUp", function(self, button)
		if button == "LeftButton" and self.left then EndDrag(self) end
	end)
	grip:SetScript("OnHide", function(self)
		if self.left then EndDrag(self) end
	end)
	grip:SetScript("OnClick", function() ns.SetWindowScale(f, 1) end) -- right-click
	grip:SetScript("OnEnter", function(self)
		GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
		GameTooltip:AddLine("Size", 1, 1, 1)
		GameTooltip:AddLine("Drag to make the window bigger or smaller. Right-click: back to 100%.", nil, nil, nil, true)
		GameTooltip:Show()
	end)
	grip:SetScript("OnLeave", GameTooltip_Hide)
	f.scaleGrip = grip
	return grip
end

local function MakeWindow(name, width, height, title)
	local ok, f = pcall(CreateFrame, "Frame", name, UIParent, "BasicFrameTemplateWithInset")
	if not ok or not f then
		f = CreateFrame("Frame", name, UIParent, "BackdropTemplate")
		f:SetBackdrop({
			bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
			edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
			tile = true, tileSize = 32, edgeSize = 32,
			insets = { left = 8, right = 8, top = 8, bottom = 8 },
		})
		local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
		close:SetPoint("TOPRIGHT", -4, -4)
	end
	f.windowName = name
	f:SetSize(width, height)
	f:SetFrameStrata("DIALOG")
	f:SetMovable(true)
	f:SetUserPlaced(false) -- drop any spot the game's layout cache kept from older builds
	f:EnableMouse(true)
	f:RegisterForDrag("LeftButton")
	f:SetScript("OnDragStart", f.StartMoving)
	f:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		self:SetUserPlaced(false) -- our own saved spot wins, not the game's layout cache
		ns.SaveWindow(self)
	end)
	f:SetClampedToScreen(true)
	ns.PlaceWindow(f)
	AddScaleGrip(f, width, height)
	f:Hide()

	local t = f:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
	t:SetPoint("TOP", 0, -6)
	t:SetText(title)
	f.titleText = t

	tinsert(UISpecialFrames, name) -- Esc closes it
	return f
end

local function Button(parent, text, width, onClick)
	local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
	b:SetSize(width, 24)
	b:SetText(text)
	b:SetScript("OnClick", onClick)
	return b
end

-- title and body may be functions, called each time the tooltip opens. anchor: ANCHOR_RIGHT unless
-- given (a button at the window's right edge passes ANCHOR_LEFT so the tooltip stays on the window).
local function Tooltip(frame, title, body, anchor)
	frame:SetScript("OnEnter", function(self)
		GameTooltip:SetOwner(self, anchor or "ANCHOR_RIGHT")
		GameTooltip:AddLine(type(title) == "function" and title() or title, 1, 1, 1)
		local text = type(body) == "function" and body() or body
		if text and text ~= "" then
			GameTooltip:AddLine(text, nil, nil, nil, true)
		end
		GameTooltip:Show()
	end)
	frame:SetScript("OnLeave", GameTooltip_Hide)
end

local function Label(parent, text, font)
	local fs = parent:CreateFontString(nil, "OVERLAY", font or "GameFontHighlightSmall")
	fs:SetJustifyH("LEFT")
	fs:SetText(text or "")
	return fs
end

-- A small gold dot: this setting is changed from the game default.
function ns.Dot(parent)
	local t = parent:CreateTexture(nil, "OVERLAY")
	t:SetSize(6, 6)
	t:SetColorTexture(1, 0.82, 0, 1)
	t:SetPoint("LEFT", 1, 0)
	t:Hide()
	return t
end

-- Is this CVar changed from the game default? (nil if the client doesn't have it)
function ns.IsChanged(cvar)
	local value, default = ns.GetInfo(cvar)
	if value == nil or default == nil then return nil end
	return not ns.Same(value, default)
end

-- A slider for a numeric setting. spec: { min, max, step, width, get() -> number, set(v) commits,
-- onPreview(v) while dragging }. Applies once the slider settles (0.25 s), not on every pixel of a drag.
-- Returns the slider; slider:Refresh() moves it to get()'s value without committing.
function ns.Snap(v, min, max, step)
	v = math.min(math.max(v, min), max)
	v = min + math.floor((v - min) / step + 0.5) * step
	local decimals = 0
	local s = step
	while s < 1 and decimals < 4 do s = s * 10; decimals = decimals + 1 end
	return tonumber(string.format("%." .. decimals .. "f", math.min(v, max)))
end

-- Every setting's tooltip, in one order (PLAN, tooltip rule):
-- Blizzard's wording first, quoted (or "Not documented by Blizzard."), then one plain line, then the game default.
-- t = { quote, plain, default (text), more = { lines, shown grey below }, cvar }
function ns.SettingTip(t)
	local lines = {}
	local quote = t.quote and tostring(t.quote):gsub("^%s+", ""):gsub("%s+$", "")
	if quote and quote ~= "" then
		lines[#lines + 1] = "Blizzard: \"" .. quote .. "\""
	else
		lines[#lines + 1] = "|cff9d9d9dNot documented by Blizzard.|r"
	end
	if t.plain and t.plain ~= "" then lines[#lines + 1] = t.plain end
	if t.default ~= nil then lines[#lines + 1] = "Game default: " .. tostring(t.default) end
	if t.more and #t.more > 0 then
		lines[#lines + 1] = " "
		for _, line in ipairs(t.more) do lines[#lines + 1] = line end
	end
	if t.cvar then lines[#lines + 1] = "|cff9d9d9d" .. t.cvar .. "|r" end
	return table.concat(lines, "\n")
end

-- A small round arrow that puts something back. tip: tooltip text (string or function).
function ns.ResetArrow(parent, onClick, tip)
	local b = CreateFrame("Button", nil, parent)
	b:SetSize(16, 16)
	b:SetNormalTexture("Interface\\Buttons\\UI-RefreshButton")
	b:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
	b:SetScript("OnClick", function(self) onClick(self) end)
	if tip then Tooltip(b, "Reset", tip) end
	return b
end

-- How far apart the fine steps are (Shift held): a fifth of a step, whole numbers stay whole.
function ns.FineStep(step)
	if step >= 1 then return math.max(1, math.floor(step / 5)) end
	return step / 5
end

-- spec also takes:
--   default    the game default (number or function): a tick on the bar and the reset arrow's target
--   off        a value for an "Off" position left of the bar's low end (ResampleSharpness: -1)
--   invert     the bar runs high to low (min + max - value), as the game's Resample Sharpness bar;
--              with off, Off then sits next to the high end
--   percent    the box shows and takes percent (1.5 -> 150, 1.338 -> 133.8)
--   format(v)  box text for v; parse(text) -> v. Defaults handle percent and decimals.
--   onReset()  what the reset arrow does (default: set(default)); reset = false for no arrow; resetTip
-- get, set, default, format and parse all speak real values; the bar, the arrows and s.current speak
-- bar values (the same as real ones unless invert).
-- The wheel steps only once the bar has been clicked (until the mouse leaves it), so scrolling a list
-- past a slider never changes it.
-- Built round the bar, which the caller anchors: "<" 20 px to its left, then ">", the box and the arrow
-- (92 px) to its right. s.box, s.minus, s.plus, s.reset, s.tick.
ns.SLIDER_THUMB = 32 -- the thumb texture's width; the thumb's centre stops half of it in from each end
function ns.Slider(parent, spec)
	local min, max, step = spec.min, spec.max, spec.step
	local off = spec.off
	local fine = spec.fine or ns.FineStep(step)
	local width = spec.width or 170
	local barMin = off ~= nil and (min - step) or min
	local s = CreateFrame("Slider", nil, parent, "BackdropTemplate")
	s:SetOrientation("HORIZONTAL")
	s:SetSize(width, 16)
	if BACKDROP_SLIDER_8_8 then s:SetBackdrop(BACKDROP_SLIDER_8_8) end
	s:SetThumbTexture("Interface\\Buttons\\UI-SliderBar-Button-Horizontal")
	local thumb = s.GetThumbTexture and s:GetThumbTexture()
	if thumb and thumb.SetSize then thumb:SetSize(ns.SLIDER_THUMB, ns.SLIDER_THUMB) end
	s:SetMinMaxValues(barMin, max)
	s:SetValueStep(fine)
	s:SetObeyStepOnDrag(true)
	s.spec = spec

	-- Real value <-> bar value. Off stays Off.
	local function In(v)
		if v == nil or (off ~= nil and v == off) or not spec.invert then return v end
		return min + max - v
	end
	local Out = In -- the mirror is its own inverse
	local function Get() return In(spec.get()) end
	local function Set(b) spec.set(Out(b)) end

	-- Bar position <-> bar value. The Off position sits one step left of min.
	local function ToValue(pos, useFine)
		if off ~= nil and pos < min - step / 2 then return off end
		return ns.Snap(pos, min, max, useFine and fine or step)
	end
	local function ToBar(v)
		if off ~= nil and v == off then return barMin end
		return math.min(math.max(v, min), max)
	end
	s.ToValue, s.ToBar = ToValue, ToBar
	s.In = In -- a real value to its bar value (Format takes a bar value)

	-- Box text for a bar value (out of range values show as they are).
	local function Format(b)
		if b == nil then return "" end
		if off ~= nil and b == off then return "Off" end
		local v = Out(b)
		if spec.format then return spec.format(v) end
		if spec.percent then
			local p = v * 100
			if math.abs(p - math.floor(p + 0.5)) < 0.05 then return string.format("%d", math.floor(p + 0.5)) end
			return string.format("%.1f", p)
		end
		local decimals, st = 0, fine
		while st < 1 and decimals < 4 do st = st * 10; decimals = decimals + 1 end
		return (string.format("%." .. decimals .. "f", v):gsub("(%.%d-)0+$", "%1"):gsub("%.$", ""))
	end
	-- Typed text -> a bar value held to the range, or Off, or nil.
	local function Parse(text)
		local v
		text = tostring(text or "")
		if spec.parse then
			v = spec.parse(text)
		elseif off ~= nil and text:lower():find("off") then
			v = off
		else
			v = tonumber(text:match("%-?[%d%.]+"))
			if v and spec.percent then v = v / 100 end
		end
		if v == nil then return nil end
		if off ~= nil and v == off then return off end
		return In(math.min(math.max(v, min), max))
	end
	s.Format, s.Parse = Format, Parse

	local function Show(b)
		s.box:SetText(Format(b))
		s.shownText = s.box:GetText()
	end

	-- Commit once the value settles (0.25 s), not on every pixel of a drag.
	local function Change(b, now)
		s.current = b
		Show(b)
		if spec.onPreview then spec.onPreview(Out(b)) end
		s.token = (s.token or 0) + 1
		local token = s.token
		if now then Set(b) return end
		C_Timer.After(0.25, function()
			if token == s.token then Set(b) end
		end)
	end
	s.Change = Change
	local function Move(b)
		s.updating = true
		s:SetValue(ToBar(b))
		s.updating = false
	end

	-- The wheel steps only after a click on the bar; scrolling past leaves it alone.
	local function Arm(on)
		s.armed = on
		s:EnableMouseWheel(on)
	end
	s.Arm = Arm

	s:SetScript("OnValueChanged", function(self, pos)
		if self.updating then return end
		Arm(true)
		local b = ToValue(pos, IsShiftKeyDown())
		if b == self.current then return end
		Change(b)
	end)
	-- Hooked, so a tooltip set on the bar later keeps working.
	s:HookScript("OnMouseDown", function() Arm(true) end)
	s:HookScript("OnLeave", function() Arm(false) end)

	-- One step (a fine step with Shift) up or down, from the wheel or the arrows. Nothing at an end.
	local function Nudge(dir)
		local by = IsShiftKeyDown() and fine or step
		local cur = s.current
		local b
		if off ~= nil and cur == off then
			b = dir > 0 and min or off
		elseif off ~= nil and dir < 0 and cur ~= nil and cur - by < min - by / 2 then
			b = off
		else
			b = ns.Snap((cur or min) + dir * by, min, max, by)
		end
		if b == cur then return end
		Move(b)
		Change(b)
	end
	s.Nudge = Nudge
	Arm(false)
	s:SetScript("OnMouseWheel", function(_, delta)
		if not s.armed then return end
		Nudge(delta > 0 and 1 or -1)
	end)

	s.minus = Button(parent, "<", 18, function() Nudge(-1) end)
	s.minus:SetPoint("RIGHT", s, "LEFT", -2, 0)
	s.plus = Button(parent, ">", 18, function() Nudge(1) end)
	s.plus:SetPoint("LEFT", s, "RIGHT", 2, 0)

	-- The typed box: Enter (or clicking away) applies what was typed, Escape puts the current value back.
	local box = CreateFrame("EditBox", nil, parent, "InputBoxTemplate")
	box:SetSize(44, 18)
	box:SetFontObject("GameFontHighlightSmall") -- room for five characters (19600, 0.375)
	box:SetTextInsets(0, 0, 0, 0)
	box:SetAutoFocus(false)
	box:SetJustifyH("CENTER")
	box:SetPoint("LEFT", s.plus, "RIGHT", 6, 0)
	local function ApplyTyped(text)
		local b = Parse(text)
		if b == nil then Show(s.current) return end
		if not (off ~= nil and b == off) then b = ns.Snap(b, min, max, fine) end
		Move(b)
		Change(b, true)
	end
	box:SetScript("OnEnterPressed", function(self)
		local text = self:GetText()
		self.applied = true
		self:ClearFocus()
		self.applied = false
		ApplyTyped(text)
	end)
	box:SetScript("OnEscapePressed", function(self)
		self.applied = true
		self:ClearFocus()
		self.applied = false
		Show(s.current)
	end)
	box:SetScript("OnEditFocusLost", function(self)
		if self.applied then return end
		local text = self:GetText()
		if text ~= s.shownText then ApplyTyped(text) end
	end)
	s.box = box

	-- The game default: a tick on the bar, and where the reset arrow goes.
	local function Default()
		local d = spec.default
		if type(d) == "function" then d = d() end
		return In(tonumber(d))
	end
	s.Default = Default
	local tick = s:CreateTexture(nil, "OVERLAY")
	tick:SetColorTexture(1, 0.82, 0, 0.9)
	tick:SetSize(2, 8)
	s.tick = tick
	-- Under the thumb's centre when the slider sits at the default.
	function s:PlaceTick()
		local d = Default()
		if d == nil or max <= barMin then tick:Hide(); self.tickX = nil return end
		local half = ns.SLIDER_THUMB / 2
		local x = half + (ToBar(d) - barMin) / (max - barMin) * (width - 2 * half)
		tick:ClearAllPoints()
		tick:SetPoint("CENTER", self, "LEFT", x, -7)
		tick:Show()
		self.tickX = x
	end

	-- Moves to get()'s value without committing. Shows the real value even when it is past the bar's ends.
	function s:Refresh()
		self:PlaceTick()
		local b = Get()
		if b == nil then return end
		self.current = b
		Move(b)
		if not (self.box.HasFocus and self.box:HasFocus()) then Show(b) end
	end
	s:PlaceTick()

	if spec.reset ~= false then
		s.reset = ns.ResetArrow(parent, function()
			if spec.onReset then spec.onReset() return end
			local d = Default()
			if d == nil then return end
			Move(d)
			Change(d, true)
		end, spec.resetTip or function()
			local d = Default()
			return d ~= nil and ("Back to the game default (" .. Format(d) .. ").") or "Back to the game default."
		end)
		s.reset:SetPoint("LEFT", box, "RIGHT", 4, 0)
	end
	return s
end

-- A scrolling area filling a tab page below `top`. Returns the content frame.
function ns.ScrollPage(page, top)
	local scroll = CreateFrame("ScrollFrame", nil, page, "UIPanelScrollFrameTemplate")
	scroll:SetPoint("TOPLEFT", 0, top or 0)
	scroll:SetPoint("BOTTOMRIGHT", -26, 0)
	local content = CreateFrame("Frame", nil, scroll)
	content:SetSize(ns.ROW_W, 1)
	scroll:SetScrollChild(content)
	return content
end

-- A section header row: large gold name with a thin gold rule under it, optional grey note below.
-- The space above it is part of the row, so sections stand apart from the rows before them.
-- The row is as tall as the note's wrapped text, so a two-line note never runs into the first row.
function ns.Header(content, text, note)
	local f = CreateFrame("Frame", nil, content)
	local h = 36
	f.label = Label(f, text, "GameFontNormalLarge")
	f.label:SetPoint("TOPLEFT", 4, -12)
	f.rule = f:CreateTexture(nil, "ARTWORK")
	f.rule:SetColorTexture(1, 0.82, 0, 0.35)
	f.rule:SetHeight(1)
	f.rule:SetPoint("TOPLEFT", 0, -32)
	f.rule:SetPoint("TOPRIGHT", 0, -32)
	if note then
		f.note = Label(f, note, "GameFontHighlightSmall")
		f.note:SetTextColor(0.62, 0.62, 0.62)
		f.note:SetPoint("TOPLEFT", 6, -36)
		f.note:SetWidth(ns.ROW_W - 12)
		-- Room for every line the note wraps to; one line (12) when the game cannot measure it.
		local lines = math.ceil(tonumber((f.note:GetStringHeight())) or 0)
		h = 36 + math.max(12, lines) + 4
	end
	f:SetSize(ns.ROW_W, h)
	return f, h
end

-- A list of rows that can be filtered by the search box.
-- Add(frame, height, searchText, parentItem) returns the item; a header is an item other items name as parent.
-- Layout(filter) stacks the matching rows (and their headers) and returns how many non-header rows show.
function ns.NewList(content)
	local list = { items = {}, content = content }
	function list:Add(frame, height, search, parent)
		local item = { frame = frame, h = height, search = (search or ""):lower(), parent = parent }
		if parent then parent.isHeader = true end
		self.items[#self.items + 1] = item
		return item
	end
	function list:Layout(filter)
		filter = (filter or ""):lower()
		for _, it in ipairs(self.items) do
			it.match = filter == "" or it.search:find(filter, 1, true) ~= nil
			it.show = false
		end
		for _, it in ipairs(self.items) do
			local p = it.parent
			if it.match then
				it.show = true
				while p do p.show = true; p = p.parent end
			else
				while p do
					if p.match then it.show = true end
					p = p.parent
				end
			end
		end
		local y, count = 0, 0
		for _, it in ipairs(self.items) do
			if it.show then
				it.frame:ClearAllPoints()
				it.frame:SetPoint("TOPLEFT", 0, -y)
				it.frame:Show()
				y = y + it.h
				if not it.isHeader then count = count + 1 end
			else
				it.frame:Hide()
			end
		end
		self.content:SetHeight(math.max(y, 1))
		return count
	end
	return list
end

----------------------------------------------------------------------
-- Popups: a question with an optional name box, and the import box
----------------------------------------------------------------------

-- The presets and backups calls return nil, "reason" when they refuse. Say the reason in the window
-- (rule 6 of docs/ui-rules.md), in red: on the Presets card's line for anything done on a preset, on the
-- Backups tab's result line, or on the line above the bottom bar. Chat only when the window is closed.
local function WindowOpen() return main and main:IsShown() end

local function Said(ok, err, ...)
	if ok or not err then return ok, err, ... end
	local page = main and main.pages and main.pages.presets
	if WindowOpen() and page then
		page.cardMsg, page.cardMsgKey = "|cffff4040" .. tostring(err) .. "|r", nil
		ns.RefreshUI()
	else
		ns.Print(err)
	end
	return ok, err, ...
end

-- Create backup (the bar's button on every tab but Backups, and Backups' own).
local function SaidBackup(ok, err, ...)
	if ok or not err then return ok, err, ... end
	local page = main and main.pages and main.pages.backups
	if WindowOpen() and main.tab == "backups" and page then
		page.resultMsg = "|cffff4040" .. tostring(err) .. "|r"
	elseif not (ns.BarSay and ns.BarSay(err)) then
		ns.Print(err)
	end
	return ok, err, ...
end

local function AskAccept()
	local opts = askFrame.opts
	askFrame:Hide()
	if opts and opts.onAccept then
		local text
		if opts.edit then
			text = (askFrame.edit:GetText() or ""):gsub("^%s+", ""):gsub("%s+$", "")
		end
		opts.onAccept(text)
	end
end

local function BuildAsk()
	askFrame = MakeWindow("EyeCandyAskFrame", 420, 160, "Eye Candy")
	askFrame:SetFrameStrata("FULLSCREEN_DIALOG")
	askFrame.textFS = Label(askFrame, "", "GameFontHighlight")
	askFrame.textFS:SetPoint("TOPLEFT", 18, -32)
	askFrame.textFS:SetWidth(384)

	local edit = CreateFrame("EditBox", nil, askFrame, "InputBoxTemplate")
	edit:SetSize(330, 22)
	edit:SetPoint("TOPLEFT", 26, -78)
	edit:SetAutoFocus(false)
	edit:SetMaxLetters(60)
	edit:SetScript("OnEnterPressed", AskAccept)
	edit:SetScript("OnEscapePressed", function() askFrame:Hide() end)
	askFrame.edit = edit

	askFrame.cancel = Button(askFrame, "Cancel", 100, function() askFrame:Hide() end)
	askFrame.cancel:SetPoint("BOTTOMRIGHT", -16, 14)
	askFrame.accept = Button(askFrame, "OK", 100, AskAccept)
	askFrame.accept:SetPoint("RIGHT", askFrame.cancel, "LEFT", -6, 0)
end

-- opts: { title, text, edit = starting text (shows the name box), accept = button label, onAccept = function(text) }
function ns.Ask(opts)
	if not askFrame then BuildAsk() end
	askFrame.opts = opts
	askFrame.titleText:SetText(opts.title or "Eye Candy")
	askFrame.textFS:SetText(opts.text or "")
	askFrame.accept:SetText(opts.accept or "OK")
	if opts.edit then
		askFrame.edit:Show()
		askFrame.edit:SetText(opts.edit)
		askFrame.edit:SetFocus()
		askFrame.edit:HighlightText()
	else
		askFrame.edit:Hide()
	end
	askFrame:Show()
	askFrame:Raise()
end

local function CountOf(x)
	if type(x) == "number" then return x end
	if type(x) ~= "table" then return 0 end
	local n = 0
	for _ in pairs(x) do n = n + 1 end
	return n
end

-- What an import would do, as lines for the Import strip. Returns the text, and whether the code
-- can be imported, and whether its name clashes with one of yours.
function ns.ImportPreviewText(text)
	text = tostring(text or "")
	if not text:match("%S") then return "", false, false end
	local p = ns.PreviewImport and ns.PreviewImport(text) or nil
	if not (p and p.ok) then
		return "|cffff4040Can't read this code.|r " .. tostring(p and p.err or "Check you copied all of it."), false, false
	end
	local lines = {}
	lines[#lines + 1] = "|cffffd100" .. tostring(p.name or "Unnamed") .. "|r"
		.. (p.author and (" by " .. tostring(p.author)) or "")
		.. (p.date and (", made " .. tostring(p.date)) or "")
		.. (p.gameVersion and (", game " .. tostring(p.gameVersion)) or "")
		.. string.format(". Changes %d settings.", CountOf(p.changes))
	local skipped = p.skipped or {}
	if #skipped > 0 then
		local shown = {}
		for i = 1, math.min(#skipped, 8) do shown[i] = tostring(skipped[i]) end
		lines[#lines + 1] = string.format("|cffff4040Skips %d settings Eye Candy doesn't save in presets:|r %s%s", #skipped,
			table.concat(shown, ", "), #skipped > 8 and ", ..." or "")
	end
	if p.clash then
		lines[#lines + 1] = "You already have a preset called \"" .. tostring(p.name) .. "\". Replace it, or keep both."
	else
		lines[#lines + 1] = "It's saved as a new preset. Nothing changes until you press Apply on it."
	end
	return table.concat(lines, "\n"), true, p.clash and true or false
end

----------------------------------------------------------------------
-- Presets tab
-- At the top, the "On now" card: the preset you are on, and Back to before. Below it one list:
-- Your presets (with Save and the Import strip), Quality levels, Looks and Situations. A row has
-- one Apply and a "..." menu (Share, Duplicate, Rename, Delete). The row you are on is gold.
----------------------------------------------------------------------

local ROW_H, ROW_GAP, GROUP_GAP = 34, 4, 24
local CARD_H = 72
-- The Back button stays short: the name is cut to a few characters (whole UTF-8 characters,
-- never half of one) and the full name is in the tooltip.
local BACK_NAME_MAX, BACK_W_MAX = 18, 230

-- One line under each name. Tiers say what they are for; the rest use the first sentence of
-- their description, so a new Look or Situation gets a line without a change here.
local TIER_LINES = {
	"Most FPS, least detail.",
	"Good FPS, good looks.",
	"Sharp and smooth on a decent PC.",
	"Nearly everything up. Needs a strong PC.",
	"Everything up. Costs a lot of FPS.",
	"Cinematic, furthest view, highest render scale. Big FPS cost.",
}

local GROUP_WORD = { Tiers = "Quality level", Looks = "Look", Situations = "Situation", Yours = "Your preset" }

function ns.PresetLine(p)
	if p.group == "Tiers" and TIER_LINES[p.index] then return TIER_LINES[p.index] end
	if not p.builtin then
		local who = p.author and p.author ~= "" and p.author ~= ns.CharacterName() and ("From " .. tostring(p.author)) or "Saved"
		return who .. (p.date and (", " .. tostring(p.date)) or "")
	end
	local d = tostring(p.desc or ""):gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
	return d:match("^(.-[%.!?])%s") or d:match("^[^\n]*") or ""
end

local function TierColour(p)
	if p.group ~= "Tiers" or not p.index then return nil end
	if p.index > #ns.TIERS then return "ffff7b54" end
	return ns.TIER_COLOURS[p.index]
end

local function RGB(hex)
	return tonumber(hex:sub(3, 4), 16) / 255, tonumber(hex:sub(5, 6), 16) / 255, tonumber(hex:sub(7, 8), 16) / 255
end

local function PresetAction(p, action)
	-- "New" lasts until the next apply, rename or delete; so does the import result line.
	local page = main and main.pages and main.pages.presets
	if page and (action == "apply" or action == "rename" or action == "delete") then
		page.newId, page.importMsg = nil, nil
	end
	-- A new action clears the last result on the card; a refusal of this one writes its own.
	if page and page.cardMsg then
		page.cardMsg, page.cardMsgKey = nil, nil
		ns.RefreshUI()
	end
	if action == "apply" then
		local ok, err = ns.ApplyPresetById(p.id)
		if not ok and err then
			if page and WindowOpen() then page.cardMsg, page.cardMsgKey = "|cffff4040" .. tostring(err) .. "|r", nil else ns.Print(err) end
			if ns.RefreshUI then ns.RefreshUI() end
		end
	elseif action == "duplicate" then
		Said(ns.DuplicatePreset(p.id))
	elseif action == "share" then
		local text = Said(ns.ExportPreset(p.id))
		if text then
			ns.ShowText(text, "Everything is selected. Press Ctrl+C, then paste it to a friend. They paste it into Import on the Presets tab.")
		end
		return
	elseif action == "rename" then
		ns.Ask({ title = "Rename preset", text = "New name for \"" .. p.name .. "\":", edit = p.name, accept = "Rename",
			onAccept = function(name)
				if name ~= "" then Said(ns.RenamePreset(p.id, name)) end
				ns.RefreshUI()
			end })
		return
	elseif action == "delete" then
		ns.Ask({ title = "Delete preset", text = "Delete \"" .. p.name .. "\"? This can't be undone.", accept = "Delete",
			onAccept = function()
				Said(ns.DeletePreset(p.id))
				ns.RefreshUI()
			end })
		return
	end
	ns.RefreshUI()
end
ns.PresetAction = PresetAction

-- The "..." menu: built-ins can be shared and copied; yours can also be renamed and deleted.
function ns.PresetMenuItems(p)
	local items = { { "share", "Share" }, { "duplicate", "Duplicate" } }
	if not p.builtin then
		items[#items + 1] = { "rename", "Rename" }
		items[#items + 1] = { "delete", "|cffff4040Delete|r" }
	end
	return items
end

-- The game's own context menu when it has one, else a small list of buttons by the owner.
local menuFrame
function ns.OpenPresetMenu(owner, p)
	local items = ns.PresetMenuItems(p)
	if MenuUtil and MenuUtil.CreateContextMenu then
		MenuUtil.CreateContextMenu(owner, function(_, root)
			if root.CreateTitle then root:CreateTitle(p.name) end
			for _, it in ipairs(items) do
				root:CreateButton(it[2], function() PresetAction(p, it[1]) end)
			end
		end)
		return
	end
	if not menuFrame then
		menuFrame = CreateFrame("Frame", "EyeCandyPresetMenu", UIParent, "BackdropTemplate")
		menuFrame:SetFrameStrata("FULLSCREEN_DIALOG")
		menuFrame:SetSize(120, 8)
		local bg = menuFrame:CreateTexture(nil, "BACKGROUND")
		bg:SetAllPoints()
		bg:SetColorTexture(0.05, 0.05, 0.05, 0.95)
		menuFrame.buttons = {}
		tinsert(UISpecialFrames, "EyeCandyPresetMenu")
		-- A click anywhere else closes it, and so does closing the window.
		local catcher = CreateFrame("Button", nil, UIParent)
		catcher:SetAllPoints(UIParent)
		catcher:SetFrameStrata("FULLSCREEN")
		catcher:RegisterForClicks("AnyUp")
		catcher:SetScript("OnClick", function() menuFrame:Hide() end)
		catcher:Hide()
		menuFrame.catcher = catcher
		menuFrame:SetScript("OnShow", function() catcher:Show() end)
		menuFrame:SetScript("OnHide", function() catcher:Hide() end)
		if main then main:HookScript("OnHide", function() menuFrame:Hide() end) end
	end
	for i, it in ipairs(items) do
		local b = menuFrame.buttons[i]
		if not b then
			b = Button(menuFrame, "", 112, nil)
			b:SetPoint("TOPLEFT", 4, -4 - (i - 1) * 26)
			menuFrame.buttons[i] = b
		end
		b:SetText(it[2])
		b:SetScript("OnClick", function()
			menuFrame:Hide()
			PresetAction(p, it[1])
		end)
		b:Show()
	end
	for i = #items + 1, #menuFrame.buttons do menuFrame.buttons[i]:Hide() end
	menuFrame:SetHeight(8 + #items * 26)
	menuFrame:ClearAllPoints()
	menuFrame:SetPoint("TOPRIGHT", owner, "BOTTOMRIGHT", 0, -2)
	menuFrame.p = p
	menuFrame:Show()
	menuFrame:Raise()
end

-- A row's name box and the length ShortName cuts to agree: 26 characters is about 170px at
-- GameFontHighlight (about 6.5px a character), inside the 180px box. The full name is in the row's
-- tooltip. Where the game can measure the text, a name of wide letters is cut again until it fits.
local ROW_NAME_X, ROW_NAME_W, ROW_NAME_CHARS = 14, 180, 26

-- GetStringWidth stops at the box's width when the text cannot wrap (warcraft.wiki.gg
-- API:FontString_GetStringWidth), so the unbounded width is the one to read.
local function TextWidth(fs)
	local get = fs.GetUnboundedStringWidth or fs.GetStringWidth
	return tonumber((get(fs))) or 0
end

local function FitRowName(fs, name)
	local n = ROW_NAME_CHARS
	fs:SetText(ns.ShortName(name, n))
	local w = TextWidth(fs)
	while w > ROW_NAME_W and n > 6 do
		n = n - 1
		fs:SetText(ns.ShortName(name, n))
		w = TextWidth(fs)
	end
end

local function PresetRow(content)
	local row = CreateFrame("Button", nil, content)
	row:SetSize(ns.ROW_W, ROW_H)
	row.bg = row:CreateTexture(nil, "BACKGROUND")
	row.bg:SetAllPoints()
	row.bar = row:CreateTexture(nil, "ARTWORK")
	row.bar:SetPoint("TOPLEFT")
	row.bar:SetPoint("BOTTOMLEFT")
	row.bar:SetWidth(4)
	row.name = Label(row, "", "GameFontHighlight")
	row.name:SetPoint("LEFT", ROW_NAME_X, 0)
	row.name:SetWidth(ROW_NAME_W)
	row.name:SetJustifyH("LEFT")
	if row.name.SetWordWrap then row.name:SetWordWrap(false) end

	row.more = Button(row, "...", 30, function() ns.OpenPresetMenu(row.more, row.p) end)
	row.more:SetPoint("RIGHT", -4, 0)
	Tooltip(row.more, "More", "Share, Duplicate, and for your own presets Rename and Delete. Right-clicking the row opens this too.", "ANCHOR_LEFT")
	row.apply = Button(row, "Apply", 70, function() PresetAction(row.p, "apply") end)
	row.apply:SetPoint("RIGHT", row.more, "LEFT", -4, 0)
	Tooltip(row.apply, "Apply", "Applies this preset now. Back to before undoes it.", "ANCHOR_LEFT")
	row.tag = Label(row, "", "GameFontNormal")
	row.tag:SetPoint("RIGHT", row.more, "LEFT", -10, 0)
	row.tag:SetJustifyH("RIGHT")
	-- The grey line ends where the tag starts, so "On now (12 changed)" never runs over it.
	row.line = Label(row, "", "GameFontHighlightSmall")
	row.line:SetPoint("LEFT", ROW_NAME_X + ROW_NAME_W + 10, 0)
	row.line:SetPoint("RIGHT", row.tag, "LEFT", -10, 0)
	row.line:SetJustifyH("LEFT")
	row.line:SetTextColor(0.62, 0.62, 0.62)
	if row.line.SetWordWrap then row.line:SetWordWrap(false) end

	row:RegisterForClicks("RightButtonUp")
	row:SetScript("OnClick", function(self) ns.OpenPresetMenu(self.more, self.p) end)
	row:SetScript("OnEnter", function(self)
		self.hover = true
		self:Paint()
		local p = self.p
		if not p then return end
		GameTooltip:SetOwner(self, "ANCHOR_CURSOR")
		GameTooltip:AddLine(p.name, 1, 1, 1)
		local body = p.look and ns.LookTooltip(p.look) or p.desc
		if body and body ~= "" then GameTooltip:AddLine(body, nil, nil, nil, true) end
		GameTooltip:Show()
	end)
	row:SetScript("OnLeave", function(self)
		-- Moving onto Apply or "..." still counts as over the row, so the highlight doesn't flicker.
		if self:IsMouseOver() then
			GameTooltip_Hide()
			return
		end
		self.hover = false
		self:Paint()
		GameTooltip_Hide()
	end)

	-- Gold for the preset you are on, a faint grey otherwise, a little lighter under the mouse.
	function row:Paint()
		if self.on then
			self.bg:SetColorTexture(1, 0.82, 0, self.hover and 0.2 or 0.14)
			self.bar:SetColorTexture(1, 0.82, 0, 1)
			self.bar:Show()
		else
			self.bg:SetColorTexture(1, 1, 1, self.hover and 0.1 or 0.05)
			local tc = TierColour(self.p or {})
			if tc then
				local r, g, b = RGB(tc)
				self.bar:SetColorTexture(r, g, b, 0.9)
				self.bar:Show()
			else
				self.bar:Hide()
			end
		end
	end
	return row
end

-- The Import strip is as tall as what it holds. With nothing to say it ends 8 under the paste box
-- (box top 28 + height 22). With a preview, a message or an error, it ends 6 under that text, which
-- starts at 56: a long name line, a skip list and the clash line can take four lines or more.
local STRIP_TEXT_TOP, STRIP_EMPTY_H = 56, 58

-- Size the strip to the text it holds now. 12px a line when the game cannot measure it.
-- Returns true when the height changed.
local function FitImportStrip(page)
	local s = page.strip
	local text = s.result:GetText() or ""
	local h = STRIP_EMPTY_H
	if text ~= "" then
		local used = math.ceil(tonumber((s.result:GetStringHeight())) or 0)
		if used <= 0 then
			local _, breaks = text:gsub("\n", "")
			used = (breaks + 1) * 12
		end
		h = STRIP_TEXT_TOP + used + 6
	end
	local changed = s.h ~= h
	s.h = h
	s:SetSize(ns.ROW_W, h)
	return changed
end

-- Fit the strip, and lay the list out again when its height changed.
local function RefitImportStrip(page)
	if FitImportStrip(page) and page.relayout then page.relayout() end
end

-- The Import strip, under your presets: paste a code, see what it is, save it as a new preset.
local function BuildImportStrip(page)
	local s = CreateFrame("Frame", nil, page.content)
	s.h = STRIP_EMPTY_H
	s:SetSize(ns.ROW_W, STRIP_EMPTY_H)
	local bg = s:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(1, 1, 1, 0.04)
	s.title = Label(s, "Import a preset", "GameFontNormal")
	s.title:SetPoint("TOPLEFT", 14, -8)
	s.hint = Label(s, "Got a code from a friend? Paste it here. It's saved as a new preset in this list.", "GameFontHighlightSmall")
	s.hint:SetPoint("LEFT", s.title, "RIGHT", 10, 0)
	s.hint:SetTextColor(0.62, 0.62, 0.62)

	local box = CreateFrame("EditBox", nil, s, "InputBoxTemplate")
	box:SetSize(470, 22)
	box:SetPoint("TOPLEFT", 20, -28)
	box:SetAutoFocus(false)
	box:SetMaxLetters(0)
	box:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
	box:SetScript("OnTextChanged", function() ns.UpdateImportStrip(page) end)
	s.box = box

	s.import = Button(s, "Import", 80, function() ns.ImportFromStrip(page, "keep") end)
	s.import:SetPoint("LEFT", box, "RIGHT", 10, 0)
	Tooltip(s.import, "Import", "Saves the code as a new preset in Your presets. Nothing changes until you press Apply on it.", "ANCHOR_LEFT")
	s.keep = Button(s, "Keep both", 90, function() ns.ImportFromStrip(page, "keep") end)
	s.keep:SetPoint("LEFT", box, "RIGHT", 10, 0)
	Tooltip(s.keep, "Keep both", "Keeps yours and saves the new one with \"(2)\" on the end.", "ANCHOR_LEFT")
	s.replace = Button(s, "Replace", 80, function() ns.ImportFromStrip(page, "replace") end)
	s.replace:SetPoint("LEFT", s.keep, "RIGHT", 4, 0)
	Tooltip(s.replace, "Replace", "Overwrites your preset that has the same name.", "ANCHOR_LEFT")

	s.result = Label(s, "", "GameFontHighlightSmall")
	s.result:SetPoint("TOPLEFT", 20, -56)
	s.result:SetWidth(ns.ROW_W - 40)
	page.strip = s
	ns.UpdateImportStrip(page)
end

function ns.UpdateImportStrip(page)
	local s = page.strip
	local text = s.box:GetText() or ""
	local shown, ok, clash = ns.ImportPreviewText(text)
	if text:match("%S") then page.importMsg = nil end
	s.result:SetText(text:match("%S") and shown or (page.importMsg or ""))
	s.import:SetShown(ok and not clash)
	s.keep:SetShown(clash)
	s.replace:SetShown(clash)
	RefitImportStrip(page)
end

function ns.ImportFromStrip(page, mode)
	local s = page.strip
	local p, err = ns.ImportPreset(s.box:GetText() or "", mode)
	if not p then
		s.result:SetText("|cffff4040" .. tostring(err) .. "|r")
		RefitImportStrip(page)
		return
	end
	page.newId = p.id
	s.box:SetText("")
	s.box:ClearFocus()
	page.importMsg = "|cff7cff7cSaved \"" .. p.name .. "\" in Your presets, marked New.|r Press Apply on it to use it."
	ns.UpdateImportStrip(page)
	ns.RefreshUI()
	-- Scroll the new row into view, with its heading's worth of room above it.
	local top = 0
	for _, row in ipairs(page.rows or {}) do
		if row:IsShown() and row.p and row.p.id == p.id then top = math.max(0, (row.top or 0) - 36) end
	end
	page.scrolledTo = top
	local scroll = page.content.GetParent and page.content:GetParent()
	if scroll and scroll.SetVerticalScroll then pcall(scroll.SetVerticalScroll, scroll, top) end
end

-- Under the Capital city and Raid & PvP rows: let Eye Candy switch it on by itself, and off when you
-- leave (Situations.lua). field is the page's name for the box; key the Situation's.
local SITUATION_BOXES = {
	["look:city"] = {
		field = "cityBox", key = "city", label = "Switch in cities by itself",
		tip = "In a capital city, lowers view distance, environment detail, fog and far-away character detail. Only where yours are higher. They go back when you leave. Never in combat.",
		line = "In a capital city, lowers some costly settings where yours are higher. They go back when you leave.",
	},
	["look:raid"] = {
		field = "instanceBox", key = "raid", label = "Switch in dungeons, raids and battlegrounds by itself",
		tip = "In a dungeon, raid, battleground or arena, lowers your settings to Raid & PvP's. Only where yours are higher. They go back when you leave. Never in combat.\nIf the game's own Raid and Battleground settings are on, the game sets its own graphics settings in raids and battlegrounds. Eye Candy then lowers only the rest there.",
		line = "In dungeons, raids, battlegrounds and arenas, lowers costly settings to Raid & PvP's. They go back when you leave.",
	},
}
local function SituationBox(page, spec)
	if page[spec.field] then return page[spec.field] end
	local box = CreateFrame("CheckButton", nil, page.content, "UICheckButtonTemplate")
	box:SetSize(22, 22)
	box:SetScript("OnClick", function(self)
		ns.SetAutoSituation(spec.key, self:GetChecked() and true or false)
	end)
	box.text = Label(box, "", "GameFontHighlightSmall")
	box.text:SetPoint("LEFT", box, "RIGHT", 2, 0)
	Tooltip(box, spec.label, spec.tip)
	-- What it does, on the screen (rule 23). The tooltip has the detail.
	local note = Label(page.content, spec.line, "GameFontHighlightSmall")
	note:SetTextColor(0.62, 0.62, 0.62)
	note:SetWidth(ns.ROW_W - 50)
	if note.SetWordWrap then note:SetWordWrap(false) end
	box.note = note
	page[spec.field] = box
	return box
end

-- The box's words: its label, then "On now" while its switch has settings lowered, or that it waits
-- for a fight to end (rule 25).
local function SituationBoxText(spec)
	local text = spec.label
	if ns.IsAutoSituationOn(spec.key) and ns.SituationWaiting and ns.SituationWaiting() then
		return text .. "  |cff9d9d9dWaits for the fight to end|r"
	end
	if ns.ActiveSituationKey and ns.ActiveSituationKey() == spec.key then
		local where = ns.SituationPlace and ns.SituationPlace()
		local none = ns.SituationNote and ns.SituationNote() == false
		return text .. "  |cffffd100On now" .. (where and (": in " .. where) or "") .. "|r"
			.. (none and "  |cff9d9d9dNothing needed lowering|r" or "")
	end
	return text
end

local function RefreshPresetList(page)
	local list = ns.ListPresets() or {}
	local onP, changed = nil, 0
	if ns.OnPreset then onP, changed = ns.OnPreset() end
	local entries = {}
	local function AddGroup(title, note, items, opts)
		entries[#entries + 1] = { header = title, note = note, opts = opts }
		if #items == 0 and opts and opts.empty then entries[#entries + 1] = { empty = opts.empty } end
		for _, p in ipairs(items) do entries[#entries + 1] = { p = p } end
		if opts and opts.strip then entries[#entries + 1] = { strip = true } end
	end
	local tiers, looks, situations, other = {}, {}, {}, {}
	for _, p in ipairs(list.builtin or {}) do
		if p.group == "Tiers" then tiers[#tiers + 1] = p
		elseif p.group == "Looks" then looks[#looks + 1] = p
		elseif p.group == "Situations" then situations[#situations + 1] = p
		else other[#other + 1] = p end
	end
	AddGroup("Your presets", nil, list.user or {}, { save = true, strip = true,
		empty = "No presets of your own yet. Save your settings as one, or import one from a friend below." })
	AddGroup("Quality levels", "Every system at one level.", tiers)
	AddGroup("Looks", "Styles picked by eye.", looks)
	if #situations > 0 then AddGroup("Situations", "Made for one job or place.", situations) end
	if #other > 0 then AddGroup("More built-in presets", nil, other) end

	-- One ns.Header (rule 11) per group, made the first time the group shows. page.headers lists
	-- the ones showing now, in order.
	page.headerFor = page.headerFor or {}
	page.headers = {}
	for _, h in pairs(page.headerFor) do h:Hide() end
	page.rows = page.rows or {}
	page.empties = page.empties or {}
	local y, nh, nr, ne = 0, 0, 0, 0
	local boxShown = {}
	for _, e in ipairs(entries) do
		if e.header then
			nh = nh + 1
			local h = page.headerFor[e.header]
			if not h then
				local height
				h, height = ns.Header(page.content, e.header, e.note)
				h.h = height
				page.headerFor[e.header] = h
			end
			page.headers[nh] = h
			if nh > 1 then y = y + GROUP_GAP end
			h:ClearAllPoints()
			h:SetPoint("TOPLEFT", 0, -y)
			h:Show()
			if e.opts and e.opts.save then
				page.saveButton:SetParent(h)
				page.saveButton:ClearAllPoints()
				page.saveButton:SetPoint("TOPRIGHT", -4, -6)
				page.saveButton:Show()
			end
			y = y + h.h
		elseif e.empty then
			ne = ne + 1
			local f = page.empties[ne]
			if not f then
				f = Label(page.content, "", "GameFontHighlightSmall")
				f:SetTextColor(0.62, 0.62, 0.62)
				f:SetWidth(ns.ROW_W - 28)
				page.empties[ne] = f
			end
			f:SetText(e.empty)
			f:ClearAllPoints()
			f:SetPoint("TOPLEFT", 14, -(y + 4))
			f:Show()
			y = y + 24
		elseif e.strip then
			y = y + 2
			page.strip:ClearAllPoints()
			page.strip:SetPoint("TOPLEFT", 0, -y)
			page.strip:Show()
			FitImportStrip(page)
			y = y + page.strip.h
		else
			nr = nr + 1
			local row = page.rows[nr]
			if not row then
				row = PresetRow(page.content)
				page.rows[nr] = row
			end
			local p = e.p
			row.p = p
			row.on = onP ~= nil and onP.id == p.id
			row.isNew = page.newId == p.id
			FitRowName(row.name, p.name)
			row.line:SetText(ns.PresetLine(p))
			if row.on then
				row.tag:SetText(changed > 0 and string.format("|cffffd100On now|r |cff9d9d9d(%d changed)|r", changed) or "|cffffd100On now|r")
			elseif row.isNew then
				row.tag:SetText("|cff7cff7cNew|r")
			else
				row.tag:SetText("")
			end
			-- On now and unchanged: nothing to apply. Changed since: Apply puts it back.
			row.apply:SetShown(not (row.on and changed == 0))
			row.tag:ClearAllPoints()
			if row.apply:IsShown() then
				row.tag:SetPoint("RIGHT", row.apply, "LEFT", -8, 0)
			else
				row.tag:SetPoint("RIGHT", row.more, "LEFT", -10, 0)
			end
			row:Paint()
			row:ClearAllPoints()
			row:SetPoint("TOPLEFT", 0, -y)
			row.top = y
			row:Show()
			y = y + ROW_H + ROW_GAP
			local spec = SITUATION_BOXES[p.id]
			if spec and ns.SetAutoSituation then
				local box = SituationBox(page, spec)
				box:ClearAllPoints()
				box:SetPoint("TOPLEFT", 10, -(y - ROW_GAP + 2))
				box:SetChecked(ns.IsAutoSituationOn(spec.key))
				box.text:SetText(SituationBoxText(spec))
				box:Show()
				box.note:ClearAllPoints()
				box.note:SetPoint("TOPLEFT", 34, -(y - ROW_GAP + 2 + 20))
				box.note:Show()
				boxShown[spec.field] = true
				y = y + 26 + 14
			end
		end
	end
	for _, spec in pairs(SITUATION_BOXES) do
		local box = page[spec.field]
		if box and not boxShown[spec.field] then box:Hide(); box.note:Hide() end
	end
	for i = nr + 1, #page.rows do page.rows[i]:Hide() end
	for i = ne + 1, #page.empties do page.empties[i]:Hide() end
	page.content:SetHeight(math.max(y, 1))
end

-- Without the presets list: plain tier and Look buttons.
-- The Showcase button's tooltip on that fallback page. Render scale is asked for, but the game
-- won't go above its highest, so its line says so.
function ns.ShowcaseTooltip()
	local lines = { "The best-looking setup Eye Candy knows about. Sets every system to Cinematic, the Hidden tab's settings to their Showcase values (the furthest far detail, terrain and building detail), then:" }
	for _, ex in ipairs(ns.EXTRAS) do
		local v = ns.SHOWCASE_EXTRAS[ex.key]
		if v ~= nil then
			lines[#lines + 1] = "  " .. ex.name .. ": " .. ns.ExtraLabel(ex, v) .. (ex.scale and ", or the most the game allows" or "")
		end
	end
	lines[#lines + 1] = " "
	lines[#lines + 1] = "Above 100% the cost climbs fast: 200% is roughly 1.8x the GPU work of 150%."
	lines[#lines + 1] = "Applies straight away. Back to before undoes it."
	return table.concat(lines, "\n")
end

local function BuildPresetButtons(page)
	local intro = Label(page, "One click sets every system at once and applies straight away. Fine-tune anything after on the Standard and Hidden tabs.", "GameFontNormalSmall")
	intro:SetPoint("TOPLEFT", 4, -34)
	intro:SetWidth(ns.PAGE_W - 8)

	local tierLabel = Label(page, "Set all to:", "GameFontHighlightSmall")
	tierLabel:SetPoint("TOPLEFT", 4, -70)
	local prev
	for i, name in ipairs(ns.TIERS) do
		local b = Button(page, "|c" .. ns.TIER_COLOURS[i] .. name .. "|r", 96, function() ns.SetPreset(i) end)
		if prev then b:SetPoint("LEFT", prev, "RIGHT", 4, 0) else b:SetPoint("TOPLEFT", 4, -88) end
		Tooltip(b, name, "Sets every system to " .. name .. " and the Hidden tab's settings to " .. name .. "'s values, then applies straight away.\nSettings without a " .. name .. " value go back to default. Settings that wait for Apply aren't changed.")
		prev = b
	end
	local showcase = Button(page, "|cffff7b54Showcase|r", 96, function() ns.ApplyShowcase() end)
	showcase:SetPoint("LEFT", prev, "RIGHT", 4, 0)
	Tooltip(showcase, "Showcase", function() return ns.ShowcaseTooltip() end)

	local lookLabel = Label(page, "Looks:", "GameFontHighlightSmall")
	lookLabel:SetPoint("TOPLEFT", 4, -124)
	prev = nil
	for _, look in ipairs(ns.LOOKS) do
		local b = Button(page, look.name, 96, function() ns.SetLook(look.key) end)
		if prev then b:SetPoint("LEFT", prev, "RIGHT", 4, 0) else b:SetPoint("TOPLEFT", 4, -142) end
		Tooltip(b, look.name, function() return ns.LookTooltip(look) end)
		prev = b
	end
end

function ns.LookTooltip(look)
	local lines = { look.desc, " " }
	local ex = look.extras or {}
	if ex.renderScale then lines[#lines + 1] = "Render scale: asks for " .. math.floor(ex.renderScale * 100 + 0.5) .. "%, or the most the game allows" end
	if ex.sharpness then lines[#lines + 1] = "Sharpness " .. ns.FormatNumber(ex.sharpness) .. " (lower = sharper)" end
	local d = look.dials or {}
	local function v(k) return d[k] ~= nil and ns.FormatNumber(d[k]) or "-" end
	lines[#lines + 1] = "Grass " .. v("groundEffectDensity") .. " out to " .. v("groundEffectDist") .. ", fade from " .. v("groundEffectFade")
	lines[#lines + 1] = "Contrast " .. v("Contrast") .. ", brightness " .. v("Brightness") .. ", gamma " .. v("Gamma") .. ", bloom " .. v("bloomUserMult")
	lines[#lines + 1] = "Field of view " .. v("cameraFov") .. ", soft particles (depth effects) " .. v("graphicsDepthEffects")
	lines[#lines + 1] = " "
	lines[#lines + 1] = "|cff9d9d9dStarts from " .. (look.base > #ns.TIERS and "Showcase" or ns.TIERS[look.base]) .. ". Applies straight away. Tweak anything after on the Hidden tab.|r"
	return table.concat(lines, "\n")
end

-- What is running on your settings right now, in a few words, or nil (the title and the card show it).
function ns.RunningNote()
	local at = ns.AutotuneNote and ns.AutotuneNote()
	if at then return at end
	if ns.ActiveSituationName and ns.ActiveSituationName() then
		-- false: a switch is on here but lowered nothing, so there is nothing to say.
		local note = ns.SituationNote and ns.SituationNote()
		if note == false then return nil end
		return note or "In a city: some settings lowered"
	end
end

-- The "On now" card at the top of the Presets tab.
local function BuildCard(page)
	local c = CreateFrame("Frame", nil, page)
	c:SetSize(ns.ROW_W, CARD_H) -- the rows under it are ROW_W wide: one right edge
	c:SetPoint("TOPLEFT", 0, -2)
	local bg = c:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(1, 0.82, 0, 0.08)
	c.bar = c:CreateTexture(nil, "ARTWORK")
	c.bar:SetPoint("TOPLEFT")
	c.bar:SetPoint("BOTTOMLEFT")
	c.bar:SetWidth(4)
	c.bar:SetColorTexture(1, 0.82, 0, 1)
	c.kicker = Label(c, "On now", "GameFontHighlightSmall")
	c.kicker:SetPoint("TOPLEFT", 16, -8)
	c.kicker:SetTextColor(0.62, 0.62, 0.62)
	-- The kind and the change count sit beside "On now"; the name has the line below to itself.
	-- Both stop short of the Back button and never wrap.
	c.detail = Label(c, "", "GameFontHighlightSmall")
	c.detail:SetPoint("LEFT", c.kicker, "RIGHT", 8, 0)
	c.detail:SetPoint("RIGHT", c, "RIGHT", -(BACK_W_MAX + 24), 0)
	c.detail:SetJustifyH("LEFT")
	c.detail:SetWordWrap(false)
	c.detail:SetTextColor(0.62, 0.62, 0.62)
	c.name = Label(c, "", "GameFontNormalHuge")
	c.name:SetPoint("TOPLEFT", 16, -24)
	c.name:SetPoint("RIGHT", c, "RIGHT", -(BACK_W_MAX + 24), 0)
	c.name:SetJustifyH("LEFT")
	c.name:SetWordWrap(false)
	-- Third line: what Back just did, else what is running on your settings (Autotune, the city switch).
	c.note = Label(c, "", "GameFontHighlightSmall")
	c.note:SetPoint("TOPLEFT", 16, -52)
	c.note:SetPoint("RIGHT", c, "RIGHT", -(BACK_W_MAX + 24), 0)
	c.note:SetJustifyH("LEFT")
	c.note:SetWordWrap(false)
	page.card = c
	return c
end

-- What the card's result line was said about. Once any of it changes (a fight ends, a setting moves,
-- Autotune or the city switch starts), the line is out of date and goes.
local function CardState(onKey)
	local name = ns.LastPresetName and ns.LastPresetName()
	return table.concat({ onKey, tostring(InCombatLockdown()), ns.RunningNote() or "", tostring(name) }, "|")
end

local function RefreshCard(page)
	local c = page.card
	local p, changed = nil, 0
	if ns.OnPreset then p, changed = ns.OnPreset() end
	if p then
		c.name:SetText(ns.ShortName(p.name, 28))
		local word = GROUP_WORD[p.group] or "Preset"
		c.detail:SetText(changed > 0
			and string.format("%s. |cff9d9d9d%d %s changed since you applied it.|r", word, changed, changed == 1 and "setting" or "settings")
			or (word .. "."))
		c.bar:Show()
	else
		c.name:SetText("|cff9d9d9dNo preset yet|r")
		-- Back to before shows only once a preset has been applied, so it is not named here.
		c.detail:SetText("Pick one below. A preset applies when you press Apply on it.")
		c.bar:Hide()
	end
	-- Autotune and the city switch call RefreshUI when they change, so the timed check needs only this.
	page.onKey = p and (p.id .. ":" .. changed) or ""
	if page.cardMsg then
		local state = CardState(page.onKey)
		if not page.cardMsgKey then
			page.cardMsgKey = state
		elseif page.cardMsgKey ~= state then
			page.cardMsg, page.cardMsgKey = nil, nil
		end
	end
	local running = ns.RunningNote()
	c.note:SetText(page.cardMsg or (running and ("|cffffd100" .. running .. "|r")) or "")
end

ns.TAB_BUILD.presets = function(page)
	if not ns.ListPresets then
		page.status = Label(page, "", "GameFontNormalSmall")
		page.status:SetPoint("TOPLEFT", 4, -6)
		BuildPresetButtons(page)
		return
	end
	BuildCard(page)
	if ns.UndoLastPreset and ns.LastPresetName then
		-- Shown only while the last preset can still be undone in one step.
		local back = Button(page.card, "Back", 120, function()
			local n, line = ns.GoBack()
			page.cardMsg = line and ((n and "|cff7cff7c" or "|cffff4040") .. line .. "|r") or nil
			page.cardMsgKey = nil
			ns.RefreshUI()
		end)
		back:SetPoint("RIGHT", -12, 0)
		back:Hide()
		Tooltip(back, function() return back:GetText() or "Back" end, function()
			local name = ns.LastPresetName()
			return name and ("Puts every setting back as it was just before " .. name .. ".") or ""
		end, "ANCHOR_LEFT")
		page.backButton = back
	end
	page.content = ns.ScrollPage(page, -(CARD_H + 10))
	page.saveButton = Button(page.content, "Save my settings as a preset", 210, function()
		ns.Ask({ title = "Save as preset", text = "Name this preset. It saves all your graphics settings as they are now.", edit = "", accept = "Save",
			onAccept = function(name)
				page.cardMsg, page.cardMsgKey = nil, nil
				if name ~= "" then Said(ns.SaveCurrentAsPreset(name)) end
				ns.RefreshUI()
			end })
	end)
	Tooltip(page.saveButton, "Save my settings as a preset", "Saves all your graphics settings as they are now, under a name you pick.", "ANCHOR_LEFT")
	BuildImportStrip(page)
	page.relayout = function() RefreshPresetList(page) end
	-- "New" and the import message last until you leave the tab.
	page:HookScript("OnHide", function(self)
		self.newId, self.importMsg, self.cardMsg, self.cardMsgKey = nil, nil, nil, nil
		if self.strip and ns.UpdateImportStrip then ns.UpdateImportStrip(self) end
	end)
	page.usesList = true
end

function ns.ShortName(name, max)
	name = tostring(name or "")
	local out, n = {}, 0
	for ch in name:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
		n = n + 1
		if n > max then
			return table.concat(out, "", 1, max - 1) .. "..."
		end
		out[n] = ch
	end
	return name
end

ns.TAB_REFRESH.presets = function(page)
	if not page.usesList then return end
	RefreshCard(page)
	if page.backButton then
		local name = ns.LastPresetName()
		page.backName = name
		page.backButton:SetShown(name ~= nil)
		if name then
			page.backButton:SetText("Back to before " .. ns.ShortName(name, BACK_NAME_MAX))
			local fs = page.backButton:GetFontString()
			local tw = fs and tonumber(fs:GetStringWidth() or 0) or 0
			page.backButton:SetWidth(math.min(BACK_W_MAX, math.max(120, tw + 24)))
		end
	end
	RefreshPresetList(page)
end

----------------------------------------------------------------------
-- Backups tab
----------------------------------------------------------------------

local KIND_LABEL = { original = "Original, kept for good", manual = "Manual" }

-- How many backed-up values differ from the current ones (for the fallback's single backup).
local function CountDiffer(values)
	local n = 0
	for cvar, value in pairs(values or {}) do
		local now = ns.GetInfo(cvar)
		if now ~= nil and not ns.Same(now, value) then n = n + 1 end
	end
	return n
end
ns.CountDiffer = CountDiffer

function ns.AskRestore(b)
	local count
	if ns.CountBackupChanges and b.id then count = ns.CountBackupChanges(b.id) else count = CountDiffer(b.values) end
	ns.Ask({
		title = "Restore backup",
		text = string.format("Restore %d %s from %s?", count, count == 1 and "setting" or "settings", tostring(b.time or "earlier"))
			.. "\nThis can't be undone. Create a backup first if you want to keep your settings now.",
		accept = "Restore",
		onAccept = function()
			local page = main and main.pages and main.pages.backups
			if ns.RestoreBackupById and b.id then
				local n, err = ns.RestoreBackupById(b.id)
				local line = n and ns.RestoredLine and ns.RestoredLine(n, b) or err
				if page and line then
					page.resultMsg = (n and "|cff7cff7c" or "|cffff4040") .. line .. "|r"
				elseif line then
					ns.Print(line)
				end
			else
				ns.RestoreBackup()
			end
			ns.RefreshUI()
		end,
	})
end

function ns.AskCreateBackup()
	if not ns.CreateBackup then return end
	ns.Ask({ title = "Create backup", text = "Name this backup (or leave it blank to use the date).", edit = "", accept = "Create",
		onAccept = function(name)
			local page = main and main.pages and main.pages.backups
			if page then page.resultMsg = nil end
			ns.BarSay(nil)
			SaidBackup(ns.CreateBackup("manual", name ~= "" and name or nil))
			ns.RefreshUI()
		end })
end

local function BackupRow(content, index)
	local row = CreateFrame("Frame", nil, content)
	row:SetSize(ns.ROW_W, 28)
	local bg = row:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(1, 1, 1, (index % 2 == 0) and 0.04 or 0)
	row.name = Label(row, "", "GameFontHighlight") -- names are white (rule 14, rule 20)
	row.name:SetPoint("LEFT", 8, 0)
	-- The name is cut to 28 characters (the full name is in the row's tooltip); the info line gets
	-- the rest of the row up to Delete, which starts near x 576.
	row.name:SetWidth(220)
	row.name:SetJustifyH("LEFT")
	row.name:SetWordWrap(false)
	row.info = Label(row, "", "GameFontHighlightSmall")
	row.info:SetTextColor(0.616, 0.616, 0.616) -- 9d9d9d, readable (the disabled grey is too dark)
	row.info:SetPoint("LEFT", 234, 0)
	row.info:SetWidth(338)
	row.info:SetJustifyH("LEFT")
	row.info:SetWordWrap(false)
	row:EnableMouse(true)
	Tooltip(row, function() return row.b and tostring(row.b.label or KIND_LABEL[row.b.kind] or "Backup") or "" end, function()
		local b = row.b
		if not b then return "" end
		local parts = { KIND_LABEL[b.kind] or "", tostring(b.time or "") }
		if b.character and b.character ~= "" then parts[#parts + 1] = tostring(b.character) end
		return table.concat(parts, "   ")
	end)
	row.restore = Button(row, "Restore", 70, function() ns.AskRestore(row.b) end)
	row.restore:SetPoint("RIGHT", -2, 0)
	Tooltip(row.restore, "Restore", "Puts these settings back. Asks first and shows how many settings change.")
	row.delete = Button(row, "|cffff4040Delete|r", 62, function()
		ns.Ask({ title = "Delete backup", text = "Delete the backup \"" .. tostring(row.b.label) .. "\"? This can't be undone.", accept = "Delete",
			onAccept = function()
				local ok, err = ns.DeleteBackup(row.b.id)
				local page = main and main.pages and main.pages.backups
				if page then page.resultMsg = (not ok and err) and ("|cffff4040" .. err .. "|r") or nil end
				ns.RefreshUI()
			end })
	end)
	row.delete:SetPoint("RIGHT", row.restore, "LEFT", -12, 0)
	Tooltip(row.delete, "Delete", "Removes this backup for good. Asks first.", "ANCHOR_LEFT")
	return row
end

ns.TAB_BUILD.backups = function(page)
	local intro = Label(page, ns.CreateBackup
		and "Original = your settings before Eye Candy, kept for good. Create backup saves your settings now, under a name you choose."
		or "Original = your settings before Eye Candy, kept for good.", "GameFontNormalSmall")
	intro:SetPoint("TOPLEFT", 4, -4)
	intro:SetWidth(ns.PAGE_W - 150)
	local create = Button(page, "Create backup", 130, ns.AskCreateBackup)
	create:SetPoint("TOPRIGHT", -2, 0)
	create:SetEnabled(ns.CreateBackup ~= nil)
	Tooltip(create, "Create backup", "Saves every setting Eye Candy manages, as they are now, under a name you choose.")
	-- What Restore or Delete just did, under the intro. It lasts until you leave the tab.
	page.result = Label(page, "", "GameFontHighlightSmall")
	page.result:SetPoint("TOPLEFT", 4, -34)
	page.result:SetWidth(ns.PAGE_W - 150)
	page.result:SetJustifyH("LEFT")
	page.result:SetWordWrap(false)
	page:HookScript("OnHide", function(self) self.resultMsg = nil end)
	page.content = ns.ScrollPage(page, -52)
	page.rows = {}
	page.empty = Label(page.content, "No backup yet. Your Original is saved a few seconds after you log in.", "GameFontHighlightSmall")
	page.empty:SetPoint("TOPLEFT", 8, -8)
end

ns.TAB_REFRESH.backups = function(page)
	local list
	if ns.ListBackups then
		list = ns.ListBackups() or {}
	else
		local b = ns.OriginalBackup and ns.OriginalBackup()
		list = b and { { kind = "original", label = "Original settings", time = b.time, values = b.values } } or {}
	end
	page.empty:SetShown(#list == 0)
	page.result:SetText(page.resultMsg or "")
	-- The Original backup goes first (this only reorders what is shown).
	local ordered = {}
	for _, b in ipairs(list) do if b.kind == "original" then ordered[#ordered + 1] = b end end
	for _, b in ipairs(list) do if b.kind ~= "original" then ordered[#ordered + 1] = b end end
	list = ordered
	for i, b in ipairs(list) do
		local row = page.rows[i]
		if not row then
			row = BackupRow(page.content, i)
			row:SetPoint("TOPLEFT", 0, -(i - 1) * 28)
			page.rows[i] = row
		end
		row.b = b
		row.name:SetText(ns.ShortName(tostring(b.label or KIND_LABEL[b.kind] or "Backup"), 28))
		local count = (ns.CountBackupChanges and b.id) and ns.CountBackupChanges(b.id) or CountDiffer(b.values)
		-- The count goes first: the line does not wrap, so if it is too long only its end (the
		-- character name) is cut, never the count.
		local parts = { count == 0 and "matches now" or (count == 1 and "1 setting differs" or (count .. " settings differ")) }
		if KIND_LABEL[b.kind] then parts[#parts + 1] = KIND_LABEL[b.kind] end
		parts[#parts + 1] = tostring(b.time or "")
		-- The character name only; the full Name-Realm is in the row's tooltip.
		if b.character and b.character ~= "" then parts[#parts + 1] = (tostring(b.character):match("^([^-]+)")) end
		row.info:SetText(table.concat(parts, "  "))
		row.delete:SetShown(ns.DeleteBackup ~= nil and b.kind ~= "original")
		row:Show()
	end
	for i = #list + 1, #page.rows do page.rows[i]:Hide() end
	page.content:SetHeight(math.max(#list * 28, 1))
end

----------------------------------------------------------------------
-- Main window
----------------------------------------------------------------------

local function EnsureBuilt(key)
	local page = main.pages[key]
	if not page.built then
		page.built = true
		if ns.TAB_BUILD[key] then ns.TAB_BUILD[key](page) end
		if ns.TAB_LIST[key] then ns.TAB_LIST[key]:Layout(ns.searchText) end
	end
	return page
end

-- The search box filters the Standard and Hidden tabs together.
function ns.SetSearch(text)
	ns.searchText = (text or ""):gsub("^%s+", ""):gsub("%s+$", "")
	if not main then return end
	local counts = {}
	for _, key in ipairs({ "standard", "hidden" }) do
		if ns.TAB_LIST[key] or ns.TAB_BUILD[key] then
			EnsureBuilt(key)
			counts[key] = ns.TAB_LIST[key] and ns.TAB_LIST[key]:Layout(ns.searchText) or 0
		end
	end
	if ns.searchText == "" then
		main.searchCount:SetText("")
	else
		main.searchCount:SetText(string.format("Standard %d, Hidden %d", counts.standard or 0, counts.hidden or 0))
	end
	return counts
end

----------------------------------------------------------------------
-- Shrink: the main window rolls up to a small bar (title and Apply), so the world shows
-- while you try settings. Its top-left corner stays put. Opening a tab opens it back up.
----------------------------------------------------------------------

local SHRUNK_W, SHRUNK_H = 300, 66

-- The title: the long one, the short one when shrunk, or what Compare is showing.
local function SetTitle()
	local label = ns.CompareLabel and ns.CompareLabel()
	main.shownLabel = label
	if label and main.shrunk then
		-- The 300-wide bar: the label alone, cut to fit between the corners.
		main.titleText:SetText("|cffffd100" .. ns.ShortName(label, 32) .. "|r")
	elseif label then
		main.titleText:SetText("Eye Candy  |cffffd100" .. ns.ShortName(label, 60) .. "|r")
	elseif main.shrunk then
		main.titleText:SetText("Eye Candy")
	else
		-- The preset you are on, on every tab.
		local p = ns.OnPreset and ns.OnPreset()
		local running = ns.RunningNote()
		local text = p and ("Eye Candy  |cffffd100" .. ns.ShortName(p.name, running and 28 or 60) .. "|r") or (running and "Eye Candy" or main.fullTitle)
		if running then text = text .. "  |cffffd100" .. running .. "|r" end
		main.titleText:SetText(text)
	end
end

-- Peek and Compare sit left of Export on the full bar, and right of Apply on the shrunk one.
local function PlaceBarButtons()
	local prev
	for _, b in ipairs(main.barButtons) do
		b:ClearAllPoints()
		if main.shrunk then
			b:SetPoint("LEFT", prev or main.apply, "RIGHT", 4, 0)
		else
			b:SetPoint("RIGHT", prev or main.export, "LEFT", prev and -4 or -6, 0)
		end
		prev = b
	end
end

-- Apply only means something on the Hidden tab (every other tab applies at once), so it shows there and on
-- the shrunk bar. Create backup is left off the Backups tab, which has its own. The rest close up.
local function PlaceBottomBar()
	if not (main and main.apply and main.keep) then return end
	local tab = main.tab
	local showApply = main.shrunk or tab == "hidden"
	local showBackup = not main.shrunk and tab ~= "backups"
	main.apply:SetShown(showApply)
	main.createBackup:SetShown(showBackup)
	local prev
	if showApply then prev = main.apply end
	if showBackup then
		main.createBackup:ClearAllPoints()
		if prev then main.createBackup:SetPoint("LEFT", prev, "RIGHT", 6, 0) else main.createBackup:SetPoint("BOTTOMLEFT", 16, 14) end
		prev = main.createBackup
	end
	main.keep:ClearAllPoints()
	if prev then main.keep:SetPoint("LEFT", prev, "RIGHT", 10, 0) else main.keep:SetPoint("BOTTOMLEFT", 12, 12) end
end

-- Say a bottom bar result in red above the bar (nil clears it). True when the window took it, so a
-- caller can fall back to chat when the window is closed.
function ns.BarSay(text)
	if not (main and main.barMsg) then return false end
	if text and not main:IsShown() then return false end
	main.barMsg:SetText(text and ("|cffff4040" .. tostring(text) .. "|r") or "")
	if main.shrunk then
		-- The 300-wide bar has no room above the buttons: it grows for two lines.
		main.barMsg:SetWidth(SHRUNK_W - 28)
		main.barMsg:SetWordWrap(true)
		main:SetSize(SHRUNK_W, text and (SHRUNK_H + 28) or SHRUNK_H)
	else
		main.barMsg:SetWidth(WIDTH - 40)
		main.barMsg:SetWordWrap(false)
	end
	return true
end

-- The bar's Apply. With nothing to apply the core says so in chat; here it is said in the window
-- instead (a /ec apply keeps chat). Every other line it prints still goes to chat.
function ns.BarApply()
	ns.BarSay(nil)
	local real, lines = ns.Print, {}
	ns.Print = function(msg) lines[#lines + 1] = msg end
	local ok, err = pcall(ns.ApplyAll, false, false)
	ns.Print = real
	for i, line in ipairs(lines) do
		if i == 1 and #lines == 1 and tostring(line):match("^nothing to apply") and ns.BarSay(line) then
			-- said in the window
		else
			real(line)
		end
	end
	if not ok then error(err, 0) end
end

local function RefreshCompare()
	if main and main.compare then
		local label = ns.CompareLabel and ns.CompareLabel()
		main.compare:SetText(not label and "Compare" or (label == "Showing: now" and "Show before" or "Show now"))
	end
	if main then SetTitle() end
end

local function SetShrunk(on)
	on = on and true or false
	if not main or (main.shrunk or false) == on then return end
	-- Anchor by the top-left first, so a centred window rolls up toward its title, not its middle.
	local x, y = TopLeft(main)
	if x then PlaceAt(main, x, y, tonumber(main:GetScale() or 1) or 1) end
	main.shrunk = on
	if main.barMsg then main.barMsg:SetText("") end
	for _, fr in ipairs(main.rollUp) do fr:SetShown(not on) end
	if on then
		for _, page in pairs(main.pages) do page:Hide() end
		main.search:Hide()
		main.searchCount:Hide()
		main:SetSize(SHRUNK_W, SHRUNK_H)
	else
		main:SetSize(WIDTH, HEIGHT)
	end
	SetTitle()
	PlaceBottomBar()
	PlaceBarButtons()
	main.shrink:SetNormalTexture(on and "Interface\\Buttons\\UI-PlusButton-Up" or "Interface\\Buttons\\UI-MinusButton-Up")
	main.shrink:SetPushedTexture(on and "Interface\\Buttons\\UI-PlusButton-Down" or "Interface\\Buttons\\UI-MinusButton-Down")
end

function ns.ToggleShrink()
	if not main then return end
	if main.shrunk then
		ns.ShowTab(main.tab or "presets")
	else
		SetShrunk(true)
	end
end

function ns.IsShrunk()
	return main and main.shrunk or false
end

function ns.ShowTab(key)
	if not main then ns.BuildMain() end
	SetShrunk(false)
	for _, t in ipairs(TABS) do
		local page = main.pages[t.key]
		if t.key == key then
			EnsureBuilt(key)
			page:Show()
			main.tabButtons[t.key]:LockHighlight()
		else
			page:Hide()
			main.tabButtons[t.key]:UnlockHighlight()
		end
	end
	main.tab = key
	ns.BarSay(nil)
	PlaceBottomBar()
	local searchable = key == "standard" or key == "hidden"
	main.search:SetShown(searchable)
	main.searchCount:SetShown(searchable)
	if not main:IsShown() then main:Show() end
	ns.RefreshUI()
end

function ns.RefreshUI()
	if not (main and main:IsShown()) then return end
	local page = main.pages[main.tab]
	local fn = ns.TAB_REFRESH[main.tab]
	if fn and page and page.built then fn(page) end
	main.keep:SetChecked(ns.db.keepApplied)
	main.createBackup:SetEnabled(ns.CreateBackup ~= nil)
	RefreshCompare()
end

-- Fade: after a second without the mouse over it, the main window fades a little, so more of
-- the world shows. It comes back at once when the mouse returns, and never fades while you type
-- in it or drag it. /ec fade turns it off (EyeCandyDB.noFade).
ns.FADE_ALPHA, ns.FADE_DELAY = 0.7, 1

-- True when the box with the keyboard is one of this window's own (chat and other addons don't count).
local function OwnsFocus(self)
	local f = GetCurrentKeyBoardFocus and GetCurrentKeyBoardFocus()
	for _ = 1, 30 do
		if not f then return false end
		if f == self then return true end
		f = f.GetParent and f:GetParent()
	end
	return false
end

-- A dropdown's list (Menu.lua, checked on the forever branch) is not a child of the window.
local function MenuOpen()
	local m = Menu and Menu.GetManager and Menu.GetManager()
	return m and m.IsAnyMenuOpen and m:IsAnyMenuOpen() and true or false
end

function ns.FadeStep(self, elapsed)
	elapsed = tonumber(elapsed) or 0
	-- Moving the window keeps the mouse over it; scaling can leave it, so the grip's drag counts.
	local busy = self:IsMouseOver() or OwnsFocus(self) or MenuOpen()
		or (self.scaleGrip and self.scaleGrip.left ~= nil) or (ns.db and ns.db.noFade)
	self.awayFor = busy and 0 or (self.awayFor or 0) + elapsed
	local target = (self.awayFor >= ns.FADE_DELAY) and ns.FADE_ALPHA or 1
	local alpha = tonumber(self:GetAlpha() or 1) or 1
	if target == 1 then
		if alpha ~= 1 then self:SetAlpha(1) end -- back at once
	elseif alpha > target then
		self:SetAlpha(math.max(target, alpha - elapsed * 1.5)) -- fade over about a fifth of a second
	end
end

function ns.BuildMain()
	local title = "Eye Candy  |cff9d9d9dGraphics presets and hidden settings|r"
	main = MakeWindow("EyeCandyMainFrame", WIDTH, HEIGHT, title)
	main.fullTitle = title
	main.pages, main.tabButtons, main.rollUp = {}, {}, { main.scaleGrip }

	-- Shrink button, left of the close button.
	local shrink = CreateFrame("Button", nil, main)
	shrink:SetSize(16, 16)
	shrink:SetPoint("TOPRIGHT", -28, -3)
	shrink:SetFrameLevel((tonumber(main:GetFrameLevel() or 0) or 0) + 5)
	shrink:SetNormalTexture("Interface\\Buttons\\UI-MinusButton-Up")
	shrink:SetPushedTexture("Interface\\Buttons\\UI-MinusButton-Down")
	shrink:SetHighlightTexture("Interface\\Buttons\\UI-PlusButton-Hilight", "ADD")
	shrink:SetScript("OnClick", function(self)
		ns.ToggleShrink()
		-- Still under the mouse: show the tooltip for the new state.
		if self:IsMouseOver() then
			local enter = self:GetScript("OnEnter")
			if enter then enter(self) end
		end
	end)
	Tooltip(shrink, function() return main.shrunk and "Open up" or "Shrink" end, function()
		return main.shrunk and "Opens the full window again."
			or "Rolls the window up to a small bar with Apply, so you can see the game while you try settings."
	end)
	main.shrink = shrink

	local prev
	for _, t in ipairs(TABS) do
		local b = Button(main, t.label, t.width, function() ns.ShowTab(t.key) end)
		if prev then b:SetPoint("LEFT", prev, "RIGHT", 2, 0) else b:SetPoint("TOPLEFT", 14, -28) end
		main.tabButtons[t.key] = b
		tinsert(main.rollUp, b)
		prev = b

		local page = CreateFrame("Frame", nil, main)
		page:SetPoint("TOPLEFT", 12, -58)
		page:SetPoint("BOTTOMRIGHT", -12, 48)
		page:Hide()
		main.pages[t.key] = page
	end

	local ok, search = pcall(CreateFrame, "EditBox", "EyeCandySearchBox", main, "SearchBoxTemplate")
	if not ok or not search then
		search = CreateFrame("EditBox", "EyeCandySearchBox", main, "InputBoxTemplate")
	end
	search:SetSize(160, 20)
	search:SetPoint("TOPRIGHT", -20, -30)
	search:SetAutoFocus(false)
	search:HookScript("OnTextChanged", function(self) ns.SetSearch(self:GetText()) end)
	search:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
	Tooltip(search, "Search", "Type part of a name to filter the Standard and Hidden tabs, for example grass, shadow or water.")
	main.search = search
	main.searchCount = Label(main, "", "GameFontDisableSmall")
	-- Pinned between the last tab and the search box, so it can never run into either.
	main.searchCount:SetPoint("LEFT", prev, "RIGHT", 8, 0)
	main.searchCount:SetPoint("RIGHT", search, "LEFT", -8, 0)
	main.searchCount:SetJustifyH("RIGHT")
	main.searchCount:SetWordWrap(false)

	-- Bottom bar
	local apply = Button(main, "Apply", 100, function() ns.BarApply() end)
	apply:SetPoint("BOTTOMLEFT", 16, 14)
	main.apply = apply
	Tooltip(apply, "Apply", "Applies the levels and settings on the Hidden tab that wait for Apply. The rest change at once.")

	-- A result of a bottom bar button (a refused Compare, Peek, Create backup, or Apply with nothing to apply),
	-- red, on the line above the bar. It goes when you change tab, shrink or open up, press another bar
	-- button, or Compare flips. Shrunk, the window grows a line to hold it (ns.BarSay).
	main.barMsg = Label(main, "", "GameFontHighlightSmall")
	main.barMsg:SetPoint("BOTTOMLEFT", 18, 38)
	main.barMsg:SetJustifyH("LEFT")
	main.barMsg:SetWordWrap(false)
	main.barMsg:SetWidth(WIDTH - 40)

	main.createBackup = Button(main, "Create backup", 120, ns.AskCreateBackup)
	main.createBackup:SetPoint("LEFT", apply, "RIGHT", 6, 0)
	Tooltip(main.createBackup, "Create backup", function()
		return ns.CreateBackup and "Saves all your graphics settings as they are now, under a name you pick."
			or "Not available. The backups list didn't load."
	end)

	main.keep = CreateFrame("CheckButton", nil, main, "UICheckButtonTemplate")
	main.keep:SetPoint("LEFT", main.createBackup, "RIGHT", 10, 0)
	main.keep:SetScript("OnClick", function(self)
		ns.db.keepApplied = self:GetChecked() and true or false
		ns.SaveMirror()
	end)
	local keepText = Label(main, "Keep my settings applied", "GameFontHighlightSmall")
	keepText:SetPoint("LEFT", main.keep, "RIGHT", 2, 0)
	Tooltip(main.keep, "Keep my settings applied", "The game's own Graphics menu resets some hidden settings (grass, weather, distances). With this on, Eye Candy puts yours back after login and after you close Options.")

	local export = Button(main, "Copy my settings", 124, function() ns.BarSay(nil); ns.ShowExport(IsShiftKeyDown()) end)
	export:SetPoint("BOTTOMRIGHT", -16, 14)
	Tooltip(export, "Copy my settings", "Opens a box with your graphics settings, already selected. Press Ctrl+C to copy. Shift-click to include every setting, not just the changed ones.")
	for _, fr in ipairs({ main.createBackup, main.keep, keepText, export }) do tinsert(main.rollUp, fr) end
	main.export = export

	-- Peek and Compare (Peek.lua, Compare.lua), when loaded. They stay on the shrunk bar.
	main.barButtons = {}
	if ns.ToggleCompare then
		local compare = Button(main, "Compare", 96, function(self, button)
			local ok, err
			ns.BarSay(nil)
			if button == "RightButton" then
				if not (ns.IsComparing and ns.IsComparing()) then return end
				ok, err = ns.StopCompare()
			else
				ok, err = ns.ToggleCompare()
			end
			if not ok and err then ns.BarSay(err) end
			RefreshCompare()
			-- Still under the mouse: show the tooltip for the new state.
			if self:IsMouseOver() then
				local enter = self:GetScript("OnEnter")
				if enter then enter(self) end
			end
		end)
		compare:RegisterForClicks("LeftButtonUp", "RightButtonUp")
		Tooltip(compare, "Compare", function()
			local label = ns.CompareLabel and ns.CompareLabel()
			if label then
				return label .. ".\nClick to flip. Right-click, or closing Eye Candy, ends on now."
			end
			return "Flips your settings between before your last change and now, so you can see the difference in the same spot. Click again to flip."
		end)
		main.compare = compare
		tinsert(main.barButtons, compare)
	end
	if ns.TogglePeek then
		local peek = Button(main, "Peek", 60, function()
			ns.BarSay(nil)
			local ok, err = ns.TogglePeek()
			if not ok and err then ns.BarSay(err) end
		end)
		Tooltip(peek, "Peek", "Hides the game's UI and Eye Candy so you can see the world. Press Back or Esc to bring it all back.")
		main.peek = peek
		tinsert(main.barButtons, peek)
	end
	PlaceBarButtons()

	main:SetScript("OnShow", function()
		main:SetAlpha(1)
		main.awayFor = 0
		if main.tab then ns.RefreshUI() end
	end)
	-- Closing Eye Candy ends Compare on now, so the game is never left on the old settings.
	-- Peek and Alt+Z only hide it for a moment (Alt+Z hides the parent, so IsShown stays true).
	main:SetScript("OnHide", function(self)
		ns.BarSay(nil)
		if self:IsShown() or (ns.IsPeeking and ns.IsPeeking()) then return end
		if ns.IsComparing and ns.IsComparing() and ns.StopCompare then
			local ok, err = ns.StopCompare()
			if ok then ns.Print("compare ended. Showing: now.") elseif err then ns.Print(err) end
		end
	end)
	main:SetScript("OnUpdate", ns.MainTick)
end

-- Every frame while the window is open: the fade, then the Compare button. Compare can end on
-- its own (combat, /ec compare stop), so the button and title redraw when its label changes.
-- Back to before shows only while nothing has changed since the preset (Presets.lua checks every
-- setting). Switching tabs redraws it; this catches a change made while the Presets tab is open
-- (the game's own menu, a slash command, Keep my settings applied), once a second. Each check reads
-- every managed setting, so it is skipped while there is no preset to go back to.
ns.BACK_CHECK_EVERY = 1

function ns.MainTick(self, elapsed)
	ns.FadeStep(self, elapsed)
	if self.compare and (ns.CompareLabel and ns.CompareLabel()) ~= self.shownLabel then
		ns.BarSay(nil)
		RefreshCompare()
	end
	local page = self.tab == "presets" and not self.shrunk and self.pages and self.pages.presets
	local back = page and page.built and page.backButton and (page.backName or (ns.db and ns.db.lastBefore))
	-- The "On now" card and row say how many settings changed since; a change keeps them current.
	local on = page and page.built and page.usesList and ns.OnPreset and ns.db and (ns.db.onPreset or ns.db.look)
	-- A result on the card goes once what it was about has changed (CardState).
	local msg = page and page.built and page.cardMsg and page.cardMsgKey
	if back or on or msg then
		self.backCheck = (self.backCheck or 0) + (tonumber(elapsed) or 0)
		if self.backCheck >= ns.BACK_CHECK_EVERY then
			self.backCheck = 0
			local p, changed = nil, 0
			if (on or msg) and ns.OnPreset then p, changed = ns.OnPreset() end
			local onKey = p and (p.id .. ":" .. changed) or ""
			if (back and ns.LastPresetName() ~= page.backName) or (on and onKey ~= page.onKey)
				or (msg and CardState(onKey) ~= page.cardMsgKey) then
				ns.TAB_REFRESH.presets(page)
				SetTitle()
			end
		end
	end
end

function ns.ToggleMain()
	if main and main:IsShown() and main.shrunk then
		ns.ShowTab(main.tab or "presets") -- shrunk: open it up rather than close it
	elseif main and main:IsShown() then
		main:Hide()
	else
		ns.ShowTab("presets")
	end
end

-- /ec advanced: straight to the Hidden tab.
function ns.ToggleAdvanced()
	if main and main:IsShown() and main.tab == "hidden" then
		main:Hide()
	else
		ns.ShowTab("hidden")
	end
end

----------------------------------------------------------------------
-- Export box: text pre-highlighted, Ctrl+C to copy.
----------------------------------------------------------------------

local EXPORT_HINT = "Everything is selected. Press Ctrl+C, then paste it into a bug report on GitHub."

local function BuildExport()
	exportFrame = MakeWindow("EyeCandyExportFrame", 640, 460, "Copy my settings  |cff9d9d9dCtrl+C to copy, Esc to close|r")
	-- One draw layer above the main window, so the two never interleave.
	exportFrame:SetFrameStrata("FULLSCREEN_DIALOG")

	local scroll = CreateFrame("ScrollFrame", nil, exportFrame, "UIPanelScrollFrameTemplate")
	scroll:SetPoint("TOPLEFT", 14, -32)
	scroll:SetPoint("BOTTOMRIGHT", -34, 44)

	local edit = CreateFrame("EditBox", nil, scroll)
	edit:SetMultiLine(true)
	edit:SetAutoFocus(false)
	edit:SetFontObject(ChatFontNormal)
	edit:SetWidth(580)
	edit:SetMaxLetters(0)
	edit:SetScript("OnEscapePressed", function() exportFrame:Hide() end)
	-- Read only: any typing puts the text back and re-selects it.
	edit:SetScript("OnTextChanged", function(self, userInput)
		if userInput then
			self:SetText(exportFrame.text or "")
			self:HighlightText()
		end
	end)
	edit:SetScript("OnMouseUp", function(self) self:HighlightText() end)
	scroll:SetScrollChild(edit)
	exportFrame.edit = edit

	exportFrame.hint = exportFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
	exportFrame.hint:SetPoint("BOTTOMLEFT", 18, 18)
	exportFrame.hint:SetText(EXPORT_HINT)

	local again = Button(exportFrame, "Select all", 100, function()
		edit:SetFocus()
		edit:HighlightText()
	end)
	again:SetPoint("BOTTOMRIGHT", -16, 12)
end

function ns.ShowExport(includeAll)
	ns.ShowText(ns.BuildExport(includeAll))
end

function ns.ShowText(text, hint)
	if not exportFrame then BuildExport() end
	exportFrame.text = text
	exportFrame.hint:SetText(hint or EXPORT_HINT)
	exportFrame.edit:SetText(exportFrame.text)
	exportFrame:Show()
	exportFrame:Raise()
	exportFrame.edit:SetFocus()
	exportFrame.edit:HighlightText()
	exportFrame.edit:SetCursorPosition(0)
	exportFrame.edit:HighlightText()
end

-- Shared with the other files
ns.MakeWindow = MakeWindow
ns.Button = Button
ns.Tooltip = Tooltip
ns.Label = Label
