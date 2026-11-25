-- Eye Candy: minimap button and the game's Options > AddOns entry.
-- The button is self-made rather than LibDBIcon: Eye Candy bundles no libraries, and LibDBIcon would
-- need four (LibStub, CallbackHandler, LibDataBroker, LibDBIcon) for one button. The layout copies
-- LibDBIcon's look so it sits with other addons' buttons. Saved in EyeCandyDB.minimap { hide, angle }.

local _, ns = ...

local ICON = "Interface\\Icons\\INV_Misc_Spyglass_03"
local button

local function MinimapDB()
	ns.db.minimap = ns.db.minimap or {}
	if ns.db.minimap.angle == nil then ns.db.minimap.angle = 225 end
	return ns.db.minimap
end

-- Place the button on the minimap's edge at `angle` degrees (0 = right, 90 = top).
function ns.PlaceMinimapButton(angle)
	if not (button and Minimap) then return end
	local a = math.rad(angle)
	local radius = ((Minimap:GetWidth() or 140) / 2) + 5
	button:ClearAllPoints()
	button:SetPoint("CENTER", Minimap, "CENTER", math.cos(a) * radius, math.sin(a) * radius)
end

-- The angle from the minimap's centre to the cursor, in degrees.
local function CursorAngle()
	local mx, my = Minimap:GetCenter()
	local px, py = GetCursorPosition()
	local scale = Minimap:GetEffectiveScale() or 1
	if not (mx and px) then return MinimapDB().angle end
	return math.deg(math.atan2(py / scale - my, px / scale - mx)) % 360
end

local function OnDragUpdate()
	local angle = CursorAngle()
	MinimapDB().angle = angle
	ns.PlaceMinimapButton(angle)
end

function ns.CreateMinimapButton()
	if button or not Minimap then return button end
	button = CreateFrame("Button", "EyeCandyMinimapButton", Minimap)
	button:SetSize(31, 31)
	button:SetFrameStrata("MEDIUM")
	button:SetFrameLevel(8)
	button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	button:RegisterForDrag("LeftButton")
	button:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")

	local overlay = button:CreateTexture(nil, "OVERLAY")
	overlay:SetSize(50, 50)
	overlay:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
	overlay:SetPoint("TOPLEFT")
	local background = button:CreateTexture(nil, "BACKGROUND")
	background:SetSize(24, 24)
	background:SetTexture("Interface\\Minimap\\UI-Minimap-Background")
	background:SetPoint("CENTER")
	local icon = button:CreateTexture(nil, "ARTWORK")
	icon:SetSize(18, 18)
	icon:SetTexture(ICON)
	icon:SetPoint("CENTER")
	button.icon = icon

	button:SetScript("OnClick", function(_, mouse)
		if mouse == "RightButton" then
			ns.ShowTab("backups")
		else
			ns.ToggleMain()
		end
	end)
	button:SetScript("OnDragStart", function(self)
		self:LockHighlight()
		self:SetScript("OnUpdate", OnDragUpdate)
	end)
	button:SetScript("OnDragStop", function(self)
		self:SetScript("OnUpdate", nil)
		self:UnlockHighlight()
	end)
	ns.Tooltip(button, "Eye Candy", "Click: open Eye Candy.\nRight-click: open Backups.\nDrag: move this button.\n|cff9d9d9dHide it with /ec minimap, or in Options > AddOns > Eye Candy.|r")

	ns.PlaceMinimapButton(MinimapDB().angle)
	button:SetShown(not MinimapDB().hide)
	return button
end

function ns.SetMinimapButtonShown(show)
	MinimapDB().hide = not show
	if show then ns.CreateMinimapButton() end
	if button then button:SetShown(show) end
	if ns.optionsPanel and ns.optionsPanel.minimapCheck then ns.optionsPanel.minimapCheck:SetChecked(show) end
end

-- The game's addon menu by the minimap (the .toc names this function in AddonCompartmentFunc).
-- Works even with the minimap button hidden. Left click opens the window, right click opens Backups.
function EyeCandy_OnAddonCompartmentClick(_, mouse)
	if mouse == "RightButton" then
		ns.ShowTab("backups")
	else
		ns.ToggleMain()
	end
end

-- One line for /ec report: what the button's setting says and what the button is doing now.
function ns.MinimapReportLine()
	local db = ns.db and ns.db.minimap or {}
	local made, shown, parent = "no", "no", "none"
	if button then
		made = "yes"
		shown = button:IsShown() and "yes" or "no"
		local p = button:GetParent()
		parent = (p and p.GetName and p:GetName()) or (p and "unnamed frame") or "none"
	end
	return string.format("Minimap button: set to %s, made %s, shown %s, on %s. Saved settings at login: %s.",
		db.hide and "hidden" or "shown", made, shown, parent,
		ns.dbStartedEmpty and "missing, so it started fresh" or "loaded")
end

function ns.ToggleMinimapButton()
	local show = MinimapDB().hide == true
	ns.SetMinimapButtonShown(show)
	ns.Print(show and "minimap button shown." or "minimap button hidden. /ec minimap brings it back.")
end

----------------------------------------------------------------------
-- Options > AddOns > Eye Candy
----------------------------------------------------------------------

function ns.CreateOptionsPanel()
	if ns.optionsPanel or not (Settings and Settings.RegisterCanvasLayoutCategory and Settings.RegisterAddOnCategory) then return end
	local panel = CreateFrame("Frame")
	panel.name = "Eye Candy"
	ns.optionsPanel = panel

	local title = ns.Label(panel, "Eye Candy", "GameFontNormalLarge")
	title:SetPoint("TOPLEFT", 16, -16)
	local text = ns.Label(panel, "Graphics presets, Looks, hidden graphics settings and backups.\nOpen the window here, with /ec, or with the minimap button.", "GameFontHighlight")
	text:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -10)
	text:SetWidth(560)

	local open = ns.Button(panel, "Open Eye Candy", 160, function()
		if SettingsPanel and SettingsPanel:IsShown() then
			if HideUIPanel then HideUIPanel(SettingsPanel) else SettingsPanel:Hide() end
		end
		ns.ShowTab("presets")
	end)
	open:SetPoint("TOPLEFT", text, "BOTTOMLEFT", 0, -16)

	local check = CreateFrame("CheckButton", nil, panel, "UICheckButtonTemplate")
	check:SetPoint("TOPLEFT", open, "BOTTOMLEFT", -4, -12)
	check:SetChecked(not MinimapDB().hide)
	check:SetScript("OnClick", function(self) ns.SetMinimapButtonShown(self:GetChecked() and true or false) end)
	local checkText = ns.Label(panel, "Show the minimap button", "GameFontHighlight")
	checkText:SetPoint("LEFT", check, "RIGHT", 2, 0)
	panel.minimapCheck = check

	local category = Settings.RegisterCanvasLayoutCategory(panel, panel.name)
	Settings.RegisterAddOnCategory(category)
	ns.optionsCategory = category
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:SetScript("OnEvent", function()
	if not ns.db then return end
	ns.CreateMinimapButton()
	ns.CreateOptionsPanel()
end)
