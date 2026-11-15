"""The shared bottom bar: Apply only on Hidden and the shrunk bar, Create backup off the Backups tab,
the remaining buttons close up, and "Copy my settings".
Run: python tests/test_bar_tidy.py"""
from lib import boot as lib_boot, check, done

PRE = """
local cf = CreateFrame
function CreateFrame(kind, name, parent, template) local f = cf(kind, name, parent, template); f.parent = parent; return f end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "SetPoint" then return function(self, p, rel, rp, x, y) self.anchor = { p, rel, rp, x, y } end end
  return index(t, k)
end
"""

lua = lib_boot(PRE)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY("")')
E, X = lua.eval, lua.execute
M = 'EyeCandyMainFrame'
shown = lambda n: E('%s.%s.shown' % (M, n)) is not False

for tab in ("presets", "standard", "backups"):
    X('NS.ShowTab("%s")' % tab)
    check(not shown("apply"), "Apply is hidden on the %s tab" % tab)
X('NS.ShowTab("hidden")')
check(shown("apply") and shown("createBackup"), "Apply and Create backup show on the Hidden tab")
check(E(M + '.createBackup.anchor[2] == ' + M + '.apply'), "on Hidden, Create backup sits right of Apply")

# Closed up: with Apply gone, Create backup takes its place and the checkbox follows it.
X('NS.ShowTab("presets")')
check(E(M + '.createBackup.anchor[1]') == "BOTTOMLEFT" and E(M + '.createBackup.anchor[2]') == 16, "on Presets, Create backup moves to the left edge")
check(E(M + '.keep.anchor[2] == ' + M + '.createBackup'), "the checkbox follows Create backup")

# Backups tab: no bar Create backup, the checkbox takes the left edge.
X('NS.ShowTab("backups")')
check(not shown("createBackup"), "Create backup is hidden on the Backups tab")
check(E(M + '.keep.anchor[1]') == "BOTTOMLEFT" and shown("keep"), "on Backups the checkbox closes up to the left edge")

# Shrunk bar keeps Apply (from any tab), drops the rest, and Peek and Compare follow Apply.
for tab in ("presets", "hidden"):
    X('NS.ShowTab("%s"); %s.shrink.scripts.OnClick(%s.shrink)' % (tab, M, M))
    check(E('NS.IsShrunk()') == True and shown("apply"), "the shrunk bar keeps Apply (from %s)" % tab)
    check(E(M + '.compare.anchor[2] == ' + M + '.apply'), "shrunk, Compare sits right of Apply (from %s)" % tab)
    X('NS.ToggleShrink()')
X('NS.ShowTab("presets")')
check(E('NS.IsShrunk()') == False and not shown("apply") and shown("createBackup"), "opened up again, the bar is the tab's own")

# Labels and tooltips.
check(E(M + '.export.text') == "Copy my settings", "the export button reads Copy my settings")
done()
