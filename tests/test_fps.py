"""Live FPS (FPS.lua): the reader runs only while watched, the bar number is smoothed and redrawn only
when it changes, it stops while the window is closed, and each preset remembers the FPS it gave once
you stand still out of a fight. Run: python tests/test_fps.py"""
from lib import boot, check, done

PRE = """
SETTEXT = 0
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "SetText" then return function(self, s) self.text = s; SETTEXT = SETTEXT + 1 end end
  if k == "SetPoint" then return function(self, p, rel, rp, x, y) self.anchor = { p, rel, rp, x, y } end end
  if k == "GetStringWidth" then return function(self) return TITLE_W and self == (EyeCandyMainFrame or {}).titleText and TITLE_W or 0 end end
  return index(t, k)
end
MOVING, FACING, ZONE, SUBZONE = false, 1.0, "Elwynn Forest", "Goldshire"
function IsPlayerMoving() return MOVING end
function GetPlayerFacing() return FACING end
function GetRealZoneText() return ZONE end
function GetSubZoneText() return SUBZONE end
"""
lua = boot(PRE)
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
X("""
-- n frames of dt seconds each, through the reader's own OnUpdate.
function FRAMES(n, dt) local f = NS.FPS.frame; for i = 1, n do f.scripts.OnUpdate(f, dt) end end
""")

# Pure parts.
check(E('NS.FPS.Smooth(nil, 60)') == 60, "the first reading stands alone")
check(E('NS.FPS.Smooth(60, 80)') == 70, "each reading moves the number half way")
check(E('NS.FPS.Shown(62, 62.6)') == 62, "a small move (62.6 against 62) keeps the shown number, so it never flickers")
check(E('NS.FPS.Shown(62, 63.2)') == 63, "a bigger move (63.2) moves it to the rounded number")
check(E('NS.FPS.Shown(119, 119.8)') == 120, "a steady 120 still reaches 120")
check(E('NS.FPS.Shown(nil, 59.5)') == 60, "the first number is rounded")

# The reader: nothing runs until someone watches.
check(not E('NS.FPS.frame.shown') and not E('NS.FPS.IsWatching()'), "with nobody watching, the reader's frame is hidden")
X('GOT = {}; NS.FPS.Watch("t", function(now, raw, n, t, long) GOT[#GOT+1] = { now, raw, n, long } end)')
check(E('NS.FPS.frame.shown') == True, "a watcher starts the reader")
X('FRAMES(31, 1/64)')
check(E('#GOT') == 0, "no reading before half a second")
X('FRAMES(1, 1/64)')
check(E('#GOT') == 1 and E('GOT[1][2]') == 64 and E('GOT[1][3]') == 32, "half a second of 64 FPS frames gives one reading of 64")
check(E('NS.FPS.Now()') == 64, "Now gives the smoothed FPS")
X('FRAMES(1, 0.25); FRAMES(16, 1/64)')
check(E('#GOT') == 2 and E('GOT[2][4]') == 0.25, "the longest frame in a reading is passed on (a hitch shows)")
X('NS.FPS.Unwatch("t")')
check(not E('NS.FPS.frame.shown') and E('NS.FPS.Now()') is None, "the last watcher out stops the reader and clears Now")


# A measurement (pure): settle, then 4 seconds of frames; moving starts it over.
X('M = NS.FPS.NewMeasure("x")')
X('for i = 1, 5 do R = NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, true) end')
check(E('M.phase') == "settle" and E('R') is None, "under 3 seconds still, it is still settling")
X('R = NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, true)')
check(E('M.phase') == "sample", "after 3 seconds with readings that agree, it samples")
X('R = NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, false)')
check(E('M.phase') == "settle" and E('M.frames') == 0, "moving starts the measurement over")
X('M = NS.FPS.NewMeasure("x"); for i = 1, 6 do NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, true) end')
X('R = nil; for i = 1, 8 do R = R or NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, true) end')
check(E('R') == "done" and abs(E('M.fps') - 60) < 0.01, "4 seconds of 60 FPS frames measure 60")
# One hitch is left out: 29 frames of 1/60 plus one of 0.25 s in one reading.
X('M = NS.FPS.NewMeasure("x"); M.phase = "sample"; R = nil')
X('R = NS.FPS.MeasureStep(M, 30 / (29/60 + 0.25), 30, 29/60 + 0.25, 0.25, true)')
X('for i = 1, 7 do R = R or NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, true) end')
check(E('R') == "done" and abs(E('M.fps') - 60) < 0.01, "one long frame (a shader loading) is left out of the result")
# Readings that never agree still sample after 10 seconds.
X('M = NS.FPS.NewMeasure("x"); for i = 1, 20 do NS.FPS.MeasureStep(M, i % 2 == 0 and 40 or 80, 30, 0.5, 1/40, true) end')
check(E('M.phase') == "sample", "settling waits 10 seconds at most")
X('M = NS.FPS.NewMeasure("x"); R = nil; for i = 1, 120 do R = R or NS.FPS.MeasureStep(M, 60, 30, 0.5, 1/60, false) end')
check(E('R') == "gave up", "never standing still, it gives up after a minute")

# The window's number.
X('SlashCmdList.EYECANDY(""); MAIN = EyeCandyMainFrame; MAIN.shown = true; MAIN.hooks.OnShow(MAIN)')
check(E('NS.FPS.IsWatching("bar")') == True, "opening the window starts the number")
X('FRAMES(32, 1/64)')
check(E('MAIN.fps.text') == "64 FPS", "the bar shows 64 FPS")
X('SETTEXT = 0; for i = 1, 10 do FRAMES(32, 1/64 + (i % 2 == 0 and 0.0001 or -0.0001)) end')
check(E('SETTEXT') == 0, "a steady FPS sets no text at all (no string built each reading)")
X('for i = 1, 20 do FRAMES(64, 1/128) end')
check(E('MAIN.fps.text') == "128 FPS", "it follows a change and settles on it (128 FPS)")
X('MAIN.shown = false; MAIN.hooks.OnHide(MAIN)')
check(not E('NS.FPS.IsWatching("bar")') and not E('NS.FPS.frame.shown'), "closing the window stops the reader")
X('MAIN.shown = true; MAIN.hooks.OnShow(MAIN)')
check(E('MAIN.fps.text') == "", "opened again, it starts blank, not with an old number")

# Where it sits.
X('NS.ShowTab("presets")')
check(E('MAIN.fps.anchor[2] == MAIN.peek') and E('MAIN.fps.anchor[1]') == "RIGHT", "on the full bar it sits left of Peek")
X('NS.ShowTab("hidden")')
check(E('MAIN.fps.anchor[2] == MAIN.peek') and E('MAIN.fps.shown') is not False, "on the Hidden tab too, next to the bar's buttons")
X('NS.ToggleShrink()')
check(E('MAIN.fps.anchor[1]') == "TOPLEFT" and E('MAIN.fps.shown') is not False, "shrunk, it sits at the left of the title row")
X('TITLE_W = 200; NS.ToggleShrink(); NS.ToggleShrink()')
check(E('MAIN.fps.shown') is False, "shrunk with a long title (Compare), it hides rather than overlap")
X('FRAMES(30, 1/60)')
check(E('MAIN.fps.shown') is False, "and stays hidden at the next reading")
X('TITLE_W = nil; FRAMES(30, 1/60)')
check(E('MAIN.fps.shown') is True, "it comes back once the title leaves room")
X('NS.ToggleShrink()')

# A preset remembers what it gave.
X('NS.ApplyPresetById("look:moody")')
check(E('NS.FPS.Measuring()') == "look:moody", "applying a preset starts measuring it")
X('for i = 1, 30 do FRAMES(30, 1/63) end')
check(E('EyeCandyDB.presetFPS["look:moody"].fps') == 63 and E('EyeCandyDB.presetFPS["look:moody"].zone') == "Goldshire",
      "standing still, Moody remembers 63 FPS in Goldshire")
check(E('NS.FPS.Measuring()') is None, "the measurement ends once it has a number")
check(E('NS.FPS.PresetLine("look:moody")') == "Last time: 63 FPS in Goldshire.", "the line reads Last time: 63 FPS in Goldshire.")
X('SUBZONE = ""')
X('EyeCandyDB.presetFPS.x = { fps = 41, zone = NS.FPS.Where() }')
check(E('NS.FPS.PresetLine("x")') == "Last time: 41 FPS in Elwynn Forest.", "with no subzone, the zone is named")
X('SUBZONE = "Goldshire"')

# In a fight, it never measures.
X('NS.ApplyPresetById("tier2"); INCOMBAT = true; for i = 1, 30 do FRAMES(30, 1/90) end; INCOMBAT = false')
check(E('EyeCandyDB.presetFPS["tier2"]') is None and E('NS.FPS.Measuring()') == "tier2", "in a fight it waits and stores nothing")
X('for i = 1, 30 do FRAMES(30, 1/90) end')
check(E('EyeCandyDB.presetFPS["tier2"].fps') == 90, "after the fight, standing still, it measures")

# Moving, or turning, starts it over.
X('NS.ApplyPresetById("tier3"); for i = 1, 8 do FRAMES(30, 1/70) end; MOVING = true; FRAMES(30, 1/70); MOVING = false')
X('for i = 1, 8 do FRAMES(30, 1/70) end')
check(E('EyeCandyDB.presetFPS["tier3"]') is None, "moving part way starts the settling again")
X('for i = 1, 30 do FRAMES(30, 1/70) end')
check(E('EyeCandyDB.presetFPS["tier3"].fps') == 70, "then standing still, it measures")
X('NS.ApplyPresetById("tier4"); for i = 1, 8 do FRAMES(30, 1/50) end; FACING = 2.0; FRAMES(30, 1/50)')
X('for i = 1, 8 do FRAMES(30, 1/50) end')
check(E('EyeCandyDB.presetFPS["tier4"]') is None, "turning part way starts it again")
X('for i = 1, 30 do FRAMES(30, 1/50) end')
check(E('EyeCandyDB.presetFPS["tier4"].fps') == 50, "then it measures")

# A setting changed since the preset: not the preset's FPS, so nothing is kept.
X('NS.ApplyPresetById("tier5"); for i = 1, 8 do FRAMES(30, 1/45) end; SetCVar("graphicsShadowQuality", "0")')
X('for i = 1, 30 do FRAMES(30, 1/45) end')
check(E('EyeCandyDB.presetFPS["tier5"]') is None, "a setting changed since the preset: nothing is kept")

# A new preset part way replaces the one being measured.
X('NS.ApplyPresetById("tier1"); for i = 1, 4 do FRAMES(30, 1/100) end; NS.ApplyPresetById("look:moody")')
X('for i = 1, 30 do FRAMES(30, 1/55) end')
check(E('EyeCandyDB.presetFPS["tier1"]') is None and E('EyeCandyDB.presetFPS["look:moody"].fps') == 55,
      "a second preset part way: only the second is measured")

# A loading screen ends it.
X('NS.ApplyPresetById("tier1"); FIRE("PLAYER_LEAVING_WORLD")')
check(E('NS.FPS.Measuring()') is None and not E('NS.FPS.IsWatching("preset")'), "a loading screen ends the measurement")

# Your own preset, and its tooltip.
X('MINE = NS.SaveCurrentAsPreset("Night raid"); NS.ApplyPresetById(MINE.id); for i = 1, 30 do FRAMES(30, 1/72) end')
check(E('EyeCandyDB.presetFPS[MINE.id].fps') == 72, "your own preset is measured too")
X("""TIP = {}; GameTooltip.AddLine = function(_, s) TIP[#TIP+1] = s end
NS.ShowTab("presets")
local rows = EyeCandyMainFrame.pages.presets.rows
for _, r in ipairs(rows) do if r.p and r.p.id == MINE.id then ROW = r end end
ROW.scripts.OnEnter(ROW)""")
check(E('TIP[#TIP]') == "Last time: 72 FPS in Goldshire.", "the preset's tooltip ends with Last time: 72 FPS in Goldshire.")
X('NS.DeletePreset(MINE.id)')
check(E('EyeCandyDB.presetFPS[MINE.id]') is None, "deleting the preset deletes its number")
done()
