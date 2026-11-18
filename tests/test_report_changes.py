"""/ec report lists the settings changed since login, who changed them, and the loading screens
in between (Report.lua). Run: python tests/test_report_changes.py"""
from lib import boot, check, done

# The game's hooksecurefunc and GetTime, which the harness lacks.
PRE = """
CLOCK = 100
function GetTime() return CLOCK end
function hooksecurefunc(a, b, c)
  local t, name, fn = _G, a, b
  if type(a) == "table" then t, name, fn = a, b, c end
  local orig = t[name]
  t[name] = function(...) local r = { orig(...) }; fn(...); return unpack(r) end
end
"""
OURS = r'[string \"@Interface\\AddOns\\EyeCandy\\Situations.lua\"]:180: in function <x>'
OTHER = r'[string \"@Interface\\AddOns\\Blizzard_Settings\\Thing.lua\"]:9: in function <y>'


def report(lua):
    lua.execute('SlashCmdList.EYECANDY("report")')
    return lua.eval('EyeCandyExportFrame.text')


def section(rep):
    return rep.split("--- Settings changed since login")[1].split("=== Eye Candy graphics export")[0]


lua = boot(PRE)
sec = section(report(lua))
check("(none seen)" in sec, "with nothing changed it says none seen")
check("keep applied" in sec and "city switch off" in sec and "instance switch off" in sec
      and "Steady FPS off" in sec and "Lowered now: none." in sec, "it says which of Eye Candy's own switches are on (%r)" % sec.split("\n")[1])

# A flight: the game menu changes Brightness, a loading screen, then Eye Candy changes lighting.
lua.execute('CLOCK = 130; DEBUGSTACK = "' + OTHER + '"; SetCVar("Brightness", 60)')
lua.execute('CLOCK = 200; FIRE("PLAYER_LEAVING_WORLD")')
lua.execute('CLOCK = 210; DEBUGSTACK = "' + OURS + '"; SetCVar("graphicsLightMode", 1)')
lua.execute('DEBUGSTACK = ""; SetCVar("someUnlistedThing", 3)')
sec = section(report(lua))
lines = [l for l in sec.split("\n") if l.strip()]
bright = next((i for i, l in enumerate(lines) if "Brightness" in l), -1)
load = next((i for i, l in enumerate(lines) if "loading screen" in l), -1)
light = next((i for i, l in enumerate(lines) if "graphicsLightMode" in l), -1)
check(bright >= 0 and "60" in lines[bright] and "by the game or another addon" in lines[bright], "a change from elsewhere is listed with who made it")
check(light >= 0 and "by Eye Candy" in lines[light], "a change Eye Candy made is listed as Eye Candy's")
check(0 <= bright < load < light, "changes and loading screens are in the order they happened")
check("30s" in lines[bright] and "110s" in lines[light], "each line says the seconds since login (%r)" % lines[light])
check("someUnlistedThing" not in sec, "settings the report doesn't list are left out")

# C_CVar.SetCVar is watched too, and one change seen by both hooks is listed once.
lua.execute('C_CVar.SetCVar("Gamma", 0.8)')
sec = section(report(lua))
check(sec.count("Gamma") == 1, "a change through C_CVar.SetCVar is listed once")

# CVar names ignore case in the game.
lua.execute('SetCVar("brightness", 51)')
check("brightness" in section(report(lua)), "a change written in other letter case is still listed")

# Only the newest 15 are kept.
lua.execute('for i = 1, 20 do CLOCK = CLOCK + 5; SetCVar("Contrast", 40 + i) end')
sec = section(report(lua))
check("Contrast                       60" in sec and "Contrast                       45" not in sec, "only the newest 15 are kept")
check("Not seen: changes the game engine makes" in sec, "the report says what it can't see")

# A client without hooksecurefunc: the report still builds and says so.
lua2 = boot()
sec = section(report(lua2))
check("not watched" in sec, "without hooksecurefunc the report says the changes are not watched")
done()
