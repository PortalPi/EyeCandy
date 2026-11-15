"""Checks that the search count sits between the last tab and the search box (rule 19, rule 16).
Run: python tests/test_search_count.py"""
from lib import boot, check, done

lua = boot()
# The harness keeps no geometry, so record what the window build asks for.
lua.execute("""
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
local over = {
  SetSize = function(self, w, h) self.w, self.h = w, h end,
  SetPoint = function(self, p, rel, rp, x, y)
    self.pts = self.pts or {}; self.pts[#self.pts + 1] = { p = p, rel = rel, rp = rp, x = x, y = y }
  end,
  SetWordWrap = function(self, v) self.wordWrap = v end,
  SetJustifyH = function(self, v) self.justify = v end,
}
mt.__index = function(t, k) if over[k] then return over[k] end return index(t, k) end
FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("")
""")
E = lua.eval
keys = ["presets", "standard", "hidden", "backups", "autotune"]

# Walk the tab row from its first anchor to the last tab's right edge.
x = None
for i, k in enumerate(keys):
    w = E('EyeCandyMainFrame.tabButtons.%s.w' % k)
    pt = E('EyeCandyMainFrame.tabButtons.%s.pts[1]' % k)
    if i == 0:
        x = pt["rel"]                                 # SetPoint("TOPLEFT", 14, -28)
    else:
        x += pt["x"]
    x += w
last_right = x
win_w = E('EyeCandyMainFrame.w')
search_w = E('EyeCandySearchBox.w')
sp = E('EyeCandySearchBox.pts[1]')
search_left = win_w + sp["rel"] - search_w        # SetPoint("TOPRIGHT", -20, -30)

pts = {E('EyeCandyMainFrame.searchCount.pts[%d].p' % i): i for i in (1, 2)}
check(set(pts) == {"LEFT", "RIGHT"}, "the count is held by a left and a right anchor, so it cannot spill (%s)" % list(pts))
left = E('EyeCandyMainFrame.searchCount.pts[%d]' % pts["LEFT"])
right = E('EyeCandyMainFrame.searchCount.pts[%d]' % pts["RIGHT"])
check(E('EyeCandyMainFrame.searchCount.pts[%d].rel == EyeCandyMainFrame.tabButtons.autotune' % pts["LEFT"]) and left["rp"] == "RIGHT", "the count starts at the last tab's right edge")
check(E('EyeCandyMainFrame.searchCount.pts[%d].rel == EyeCandySearchBox' % pts["RIGHT"]) and right["rp"] == "LEFT", "the count ends at the search box's left edge")
room = (search_left + right["x"]) - (last_right + left["x"])
check(room >= 130, "the count has room for 'Standard 12, Hidden 34' at about 5.5px a character: %spx" % room)
check(last_right < search_left, "the last tab (right edge %s) ends before the search box (left edge %s)" % (last_right, search_left))
check(E('EyeCandyMainFrame.searchCount.wordWrap') == False, "the count does not wrap")
check(E('EyeCandyMainFrame.searchCount.justify') == "RIGHT", "the count is right-justified against the search box")
for k in keys:
    check(E('EyeCandyMainFrame.tabButtons.%s.w' % k) >= 70, "tab %s is wide enough for its label" % k)

lua.execute('NS.SetSearch("grass")')
check("Standard" in E('EyeCandyMainFrame.searchCount.text') and "Hidden" in E('EyeCandyMainFrame.searchCount.text'), "the count still says both tabs")
done()
