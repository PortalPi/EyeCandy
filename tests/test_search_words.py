"""Checks the search box tooltip: no internal word on screen (rule 2) and every example it gives
really finds something. Run: python tests/test_search_words.py"""
import re
from lib import boot, check, done

lua = boot()
lua.execute("""
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
local over = { GetText = function(self) return self.text end }
mt.__index = function(t, k) if over[k] then return over[k] end return index(t, k) end
GameTooltip.AddLine = function(self, t) self.lines = self.lines or {}; self.lines[#self.lines + 1] = t end
GameTooltip.SetOwner = function(self) self.lines = {} end
FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("")
""")
E = lua.eval
lua.execute('EyeCandySearchBox.scripts.OnEnter(EyeCandySearchBox)')
body = E('table.concat(GameTooltip.lines, " | ")')
check("Type part of a name" in body, "the search tooltip opens: %s" % body)
check(not re.search(r"\blod\b", body, re.I), "the search tooltip never says LOD (rule 2)")
m = re.search(r"for example (.+?)\.", body)
check(m is not None, "the tooltip gives examples")
words = re.split(r",\s*|\s+or\s+", m.group(1)) if m else []
check(len(words) >= 2, "it gives at least two examples: %s" % words)
for w in words:
    counts = lua.eval('NS.SetSearch("%s")' % w)
    n = counts["standard"] + counts["hidden"]
    check(n > 0, "searching '%s' finds something (%d)" % (w, n))
lua.execute('NS.SetSearch("")')
done()
