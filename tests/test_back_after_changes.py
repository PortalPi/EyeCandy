"""/ec back (and the window's Back button) is not offered once any setting changed after the preset,
even a dial or a Standard row that took no backup of its own (found while testing the window).

Run alone: python tests/test_back_after_changes.py
"""
from lib import boot, chat, check, done

REG = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
"""

lua = boot()
lua.execute(REG)
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
ev = lambda s: lua.eval(s)

# Each way of applying a preset leaves Back offered while nothing has changed since.
for pid, name in [("look:raid", "Raid & PvP"), ("tier3", None)]:
    check(ev('NS.ApplyPresetById("%s")' % pid) == True, "%s applies" % pid)
    got = ev('NS.LastPresetName()')
    check(got is not None and (name is None or got == name), "%s: Back is offered straight after" % pid)
mine = ev('NS.SaveCurrentAsPreset("Mine")')
check(mine is not None and ev('NS.ApplyPresetById("%s")' % mine['id']) == True, "your own preset applies")
check(ev('NS.LastPresetName()') == "Mine", "your own preset: Back is offered straight after")

# The window's case: a change that takes no backup (a dial, or a second Standard row).
lua.execute('NS.ApplyPresetById("look:raid")')
check(ev('NS.LastPresetName()') == "Raid & PvP", "setup: Back offered after Raid & PvP")
lua.execute('SetCVar("weatherDensity", "3"); CHAT = {}')
check(ev('NS.LastPresetName()') is None, "a setting changed with no backup: Back is no longer offered")
lua.execute('SlashCmdList.EYECANDY("back")')
check(any("Settings changed since Raid & PvP" in line for line in chat(lua)), "and /ec back says settings changed")
check(ev('GetCVar("weatherDensity")') == "3", "and leaves that change alone")

# Putting it back the way the preset left it offers Back again.
lua.execute('SetCVar("weatherDensity", "0")')
check(ev('NS.LastPresetName()') == "Raid & PvP", "set back to what the preset left: Back is offered again")

# A record from an older build (no "after"): loading backups at login (which calls ns.NoteApplied) does
# not fill it with whatever the game is at then, and with no way to tell what changed since, Back is not
# offered, since it could quietly undo later changes. Compare can still use it.
lua.execute('EyeCandyDB.lastBefore.after = nil; SetCVar("weatherDensity", "3"); NS.LoadBackups()')
check(ev('EyeCandyDB.lastBefore.after') is None, "loading at login leaves an older record without 'after'")
check(ev('NS.LastPresetName()') is None, "an older record without 'after' doesn't offer Back")
check(ev('NS.ToggleCompare()') is True and ev('NS.CompareLabel()') == "Showing: before Raid & PvP" and ev('GetCVar("farclip")') == ev('EyeCandyDB.lastBefore.values.farclip'), "but Compare can still show it")
lua.execute('NS.StopCompare()')

# A new preset fills its own record, and nothing is left waiting afterwards.
lua.execute('NS.ApplyPresetById("look:raid")')
check(ev('EyeCandyDB.lastBefore.after') is not None and ev('NS.awaitingAfter') is None, "the preset's own apply fills 'after' and stops waiting")

# Back keeps its own record, not a backup row (automatic backups are gone).
rows = lambda: ev('#NS.ListBackups()')
n = rows()
lua.execute('SetCVar("weatherDensity", "2"); NS.ApplyPresetById("look:raid")')
check(rows() == n and ev('EyeCandyDB.lastBefore.values.weatherDensity') == "2", "a preset adds no backup row; Back's record holds what was there")
lua.execute('NS.ApplyAll(false, true)')
check(rows() == n and ev('NS.LastPresetName()') == "Raid & PvP", "Apply with nothing changed adds no row and keeps Back")
lua.execute('CHAT = {}; SlashCmdList.EYECANDY("back")')
check(ev('GetCVar("weatherDensity")') == "2" and rows() == n, "Back puts it back and adds no row")
check(ev('EyeCandyDB.lastBefore') is None and ev('NS.LastPresetName()') is None, "one step only: afterwards there is nothing to go back to")
said = chat(lua)
check(len(said) == 1 and "Back to before Raid & PvP: " in said[0] and said[0].endswith(" put back."), "/ec back says once what it put back (%s)" % said)

# Each preset replaces the record, so Back goes to before the newest one, not further.
lua.execute('NS.ApplyPresetById("look:raid"); NS.ApplyPresetById("look:laptop")')
check(ev('NS.LastPresetName()') == "Laptop" and rows() == n, "a second preset replaces the record")
lua.execute('SlashCmdList.EYECANDY("back")')
check(ev('EyeCandyDB.look') == "raid", "Back returns to before Laptop (Raid & PvP), one step")

# In combat Back refuses and keeps the record for later.
lua.execute('NS.ApplyPresetById("look:laptop"); INCOMBAT = true; CHAT = {}; SlashCmdList.EYECANDY("back"); INCOMBAT = false')
check(ev('EyeCandyDB.look') == "laptop" and ev('NS.LastPresetName()') == "Laptop", "in combat Back changes nothing and is still offered after")
said = chat(lua)
check(len(said) == 1 and "Can't restore in combat" in said[0], "and /ec back says why, once (%s)" % said)
done()
