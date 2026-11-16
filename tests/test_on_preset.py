"""The preset you are on (ns.OnPreset, Presets.lua) and its highlight on the Presets tab.
Run: python tests/test_on_preset.py"""
from lib import boot, check, done

REG = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end
"""

lua = boot()
lua.execute(REG)
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("")')
E, X = lua.eval, lua.execute


def on():
    X('ONP, ONC = NS.OnPreset()')
    return (E('ONP and ONP.name'), E('ONC'))


check(on() == (None, None), "before any preset, you are on none")

X('NS.ApplyPresetById("tier3")')
check(on() == ("High", 0), "after applying High you are on High, unchanged")

X('NS.ApplyPresetById("look:moody")')
check(on() == ("Moody", 0), "after applying Moody you are on Moody")

was = E('GetCVar("farclip")')
X('SetCVar("farclip", "%s")' % ("1000" if was != "1000" else "2000"))
# A Look sets ns.db.look, but a changed setting still shows as changed.
check(on() == ("Moody", 1), "a setting changed since Moody shows Moody with one change")
X('SetCVar("farclip", "%s")' % was)
check(on() == ("Moody", 0), "putting it back shows Moody unchanged again")

X('MINE = NS.SaveCurrentAsPreset("Night raid"); NS.ApplyPresetById(MINE.id)')
check(on() == ("Night raid", 0), "your own preset can be the one you are on")
X('NS.RenamePreset(MINE.id, "Late raid")')
check(on() == ("Late raid", 0), "a renamed preset keeps its highlight under its new name")

# A value the game refuses is recorded as the game kept it, so it never reads as a change.
X('ORIGSET = SetCVar; SetCVar = function(k, v) if k == "farclip" then return ORIGSET(k, "777") end return ORIGSET(k, v) end')
X('NS.ApplyPresetById("tier4")')
check(E('GetCVar("farclip")') == "777", "setup: the game kept its own value")
check(on() == ("Ultra", 0), "a value the game refused doesn't make the preset look changed")
X('SetCVar = ORIGSET')

# /ec look crisp from chat skips the window: ns.db.look wins over the older record.
X('NS.SetLook("crisp")')
check(on() == ("Crisp", 0), "a Look set from chat shows as the one you are on")

X('NS.ApplyPresetById(MINE.id); NS.DeletePreset(MINE.id)')
check(on() == (None, None), "a deleted preset is no longer the one you are on")

# Import only saves: you stay on what you had until you press Apply on the new one.
X('NS.SetLook("crisp"); S = NS.ExportPreset("look:painterly"); NEW = NS.ImportPreset(S, "keep")')
check(E('NEW.name') == "Painterly (2)" and on() == ("Crisp", 0), "importing a preset doesn't change the one you are on")
X('NS.ApplyPresetById(NEW.id)')
check(on() == ("Painterly (2)", 0), "an imported preset you apply is the one you are on, under its saved name")

# Back to before puts you back on the preset you had.
X('NS.ApplyPresetById("tier3"); NS.ApplyPresetById("look:moody"); NS.GoBack()')
check(on() == ("High", 0), "Back to before Moody puts you back on High")

# A backup restore replaces every setting: you are on no preset after it.
X('NS.ApplyPresetById("tier3"); B = NS.CreateBackup("manual", "Test"); NS.ApplyPresetById("look:moody")')
check(on() == ("Moody", 0), "setup: on Moody")
X('NS.RestoreBackupById(B.id)')
check(on() == (None, None), "after a backup restore you are on no preset")

# A quality level set from chat is the one you are on.
X('SlashCmdList.EYECANDY("preset ultra")')
check(on() == ("Ultra", 0), "/ec preset ultra shows Ultra as the one you are on")

# A setting the city switch lowered is not a change of yours.
X('NS.ApplyPresetById("tier3"); KEPT = GetCVar("farclip"); REAL_SV = NS.SituationValue')
X('NS.SituationValue = function(c, v) if c == "farclip" then return KEPT end return v end; SetCVar("farclip", "200")')
check(on() == ("High", 0), "a value the city switch lowered doesn't count as changed")
X('NS.SituationValue = REAL_SV; SetCVar("farclip", KEPT)')
done()
