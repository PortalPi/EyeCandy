"""A built-in preset hands back the Extras the last built-in set (render scale override, resample,
sharpness, far character detail), and keeps the ones you set yourself. ns.db.presetExtras records
what the last built-in set; one still at that value goes, one you changed since is yours.
ns.PresetValues gives what applying gives.
Run: python tests/test_preset_extras.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
X('EX = {}; for _, ex in ipairs(NS.EXTRAS) do EX[ex.key] = ex end')
g = lambda c: E('GetCVar("%s")' % c)
ex = lambda k: E('NS.db.extras.%s' % k)
apply = lambda pid: X('NS.ApplyPresetById("%s")' % pid)
# Yours, on the Hidden tab: set, then Apply.
mine = lambda k, v: X('NS.SetExtra(EX.%s, %s); NS.ApplyAll(false, true)' % (k, v))
none_left = lambda: E('next(NS.db.extras) == nil')
# Before Eye Candy (the harness's start values, kept in the Original backup).
BEFORE = {"ResampleQuality": "3", "ResampleSharpness": "0.2", "entityLodDist": "10"}
HIGH_SCALE = E('tostring(NS.CATEGORIES[1].cvars[1][3][3])')
check(E('NS.CATEGORIES[1].cvars[1][1]') == "RenderScale", "set up: the first row is render scale")

# 1. A Look, then a quality level: the Look's Extras go, the level's render scale goes on, and the
# others go back to your value from before Eye Candy.
apply("look:moody")
check(ex("renderScale") == 1.5 and g("RenderScale") == "1.5", "Moody sets its render scale")
apply("tier3")
check(none_left(), "Moody then High: none of Moody's Extras stay (%r)" % dict(E('NS.db.extras').items()))
check(g("RenderScale") == HIGH_SCALE, "and render scale is High's (%r, want %r)" % (g("RenderScale"), HIGH_SCALE))
check(all(g(c) == v for c, v in BEFORE.items()), "and resample, sharpness and character detail are back to before (%r)" % {c: g(c) for c in BEFORE})

# 2. Showcase, then a quality level.
apply("tier6")
check(ex("renderScale") == 2, "Showcase sets its render scale")
apply("tier4")
check(none_left() and g("RenderScale") == E('tostring(NS.CATEGORIES[1].cvars[1][3][4])'), "Showcase then Ultra: Showcase's Extras go, render scale is Ultra's (%r)" % g("RenderScale"))

# 3. Between two Looks: Moody, then Capital city (only character detail of its own).
apply("look:moody")
apply("look:city")
check(ex("renderScale") is None and ex("resample") is None and ex("sharpness") is None, "Moody then Capital city: Moody's render scale, resample and sharpness go")
check(ex("entityLod") == 10 and g("entityLodDist") == "10", "and character detail is Capital city's")
check(g("RenderScale") == HIGH_SCALE and g("ResampleQuality") == "3", "render scale is High's (Capital city's base) and resample is back to before")
apply("tier3")
check(none_left(), "Capital city then High: its character detail goes too")

# 4. Yours stay: one a preset doesn't set, and one you changed after the preset set it.
mine("resample", 1)
apply("look:city")
apply("tier3")
check(ex("resample") == 1 and g("ResampleQuality") == "1", "your resample, set on the Hidden tab, stays through a Situation and a quality level")
apply("look:moody")
check(ex("resample") == 2, "a Look's own Extra replaces yours")
mine("sharpness", 0.8)
apply("tier3")
check(ex("sharpness") == 0.8 and g("ResampleSharpness") == "0.8", "sharpness you changed after Moody is yours: it stays")
check(ex("renderScale") is None and ex("resample") is None and ex("entityLod") is None, "Moody's others go")
X('NS.SetExtra(EX.sharpness, nil); NS.ApplyAll(false, true)')

# 5. A render scale override of yours stays through a quality level, and PresetValues says so.
mine("renderScale", 1.2)
X('PV = NS.PresetValues("tier4")')
check(E('PV.RenderScale') == "1.2", "PresetValues for Ultra gives your render scale override (%r)" % E('PV.RenderScale'))
apply("tier4")
check(g("RenderScale") == "1.2", "and applying Ultra keeps it")
X('NS.SetExtra(EX.renderScale, nil); NS.ApplyAll(false, true)')
apply("tier3")

# 6. PresetValues gives what applying gives, from a Look and from Showcase.
for start, pid in (("look:moody", "tier3"), ("tier6", "tier2"), ("look:moody", "look:city"), ("look:laptop", "tier5")):
    apply(start)
    X('SET = {}; for key in pairs(NS.db.presetExtras) do SET[#SET + 1] = EX[key].cvar end')
    X('PV = NS.PresetValues("%s"); CHAT = {}' % pid)
    apply(pid)
    X('BAD = {}; for cvar, v in pairs(PV) do local now = GetCVar(cvar); if now ~= nil and not NS.Same(now, v) then BAD[#BAD + 1] = cvar .. "=" .. tostring(v) .. " got " .. tostring(now) end end')
    said = " ".join(str(E('CHAT[%d]' % i)) for i in range(1, E('#CHAT') + 1))
    bad = [b for b in (E('BAD[%d]' % i) for i in range(1, E('#BAD') + 1)) if ("asked " + b.split("=")[1].split(" ")[0]) not in said]
    check(not bad, "%s then %s: applying sets each value PresetValues gave (%r)" % (start, pid, bad))
    cvars = [E('SET[%d]' % i) for i in range(1, E('#SET') + 1)]
    check(len(cvars) >= 2 and all(E('PV.%s' % c) is not None and E('NS.Same(PV.%s, GetCVar("%s"))' % (c, c)) for c in cvars),
          "%s then %s: PresetValues names each Extra %s set, at what applying gives (%r)" % (start, pid, start, cvars))
X('NS.SetExtra(EX.resample, nil); NS.ApplyAll(false, true)')
apply("tier3")

# 7. Back to before puts the record back with the choices, so yours from before stay yours.
# Your resample at Bicubic (2), the same as Moody's: Back to before Moody, then a quality level, keeps it.
mine("resample", 2)
apply("tier3")
apply("look:moody")
X('BK1, BK2 = NS.GoBack(1)')
check(E('BK1') is not None and ex("resample") == 2 and ex("renderScale") is None, "Back to before Moody: your resample is back, Moody's render scale gone (%r)" % E('BK2'))
apply("tier4")
check(ex("resample") == 2 and g("ResampleQuality") == "2", "then Ultra keeps your resample (%r)" % ex("resample"))
X('NS.SetExtra(EX.resample, nil); NS.ApplyAll(false, true)')

# 8. Your own preset clears the Extras and the record: a render scale you set after it is yours.
apply("look:moody")
X('MINE = NS.SaveCurrentAsPreset("Mine"); NS.ApplyPresetById(MINE.id)')
check(none_left() and E('next(NS.db.presetExtras or {}) == nil'), "your preset clears the Extras and the record")
mine("renderScale", 1.5)
apply("tier3")
check(ex("renderScale") == 1.5, "a render scale you set after your preset stays through High, even at Moody's 150%")
X('NS.SetExtra(EX.renderScale, nil); NS.ApplyAll(false, true)')

# 9. A restore from an older version has no record: a Look's Extras are worked out from its Look.
apply("tier3")
apply("look:moody")
X('S = NS.db.steps[1]; S.state.presetExtras = nil; for k in pairs(S.state.extras) do S.state.extras[k] = nil end')
X('S.state.extras.renderScale = 1.5; S.state.look = "moody"')
X('NS.GoBack(1)')
apply("tier3")
check(ex("renderScale") is None, "a step saved on Moody with no record (made up here, as an older version saved it), put back: Moody's render scale still goes on High")

# 10. An Extra you set back to "Use tier" while its setting still holds the Look's value: handed back.
apply("look:moody")
X('NS.SetExtra(EX.sharpness, nil); NS.ApplyAll(false, true)')
check(g("ResampleSharpness") == "0.5", "set up: sharpness on Use tier still holds Moody's 0.5")
X('PV = NS.PresetValues("tier3")')
apply("tier3")
check(g("ResampleSharpness") == "0.2" and E('PV.ResampleSharpness') == "0.2", "then High hands it back to before, and PresetValues says so (%r, %r)" % (g("ResampleSharpness"), E('PV.ResampleSharpness')))

# 11. A saved file from before the record was kept, on Moody: worked out at login.
old = boot(svdb='EyeCandyDB = { tiers = {}, extras = { renderScale = 1.5, resample = 2, sharpness = 0.5, entityLod = 20 }, advanced = {}, look = "moody", keepApplied = true }')
old.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); NS.ApplyPresetById("tier3")')
check(old.eval('next(NS.db.extras) == nil'), "a saved file on Moody with no record: High still hands back Moody's Extras")
done()
