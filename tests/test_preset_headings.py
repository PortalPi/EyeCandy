"""The Presets list headings are ns.Header (UI rule 11), spaced by rule 12, and the Save button
sits on the Your presets heading. Run: python tests/test_preset_headings.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X("""
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  if k == "SetParent" then return function(self, p) self.parent = p end end
  if k == "SetPoint" then
    return function(self, p, x, y)
      if p == "TOPLEFT" and type(x) == "number" then self.pt = { x, y } end
      if p == "TOPRIGHT" and type(x) == "number" then self.ptr = { x, y } end
    end
  end
  return index(t, k)
end
-- Count what ns.Header builds.
HEADERS = {}
local real = NS.Header
NS.Header = function(...) local f, h = real(...); HEADERS[#HEADERS + 1] = f; return f, h end
""")
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'

check(E('#HEADERS') == 4, "the four list headings come from ns.Header (%d built)" % E('#HEADERS'))
for i, t in enumerate(["Your presets", "Quality levels", "Looks", "Situations"], 1):
    check(E('HEADERS[%d].label.text' % i) == t and E('%s.headers[%d] == HEADERS[%d]' % (P, i, i)) is True, "heading %d is %s" % (i, t))
check(E('HEADERS[1].note') is None and E('HEADERS[2].note.text') == "Every system at one level.",
      "Your presets has no note; the others keep theirs, under the rule")

# One left edge; each heading starts 24 (GROUP_GAP, rule 12) below the content above it.
check(all(E('%s.headers[%d].pt[1]' % (P, i)) == 0 for i in range(1, 5)), "every heading starts at the left edge")
y = [-E('%s.headers[%d].pt[2]' % (P, i)) for i in range(1, 5)]
check(y[0] == 0 and y[0] < y[1] < y[2] < y[3], "headings run down the page in order (%s)" % y)
# Your presets (36 tall, no note) then an empty note, the empty line, the strip (2 + its height), then 24.
strip_end = -E('%s.strip.pt[2]' % P) + E('%s.strip.h' % P)
check(y[1] == strip_end + 24, "Quality levels starts 24 below the Import strip (%s vs %s)" % (y[1], strip_end + 24))
# Quality levels' note makes it 52 tall: its first row starts at heading + 52.
first_tier = min(E('%s.rows[%d].top' % (P, i)) for i in range(1, E('#%s.rows' % P) + 1) if E('%s.rows[%d].top' % (P, i)) > y[1])
check(first_tier == y[1] + 52, "the first quality level starts right under its heading (52 tall)")

# The Save button sits on the Your presets heading: its right end, clear of the rule at 32.
check(E('%s.saveButton.parent == HEADERS[1]' % P) is True, "Save is a child of the Your presets heading")
check(E('%s.saveButton.ptr[1]' % P) == -4 and E('%s.saveButton.ptr[2]' % P) == -6, "Save is at the top right, 6 down (the rule is at 32)")
done()
