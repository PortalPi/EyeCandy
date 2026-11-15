"""Headings: ns.Header is as tall as its note's wrapped text (UI rule 16: nothing overlaps by accident).
The harness has no font metrics, so GetStringHeight is stubbed: 12 a line, wrapped at 100 characters.
Run: python tests/test_headers.py"""
from lib import boot, check, done, GEO

lua = boot()
E, X = lua.eval, lua.execute
X(GEO)
STUB = """
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetStringHeight" and MEASURE then
    return function(self) return 12 * math.ceil(#(self.text or "") / 100) end
  end
  return index(t, k)
end
content = CreateFrame("Frame")
"""
X(STUB)
LONG = "x" * 165

# The harness measures nothing: one line.
check(E('select(2, NS.Header(content, "A", "short"))') == 52, "unmeasured note: one line, 52 tall as before")
check(E('select(2, NS.Header(content, "A"))') == 36, "no note: 36 tall")

X("MEASURE = true")
check(E('select(2, NS.Header(content, "A", "short"))') == 52, "a one-line note keeps the 52px header")
check(E('select(2, NS.Header(content, "A"))') == 36, "no note still 36")
h = E('select(2, NS.Header(content, "A", "%s"))' % LONG)
check(h == 64, "a 165-character note wraps to two lines, 12 taller (%s)" % h)
X('H = NS.Header(content, "A", "%s")' % LONG)
check(E("H.geo.h") == 64, "the frame itself is sized to the returned height")
h3 = E('select(2, NS.Header(content, "A", "%s"))' % ("y" * 250))
check(h3 == 76, "three lines: 76 (%s)" % h3)
# the real Ambient Occlusion note in Advanced.lua
X("""
local grp
for _, g in ipairs(NS.ADVANCED) do if g.key == "ao" then grp = g end end
AO = grp.note
""")
check(E("#AO") > 100, "the Ambient Occlusion note is longer than one line")
check(E("select(2, NS.Header(content, 'AO', AO))") == 64, "the Ambient Occlusion header has room for two lines")
done()
