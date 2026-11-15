"""The Hidden tab's row names (docs/ui-rules.md): white, not gold (rule 20), and never wrapped
(rule 16): a name too long for its box is cut, and the tooltip has it in full.
Run: python tests/test_hidden_names.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
# Record each FontString's font and word wrap (the harness drops both). The Hidden tab is built
# when it is first shown, so this is in place before its rows exist.
X('''
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "CreateFontString" then
    return function(_, _, _, font)
      local fs = index(t, k)()
      fs.font, fs.wrap = font, true
      fs.SetWordWrap = function(self, on) self.wrap = on end
      fs.SetFontObject = function(self, f) self.font = f end
      return fs
    end
  end
  return index(t, k)
end''')
X('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden"); NS.RefreshUI()')

def rows(kind):
    return [(E('NS.%s[%d].label.text' % (kind, i)), E('NS.%s[%d].label.font' % (kind, i)), E('NS.%s[%d].label.wrap' % (kind, i)))
            for i in range(1, E('#NS.%s' % kind) + 1)]

levels, extras, dials = rows('tierRows'), rows('extraRows'), rows('advRows')
check(len(levels) > 5 and len(extras) > 2 and len(dials) > 40, "the Hidden tab has its level, setting and dial rows (%d, %d, %d)" % (len(levels), len(extras), len(dials)))
gold = [t for t, f, w in levels + extras if f != "GameFontHighlight"]
check(not gold, "level and setting row names are white, not gold (%s)" % gold[:3])
wraps = [t for t, f, w in levels + extras + dials if w is not False]
check(not wraps, "no Hidden row name wraps (%s)" % wraps[:3])
done()
