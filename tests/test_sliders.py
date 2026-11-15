"""Checks for the sliders (roadmap step 5): typed box, arrows, Shift fine steps, wheel,
a tick at the game default, a reset arrow, sharpness Off, and the PLAN's steps.
Run: python tests/test_sliders.py"""
from lib import boot as lib_boot, check, done

GETTEXT = """local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end"""

SETUP = """
local reg = { RenderScale="1", ResampleSharpness="0.2", ResampleQuality="3", entityLodDist="10", graphicsViewDistance="5",
 Gamma="1", cameraFov="90", bloomUserMult="1", groundEffectDensity="64", groundEffectDist="200", groundEffectFade="200",
 farclip="5000", horizonClip="5000", horizonStart="1000", assaoRadius="1.85", assaoSharpness=".98" }
for k, v in pairs(reg) do C_CVar.RegisterCVar(k, v) end
SHIFT = false
function IsShiftKeyDown() return SHIFT end
function FINDROW(cvar) for _, r in ipairs(NS.advRows) do if r.d[1] == cvar then return r end end end
function EXROW(key) for _, r in ipairs(NS.extraRows) do if r.ex.key == key then return r end end end
function STDROW(cvar) for _, r in ipairs(NS.stdRows) do if r.def.cvar == cvar then return r end end end
function CLICK(b) b.scripts.OnClick(b) end
function TYPE(s, text) s.box.text = text; s.box.scripts.OnEnterPressed(s.box) end
function DRAG(s, pos) s.scripts.OnValueChanged(s, pos); RUNTIMERS() end
function WHEEL(s, d) s.hooks.OnMouseDown(s); s.scripts.OnMouseWheel(s, d); RUNTIMERS() end
-- The real client fires OnValueChanged when SetValue moves the bar; the stub doesn't unless asked.
function LIVE(s) s.SetValue = function(self, v) if v ~= self.pos then self.pos = v; self.scripts.OnValueChanged(self, v) end end end
"""


def boot(**kw):
    lua = lib_boot(**kw)
    lua.execute(GETTEXT)
    lua.execute(SETUP)
    return lua


lua = boot()
E = lambda e: lua.eval(e)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY("")')

# The shared slider on its own
lua.execute("""SETS = {}
T = NS.Slider(CreateFrame("Frame"), { min = 0, max = 2, step = 0.05, off = -1, width = 205, default = 0.2,
  get = function() return CUR end, set = function(v) SETS[#SETS + 1] = v; CUR = v end })
CUR = 0.2; T:Refresh()""")
check(E('T.box.text') == "0.2", "the typed box shows the value")
lua.execute('DRAG(T, 0.37)')
check(E('CUR') == 0.35, "dragging snaps to the step (0.37 -> 0.35)")
lua.execute('SHIFT = true; DRAG(T, 0.37); SHIFT = false')
check(E('CUR') == 0.37, "Shift gives fine steps (0.37 stays 0.37)")
lua.execute('CUR = 0.2; T:Refresh(); WHEEL(T, 1)')
check(E('CUR') == 0.25, "the mouse wheel moves one step")
lua.execute('SHIFT = true; WHEEL(T, -1); SHIFT = false')
check(E('CUR') == 0.24, "Shift and the wheel move one fine step")
lua.execute('CUR = 0.2; T:Refresh(); CLICK(T.plus); RUNTIMERS()')
check(E('CUR') == 0.25, "the > arrow moves one step up")
lua.execute('CLICK(T.minus); RUNTIMERS()')
check(E('CUR') == 0.2, "the < arrow moves one step down")
lua.execute('CUR = 0; T:Refresh(); CLICK(T.minus); RUNTIMERS()')
check(E('CUR') == -1 and E('T.box.text') == "Off", "one step below the low end is Off (-1)")
lua.execute('CLICK(T.plus); RUNTIMERS()')
check(E('CUR') == 0, "one step up from Off is the low end")
lua.execute('DRAG(T, -0.05)')
check(E('CUR') == -1, "the bar's far left is Off")
n = E('#SETS')
lua.execute('TYPE(T, "1.3")')
check(E('CUR') == 1.3 and E('#SETS') == n + 1, "a typed value applies on Enter, straight away")
lua.execute('TYPE(T, "off")')
check(E('CUR') == -1, "typing Off picks Off")
lua.execute('TYPE(T, "9")')
check(E('CUR') == 2, "a typed value past the end is held to the range")
n = E('#SETS')
lua.execute('TYPE(T, "abc")')
check(E('#SETS') == n and E('T.box.text') == "2", "a typed word that isn't a number changes nothing")
check(abs(E('T.tickX') - (16 + 0.25 / 2.05 * (205 - 32))) < 1e-6, "the tick sits under the thumb's centre at the game default")
lua.execute('CLICK(T.reset)')
check(E('CUR') == 0.2, "the reset arrow puts back the game default")
lua.execute("""P = NS.Slider(CreateFrame("Frame"), { min = 0.33, max = 2, step = 0.01, percent = true,
  get = function() return PCUR end, set = function(v) PCUR = v end }); PCUR = 1.5; P:Refresh()""")
check(E('P.box.text') == "150", "a percent slider shows 150 for 1.5")
lua.execute('TYPE(P, "137%")')
check(E('PCUR') == 1.37, "typing 137 sets 1.37")
lua.execute('PCUR = 1.338; P:Refresh()')
check(E('P.box.text') == "133.8", "a Shift-step percent shows its decimal (133.8, not 134)")

# Review fixes on the slider
lua.execute('CUR = 5; T:Refresh()')
check(E('T.box.text') == "5", "the box shows the real value even past the bar's end (5 on a 0 to 2 bar)")
lua.execute('CUR = 2; T:Refresh(); N = #SETS; CLICK(T.plus); RUNTIMERS(); WHEEL(T, 1)')
check(E('#SETS') == E('N'), "the > arrow and the wheel at the top end change nothing")
check(E('T.armed') == True, "a click on the bar lets the wheel step it")
lua.execute('T.hooks.OnLeave(T); CUR = 1; T:Refresh(); N = #SETS; T.scripts.OnMouseWheel(T, 1); RUNTIMERS()')
check(E('#SETS') == E('N') and E('CUR') == 1, "once the mouse leaves the bar the wheel does nothing (scrolling a list past it is safe)")
lua.execute("""U = NS.Slider(CreateFrame("Frame"), { min = 0, max = 2, step = 0.05, get = function() return 1 end, set = function(v) UCUR = v end })
U:Refresh(); U.scripts.OnMouseWheel(U, 1); RUNTIMERS()""")
check(E('UCUR') is None, "a slider never clicked ignores the wheel")
lua.execute('LIVE(T); CUR = 1.5; N = #SETS; T:Refresh(); RUNTIMERS(); CUR = 0.4; T:Refresh(); RUNTIMERS()')
check(E('#SETS') == E('N'), "moving the bar to the current value never applies anything")
lua.execute('T.box.text = "1.1"; T.box.scripts.OnEditFocusLost(T.box)')
check(E('CUR') == 1.1, "clicking away from the box applies what was typed")
lua.execute('T.box.text = "0.5"; T.box.scripts.OnEscapePressed(T.box)')
check(E('CUR') == 1.1 and E('T.box.text') == "1.1", "Escape puts the value back and applies nothing")
lua.execute('T.box.HasFocus = function() return true end; T.box.text = "1.7"; CUR = 0.6; T:Refresh(); T.box.HasFocus = nil')
check(E('T.box.text') == "1.7", "a refresh doesn't wipe what is being typed")
lua.execute("""DEF = nil; D = NS.Slider(CreateFrame("Frame"), { min = 0, max = 10, step = 1, default = function() return DEF end,
  get = function() return 3 end, set = function() end })""")
lua.execute('DEF = 5; D:Refresh()')
check(E('D.tickX') is not None, "the default tick appears once the default is known (not only at build time)")
lua.execute("""I = NS.Slider(CreateFrame("Frame"), { min = 0, max = 2, step = 0.05, off = -1, invert = true,
  get = function() return ICUR end, set = function(v) ICUR = v end }); ICUR = 0.2; I:Refresh()""")
lua.execute('CLICK(I.plus); RUNTIMERS()')
check(abs(E('ICUR') - 0.15) < 1e-9, "on a turned-round bar > lowers the value (sharper)")
lua.execute('ICUR = 2; I:Refresh(); CLICK(I.minus); RUNTIMERS()')
check(E('ICUR') == -1, "on a turned-round bar, Off sits past the high end")
lua.execute('TYPE(I, "3")')
check(E('ICUR') == 2, "typing past the end of a turned-round bar holds to the end, never Off")

# Extras: render scale, sharpness and character detail are sliders
lua.execute('NS.ShowTab("hidden")')
check(E('EXROW("renderScale").slider ~= nil and EXROW("sharpness").slider ~= nil and EXROW("entityLod").slider ~= nil'), "render scale, sharpness and character detail are sliders")
check(E('EXROW("resample").slider == nil'), "the resample filter (named choices) stays a stepper")
lua.execute('TYPE(EXROW("renderScale").slider, "137")')
check(E('EyeCandyDB.extras.renderScale') == 1.37 and E('GetCVar("RenderScale")') == "1", "render scale goes in 1% steps and waits for Apply")
lua.execute('TYPE(EXROW("renderScale").slider, "20")')
check(E('EyeCandyDB.extras.renderScale') == 0.33, "render scale stops at the game's lowest (33%)")
lua.execute('TYPE(EXROW("renderScale").slider, "250")')
check(E('EyeCandyDB.extras.renderScale') == 2, "render scale stops at the game's highest (200%)")
lua.execute('CLICK(EXROW("renderScale").slider.reset)')
check(E('EyeCandyDB.extras.renderScale') is None and "Use level" in E('EXROW("renderScale").status.text'), "the reset arrow goes back to Use level")
lua.execute('TYPE(EXROW("entityLod").slider, "37")')
check(E('EyeCandyDB.extras.entityLod') == 37, "character detail takes any whole number from 5 to 100")
lua.execute('CLICK(EXROW("sharpness").slider.minus); RUNTIMERS()')
check(E('EyeCandyDB.extras.sharpness') == 0.25, "sharpness moves in 0.05 steps, and < is softer (the bar runs like the game's)")
lua.execute('TYPE(EXROW("sharpness").slider, "2"); CLICK(EXROW("sharpness").slider.minus); RUNTIMERS()')
check(E('EyeCandyDB.extras.sharpness') == -1, "sharpness Off sits next to the soft end, not next to the sharpest")
lua.execute('TYPE(EXROW("sharpness").slider, "off"); SlashCmdList.EYECANDY("apply")')
check(E('EyeCandyDB.extras.sharpness') == -1 and E('GetCVar("ResampleSharpness")') == "-1", "sharpness Off applies -1")
mirror = E('GetCVar("eyeCandyMirror")')
check("sharpness:-1" in mirror, "the mirror keeps sharpness Off (%s)" % mirror)
lua.execute('local p = NS.SaveCurrentAsPreset("Soft"); SHARE = NS.ExportPreset(p.id); NS.DeletePreset(p.id); PV = NS.PreviewImport(SHARE)')
check(E('PV.ok') == True and E('(function() for _, c in ipairs(PV.skipped or {}) do if c == "ResampleSharpness" then return false end end return true end)()'), "a shared preset with sharpness Off imports it (-1 is in range)")
lua2 = boot(mirror=mirror)
lua2.execute('FIRE("PLAYER_LOGIN")')
check(lua2.eval('EyeCandyDB.extras.sharpness') == -1, "sharpness Off survives a lost settings file (read back from the mirror)")

# Dials: the PLAN's steps, and the box, arrows and tick
steps = {"groundEffectDensity": 1, "groundEffectDist": 5, "groundEffectFade": 5, "farclip": 50, "horizonClip": 50,
         "horizonStart": 50, "Gamma": 0.05, "bloomUserMult": 0.05, "cameraFov": 1, "assaoRadius": 0.025, "assaoSharpness": 0.005}
bad = [c for c, s in steps.items() if abs(E('FINDROW("%s").d[5]' % c) - s) > 1e-9]
check(not bad, "dial steps follow the PLAN table (wrong: %s)" % bad)
check(E('NS.SnapAdvanced(FINDROW("assaoRadius").d, 1.8624)') == 1.85 and E('NS.SnapAdvanced(FINDROW("assaoRadius").d, 1.8626)') == 1.875, "a 0.025 step snaps exactly (1.875, not 1.88)")
grass = E('GetCVar("groundEffectDensity")')
lua.execute('TYPE(FINDROW("groundEffectDensity").slider, "131")')
check(E('GetCVar("groundEffectDensity")') == "131" and E('EyeCandyDB.advanced.groundEffectDensity') == 131, "a typed dial value applies straight away")
far = int(E('GetCVar("farclip")'))
lua.execute('local s = FINDROW("farclip").slider; s:Refresh(); CLICK(s.plus); RUNTIMERS()')
check(E('GetCVar("farclip")') == str(far + 50), "far clip moves in 50s")
check(E('FINDROW("farclip").slider.tickX') is not None and E('FINDROW("farclip").slider.reset') is None, "dials show the default tick; their own reset arrow hands the dial back")
lua.execute('CLICK(FINDROW("groundEffectDensity").reset)')
check(E('EyeCandyDB.advanced.groundEffectDensity') is None and E('GetCVar("groundEffectDensity")') == grass, "a dial's reset arrow hands it back (%s)" % grass)
lua.execute('INCOMBAT = true; TYPE(FINDROW("farclip").slider, "8000"); INCOMBAT = false')
check(E('GetCVar("farclip")') == str(far + 50), "a typed dial value never applies in combat")
lua.execute('TYPE(FINDROW("farclip").slider, "5013")')
check(E('GetCVar("farclip")') == "5010", "a typed dial value snaps to the fine step (far clip 5013 -> 5010)")
lua.execute('SetCVar("groundEffectDensity", "8"); FINDROW("groundEffectDensity").slider:Refresh()')
check(E('FINDROW("groundEffectDensity").slider.box.text') == "8", "a dial's box shows a live value below its range (8), not the range's end")
lua.execute('NS.RefreshUI()')
for name, rows in (("dial", "advRows"), ("Extra", "extraRows"), ("Standard", "stdRows")):
    lua.execute('for _, r in ipairs(NS.%s) do if r.slider and r.slider.spec then LIVE(r.slider) end end' % rows)
lua.execute('ADV = 0; for _ in pairs(EyeCandyDB.advanced) do ADV = ADV + 1 end; EX = 0; for _ in pairs(EyeCandyDB.extras) do EX = EX + 1 end; N = #SETLOG')
lua.execute('SetCVar("farclip", "19950"); N = #SETLOG; NS.RefreshUI(); RUNTIMERS(); NS.ShowTab("standard"); NS.RefreshUI(); RUNTIMERS()')
check(E('#SETLOG') == E('N') and E('(function() local n = 0; for _ in pairs(EyeCandyDB.advanced) do n = n + 1 end; return n end)()') == E('ADV')
      and E('(function() local n = 0; for _ in pairs(EyeCandyDB.extras) do n = n + 1 end; return n end)()') == E('EX'),
      "refreshing the window moves every slider without applying or saving anything")
lua.execute('NS.ShowTab("hidden")')

# Standard tab: the game's units in the box, sharpness Off
lua.execute('NS.ShowTab("standard")')
lua.execute('SetCVar("graphicsViewDistance", "4"); STDROW("graphicsViewDistance").slider:Refresh()')
check(E('STDROW("graphicsViewDistance").slider.box.text') == "5", "View Distance shows 1 to 10 in the box, as the game does (4 -> 5)")
lua.execute('TYPE(STDROW("graphicsViewDistance").slider, "10")')
check(E('GetCVar("graphicsViewDistance")') == "9", "typing 10 sets View Distance to the top (9)")
lua.execute('TYPE(STDROW("RenderScale").slider, "175")')
check(E('GetCVar("RenderScale")') == "1.75", "typing 175 sets Render Scale to 175%")
lua.execute('TYPE(STDROW("ResampleSharpness").slider, "off")')
check(E('GetCVar("ResampleSharpness")') == "-1" and E('STDROW("ResampleSharpness").slider.box.text') == "Off", "Standard sharpness has an Off position")
check(E('NS.FormatStandard(NS.StandardRow("ResampleSharpness"), "-1")') == "Off", "sharpness -1 reads Off, not -1")
lua.execute('SetCVar("ResampleSharpness", "0.2"); STDROW("ResampleSharpness").slider:Refresh(); CLICK(STDROW("ResampleSharpness").slider.plus); RUNTIMERS()')
check(E('GetCVar("ResampleSharpness")') == "0.15", "the sharpness > arrow sharpens by 0.05 (the bar runs like the game's)")
lua.execute('TYPE(STDROW("ResampleSharpness").slider, "3")')
check(E('GetCVar("ResampleSharpness")') == "2", "typing 3 into Standard sharpness holds to 2 (softest), never Off")
lua.execute('SetCVar("Gamma", "1"); STDROW("Gamma").slider:Refresh(); SHIFT = true; CLICK(STDROW("Gamma").slider.plus); RUNTIMERS(); SHIFT = false')
check(E('GetCVar("Gamma")') == "1.01", "Shift on a Standard row gives fine steps (Gamma 1 -> 1.01)")
lua.execute('SetCVar("Gamma", "1"); STDROW("Gamma").slider:Refresh(); CLICK(STDROW("Gamma").slider.plus); RUNTIMERS()')
check(E('GetCVar("Gamma")') == "1.05", "Gamma moves in 0.05 steps")
lua.execute('CLICK(STDROW("Gamma").slider.reset)')
check(E('GetCVar("Gamma")') == "1", "the reset arrow puts the game default back")

done()
