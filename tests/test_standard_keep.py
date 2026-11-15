"""A Standard tab change to a setting an Extra owns is counted as applied by backups,
while tier choices not yet applied stay out (uses ns.NoteAppliedExtra from Backups.lua).
Run: python tests/test_standard_keep.py"""
from lib import boot, check, done

lua = boot()
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
E, X = lua.eval, lua.execute

# Apply with Balanced clarity and sharpness 0.2, so backups have a snapshot of what's applied.
X('EyeCandyDB.tiers.clarity = 2; EyeCandyDB.extras.sharpness = 0.2; NS.ApplyAll(false, true)')
# Then a tier button pressed but not applied, and Sharpness changed on the Standard tab.
X('EyeCandyDB.tiers.clarity = 5; NS.SetStandard("ResampleSharpness", 0.5)')
check(E('EyeCandyDB.extras.sharpness') == 0.5, "the sharpness Extra keeps the Standard tab's value")
b = E('NS.CreateBackup("manual", "after standard")')
check(b['state']['extras']['sharpness'] == 0.5, "a backup made now holds the sharpness the Standard tab applied")
check(b['state']['tiers']['clarity'] == 2, "and the tier from the last Apply, not the one not yet applied")

# The game's own menu changing it is applied at once too.
X('NS.SnapshotGameMenu(); SetCVar("ResampleSharpness", "0.8"); NS.KeepGameMenuChanges()')
b = E('NS.CreateBackup("manual", "after game menu")')
check(b['state']['extras']['sharpness'] == 0.8, "a change from the game's menu is counted as applied too")

# The Extra set back to "Use tier" but not applied, then the Standard tab moves it: the applied
# snapshot follows the game, and the unapplied "Use tier" choice stays.
X('EyeCandyDB.extras.sharpness = 0.2; NS.ApplyAll(false, true); EyeCandyDB.extras.sharpness = nil')
X('NS.SetStandard("ResampleSharpness", 0.4)')
check(E('EyeCandyDB.extras.sharpness') is None, "an Extra set to Use tier stays on Use tier after a Standard change")
b = E('NS.CreateBackup("manual", "after use tier")')
check(b['state']['extras']['sharpness'] == 0.4, "a backup made now holds the sharpness the Standard tab set, not the old 0.2")

# Without the backups hook (an older Backups.lua), the Standard tab still works.
lua2 = boot()
lua2.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); NS.NoteAppliedExtra = nil; EyeCandyDB.extras.sharpness = 0.2')
lua2.execute('NS.SetStandard("ResampleSharpness", 0.5)')
check(lua2.eval('EyeCandyDB.extras.sharpness') == 0.5, "without the backups hook the Standard tab still keeps the value")
done()
