"""What the slash commands print matches the window: /ec backups gives each backup's count
first, like the Backups tab rows, and /ec find's example is a plain word, not "lod"
(docs/ui-rules.md rule 2).
Run: python tests/test_slash_words.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN")')
X('''
NS.ListBackups = function() return {
  {id=2, kind="manual", label="Raid", time="2026-11-06 10:40", character="Charactername-Realm", values={}},
  {id=1, kind="original", label="Original settings", time="2026-11-05 09:00", values={}} } end
NS.CountBackupChanges = function(id) return ({ [2] = 12, [1] = 1 })[id] end
CHAT = {}
''')
X('SlashCmdList.EYECANDY("backups")')
lines = [E('CHAT[%d]' % i) for i in range(1, E('#CHAT') + 1)]
raid = next((l for l in lines if "Raid" in l), "")
orig = next((l for l in lines if "Original settings" in l), "")
print(repr(raid)); print(repr(orig))
check(raid.find("12 settings differ") != -1 and raid.find("12 settings differ") < raid.find("2026-11-06 10:40"), "a backup's count comes before its time, as on the Backups tab")
check(raid.find("Manual") != -1 and raid.find("Charactername-Realm") > raid.find("2026-11-06"), "the kind, time and character are still there, the character last")
check(orig.find("1 setting differs") != -1 and orig.find("1 setting differs") < orig.find("2026-11-05"), "one setting is said in the singular, first")
check(orig.endswith("Original, kept for good, 2026-11-05 09:00)"), "a backup with no character ends on its time, with no dangling comma (%r)" % orig)
X('NS.ListBackups = function() return { {id=3, kind="manual", label="", time="2026-11-07 08:00", values={}} } end; NS.CountBackupChanges = function() return 0 end; CHAT = {}')
X('SlashCmdList.EYECANDY("backups")')
blank = E('CHAT[1]')
check("3. Manual  (matches now, Manual, 2026-11-07 08:00)" in blank, "a backup with no name is named by its kind, as on the tab (%r)" % blank)

usage = E('NS.BuildFind("")')
check("lod" not in usage.lower(), "the find example no longer says lod (%r)" % usage)
check("find shadow" in usage, "it gives shadow as the example (%r)" % usage)
done()
