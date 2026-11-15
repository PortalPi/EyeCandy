"""ns.NoteAppliedExtra: a backup holds an Extra the Standard tab applied on its own, but not tier
choices made and not yet applied (needed by the window).

Run alone: python tests/test_backups_extra.py
"""
from lib import boot, check, done

lua = boot()
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
ev = lambda s: lua.eval(s)

# A snapshot exists: Apply with Balanced clarity and sharpness 0.2.
lua.execute('EyeCandyDB.tiers.clarity = 2; EyeCandyDB.extras.sharpness = 0.2; NS.ApplyAll(false, true)')
# Then: a tier button pressed but not applied, and the Standard tab applying sharpness 0.5 at once.
lua.execute('EyeCandyDB.tiers.clarity = 5; EyeCandyDB.extras.sharpness = 0.5; NS.NoteAppliedExtra("sharpness", 0.5)')
b = ev('NS.CreateBackup("manual", "after standard")')
check(b['state']['extras']['sharpness'] == 0.5, "the backup holds the Extra the Standard tab applied")
check(b['state']['tiers']['clarity'] == 2, "and the tier from the last Apply, not the unapplied tier choice")

# Clearing the Extra on its own is recorded too.
lua.execute('EyeCandyDB.extras.sharpness = nil; NS.NoteAppliedExtra("sharpness", nil)')
b = ev('NS.CreateBackup("manual", "after clearing")')
check(b['state']['extras']['sharpness'] is None, "clearing the Extra on its own is recorded")

# The window's edge case: sharpness 0.2 applied, then set back to "Use tier" without
# applying, then the Standard tab sets the setting itself. The snapshot follows the game.
lua.execute('EyeCandyDB.extras.sharpness = 0.2; NS.ApplyAll(false, true)')
lua.execute('EyeCandyDB.extras.sharpness = nil; NS.NoteAppliedExtra("sharpness", 0.6)')
b = ev('NS.CreateBackup("manual", "use tier then standard")')
check(b['state']['extras']['sharpness'] == 0.6, "an Extra set to Use tier but not applied takes the Standard tab's value")
check(ev('EyeCandyDB.extras.sharpness') is None, "and the Use tier choice itself is left alone")

# An Extra neither in force nor chosen stays out, so the Standard tab can call this for every Extra.
check(ev('EyeCandyDB.extras.renderScale') is None, "setup: no render scale Extra chosen")
lua.execute('NS.NoteAppliedExtra("renderScale", 1.5)')
b = ev('NS.CreateBackup("manual", "untouched extra")')
check(b['state']['extras']['renderScale'] is None, "an Extra not in force and not chosen is not recorded")

# Before any snapshot, the call is harmless.
lua2 = boot()
lua2.execute('NS.NoteAppliedExtra("sharpness", 1)')
check(True, "calling it before any snapshot exists raises no error")
done()
