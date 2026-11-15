"""The Import strip grows to fit its preview text (UI rule 16), and the list under it moves down by
the same amount. The harness has no font metrics, so GetStringHeight is stubbed: 12 a line, a line
wraps at 110 characters (colour codes not counted).
Run: python tests/test_import_strip.py"""
from lib import boot, check, done, GEO

lua = boot()
E, X = lua.eval, lua.execute
X(GEO)
X("""
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
MEASURE = false
mt.__index = function(t, k)
  if k == "GetStringHeight" and MEASURE then
    return function(self)
      local n = 0
      for line in ((self.text or "") .. "\\n"):gmatch("(.-)\\n") do
        local plain = line:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
        n = n + math.max(1, math.ceil(#plain / 110))
      end
      return 12 * n
    end
  end
  if k == "SetPoint" then
    local sp = index(t, k)
    return function(self, p, rel, rp, x, y)
      if p == "TOPLEFT" and type(rel) == "number" then self.pt = { rel, rp } end
      return sp(self, p, rel, rp, x, y)
    end
  end
  return index(t, k)
end
""")
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'
S = P + '.strip'

# A preview with a long name line, eight skipped settings with long names and a clash: four or more lines.
X("""
NAMES = {}
for i = 1, 8 do NAMES[i] = "someRatherLongSettingNameNumber" .. i .. " (not supported by your GPU)" end
NS.PreviewImport = function() return { ok = true, name = "A friend's preset", author = "SomeoneWithALongName",
  date = "2026-11-01", gameVersion = "12.0.5", changes = { a = 1, b = 2 }, skipped = NAMES, clash = true } end
""")


def headingY():
    return E(P + '.headers[2].pt[2]')


def fits():
    # The strip ends 6 under its text, which starts at 56: no spare space, no floor.
    return 56 + E('%s.result.GetStringHeight(%s.result)' % (S, S)) + 6


# Not measurable (the harness): 12px a line of text.
X('%s.box.text = "code"; NS.UpdateImportStrip(%s)' % (S, P))
lines = E(S + '.result.text').count("\n") + 1
hU = E(S + '.h')
check(hU == 56 + lines * 12 + 6, "unmeasured text: 12px a line, %d lines (%s)" % (lines, hU))
check(E(S + '.geo.h') == hU, "the frame is sized to match")
yU = headingY()

# Measured: a short preview fits in 92, a long one grows.
X("MEASURE = true")
X('NS.PreviewImport = nil; %s.box.text = ""; NS.UpdateImportStrip(%s)' % (S, P))
# Empty: the strip is as tall as its content. Box top 28 + box height 22 + 8 spacing = 58, no spare space.
check(E(S + '.h') == 58, "empty box: the strip is as tall as its content, 58 (%s)" % E(S + '.h'))
check(E(S + '.geo.h') == 58, "empty box: the frame is 58 tall")
check(E(S + '.result.text') == "", "empty box: no result text")
y58 = headingY()
check(y58 is not None and yU is not None and y58 == yU + (hU - 58),
      "empty box: the list below came up with the strip (%s vs %s)" % (y58, yU))
X("""NS.PreviewImport = function() return { ok = true, name = "Short", changes = { a = 1 }, skipped = {}, clash = false } end""")
X('%s.box.text = "code"; NS.UpdateImportStrip(%s)' % (S, P))
check(E(S + '.h') == fits() and E(S + '.h') < 92, "a short preview fits its text, with no spare space (%s)" % E(S + '.h'))
X("""
NS.PreviewImport = function() return { ok = true, name = "A friend's preset", author = "SomeoneWithALongName",
  date = "2026-11-01", gameVersion = "12.0.5", changes = { a = 1, b = 2 }, skipped = NAMES, clash = true } end
""")
X('%s.box.text = "code2"; NS.UpdateImportStrip(%s)' % (S, P))
used = E('%s.result.GetStringHeight(%s.result)' % (S, S))
check(used > 36, "the long preview needs more than three lines (%s px)" % used)
h = E(S + '.h')
check(h == 56 + used + 6 and h > 92, "the strip grows to fit it: %s tall for %s px of text" % (h, used))
check(E(S + '.geo.h') == h, "the frame is sized to match")
check(headingY() == y58 - (h - 58) if headingY() is not None and y58 is not None else False,
      "the next heading moved down by the growth (%s -> %s)" % (y58, headingY()))

# A bad code message is one line again: the strip shrinks to fit it and the list comes up.
X('NS.PreviewImport = nil; %s.box.text = "hello"; NS.UpdateImportStrip(%s)' % (S, P))
one = E(S + '.h')
check(one == 56 + 12 + 6 and headingY() == y58 - (one - 58), "a one-line message: the strip is one line under the box, no spare space (%s)" % one)

# Cleared: the long preview, then an empty box. The strip shrinks to its content again.
X('NS.PreviewImport = function() return { ok = true, name = "A friend\'s preset", author = "SomeoneWithALongName", date = "2026-11-01", gameVersion = "12.0.5", changes = { a = 1, b = 2 }, skipped = NAMES, clash = true } end')
X('%s.box.text = "code2"; NS.UpdateImportStrip(%s)' % (S, P))
check(E(S + '.h') > 92, "long preview again: the strip is tall (%s)" % E(S + '.h'))
X('NS.PreviewImport = nil; %s.box.text = ""; NS.UpdateImportStrip(%s)' % (S, P))
check(E(S + '.h') == 58 and E(S + '.geo.h') == 58 and headingY() == y58, "cleared: the strip shrinks back to 58 and the list comes up")
X('%s.box.text = "hello"; NS.UpdateImportStrip(%s)' % (S, P))

# An error from the Import button also fits.
X("""NS.ImportPreset = function() return nil, string.rep("This code is no good because of reasons. ", 6) end""")
X('%s.import.scripts.OnClick(%s.import)' % (S, S))
check(E(S + '.h') > 92 and "no good" in E(S + '.result.text'), "a long error from Import makes the strip grow (%s)" % E(S + '.h'))
done()
