"""The Hidden tab's words (docs/ui-rules.md rule 2): a system's level row says "<System> level",
not "Tier"; Extras and dials are both "setting"; no LOD or profile on screen. The intro says which
settings wait for Apply, and a level or setting you changed says "not applied yet" until Apply
(rule 4). The list starts under the intro, however long it is.
Run: python tests/test_hidden_words.py"""
import re
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
# The intro is measured when the tab is built: give its FontString a height (3 lines of 12px).
X('''local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "CreateFontString" then
    return function() local fs = index(t, k)(); fs.GetStringHeight = function() return INTRO_H end; return fs end
  end
  return index(t, k)
end
INTRO_H = 50''')
X('C_CVar.RegisterCVar("RenderScale", "1"); C_CVar.RegisterCVar("ResampleSharpness", "0.2")')
X('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden"); NS.RefreshUI()')
X('TIPS = {}; GameTooltip.AddLine = function(_, t) if t then TIPS[#TIPS + 1] = tostring(t) end end')
X('function HOVER(f) if f and f.scripts and f.scripts.OnEnter then f.scripts.OnEnter(f) end end')
page = 'EyeCandyMainFrame.pages.hidden'

check(E(page + '.listTop') == 60, "the list starts under a 50px intro (%r)" % E(page + '.listTop'))

# Setting names are not words a player reads as names; take each one out before looking.
CVARS = set(E('''(function() local t = {}
  for _, d in ipairs(NS.AdvancedCVars()) do t[#t + 1] = d[1] end
  for _, ex in ipairs(NS.EXTRAS) do t[#t + 1] = ex.cvar end
  for _, c in ipairs(NS.CATEGORIES) do for _, r in ipairs(c.cvars) do t[#t + 1] = r[1] end end
  return table.concat(t, " ") end)()''').split())
BANNED = re.compile(r'\b(tiers?|dials?|LOD|profile)\b|\bExtras?\b|\bextras\b', re.I)
# Plain English, not the old names: "extra sharpness" is Blizzard's CMAA 2 setting, the
# terrain detail note quotes Blizzard's old docs word for word, and Entity LoD is an addon's name.
ALLOWED = ['extra sharpness', "render the lowest LOD for terrain", "(Entity LoD)"]


def bad_words(text):
    t = re.sub(r'\|c[0-9a-fA-F]{8}|\|r', '', text or '')
    for a in ALLOWED:
        t = t.replace(a, '')
    for c in sorted(CVARS, key=len, reverse=True):
        t = t.replace(c, '')
    return BANNED.findall(t)


def collect():
    texts = [('intro', E(page + '.intro and ' + page + '.intro.text'))]
    for i in range(1, E('#NS.TAB_LIST.hidden.items') + 1):
        f = 'NS.TAB_LIST.hidden.items[%d].frame' % i
        for part in ('label', 'note', 'status', 'value'):
            t = E('%s.%s and %s.%s.text' % (f, part, f, part))
            if t:
                texts.append(('%s.%s' % (f, part), t))
        X('TIPS = {}; HOVER(%s)' % f)
        texts += [('tooltip of item %d' % i, t) for t in E('TIPS').values()]
    X('TIPS = {}; HOVER(%s.resetAll); HOVER(EyeCandyMainFrame.apply)' % page)
    texts += [('reset or Apply tooltip', t) for t in E('TIPS').values()]
    texts.append(('reset button', E(page + '.resetAll.text')))
    for i in range(1, E('#NS.EXTRAS') + 1):
        for j in range(1, E('#NS.EXTRAS[%d].options' % i) + 1):
            texts.append(('Extra option', E('NS.EXTRAS[%d].options[%d][2]' % (i, j))))
    return texts


# Once with nothing set, once with every level at Cinematic (the level tooltips then list each
# setting by name) and every setting picked.
texts = collect()
X('for _, c in ipairs(NS.CATEGORIES) do NS.db.tiers[c.key] = 5 end; NS.db.extras.renderScale = 1.5; NS.db.extras.sharpness = 0.5; NS.RefreshUI()')
texts += collect()
texts.append(('Showcase', E('(function() for _, p in ipairs(NS.ListPresets().builtin) do if p.index == #NS.TIERS + 1 then return p.desc end end end)()')))
found = ['%s: %s in %r' % (where, w, t[:90]) for where, t in texts if t for w in bad_words(t)]
check(len(texts) > 300 and not found, "no tier, dial, Extra, LOD or profile on the Hidden tab (%d texts; %s)" % (len(texts), found[:5]))
intro = E(page + '.intro.text') or ''
check(all(E('NS.EXTRAS[%d].name' % i) in intro for i in range(1, E('#NS.EXTRAS') + 1)) and "Levels wait for the Apply button" in intro,
      "the intro names every setting that waits for Apply")

# The level row is named for its system, and the reset button is plain.
check(E('NS.tierRows[1].label.text') == E('NS.tierRows[1].cat.name') + " level", "a level row says <System> level (%r)" % E('NS.tierRows[1].label.text'))
check(E(page + '.resetAll.text') == "Reset hidden settings", "the reset button says Reset hidden settings")
# Search still finds the level rows by the old word, and hides the rest.
X('NS.SetSearch("tier")')
check(E('NS.tierRows[1].shown') == True and E('NS.advRows[1].shown') == False, "searching tier finds the level rows and hides the others")
X('NS.SetSearch("")')

# A level waits for Apply after you step it, even after an earlier Apply.
X('function EXROW(key) for _, r in ipairs(NS.extraRows) do if r.ex.key == key then return r end end end')
X('NS.ApplyAll(false, true); NS.RefreshUI()')
done_line = E('NS.tierRows[1].status.text')
check("set" in done_line and "not applied" not in done_line, "after Apply a level row says how many it set (%r)" % done_line)
X('NS.StepTier(NS.tierRows[1].cat, -1)')
check("not applied yet" in E('NS.tierRows[1].status.text'), "stepping a level after an Apply says not applied yet (%r)" % E('NS.tierRows[1].status.text'))
X('NS.ApplyAll(false, true); NS.RefreshUI()')
check("not applied" not in E('NS.tierRows[1].status.text'), "Apply clears it")
# A setting the game has, with nothing waiting, says only what is on now.
X('NS.db.extras.sharpness = nil; SetCVar("ResampleSharpness", "0.5"); NS.RefreshUI()')
s = E('EXROW("sharpness").status.text')
check(s.endswith("now 0.5") and "Apply" not in s, "a setting with nothing waiting says only what is on (%r)" % s)
# The resample filter is a stepper: stepping it waits for Apply too.
# (Levels off first: Cinematic's 150% render scale would make the game ignore the filter.)
X('for _, c in ipairs(NS.CATEGORIES) do NS.db.tiers[c.key] = nil end; SetCVar("RenderScale", "1"); NS.db.extras.renderScale = nil; NS.ApplyAll(false, true); NS.StepExtra(EXROW("resample").ex, -1)')  # to Bicubic (2); the game is on 3
s = E('EXROW("resample").status.text')
check("not applied yet" in s, "a stepped setting says not applied yet (%r)" % s)
done()
