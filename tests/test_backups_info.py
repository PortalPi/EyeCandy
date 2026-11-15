"""Backups row info line: the change count comes first, so a long line can only lose the end (the
character name), never the count (rule 16). Restore and Delete still ask the same questions.
Run: python tests/test_backups_info.py"""
from lib import boot, check, done

PRE = """
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  return index(t, k)
end
"""
API = """
NS.ListBackups = function() return {
  {id="b2", kind="manual", label="Raid", time="2026-11-06 10:40", character="Charactername-SERVER1Realm2PvP", values={}},
  {id="b1", kind="original", label="Original settings", time="2026-11-06 10:40", character="Charactername-Realm", values={}} } end
NS.CountBackupChanges = function(id) return ({ b2 = 12, b1 = 1 })[id] end
NS.DeleteBackup = function() end
"""
lua = boot(PRE)
lua.execute(API)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("backups")')
E, X = lua.eval, lua.execute
B = 'EyeCandyMainFrame.pages.backups.rows'

orig, raid = E(B + '[1].info.text'), E(B + '[2].info.text')
print(repr(orig)); print(repr(raid))
check(orig.startswith("1 setting differs"), "the Original's line starts with the count")
check(raid.startswith("12 settings differ"), "a manual row's line starts with the count")
for t in (orig, raid):
    i_kind = t.find("Original, kept for good") if "Original" in t else t.find("Manual")
    check(t.find("differ") < i_kind < t.find("2026-11-06") < t.find("Charactername"), "order is count, kind, time, character (%s)" % t)
    check(t.rstrip().endswith("Charactername"), "the character name is last, so a cut takes it first")
check(len(orig) <= 76 and orig.index("differs") + len("differs") < 20, "the count sits in the first 20 characters, well inside the 338px line")
X(API.replace('{ b2 = 12, b1 = 1 }', '{ b2 = 0, b1 = 0 }') + '; NS.RefreshUI()')
check(E(B + '[2].info.text').startswith("matches now"), "no changes reads 'matches now' first")
X('NS.ListBackups = function() return { {id="b5", kind="test", label="X", time="2026-11-06 10:40", values={}} } end; NS.RefreshUI()')
check("   " not in E(B + '[1].info.text'), "a backup of an unknown kind leaves no gap in the line (%s)" % E(B + '[1].info.text'))
X(API + '; NS.RefreshUI()')

# Restore and Delete still ask the same questions.
X('NS.AskRestore(NS.ListBackups()[1])')
t = E('EyeCandyAskFrame.textFS.text')
check(t.startswith("Restore 12 settings from") and "This can't be undone." in t, "Restore still asks first and says how many change (%s)" % t)
X('local d = EyeCandyMainFrame.pages.backups.rows[2].delete; d.scripts.OnClick(d)')
t = E('EyeCandyAskFrame.textFS.text')
check(t.startswith('Delete the backup "Raid"?') and "can't be undone" in t, "Delete still asks first (%s)" % t)
check(E(B + '[1].delete.shown') == False and E(B + '[2].delete.shown') == True, "only the manual row has Delete")
done()
