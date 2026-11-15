"""The Presets list keeps its groups 24 apart, on the 4/8/16/24 spacing scale (docs/ui-rules.md
rule 12 and the checklist): rows are 4 apart, so a group sits six row gaps from the one above it.
Run: python tests/test_group_gap.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X("""
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "SetPoint" then
    return function(self, p, x, y) if p == "TOPLEFT" and type(x) == "number" then self.pt = { x, y } end end
  end
  return index(t, k)
end
""")
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'

ROW_H, ROW_GAP, GAP = 34, 4, 24
names = [E('%s.headers[%d].label.text' % (P, i)) for i in range(1, E('#%s.headers' % P) + 1)]
heads = [-E('%s.headers[%d].pt[2]' % (P, i)) for i in range(1, len(names) + 1)]
tops = sorted(E('%s.rows[%d].top' % (P, i)) for i in range(1, E('#%s.rows' % P) + 1) if E('%s.rows[%d].shown' % (P, i)))
check(len(heads) >= 4 and len(tops) > 10, "the list shows its groups and rows (%d headings, %d rows)" % (len(heads), len(tops)))

# Rows inside a group are 4 apart.
# (The Capital city row has its 40px switch under it, so its next row is 44 down.)
inside = {b - a - ROW_H for a, b in zip(tops, tops[1:]) if not any(a < h < b for h in heads)}
check(ROW_GAP in inside and inside <= {ROW_GAP, ROW_GAP + 40}, "rows inside a group are %d apart (%s)" % (ROW_GAP, sorted(inside)))

# Each group after Quality levels follows a row: its heading starts 24 under that row's 4 gap.
for name, h in zip(names[2:], heads[2:]):
    above = max(t for t in tops if t < h)
    space = h - (above + ROW_H + ROW_GAP)
    check(space == GAP, "%s starts %d under the row above it (%d)" % (name, GAP, space))
done()
