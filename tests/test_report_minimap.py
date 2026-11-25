"""/ec report says what the minimap button's setting is, whether the button is shown now, what it
sits on, and whether the saved settings loaded at login (Minimap.lua, Report.lua).
Run: python tests/test_report_minimap.py"""
from lib import boot, check, done


def report(lua):
    lua.execute('SlashCmdList.EYECANDY("report")')
    return lua.eval('EyeCandyExportFrame.text')


def line(rep):
    return next((l for l in rep.split("\n") if l.startswith("Minimap button:")), "")


# Saved settings with the button hidden.
lua = boot('EyeCandyDB = { tiers = {}, extras = {}, advanced = {}, keepApplied = true, minimap = { hide = true, angle = 200 } }')
lua.execute('FIRE("PLAYER_LOGIN")')
got = line(report(lua))
check("set to hidden" in got and "made yes" in got and "shown no" in got, "a hidden button reads as set to hidden and not shown (%r)" % got)
check("Saved settings at login: loaded." in got, "saved settings that loaded say so")

# /ec minimap brings it back, and the report follows.
lua.execute('SlashCmdList.EYECANDY("minimap")')
got = line(report(lua))
check("set to shown" in got and "shown yes" in got, "after /ec minimap the report says shown (%r)" % got)

# No saved settings at all: the report says they started fresh.
lua2 = boot()
lua2.execute('FIRE("PLAYER_LOGIN")')
got = line(report(lua2))
check("missing, so it started fresh" in got and "set to shown" in got, "missing saved settings say so (%r)" % got)

done()
