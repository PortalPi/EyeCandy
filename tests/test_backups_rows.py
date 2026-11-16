"""Backups tab rows: the Original first and kept for good, the character name only (full Name-Realm
in the tooltip), no wrapping, the row words, Delete red and 12px from Restore, the restore and
empty-list text, and the same words in /ec backups.
Run: python tests/test_backups_rows.py"""
from lib import boot, chat, check, done

# Each frame remembers its anchor, word wrap, text colour and text, so layout is checked as built.
PRE = """
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  if k == "SetPoint" then return function(self, p, rel, rp, x, y) self.anchor = { p, rel, rp, x, y } end end
  if k == "SetWordWrap" then return function(self, w) self.wrap = w end end
  if k == "SetTextColor" then return function(self, r, g, b) self.colour = { r, g, b } end end
  if k == "SetWidth" then return function(self, w) self.width = w end end
  return index(t, k)
end
"""
API = """
NS.ListBackups = function() return {
  {id="b3", kind="manual", label="Before Moody", time="2026-11-15 16:53", character="Charactername-SERVER1Realm2PvP", values={}},
  {id="b2", kind="manual", label="Raid", time="2026-11-15 16:00", character="Charactername-SERVER1Realm2PvP", values={}},
  {id="b1", kind="original", label="Original settings", time="2026-11-01 10:00", values={}} } end
NS.CountBackupChanges = function(id) return ({ b3 = 11, b2 = 1, b1 = 0 })[id] end
NS.DeleteBackup = function() end
"""
lua = boot(PRE)
lua.execute(API)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("backups")')
E, X = lua.eval, lua.execute
B = 'EyeCandyMainFrame.pages.backups.rows'

check(E(B + '[1].name.text') == "Original settings" and E(B + '[2].name.text') == "Before Moody", "the Original is listed first, the rest keep their order")
check(E(B + '[3].name.text') == "Raid", "the other rows follow in order")
check(E(B + '[1].info.text').count("Original, kept for good") == 1,"the Original says it is kept for good (%s)" % E(B + '[1].info.text'))
info = E(B + '[2].info.text')
check("Charactername" in info and "SERVER1" not in info and "Charactername-" not in info, "the row shows the character name only (%s)" % info)
check("11 settings differ" in info and "from now" not in info, "N settings differ")
check("1 setting differs" in E(B + '[3].info.text'), "one setting differs, said in the singular")
check("matches now" in E(B + '[1].info.text') and "same as now" not in E(B + '[1].info.text'), "matches now, not the old wording")

# The full Name-Realm is in the row's tooltip.
X("""
TIPS = {}
GameTooltip.SetOwner = function() TIPS = {} end
GameTooltip.AddLine = function(_, t) TIPS[#TIPS + 1] = t end
local row = EyeCandyMainFrame.pages.backups.rows[2]
row.scripts.OnEnter(row)
""")
check("Charactername-SERVER1Realm2PvP" in E('table.concat(TIPS, "|")'), "the row's tooltip has the full Name-Realm")

# Layout as built: Delete 12px left of Restore and red, the meta line grey 9d9d9d and never wrapping.
r = B + '[2]'
a = r + '.delete.anchor'
check(E(a + '[1]') == "RIGHT" and E(a + '[2] == ' + r + '.restore') and E(a + '[3]') == "LEFT" and E(a + '[4]') == -12, "Delete sits 12px left of Restore")
check(E(r + '.delete.text') == "|cffff4040Delete|r", "Delete is red")
check(E(r + '.info.wrap') == False and E(r + '.name.wrap') == False, "the name and the meta line never wrap")
# The meta line runs from x 234 to 572, short of Delete; the name stops at 228, before it.
check(E(r + '.info.anchor[2]') == 234 and E(r + '.info.width') == 338 and E(r + '.name.width') == 220, "the meta line has the row up to Delete, the name stops before it")
X('NS.ListBackups = function() return { {id="b9", kind="manual", label="A very long backup name that goes on and on", time="2026-11-15 16:00", values={}} } end; NS.CountBackupChanges = function() return 0 end; NS.RefreshUI()')
check(E(B + '[1].name.text') == "A very long backup name tha...", "a long backup name is cut with ... (%s)" % E(B + '[1].name.text'))
X(API + '; NS.RefreshUI()')
c = [round(E(r + '.info.colour[%d]' % i), 3) for i in (1, 2, 3)]
check(c == [0.616, 0.616, 0.616], "the meta line is grey 9d9d9d (%s)" % c)
check(E('EyeCandyMainFrame.pages.backups.rows[1].delete.shown') == False, "the Original has no Delete")
X('local d = EyeCandyMainFrame.pages.backups.rows[2].delete; d.scripts.OnEnter(d)')
check(E('TIPS[1]') == "Delete" and "Asks first" in E('TIPS[2]'), "Delete has a tooltip")

# Restore asks first, says no backup is made for you, and that Back can undo it today (a step).
X('NS.AskRestore(NS.ListBackups()[2])')
t = E('EyeCandyAskFrame.textFS.text')
check(t.startswith("Restore 1 setting from") and "Back on the Presets tab can undo it today." in t and "can't be undone" not in t, "the restore question is true (%s)" % t)

# Restore and Delete say what happened on the Backups tab, not in chat.
X('CHAT = {}; NS.RestoreBackupById = function(id) return 4 end; NS.RestoredLine = function(n, b) return "Restored " .. n .. " settings from \\"" .. b.label .. "\\"." end')
X('NS.AskRestore(NS.ListBackups()[2]); EyeCandyAskFrame.accept.scripts.OnClick(EyeCandyAskFrame.accept)')
res = E('EyeCandyMainFrame.pages.backups.result.text')
check(res == '|cff7cff7cRestored 4 settings from "Raid".|r' and len(chat(lua)) == 0, "a restore shows its result in green on the tab, not in chat (%r)" % res)
X('NS.RestoreBackupById = function() return nil, "Can\'t restore in a fight. Try again after it." end')
X('NS.AskRestore(NS.ListBackups()[2]); EyeCandyAskFrame.accept.scripts.OnClick(EyeCandyAskFrame.accept)')
check(E('EyeCandyMainFrame.pages.backups.result.text') == "|cffff4040Can't restore in a fight. Try again after it.|r" and len(chat(lua)) == 0, "a refused restore says why in red on the tab")
X('EyeCandyMainFrame.pages.backups.hooks.OnHide(EyeCandyMainFrame.pages.backups); NS.RefreshUI()')
check(E('EyeCandyMainFrame.pages.backups.result.text') == "", "leaving the tab clears the result")

# With no backups, the empty line says when the Original is made.
X('NS.ListBackups = function() return {} end; NS.RefreshUI()')
check(E('EyeCandyMainFrame.pages.backups.empty.text') == "No backup yet. Your Original is saved a few seconds after you log in.", "the empty list says when the Original is made")
check(E('EyeCandyMainFrame.pages.backups.empty.shown') == True, "and it shows")

# /ec backups uses the same words as the rows (the real Backups.lua list).
lua2 = boot()
lua2.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); NS.CreateBackup("manual", "Raid"); CHAT = {}; SlashCmdList.EYECANDY("backups")')
said = chat(lua2)
check(any("Original, kept for good" in s and "matches now" in s for s in said), "chat lists the Original, kept for good, matches now (%s)" % said)
check(any("Raid" in s and "matches now, Manual," in s for s in said) and not any("differ from now" in s for s in said), "chat lists your own as Manual, without the old wording")
done()
