-- Eye Candy: Peek. Hides the game's UI and Eye Candy's windows so you can see the world,
-- with one small Back button. Back, Esc or /ec peek again puts everything back.
--
-- SetUIVisibility(false) is what Alt+Z calls (TOGGLEUI in Blizzard_FrameXML/Bindings_Standard.xml,
-- Gethe/wow-ui-source branch forever). It hides UIParent; the binding then reads UIParent:IsShown()
-- to know which way to toggle. Frames parented to WorldFrame stay visible while the UI is hidden:
-- Blizzard's TimerTracker moves itself to WorldFrame for spectator mode for that reason
-- (Blizzard_FrameXML/Timer.lua), and warcraft.wiki.gg's WorldFrame page says the same.
-- Not tested in game: that the Back button on WorldFrame can be clicked.
-- When the UI is hidden, Esc shows UIParent and calls SetUIVisibility(true) itself
-- (Blizzard_Game/Shared/Game.lua), so Peek notices Esc and Alt+Z through UIParent's OnShow.

local ADDON, ns = ...

-- Eye Candy's windows, by name. Another file can add its window's name here.
ns.PEEK_WINDOWS = ns.PEEK_WINDOWS or {
	"EyeCandyMainFrame", "EyeCandyExportFrame", "EyeCandyAskFrame", "EyeCandyPresetMenu",
}

local peeking = false
local hidUI = false -- true when SetUIVisibility(false) worked, false when only our windows are hidden
local hidden = {} -- the windows that were open, to show again
local back -- the Back bar
local hooked = false

local EndPeek

local function HookUIParent()
	if hooked or not (UIParent and UIParent.HookScript) then return end
	hooked = true
	-- Esc or Alt+Z brought the game's UI back: finish the peek (Blizzard already showed the UI).
	UIParent:HookScript("OnShow", function()
		if peeking then EndPeek(true) end
	end)
end

local function BackBar()
	if back then return back end
	back = CreateFrame("Frame", "EyeCandyPeekFrame", WorldFrame, "BackdropTemplate")
	back:SetSize(360, 44)
	back:SetPoint("TOP", 0, -20)
	back:SetFrameStrata("FULLSCREEN_DIALOG")
	if back.SetBackdrop then
		back:SetBackdrop({
			bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
			edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
			tile = true, tileSize = 16, edgeSize = 16,
			insets = { left = 4, right = 4, top = 4, bottom = 4 },
		})
		back:SetBackdropColor(0, 0, 0, 0.7)
	end
	back:EnableMouse(true)
	local text = back:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	local hasCompare = ns.ToggleCompare ~= nil
	text:SetPoint("LEFT", 12, hasCompare and -9 or 0)
	text:SetPoint("RIGHT", hasCompare and -224 or -104, hasCompare and -9 or 0)
	text:SetWordWrap(false) -- one line each, so a long one never runs into the label above
	back.text = text
	local button = CreateFrame("Button", nil, back, "UIPanelButtonTemplate")
	button:SetSize(90, 24)
	button:SetPoint("RIGHT", -8, 0)
	button:SetText("Back")
	button:SetScript("OnClick", function() ns.TogglePeek() end)
	back.button = button
	if hasCompare then
		back:SetSize(500, 52)
		-- What is on screen while comparing (empty otherwise).
		local label = back:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
		label:SetPoint("LEFT", 12, 9)
		label:SetPoint("RIGHT", -224, 9)
		label:SetJustifyH("LEFT")
		label:SetWordWrap(false)
		back.label = label
		-- Flips the settings without leaving the peek. Says what a click shows next.
		local compare = CreateFrame("Button", nil, back, "UIPanelButtonTemplate")
		compare:SetSize(120, 24)
		compare:SetPoint("RIGHT", button, "LEFT", -6, 0)
		compare:SetScript("OnClick", function()
			if not ns.ToggleCompare then return end
			local ok, err = ns.ToggleCompare()
			if not ok and err then ns.Print(err) end
			ns.RefreshPeekBar()
		end)
		back.compare = compare
	end
	-- In the fallback (game UI still shown), Esc closes this like any window.
	back:SetScript("OnHide", function()
		if peeking then EndPeek(false) end
	end)
	tinsert(UISpecialFrames, "EyeCandyPeekFrame")
	back:Hide()
	return back
end

-- Redraws the bar's Compare button and label. Compare.lua calls this whenever compare flips or ends.
function ns.RefreshPeekBar()
	if not (back and back.compare) then return end
	local label = ns.CompareLabel and ns.CompareLabel()
	-- About 40 characters fit; a long preset name is cut with "..." (UI.lua, whole characters).
	back.label:SetText(label and ns.ShortName and ns.ShortName(label, 40) or label or "")
	back.compare:SetText((label and label ~= "Showing: now") and "Show now" or "Show before")
end

-- Same size as Eye Candy's other windows: WorldFrame doesn't use the UI scale, UIParent does.
local function MatchUIScale(frame)
	if not (UIParent and WorldFrame and UIParent.GetEffectiveScale and WorldFrame.GetEffectiveScale) then return end
	local ui, world = UIParent:GetEffectiveScale(), WorldFrame:GetEffectiveScale()
	if type(ui) == "number" and type(world) == "number" and ui > 0 and world > 0 then frame:SetScale(ui / world) end
end

-- uiAlreadyBack: Blizzard put the UI back itself (Esc, Alt+Z), so don't show it again.
EndPeek = function(uiAlreadyBack)
	if not peeking then return end
	if hidUI and not uiAlreadyBack then
		if UIParent and not UIParent:IsShown() then pcall(UIParent.Show, UIParent) end
		if SetUIVisibility then pcall(SetUIVisibility, true) end
		if UIParent and not UIParent:IsShown() then
			-- Combat had already locked the UI. Keep the Back bar up with a way out; Esc and Alt+Z are
			-- Blizzard's own keys, so they still work, and the end of the fight tries again.
			if back then
				back.text:SetText("Combat locked the screen. Press Esc or Alt+Z.")
				back:Show()
			end
			return false
		end
	end
	peeking = false
	if back then back:Hide() end
	hidUI = false
	for _, frame in ipairs(hidden) do frame:Show() end
	wipe(hidden)
	return true
end

-- noBar: hide the screen with no Back bar (photo mode, so the bar isn't in the picture). Then the game's UI
-- must be hidden, or nothing stays hidden and it returns nil and a reason.
local function StartPeek(noBar)
	if InCombatLockdown() then
		return nil, "Can't hide the screen in combat. Try again after the fight."
	end
	peeking = true
	wipe(hidden)
	for _, name in ipairs(ns.PEEK_WINDOWS) do
		local frame = _G[name]
		if frame and frame.IsShown and frame:IsShown() then
			hidden[#hidden + 1] = frame
			frame:Hide()
		end
	end
	hidUI = false
	-- Already hidden with Alt+Z: leave it to the player, so Back doesn't bring back a UI they hid.
	if type(SetUIVisibility) == "function" and UIParent and UIParent:IsShown() then
		HookUIParent()
		local ok = pcall(SetUIVisibility, false)
		if ok and not UIParent:IsShown() then
			hidUI = true
		elseif ok then
			pcall(SetUIVisibility, true) -- it ran but the UI is still there: leave it as it was
		end
	end
	if noBar then
		HookUIParent() -- Esc and Alt+Z still end it, as they do with the bar
		if hidUI or not (UIParent and UIParent:IsShown()) then return true end
		peeking = false
		for _, frame in ipairs(hidden) do frame:Show() end
		wipe(hidden)
		return nil, "Couldn't hide the game's UI."
	end
	if not hidUI and UIParent and UIParent:IsShown() then
		ns.Print("couldn't hide the game's UI, so only Eye Candy's windows are hidden. Press Back or Esc to bring them back.")
	end
	local bar = BackBar()
	bar.text:SetText("Esc also works")
	ns.RefreshPeekBar()
	MatchUIScale(bar)
	bar:Show()
	return true
end

-- Returns true, or nil and a plain reason.
function ns.TogglePeek()
	if peeking then
		if EndPeek(false) then return true end
		return nil, "Combat locked the screen. Press Esc or Alt+Z."
	end
	return StartPeek()
end

function ns.IsPeeking()
	return peeking
end

-- Photo mode (PhotoMode.lua): hides the screen with no Back bar. It ends with ns.TogglePeek(), or Esc.
-- Returns true, or nil and a plain reason.
function ns.PeekWithoutBar()
	if peeking then return nil, "Peek is already on." end
	return StartPeek(true)
end

function ns.PeekSlash()
	local ok, err = ns.TogglePeek()
	if not ok and err then ns.Print(err) end
end

-- A hidden UI in combat is dangerous: put it back the moment combat starts.
-- PLAYER_REGEN_DISABLED fires before the combat lockdown starts, so the UI can still be shown.
local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_REGEN_DISABLED")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:SetScript("OnEvent", function(_, event)
	if event == "PLAYER_REGEN_DISABLED" and peeking then
		if EndPeek(false) then ns.Print("combat started, so your UI is back.") end
	elseif event == "PLAYER_REGEN_ENABLED" and peeking then
		EndPeek(false) -- combat locked the UI before Peek could bring it back: try again now
	end
end)
