-- Eye Candy: the eye test, a part of the Experimental tab. Like at the optician: each round shows one
-- setting two ways, 1 and 2, in the same spot. You flip between them as often as you like, then pick one.
-- After the last round your answers are on, and Save as preset keeps them as a preset of your own (the
-- same save code as Autotune's Save as preset: ns.SaveCurrentAsPreset, then ns.ApplyPresetById).
-- It flips like Compare (Compare.lua): straight to SetCVar, no backup per flip, and none of Eye Candy's
-- own choices change. Your settings from before are saved in EyeCandyDB.eyeTest first. A fight, a loading
-- screen, Options, closing the window or any other Eye Candy change ends it and puts them back. If a test
-- is still saved at the next login, that puts them back too (saved variables are only written at logout or
-- /reload, so after a crash there is usually nothing saved). It never changes settings in a fight.

local _, ns = ...
local ET = {}
ns.EyeTest = ET

-- The rounds, the easiest to see first. set: { cvar = { a, b } }, the two values shown. Which is 1 and
-- which is 2 is picked at random each round, so the order never gives the answer away. look: where to
-- look. words: names for a and b, when the game's own words for the first setting's value don't fit.
-- Each pair is far apart so the difference shows: a low and a high step of the game's own menu, or the
-- two ends of what a Look uses or a little past (Data.lua: glow 0.2 to 1, contrast 50 to 62, field of view
-- 75 to 90).
ET.ROUNDS = {
	{ key = "shadows", name = "Shadows", look = "the shadows on the ground and under things",
		set = { graphicsShadowQuality = { 1, 4 } } },
	{ key = "fov", name = "Field of view", look = "how much of the world fits on the screen",
		set = { cameraFov = { 70, 90 } } },
	{ key = "glow", name = "Glow", look = "bright lights, the sky and shiny things",
		set = { bloomUserMult = { 0.2, 1 } } },
	{ key = "contrast", name = "Contrast", look = "the dark and the bright parts",
		set = { Contrast = { 50, 65 } } },
	{ key = "view", name = "View distance", look = "far away hills, trees and buildings",
		set = { graphicsViewDistance = { 4, 9 } } },
	{ key = "scale", name = "Render scale", look = "edges and fine detail",
		set = { RenderScale = { 0.75, 1 } } },
	{ key = "sharpen", name = "Sharpening", look = "edges and textures close to you",
		set = { ResampleAlwaysSharpen = { 0, 1 }, ResampleSharpness = { -1, 0 } }, words = { "Off", "Strong" } },
	{ key = "ssao", name = "SSAO", look = "the soft shade in corners and where things meet",
		set = { graphicsSSAO = { 0, 3 } } },
	{ key = "grass", name = "Grass", look = "the grass and plants on the ground",
		set = { graphicsGroundClutter = { 3, 9 } } },
	{ key = "fog", name = "Fog and sun rays", look = "haze in the distance and light shining through it",
		set = { graphicsComputeEffects = { 1, 4 } } },
}

ET.random = math.random -- tests pass their own

local test -- nil, or { rounds, i, showing, seen, picks, phase = "round" | "result", live }
local busy = false -- true while the eye test itself sets values, so its own guard lets them through
local situationsWaiting = false -- a zone change came during the test: the switch looks again after it

local function Refresh()
	if ns.RefreshUI then ns.RefreshUI() end
end

-- The status line. kind: "done" (normal), "waiting" (grey) or "refused" (red).
local function Say(kind, text)
	ET.message, ET.messageKind = text, kind
end
ET.Say = Say

-- Chat only when the eye test isn't in front of the player: it says it there.
local function Tell(msg)
	local m = _G.EyeCandyMainFrame
	if m and m.IsShown and m:IsShown() and not m.shrunk and m.tab == "autotune"
		and ns.ExperimentPart and ns.ExperimentPart() == "eye" then return end
	ns.Print(msg)
end

local function SetValues(values)
	busy = true
	for cvar, v in pairs(values) do
		if ns.Exists(cvar) and not ns.Same(ns.GetInfo(cvar), v) then SetCVar(cvar, v) end
	end
	busy = false
end

-- A round's two sides on this PC, or nil when this game lacks one of its settings or both sides come out
-- the same (a menu value is stepped down to what the graphics card supports, render scale to the game's range).
function ET.Resolve(round)
	local a, b = {}, {}
	for cvar, pair in pairs(round.set) do
		if not ns.Exists(cvar) then return nil end
		local va, vb = pair[1], pair[2]
		if cvar == "RenderScale" then
			va, vb = ns.ClampRenderScale(va), ns.ClampRenderScale(vb)
		elseif cvar:find("^graphics") then
			va, vb = ns.ResolveMenuValue(cvar, va), ns.ResolveMenuValue(cvar, vb)
		end
		if va == nil or vb == nil then return nil end
		a[cvar], b[cvar] = va, vb
	end
	for cvar in pairs(a) do
		if not ns.Same(a[cvar], b[cvar]) then return a, b end
	end
	return nil
end

-- What one side of a round is called: its own words, or the game's words for its first setting's value.
local function SideWords(r, values)
	local def = r.def
	if def.words then
		return values == r.a and def.words[1] or def.words[2]
	end
	local cvar = next(def.set)
	local AT = ns.Autotune
	return AT and AT.ValueText(cvar, values[cvar]) or tostring(values[cvar])
end

-- Puts back the settings from before, menu values before hidden ones (a menu value can reset hidden ones),
-- then anything left over. In a fight it waits. Returns true when they are back now.
local function PutBack()
	local saved = ns.db and ns.db.eyeTest
	if not saved then return true end
	if InCombatLockdown() then
		saved.afterCombat = true
		return false
	end
	busy = true
	local ok, err = pcall(ns.ApplyValues, saved.before, false)
	busy = false
	SetValues(saved.before)
	ns.db.eyeTest = nil
	-- The city or instance switch waited while the test had your settings: it looks again now.
	if situationsWaiting then
		situationsWaiting = false
		if ns.UpdateSituations then ns.UpdateSituations() end
	end
	if not ok then error(err, 0) end
	return true
end

local function BeginRound()
	test.seen, test.showing = {}, nil
	ET.Show(1)
end

function ET.IsOn() return test ~= nil and test.live end

-- The test as it stands, for the tab: nil, or { phase, i, count, round, showing, seen, picks, live }.
function ET.State()
	if not test then return nil end
	return {
		phase = test.phase, i = test.i, count = #test.rounds, round = test.rounds[test.i],
		showing = test.showing, seen = test.seen, picks = test.picks, live = test.live,
	}
end

-- Starts the test. Returns true, or nil and a plain reason.
function ET.Start()
	if test and test.live then return nil, "The eye test is already on." end
	if InCombatLockdown() then return nil, "The eye test can't start in a fight. Try again after it." end
	local AT = ns.Autotune
	if AT and AT.IsRunning() then return nil, "Autotune is running. Stop it first." end
	if ns.db.autotune then
		return nil, "Autotune still has your settings. Save its result or press Back to before Autotune first."
	end
	if ns.IsComparing and ns.IsComparing() then
		local ok, err = ns.StopCompare()
		if not ok then return nil, err end
	end
	local rounds = {}
	for _, def in ipairs(ET.ROUNDS) do
		local a, b = ET.Resolve(def)
		if a then
			local swap = ET.random(2) == 2
			rounds[#rounds + 1] = { def = def, a = a, b = b, [1] = swap and b or a, [2] = swap and a or b }
		end
	end
	if #rounds == 0 then return nil, "This game has none of the settings the eye test uses." end
	-- Every setting on Eye Candy's list, and each round's, so the way back covers them all.
	local before = {}
	for _, cvar in ipairs(ns.AllManagedCVars()) do
		local v = ns.GetInfo(cvar)
		if v ~= nil then before[cvar] = v end
	end
	for _, r in ipairs(rounds) do
		for cvar in pairs(r.a) do before[cvar] = before[cvar] or ns.GetInfo(cvar) end
	end
	ns.db.eyeTest = { before = before }
	test = { rounds = rounds, i = 1, picks = {}, phase = "round", live = true, before = before }
	Say(nil, nil)
	ET.HookWindow()
	BeginRound()
	return true
end

-- Shows side n (1 or 2) of this round.
function ET.Show(n)
	if not (test and test.live and test.phase == "round") then return nil end
	if InCombatLockdown() then return nil, "You can't change settings in a fight. Try again after it." end
	local r = test.rounds[test.i]
	SetValues(r[n])
	test.showing = n
	test.seen[n] = true
	Refresh()
	return true
end

-- Answers this round: 1, 2, or "same" (your own setting stays). The answer stays on for the rounds after it.
-- Returns true, or nil and a plain reason.
function ET.Answer(choice)
	if not (test and test.live and test.phase == "round") then return nil end
	if InCombatLockdown() then return nil, "You can't change settings in a fight. Try again after it." end
	if not (test.seen[1] and test.seen[2]) then return nil, "Look at both first: press Show 1 and Show 2." end
	local r = test.rounds[test.i]
	local keep
	if choice == 1 or choice == 2 then
		keep = r[choice]
	else
		keep = {}
		for cvar in pairs(r.a) do keep[cvar] = test.before[cvar] end
	end
	test.picks[#test.picks + 1] = { round = r, choice = choice, values = keep }
	-- Your settings from before with the answers on top, menu values first: a menu value the round flipped can
	-- have reset hidden ones, and those come back too.
	local now = {}
	for cvar, v in pairs(test.before) do now[cvar] = v end
	for cvar, v in pairs(ET.Answers()) do now[cvar] = v end
	busy = true
	local ok, err = pcall(ns.ApplyValues, now, false)
	busy = false
	SetValues(now)
	if not ok then error(err, 0) end
	if test.i < #test.rounds then
		test.i = test.i + 1
		BeginRound()
	else
		test.phase, test.showing = "result", nil
		Tell("Eye test done. Your answers are on. Press Save as preset on the Experimental tab to keep them.")
		Refresh()
	end
	return true
end

-- Every answer's values together: the preset the test makes, on top of your own settings. "Same to me" adds
-- nothing, so your own value stays (in a city, your own and not the one the city switch lowered).
function ET.Answers()
	local out = {}
	for _, pick in ipairs(test and test.picks or {}) do
		if pick.choice ~= "same" then
			for cvar, v in pairs(pick.values) do out[cvar] = v end
		end
	end
	return out
end

-- One line an answer, for the result and the preset's note.
function ET.PickLines()
	local lines = {}
	for _, pick in ipairs(test and test.picks or {}) do
		local r = pick.round
		if pick.choice == "same" then
			lines[#lines + 1] = r.def.name .. ": the same to you, so yours stays"
		else
			lines[#lines + 1] = r.def.name .. ": " .. SideWords(r, pick.values)
		end
	end
	return lines
end

-- Ends the test and puts your settings back. why: shown to the player. A test that reached its answers
-- keeps them, so Save as preset still works.
function ET.Stop(why)
	if not (test and test.live) then return end
	test.live = false
	local back = PutBack()
	local kept = test.phase == "result"
	if not kept then test = nil end
	local lead = "Eye test ended because " .. why .. ". "
	if back then
		Say("done", lead .. "Your settings are back as they were." .. (kept and " Save as preset still saves your answers." or ""))
	else
		Say("waiting", lead .. "Your settings come back when the fight ends.")
	end
	Tell(ET.message)
	Refresh()
end

-- At the answers: puts your settings back and forgets the answers.
function ET.Back()
	if not test then return nil end
	if not PutBack() then
		return nil, "You can't go back in a fight. Your settings go back when it ends."
	end
	test = nil
	Say("done", "Eye test: your settings are back as they were.")
	Refresh()
	return true
end

-- Saves the answers as your own preset and puts it on. Returns the preset, or nil and a plain reason.
function ET.Save(name)
	if not (test and test.phase == "result") then return nil end
	if InCombatLockdown() then return nil, "Can't save in a fight. Try again after it." end
	-- Saved first, so a refused name changes nothing. The preset is your own settings from before (a menu value
	-- flipped in a round can reset hidden ones; in a city, yours from before the city switch lowered them)
	-- with the answers on top.
	local p, err = ns.SaveCurrentAsPreset(name)
	if not p then return nil, err end
	for cvar, v in pairs(test.before) do
		if p.values[cvar] ~= nil then
			if ns.SituationValue then v = ns.SituationValue(cvar, v) end
			p.values[cvar] = tostring(v)
		end
	end
	for cvar, v in pairs(ET.Answers()) do p.values[cvar] = tostring(v) end
	p.desc = "Made by the eye test. " .. table.concat(ET.PickLines(), ". ") .. "."
	-- Your settings back first, so the preset's step in today's list holds yours, not the test's.
	test.live = false
	PutBack()
	test = nil
	if ns.ApplyPresetById(p.id) then
		Say("done", "Your answers are saved as your preset \"" .. p.name .. "\" and on now.")
	else
		Say("refused", "Your preset \"" .. p.name .. "\" is saved, but it couldn't be put on. Pick it on the Presets tab to try again.")
	end
	Refresh()
	return p
end

-- A free name for the preset: "Eye test", then "Eye test (2)" and on.
function ET.FreeName()
	local name, n = "Eye test", 1
	while ns.FindPresetByName(name) do
		n = n + 1
		name = "Eye test (" .. n .. ")"
	end
	return name
end

-- One short line for the window's title and the Presets card while the eye test has your settings, or nil.
function ET.Note()
	if test and test.live and test.phase == "round" then return "Eye test is changing your settings" end
	if test and test.live then return "Eye test's answers are on, not saved yet" end
	local saved = ns.db and ns.db.eyeTest
	if saved and saved.afterCombat then return "Eye test puts your settings back after the fight" end
end

local runningNote = ns.RunningNote
ns.RunningNote = function(...)
	local note = ET.Note()
	if note then return note end
	if runningNote then return runningNote(...) end
end

-- Any other Eye Candy change ends the test first, so the way back stays right. A backup too: it must hold
-- your settings, not the test's. So does a preset's step in today's list (NoteBeforePreset, which a preset
-- calls before TakeBackup), Back on a step (RestoreStep), /ec back (GoBack) and a restore.
for _, name in ipairs({ "ApplyAll", "ApplyValues", "CreateBackup", "TakeBackup", "NoteBeforePreset",
	"RestoreStep", "GoBack", "RestoreBackupById" }) do
	local orig = ns[name]
	if orig then
		ns[name] = function(...)
			if test and test.live and not busy then ET.Stop("something else changed your settings") end
			return orig(...)
		end
	end
end

-- Compare and Autotune change settings too, and record "now" or "before" first: neither starts during the test.
local toggleCompare = ns.ToggleCompare
if toggleCompare then
	ns.ToggleCompare = function(...)
		if test and test.live then return nil, "Compare can't run during the eye test. Finish or stop the test first." end
		return toggleCompare(...)
	end
end
if ns.Autotune then
	local start = ns.Autotune.Start
	ns.Autotune.Start = function(...)
		if test and test.live then return false, "Autotune can't run during the eye test. Finish or stop the test first." end
		return start(...)
	end
end

-- The city and instance switch (Situations.lua) waits while the test has your settings, and looks again once
-- they are back: otherwise it would lower the test's values and then lose track of yours.
if ns.UpdateSituations then
	local update = ns.UpdateSituations
	ns.UpdateSituations = function(...)
		if ns.db and ns.db.eyeTest then
			situationsWaiting = true
			return
		end
		return update(...)
	end
end

-- The patch warning (PatchWatch.lua) copies your settings at logout, maybe before the test puts them back, and
-- the FPS reader (FPS.lua) measures a preset you just put on. Neither takes the test's values for yours.
if ns.PatchWatch and ns.PatchWatch.Own then
	local own = ns.PatchWatch.Own
	ns.PatchWatch.Own = function(cvar, value)
		local saved = ns.db and ns.db.eyeTest
		if value ~= nil and saved and type(saved.before) == "table" and saved.before[cvar] ~= nil then
			value = saved.before[cvar]
		end
		return own(cvar, value)
	end
end
if ns.FPS and ns.FPS.Still then
	local still = ns.FPS.Still
	ns.FPS.Still = function(...)
		if test and test.live then return false end
		return still(...)
	end
end

-- Closing the window ends the test (Peek hides it too, and that doesn't). Options can change settings.
local hookedWindow, hookedOptions = false, false
function ET.HookWindow()
	local main = _G.EyeCandyMainFrame
	if not hookedWindow and main and main.HookScript then
		hookedWindow = true
		main:HookScript("OnHide", function()
			if test and test.live and not (ns.IsPeeking and ns.IsPeeking()) then ET.Stop("you closed the window") end
		end)
	end
	if not hookedOptions and SettingsPanel and SettingsPanel.HookScript then
		hookedOptions = true
		SettingsPanel:HookScript("OnShow", function()
			if test and test.live then
				ET.Stop("Options opened")
				-- Core's own hook noted the game menu's values before this one ran, so it noted the test's. Note
				-- them again now yours are back, or closing Options would take yours as changes made there.
				if ns.SnapshotGameMenu then ns.SnapshotGameMenu() end
			end
		end)
	end
end

local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(_, event, isLogin, isReload)
	local saved = ns.db and ns.db.eyeTest
	if event == "PLAYER_REGEN_DISABLED" then
		-- Lockdown starts just after this event, so settings can still go back here.
		if test and test.live then ET.Stop("a fight started") end
	elseif event == "PLAYER_LEAVING_WORLD" or event == "PLAYER_LOGOUT" then
		if test and test.live then ET.Stop("a loading screen came up") end
	elseif event == "PLAYER_REGEN_ENABLED" then
		if saved and saved.afterCombat and not (test and test.live) and PutBack() then
			Say("done", "Eye test: the fight is over, so your settings are back as they were.")
			Tell(ET.message)
			Refresh()
		end
	elseif event == "PLAYER_ENTERING_WORLD" then
		-- A test left over from before a crash: put the settings from before back.
		if (isLogin or isReload) and saved and not test then
			if PutBack() then
				Say("done", "The eye test didn't finish last time, so your settings went back as they were.")
				Tell(ET.message)
			end
		end
	end
end)
for _, event in ipairs({ "PLAYER_ENTERING_WORLD", "PLAYER_LEAVING_WORLD", "PLAYER_LOGOUT",
	"PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED" }) do
	pcall(events.RegisterEvent, events, event)
end

----------------------------------------------------------------------
-- The eye test's part of the Experimental tab
----------------------------------------------------------------------

local W = ns.ROW_W - 16
local GREY, RED, GOLD, WHITE = "|cff9d9d9d", "|cffff4040", "|cffffd100", "|cffffffff"
local ROW, GROUP = 4, 16

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

local function Small(b)
	b:SetHeight(20)
	if b.SetNormalFontObject then b:SetNormalFontObject("GameFontNormalSmall") end
end

ET.WHY = "Like at the optician: which is better, 1 or 2? Each round shows one setting two ways, in the same spot. "
	.. "Flip between them as often as you like, then pick one. After the last round, Save as preset keeps your answers as a preset of your own."
ET.HOW = "Stand still and leave the camera where it is, so only the setting changes. "
	.. "The test changes your settings while it runs. A fight, a loading screen, Options or closing this window ends it and puts your settings back."

local function Build(page, holder)
	local c = ns.ScrollPage(holder, 0)
	c:SetHeight(400)
	local e = { content = c }
	page.eye = e
	e.head, e.headH = ns.Header(c, "Eye test", "Experimental")
	e.head:SetPoint("TOPLEFT", 0, 0)
	e.why = Text(c)
	e.why:SetText(ET.WHY)
	Under(e.why, e.head, 4)
	e.how = Text(c, "GameFontDisableSmall")
	e.how:SetText(ET.HOW)
	Under(e.how, e.why, 0, 8)
	e.start = ns.Button(c, "Start eye test", 130, function()
		local ok, err = ET.Start()
		if not ok and err then
			Say("refused", err)
			Refresh()
		end
	end)
	Under(e.start, e.how, 0, 8)
	ns.Tooltip(e.start, "Start eye test", "Changes your settings while you test. Yours are saved first, and come back if the test ends.")
	e.status = Text(c)
	Under(e.status, e.start, 0, 8)

	-- The round: which setting, where to look, the two sides and the three answers.
	e.roundHead, e.headH2 = ns.Header(c, "Round")
	Under(e.roundHead, e.status, -4, GROUP)
	e.roundText = Text(c)
	Under(e.roundText, e.roundHead, 4)
	e.show = {}
	for n = 1, 2 do
		local b = ns.Button(c, "Show " .. n, 90, function() ET.Show(n) end)
		if n == 1 then Under(b, e.roundText, 0, 8) else b:SetPoint("LEFT", e.show[1], "RIGHT", ROW, 0) end
		ns.Tooltip(b, "Show " .. n, "Puts side " .. n .. " on, so you can see it. Flip as often as you like.")
		b.label = "Show " .. n
		e.show[n] = b
	end
	e.picks = {}
	local answers = { { 1, "1 is better" }, { 2, "2 is better" }, { "same", "Same to me" } }
	for i, a in ipairs(answers) do
		local b = ns.Button(c, a[2], 110, function()
			local ok, err = ET.Answer(a[1])
			if not ok and err then
				Say("refused", err)
				Refresh()
			end
		end)
		if i == 1 then Under(b, e.show[1], 0, 8) else b:SetPoint("LEFT", e.picks[i - 1], "RIGHT", ROW, 0) end
		b.choice, b.label = a[1], a[2]
		e.picks[i] = b
	end
	ns.Tooltip(e.picks[1], "1 is better", "Keeps side 1 on and goes to the next round.")
	ns.Tooltip(e.picks[2], "2 is better", "Keeps side 2 on and goes to the next round.")
	ns.Tooltip(e.picks[3], "Same to me", "Keeps your own setting and goes to the next round.")
	e.pickText = Text(c, "GameFontDisableSmall")
	Under(e.pickText, e.picks[1], 0, 8)
	e.stop = ns.Button(c, "Stop eye test", 110, function() ET.Stop("you pressed Stop") end)
	Small(e.stop)
	Under(e.stop, e.pickText, 0, 8)
	ns.Tooltip(e.stop, "Stop eye test", "Ends the test now and puts your settings back as they were.")

	-- The answers: what you picked, a name, Save as preset and Back to before eye test.
	e.resultHead, e.headH3 = ns.Header(c, "Your answers")
	Under(e.resultHead, e.status, -4, GROUP)
	e.result = Text(c)
	Under(e.result, e.resultHead, 4)
	e.nameLabel = Text(c, "GameFontDisableSmall")
	e.nameLabel:SetText("Name of the preset")
	Under(e.nameLabel, e.result, 0, 8)
	e.name = CreateFrame("EditBox", nil, c, "InputBoxTemplate")
	e.name:SetSize(220, 24)
	e.name:SetAutoFocus(false)
	if e.name.SetMaxLetters then e.name:SetMaxLetters(40) end
	Under(e.name, e.nameLabel, 6, ROW)
	local function Save()
		local p, err = ET.Save(e.name:GetText())
		if not p and err then
			e.saveRefused = err
			Refresh()
		end
	end
	e.name:SetScript("OnEnterPressed", Save)
	e.name:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
	e.save = ns.Button(c, "Save as preset", 130, Save)
	e.save:SetPoint("LEFT", e.name, "RIGHT", 8, 0)
	ns.Tooltip(e.save, "Save as preset", "Saves your answers as your own preset and puts it on, like any preset. Back to before on the Presets tab undoes it.")
	e.back = ns.Button(c, "Back to before eye test", 160, function()
		local ok, err = ET.Back()
		if not ok and err then
			Say("refused", err)
			Refresh()
		end
	end)
	Small(e.back)
	e.back:SetPoint("LEFT", e.save, "RIGHT", 16, 0)
	ns.Tooltip(e.back, "Back to before eye test", "Puts your settings back as they were before the eye test, and forgets your answers.", "ANCHOR_LEFT")
	e.saveText = Text(c)
	Under(e.saveText, e.name, -6, 8)
	ET.HookWindow()
end

local function StatusText()
	local text = ET.message or ""
	if text == "" then return "" end
	if ET.messageKind == "refused" then return RED .. text .. "|r" end
	if ET.messageKind == "waiting" then return GREY .. text .. "|r" end
	return text
end

local function ResultText(st)
	local lines = {}
	if st.live then
		lines[1] = "Your answers are on now. Save as preset keeps them. Back to before eye test undoes them."
	else
		lines[1] = "Your settings are back as they were. Save as preset still saves your answers and puts them on."
	end
	for _, line in ipairs(ET.PickLines()) do lines[#lines + 1] = line end
	return table.concat(lines, "\n")
end

local function Refresh_(page)
	local e = page.eye
	local st = ET.State()
	local inRound = st and st.phase == "round" and st.live
	local inResult = st and st.phase == "result"
	-- Start shows unless the test has your settings. Answers kept after an ended test stay until a new start.
	local canStart = not (st and st.live)
	e.start:SetShown(canStart)
	-- A hidden Start still holds its place, so the status line moves up under the help text.
	e.status:ClearAllPoints()
	Under(e.status, canStart and e.start or e.how, 0, 8)
	local status = StatusText()
	e.status:SetText(status)
	for _, f in ipairs({ e.roundHead, e.roundText, e.show[1], e.show[2], e.picks[1], e.picks[2], e.picks[3], e.pickText, e.stop }) do
		f:SetShown(inRound and true or false)
	end
	for _, f in ipairs({ e.resultHead, e.result, e.nameLabel, e.name, e.save, e.back, e.saveText }) do
		f:SetShown(inResult and true or false)
	end
	local height = e.headH + ROW + TextH(e.why, ET.WHY) + 8 + TextH(e.how, ET.HOW)
	if canStart then height = height + 8 + 24 end
	height = height + 8 + TextH(e.status, status)
	if inRound then
		local r = st.round
		e.roundHead.label:SetText(string.format("Round %d of %d: %s", st.i, st.count, r.def.name))
		local roundText = "Look at " .. r.def.look .. ". Showing " .. (st.showing or 1) .. "."
		e.roundText:SetText(roundText)
		for n = 1, 2 do
			-- The side on now is gold (rule 20: the selected thing).
			e.show[n]:SetText((st.showing == n and GOLD or WHITE) .. e.show[n].label .. "|r")
			e.show[n].chosen = st.showing == n
		end
		local both = st.seen[1] and st.seen[2]
		for _, b in ipairs(e.picks) do b:SetEnabled(both and true or false) end
		local pickText = both and "Pick the one you like. Same to me keeps your own setting."
			or "Look at both, then pick. Press Show 2 to see the other side."
		e.pickText:SetText(pickText)
		height = height + GROUP + e.headH2 + ROW + TextH(e.roundText, roundText) + 8 + 24 + 8 + 24
			+ 8 + TextH(e.pickText, pickText) + 8 + 20
	elseif inResult then
		local text = ResultText(st)
		e.result:SetText(text)
		if not e.nameFilled then
			e.name:SetText(ET.FreeName())
			e.nameFilled = true
		end
		e.back:SetShown(st.live and true or false)
		local refused = e.saveRefused and (RED .. e.saveRefused .. "|r") or ""
		e.saveText:SetText(refused)
		height = height + GROUP + e.headH3 + ROW + TextH(e.result, text) + 8 + 12 + ROW + 24 + 8 + TextH(e.saveText, refused)
	end
	if not inResult then e.nameFilled, e.saveRefused = nil, nil end
	e.content:SetHeight(height + 16)
end

if ns.AddExperiment then
	ns.AddExperiment({
		key = "eye", name = "Eye test", build = Build, refresh = Refresh_,
		tip = "Which is better, 1 or 2? Your answers make a preset of your own.",
	})
end
