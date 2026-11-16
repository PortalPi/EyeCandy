"""Back after you change something: a change made after a step (even a dial or a Standard row, which
take no backup) shows as "Your own changes" at the top of today's steps, and Back still works on the
preset under it. Each way of applying a preset is a step.

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
top = lambda: ev('NS.BackSteps()[1] and NS.BackSteps()[1].name')

# Each way of applying a preset is a step, straight after.
for pid, name in [("look:raid", "Raid & PvP"), ("tier3", "High")]:
    check(ev('NS.ApplyPresetById("%s")' % pid) == True and top() == name, "%s: a step straight after" % pid)
mine = ev('NS.SaveCurrentAsPreset("Mine")')
check(mine is not None and ev('NS.ApplyPresetById("%s")' % mine['id']) == True and top() == "Mine", "your own preset: a step straight after")
lua.execute('SlashCmdList.EYECANDY("look raid")')
check(top() == "Raid & PvP", "a Look from chat: a step too")

# A change that takes no backup (a dial, a Standard row) shows as your own changes.
lua.execute('SetCVar("weatherDensity", "3")')
check(top() == "Your own changes", "a setting changed with no backup: your own changes are the newest step")
check(ev('NS.BackSteps()[2].name') == "Raid & PvP", "and the preset is still under it")
# Putting it back the way the preset left it: nothing of your own any more.
lua.execute('SetCVar("weatherDensity", "0")')
check(top() == "Raid & PvP", "set back to what the preset left: no own changes")

# Back on the preset under your own changes undoes both, and says the count first (in the window).
lua.execute('SetCVar("weatherDensity", "2"); NS.ApplyPresetById("look:raid"); SetCVar("weatherDensity", "3")')
n = ev('NS.CountStepChanges(NS.BackSteps()[2])')
got, line = ev('NS.GoBack(2)')
check(got == n and ev('GetCVar("weatherDensity")') == "2", "Back on the preset puts back what was there before it, your change included")

# Apply with nothing changed is no step, and keeps the preset on top.
rows = ev('#NS.ListBackups()')
lua.execute('NS.ApplyPresetById("look:raid"); NS.ApplyAll(false, true)')
check(ev('#NS.ListBackups()') == rows and top() == "Raid & PvP", "Apply with nothing changed adds no row and no step")

# A step from an older version has no record of what it left: no own changes are shown, Back still asks with the count.
lua.execute('EyeCandyDB.steps[1].after = nil; SetCVar("weatherDensity", "3"); NS.LoadBackups()')
check(ev('EyeCandyDB.steps[1].after') is None, "loading at login doesn't fill in what an older step left")
check(top() == "Raid & PvP" and ev('NS.CountStepChanges(NS.BackSteps()[1])') > 0, "an older step shows no own changes, and its count includes them")
lua.execute('NS.ApplyPresetById("look:laptop")')
check(ev('NS.BackSteps()[2].name') == "Raid & PvP", "the next preset adds no own-changes step above an older step")
lua.execute('CHAT = {}; SlashCmdList.EYECANDY("back")')
said = chat(lua)
check(len(said) == 1 and "Back to before Laptop: " in said[0] and said[0].endswith(" put back."), "/ec back says once what it put back (%s)" % said)
done()
