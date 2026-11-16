"""Standard tab rows: a value shows once, info rows say where to change them, the gold dot has a
legend, the intro and button words, and no automatic backup on a Standard change.
Run: python tests/test_standard_rows.py"""
import os
from lib import boot, check, done

STD = """
local reg = { gxMonitor="0", gxMaximize="1", useUiScale="0", uiscale="1", ffxAntiAliasingMode="4", cameraFov="90",
 graphicsShadowQuality="3", vsync="1", RenderScale="1", ResampleQuality="3" }
for k, v in pairs(reg) do C_CVar.RegisterCVar(k, v) end
function SettingsPanel:Open() self.shown = true end
function STDROW(cvar) for _, r in ipairs(NS.stdRows) do if r.def.cvar == cvar then return r end end end
CALLS = {}
"""

lua = boot()
lua.execute(STD)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("standard"); NS.RefreshUI()')
E = lua.eval

# Choice and toggle rows: the control shows the value, so the text beside it is empty.
check(E('STDROW("graphicsShadowQuality").valueText.text') == "", "a choice row's text beside the dropdown is empty")
check(E('STDROW("vsync").valueText.text') == "", "a toggle row's text beside the checkbox is empty")
# Ignored: it adds something, so it shows, without repeating the value.
lua.execute('SetCVar("RenderScale", "1.5"); NS.RefreshUI()')
t = E('STDROW("ResampleQuality").valueText.text')
check("ignored above 100%" in t and "Bicubic" not in t and "Fair" not in t, "an ignored row says only that it is ignored (%s)" % t)
lua.execute('SetCVar("RenderScale", "1"); NS.RefreshUI()')
check(E('STDROW("ResampleQuality").valueText.text') == "", "and goes back to empty when it counts again")
# A setting this client lacks still says so.
lua.execute('for _, r in ipairs(NS.stdRows) do if r.def.cvar == "vsync" then r.def.cvar = "notInThisClientXyz"; MISSING = r end end; NS.RefreshUI()')
check(E('MISSING.valueText.text') == "|cff9d9d9dnot in this game|r", "a setting this game lacks says so (%r)" % E('MISSING.valueText.text'))
lua.execute('MISSING.def.cvar = "vsync"; NS.RefreshUI()')

# Info rows keep their value and say where to change it.
check(E('STDROW("gxMaximize").valueText.text') == "Fullscreen (Windowed)", "an info row still shows what the game is using")
check("change in the game menu" in E('STDROW("gxMaximize").hint.text'), "an info row says it is changed in the game menu")
check(E('STDROW("graphicsShadowQuality").hint') is None, "a control row has no such hint")

# Intro, legend and button.
page = 'EyeCandyMainFrame.pages.standard'
src = open(os.path.join(os.path.dirname(__file__), '..', 'EyeCandy', 'Standard.lua'), encoding='utf-8').read()
check("The game's Graphics settings, in one place. They apply straight away." in src, "intro text")
check("changed from the game default" in E(page + '.legend.text'), "the gold dot has a legend line")
# Lua drops the backslash in an unknown escape ("\B" is "B"), which breaks the texture path.
check(E(page + '.legend.text').startswith("|TInterface\\Buttons\\WHITE8X8:"), "the legend's dot has a whole texture path (%r)" % E(page + '.legend.text')[:30])
check(E(page + '.gameMenu.text') == "Open the game's Graphics menu", "the button names the Graphics menu (%r)" % E(page + '.gameMenu.text'))

# No automatic backup from a Standard change.
lua.execute('NS.CreateBackup = function(...) CALLS[#CALLS + 1] = "CreateBackup:" .. tostring((...)) return nil end; NS.SetStandard("vsync", "0")')
check(E('#CALLS') == 0 and E('NS.stdUndoTaken') is None, "a Standard change takes no automatic backup and the flag is gone")
done()
