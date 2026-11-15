"""Checks for shrinking the main window to a small bar and opening it back up.
Run: python tests/test_shrink.py"""
from lib import boot as lib_boot, check, done, GEO, near

lua = lib_boot()
lua.execute(GEO)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY("")')
E, X = lua.eval, lua.execute
M = 'EyeCandyMainFrame'

check(E(M + '.shrink') is not None and E('NS.IsShrunk()') == False, "the main window has a shrink button and opens full size")
x0, y0 = E('CORNER(%s)' % M)

# Shrink: a small bar with the title and Apply, top-left where it was.
X('NS.ShowTab("hidden"); %s.shrink.scripts.OnClick(%s.shrink)' % (M, M))
check(E('NS.IsShrunk()') == True, "the shrink button shrinks the window")
check(E(M + '.geo.w') == 300 and E(M + '.geo.h') == 66, "shrunk, the window is a small bar")
x1, y1 = E('CORNER(%s)' % M)
check(near(x1, x0) and near(y1, y0), "shrinking keeps the top-left corner where it was, even from the middle of the screen")
check(E(M + '.titleText.text') == "Eye Candy", "the bar shows a short title")
hidden = E('(function() for _, f in ipairs(%s.rollUp) do if f.shown ~= false then return false end end return true end)()' % M)
check(hidden and E(M + '.pages.hidden.shown') == False and E(M + '.search.shown') == False, "tabs, pages, search and the other bottom buttons are hidden")
check(E(M + '.scaleGrip.shown') == False, "the size grip is hidden while shrunk")
check(E('#%s.rollUp' % M) >= 9, "the roll-up list covers the four tabs, grip, backup, keep, its label and export")

# Apply still works from the bar.
inlist = E('(function() for _, f in ipairs(%s.rollUp) do if f == %s.apply then return true end end return false end)()' % (M, M))
check(E(M + '.shown') == True and E(M + '.apply.shown') is not False and not inlist, "the Apply button stays on the bar")
X('SETLOG = {}; EyeCandyDB.tiers.clarity = 2; %s.apply.scripts.OnClick(%s.apply)' % (M, M))
check(E('#SETLOG') > 0, "Apply on the bar applies your settings")

# Open it back up: same tab, full size, top-left still put.
X('%s.shrink.scripts.OnClick(%s.shrink)' % (M, M))
check(E('NS.IsShrunk()') == False and E(M + '.geo.w') == 780 and E(M + '.geo.h') == 640, "clicking again opens it to full size")
check(E(M + '.tab') == "hidden" and E(M + '.pages.hidden.shown') == True and E(M + '.search.shown') == True, "it opens on the tab you were on")
check(E(M + '.tabButtons.presets.shown') == True and E(M + '.scaleGrip.shown') == True, "the tabs and the size grip come back")
x2, y2 = E('CORNER(%s)' % M)
check(near(x2, x0) and near(y2, y0), "opening up keeps the top-left corner too")
check(E(M + '.titleText.text') == E(M + '.fullTitle'), "the full title comes back")

# Opening Eye Candy another way while shrunk opens it full size.
X('NS.ToggleShrink(); %s:Hide(); SlashCmdList.EYECANDY("")' % M)
check(E('NS.IsShrunk()') == False and E(M + '.geo.h') == 640 and E(M + '.tab') == "presets", "/ec after closing a shrunk window opens it full size")
X('NS.ShowTab("standard"); NS.ToggleShrink(); SlashCmdList.EYECANDY("")')
check(E(M + '.shown') == True and E('NS.IsShrunk()') == False and E(M + '.tab') == "standard", "/ec on a shrunk window opens it up on its tab, not closes it")
X('SlashCmdList.EYECANDY("")')
check(E(M + '.shown') == False, "/ec on the full window still closes it")
X('SlashCmdList.EYECANDY("")')

# The tooltip follows the button's new state when clicked under the mouse.
X('%s.shrink.IsMouseOver = function() return true end; GameTooltip.lines = {}; GameTooltip.AddLine = function(self, t) self.lines[#self.lines + 1] = t end' % M)
X('%s.shrink.GetScript = function(self, ev) return self.scripts[ev] end; %s.shrink.scripts.OnClick(%s.shrink)' % (M, M, M))
check(E('GameTooltip.lines[#GameTooltip.lines - 1]') == "Open up", "after a click under the mouse the tooltip says \"Open up\"")
X('%s.shrink.scripts.OnClick(%s.shrink)' % (M, M))
check(E('GameTooltip.lines[#GameTooltip.lines - 1]') == "Shrink", "and \"Shrink\" after opening it up")

X('NS.ToggleShrink(); NS.ShowTab("backups")')
check(E('NS.IsShrunk()') == False and E(M + '.pages.backups.shown') == True, "going to a tab while shrunk opens the window back up")

# A scaled window shrinks and opens without moving its top-left corner.
X('NS.SetWindowScale(%s, 0.8)' % M)
x3, y3 = E('CORNER(%s)' % M)
X('NS.ToggleShrink()')
x4, y4 = E('CORNER(%s)' % M)
check(near(x4, x3) and near(y4, y3) and near(E(M + '.geo.s'), 0.8), "at 80% the bar keeps the scale and the top-left corner")
done()
