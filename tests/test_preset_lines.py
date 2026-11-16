"""Each Look and Situation row's grey line is its description's first sentence, and the line does
not wrap, so that sentence must be short enough to show whole (docs/ui-rules.md rule 16). The full
text stays in the tooltip.
Run: python tests/test_preset_lines.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN")')
X('''
LINES = {}
for _, p in ipairs(NS.ListPresets().builtin) do
  if p.group == "Looks" or p.group == "Situations" then
    LINES[#LINES + 1] = tostring(p.name) .. "\\1" .. NS.PresetLine(p) .. "\\1" .. tostring(p.desc)
  end
end
''')
rows = [E('LINES[%d]' % i).split("\1") for i in range(1, E('#LINES') + 1)]
check(len(rows) >= 8, "every built-in Look and Situation is walked (%d)" % len(rows))
# 50 characters: the longest that shows whole on the tightest row, a guess from the font. The line
# runs from x 204 to 10px before the tag, and a row that is On now with changes has the widest tag
# ("On now (12 changed)"), leaving about 275px, about 50 characters at 5.5px each.
long = [(n, len(l), l) for n, l, d in rows if len(l) > 50]
check(not long, "every row line is 50 characters or fewer, so none is cut even beside the widest tag (%r)" % long)
classic = next((l for n, l, d in rows if n == "Classic"), None)
check(classic == "Closer to how WoW used to feel.", "Classic's line is whole: %r" % classic)
cdesc = next((d for n, l, d in rows if n == "Classic"), "")
check("Low bloom, sparse grass" in cdesc and "only close" in cdesc, "and its full description is still there for the tooltip")
done()
