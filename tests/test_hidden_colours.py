"""The Hidden tab uses only the colours in docs/ui-rules.md rule 20. "custom" (set by you) is gold,
"level" (set by a level) is plain white, Reset's "Click to confirm" is red, and the changed dot is
gold. None of them borrows a quality level's stripe colour (rule 20: the stripe means FPS cost).
Run: python tests/test_hidden_colours.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
# The harness drops colour calls; keep them on the widget so the checks can read them.
X('''local mt = getmetatable(CreateFrame("Frame")); local old = mt.__index
mt.__index = function(t, k)
  if k == "SetColorTexture" then return function(self, r, g, b, a) self.rgba = { r, g, b, a } end end
  if k == "SetTextColor" then return function(self, r, g, b) self.rgb = { r, g, b } end end
  return old(t, k)
end''')
X('function CLICK(b) b.scripts.OnClick(b) end')
X('function ADVROW(cvar) for _, r in ipairs(NS.advRows) do if r.d[1] == cvar then return r end end end')
X('function EXROW(key) for _, r in ipairs(NS.extraRows) do if r.ex.key == key then return r end end end')
X('C_CVar.RegisterCVar("RenderScale", "1"); C_CVar.RegisterCVar("ResampleSharpness", "0.2"); C_CVar.RegisterCVar("ResampleQuality", "1"); C_CVar.RegisterCVar("lodObjectCullDist", "20")')
X('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden")')
P = 'EyeCandyMainFrame.pages.hidden'

GOLD, WHITE, RED = "|cffffd100", "|cffffffff", "|cffff4040"
STRIPE = [E('NS.TIER_COLOURS[%d]' % i) for i in range(1, E('#NS.TIER_COLOURS') + 1)]


def no_stripe(text):
    return not any(("|c" + c) in (text or "") for c in STRIPE)


# A dial you set yourself says custom, in gold.
X('NS.SetAdvanced("lodObjectCullDist", 5); NS.RefreshUI()')
s = E('ADVROW("lodObjectCullDist").status.text')
check(s == GOLD + "custom|r", "a dial you set says custom in gold (%r)" % s)

# A dial a level sets says level, in plain white.
X('''for _, cat in ipairs(NS.CATEGORIES) do NS.db.tiers[cat.key] = #NS.TIERS end
LEVELROW = nil
for _, r in ipairs(NS.advRows) do
  if NS.db.advanced[r.d[1]] == nil and NS.TierValueFor(r.d[1]) ~= nil and NS.GetInfo(r.d[1]) ~= nil then LEVELROW = r; break end
end
NS.RefreshUI()''')
check(E('LEVELROW ~= nil'), "some dial is set by a level once every level is at the top")
s = E('LEVELROW and LEVELROW.status.text')
check(s == WHITE + "level|r", "a dial a level sets says level in white (%r)" % s)
# Back to no levels: the top ones raise render scale, and over 100% the Resample filter is greyed.
X('for _, cat in ipairs(NS.CATEGORIES) do NS.db.tiers[cat.key] = 0 end; NS.db.extras.renderScale = nil; SetCVar("RenderScale", "1"); NS.RefreshUI()')

# An Extra you set: the slider's box and the choice's value are gold, not Ultra's orange.
X('NS.db.extras.sharpness = 0.5; NS.RefreshUI()')
rgb = E('EXROW("sharpness").slider.box.rgb')
check(rgb is not None and list(rgb.values()) == [1, 0.82, 0], "a Sharpness you set has gold text in its box (%r)" % (rgb and list(rgb.values())))
X('NS.db.extras.sharpness = nil; NS.RefreshUI()')
rgb = E('EXROW("sharpness").slider.box.rgb')
check(rgb is not None and list(rgb.values()) == [0.616, 0.616, 0.616], "one you haven't set is rule 20's grey, 9d9d9d")
X('NS.db.extras.resample = EXROW("resample").ex.options[2][1]; NS.RefreshUI()')
s = E('EXROW("resample").value.text')
check(s is not None and s.startswith(GOLD), "a Resample filter you set shows its value in gold (%r)" % s)

# The colour key in the intro matches the rows.
intro = E(P + '.intro.text') or ''
check(GOLD + "custom|r = set by you" in intro and WHITE + "level|r = set by a level" in intro and RED + "kept|r" in intro,
      "the intro's key draws custom gold, level white and kept red")
check("255:209:0|t = changed from the game default" in intro, "and its dot is gold")
check(no_stripe(intro), "the intro uses no quality level's colour")

# The changed dot itself is gold, on the Hidden and Standard tabs alike.
X('DOT = NS.Dot(CreateFrame("Frame"))')
rgba = E('DOT.rgba')
check(list(rgba.values()) == [1, 0.82, 0, 1], "the changed dot is gold (%r)" % list(rgba.values()))
legend = E('EyeCandyMainFrame.pages.standard and EyeCandyMainFrame.pages.standard.legend and EyeCandyMainFrame.pages.standard.legend.text')
if legend is None:
    X('NS.ShowTab("standard"); NS.ShowTab("hidden")')
    legend = E('EyeCandyMainFrame.pages.standard.legend.text')
check("255:209:0|t" in (legend or ''), "the Standard tab's legend shows the same gold dot (%r)" % legend)

# Reset asks to confirm in red, the colour of a destructive step (rule 15), not Cinematic's.
X('CLICK(%s.resetAll)' % P)
s = E(P + '.resetAll.text')
check(s == RED + "Click to confirm|r", "Reset's confirm is red (%r)" % s)
X('CLICK(%s.resetAll)' % P)

# Nothing on the tab's rows borrows a stripe colour.
X('NS.SetAdvanced("lodObjectCullDist", 5); NS.db.extras.resample = EXROW("resample").ex.options[2][1]; NS.RefreshUI()')
texts = E('''(function() local t = {}
for _, r in ipairs(NS.advRows) do t[#t + 1] = r.status.text or "" end
for _, r in ipairs(NS.extraRows) do t[#t + 1] = r.status.text or ""; if r.value then t[#t + 1] = r.value.text or "" end end
return table.concat(t, "\\n") end)()''')
check(no_stripe(texts), "no Hidden row's words use a quality level's colour")
done()
