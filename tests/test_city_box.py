"""The "Lower settings in capital cities" box says on the screen what it does (UI rule 23: nothing needed
lives only in a tooltip), in grey, under the box and clear of the next row.
Run: python tests/test_city_box.py"""
from lib import boot, check, done, addon

lua = boot()
E, X = lua.eval, lua.execute
X("""
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  if k == "SetTextColor" then return function(self, r, g, b) self.colour = { r, g, b } end end
  if k == "SetHeight" then return function(self, h) self.hh = h end end
  if k == "SetPoint" then
    local sp = index(t, k)
    return function(self, p, x, y) if p == "TOPLEFT" and type(x) == "number" then self.pt = { x, y } end end
  end
  return index(t, k)
end
""")
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'
box = P + '.cityBox'
note = box + '.note'
LINE = "In a capital city, lowers some costly settings where yours are higher. They go back when you leave."

check(E(note + '.shown') == True and E(note + '.text') == LINE, "a line under the city box says what it does (%r)" % E(note + '.text'))
check(E(note + '.colour[1]') == 0.62 and E(note + '.colour[3]') == 0.62, "the line is grey")
check(E(note + '.pt[2]') == E(box + '.pt[2]') - 20 and E(note + '.pt[1]') > E(box + '.pt[1]'), "the line sits under the box, in line with its text")

# True to Situations.lua: only where yours are higher, put back on leaving.
src = open(addon + 'Situations.lua', encoding='utf-8').read()
check("only where yours are higher" in src and "each one goes back to what it was" in src, "Situations.lua lowers only where yours are higher, and puts them back on leaving")
check("capital city" in LINE and "higher" in LINE and "go back when you leave" in LINE, "the line says where, how and when it undoes")

# The row after Capital city starts clear of the line.
X("""
NOTE_TOP = %s.pt[2]
local pg = EyeCandyMainFrame.pages.presets
NEXTTOP = 1e9
for _, r in ipairs(pg.rows) do if r.shown and r.top > -NOTE_TOP and r.top < NEXTTOP then NEXTTOP = r.top end end
for _, h in ipairs(pg.headers) do if h.shown and h.pt and -h.pt[2] > -NOTE_TOP and -h.pt[2] < NEXTTOP then NEXTTOP = -h.pt[2] end end
""" % note)
nxt = E('NEXTTOP') if E('NEXTTOP') < 1e9 else E('EyeCandyMainFrame.pages.presets.content.hh')
check(nxt >= -E('NOTE_TOP') + 12, "whatever comes next, or the end of the list, is below the line (at %s, line at %s)" % (nxt, -E('NOTE_TOP')))

# Hidden with the box when the city row is not shown.
X('NS.ListPresets = function() return { user = {}, builtin = {} } end; NS.RefreshUI()')
check(E(box + '.shown') == False and E(note + '.shown') == False, "no Capital city row: the box and its line are hidden")
done()
