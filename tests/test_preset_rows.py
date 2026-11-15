"""A preset row's name: the box and the cut agree (UI rule 16), the grey line starts clear of it, and
the full name is in the tooltip. The harness has no font metrics, so GetStringWidth is stubbed:
6.5 a character, 11 for a W, 3.5 for a dot (GetStringWidth stops at the box's width, as in the
game; GetUnboundedStringWidth does not). Run: python tests/test_preset_rows.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X("""
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
MEASURE = false
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  if k == "SetWidth" then return function(self, w) self.w = w end end
  if (k == "GetStringWidth" or k == "GetUnboundedStringWidth") and MEASURE then
    return function(self)
      local w = 0
      for ch in (self.text or ""):gmatch(".") do w = w + (ch == "W" and 11 or ch == "." and 3.5 or 6.5) end
      -- Like the game: GetStringWidth stops at the box's width, the unbounded one does not.
      if k == "GetStringWidth" and self.w then w = math.min(w, self.w) end
      return w
    end
  end
  if k == "SetPoint" then
    return function(self, p, x, y) if p == "LEFT" and type(x) == "number" then self.left = x end end
  end
  return index(t, k)
end
""")
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'


def row(name):
    for i in range(1, E('#%s.rows' % P) + 1):
        if E('%s.rows[%d].p.name' % (P, i)) == name and E('%s.rows[%d].shown' % (P, i)):
            return '%s.rows[%d]' % (P, i)


def refresh():
    X('NS.RefreshUI()')


FIFTY = "A very long preset name that goes on and"  # 40 characters
r = row("High")
check(E(r + '.name.w') == 180 and E(r + '.name.left') == 14, "the name box is 180 wide from x 14")
check(E(r + '.line.left') >= E(r + '.name.left') + E(r + '.name.w'), "the grey line starts clear of the name box (%s)" % E(r + '.line.left'))

# The longest built-in name fits whole.
longest = max((E('NS.ListPresets().builtin[%d].name' % i) for i in range(1, E('#NS.ListPresets().builtin') + 1)), key=len)
check(E(row(longest) + '.name.text') == longest, "the longest built-in name (%s) shows whole" % longest)

# A 40-character name: ShortName and the box agree at 26 characters, ending in ...
X('LONG = NS.SaveCurrentAsPreset("%s")' % FIFTY)
rl = row(FIFTY)
shown = E(rl + '.name.text')
check(shown == FIFTY[:25] + "...", "a 40-character name is cut to 25 characters and ... (%r)" % shown)
px = 25 * 6.5 + 3 * 3.5
check(px <= 180, "that is about %.0fpx, inside the 180px box" % px)
X('GameTooltip.AddLine = function(self, t) TIPLINE = TIPLINE or t end; TIPLINE = nil; %s.scripts.OnEnter(%s)' % (rl, rl))
check(E('TIPLINE') == FIFTY, "the row's tooltip carries the full name")
X('GameTooltip.AddLine = nil')

# Measured: a name of wide letters is cut again until it fits the box.
X('MEASURE = true; WIDE = NS.SaveCurrentAsPreset(string.rep("W", 40)); NS.RefreshUI()')
rw = row("W" * 40)
shown = E(rw + '.name.text')
w = sum(11 if c == "W" else 3.5 if c == "." else 6.5 for c in shown)
check(shown.endswith("...") and w <= 180, "a name of wide letters is cut to fit (%r, %.1fpx)" % (shown, w))
rn = row(FIFTY)
check(E(rn + '.name.text') == FIFTY[:25] + "...", "normal letters keep the 26-character cut when measured")
done()
