"""Backups row names are white (GameFontHighlight), not gold (rule 14 and rule 20: gold means on
now, headings, the selected thing). Run: python tests/test_backups_names.py"""
from lib import boot, check, done

# Each font string remembers the font it was made with.
PRE = """
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "CreateFontString" then
    return function(self, name, layer, font)
      local fs = index(t, "CreateFontString")(self, name, layer, font)
      fs.font = font
      return fs
    end
  end
  return index(t, k)
end
"""
API = """
NS.ListBackups = function() return {
  {id="b2", kind="manual", label="Raid", time="2026-11-06 10:40", character="Tester-Realm", values={}},
  {id="b1", kind="original", label="Original settings", time="2026-11-06 10:40", values={}} } end
NS.CountBackupChanges = function() return 3 end
NS.DeleteBackup = function() end
"""
lua = boot(PRE)
lua.execute(API)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("backups")')
E = lua.eval
B = 'EyeCandyMainFrame.pages.backups.rows'
for i in (1, 2):
    check(E(B + '[%d].name.font' % i) == "GameFontHighlight", "row %d name is white (%s)" % (i, E(B + '[%d].name.font' % i)))
    check(E(B + '[%d].info.font' % i) != "GameFontNormal", "row %d info line is not gold" % i)
done()
