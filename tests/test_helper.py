"""Help me pick (Helper.lua): a button on the Presets tab's Quality levels heading. It opens a strip with
one question (Prettier, Faster, Let Eye Candy pick). Prettier and Faster each suggest one preset, a
step up or down from where you are, and say what it changes before Apply. Let Eye Candy pick opens
Autotune with Best balance picked, and starts nothing. It never opens by itself.
Run: python tests/test_helper.py"""
import re
from lib import boot, check, done, addon

REG = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end
"""

lua = boot()
E, X = lua.eval, lua.execute
X(REG)
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
login_chat = list(E('CHAT').values())
X('CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'
S = P + '.helperStrip'
H = 'NS.Helper'


def click(b):
    X('%s.scripts.OnClick(%s)' % (b, b))


def pick(answer):
    return E('(function() local p, why = %s.Pick("%s"); return p and p.id or ("none: " .. tostring(why)) end)()' % (H, answer))


def unknown():
    # Not on a preset: the game's own settings, or your own preset.
    X('NS.db.onPreset = nil; NS.db.look = nil')


def on(preset_id):
    X('NS.ApplyPresetById("%s")' % preset_id)
    check(E('(NS.OnPreset())') is not None and E('(NS.OnPreset()).id') == preset_id, "set up: on %s" % preset_id)


# 1. Never by itself: nothing at login, nothing in chat, no strip when the window opens.
check(not any("pick" in str(m).lower() for m in login_chat), "nothing about Help me pick in chat at login")
check(E(S) is None or E(S + '.shown') is not True, "the window opens with no Help me pick strip")
src = open(addon + 'Helper.lua', encoding='utf-8').read()
check('ns.Print' not in src and 'StaticPopup' not in src, "Helper.lua never writes to chat and opens no popup")
check(src.count('RegisterEvent(') == 1 and 'RegisterEvent("PLAYER_REGEN_ENABLED")' in src, "its only event is the end of a fight (for an Apply that waits)")

# 2. The button sits on the Quality levels heading.
B = P + '.helperButton'
check(E(B) is not None and E(B + '.text') == "Help me pick", "a Help me pick button is on the Presets tab")
check(E('%s.header == %s.headerFor["Quality levels"]' % (B, P)) is True, "it sits on the Quality levels heading")

# 3. Pure logic: Prettier is one step up, Faster one step down.
# The harness's own settings sit between High and Ultra.
unknown()
check(pick("prettier") == "tier4" and pick("faster") == "tier3", "between High and Ultra: Prettier is Ultra, Faster is High (%s, %s)" % (pick("prettier"), pick("faster")))
on("tier4")
check(pick("prettier") == "look:beautiful" and pick("faster") == "tier3", "on Ultra: Prettier is Beautiful, Faster is High (%s, %s)" % (pick("prettier"), pick("faster")))
on("tier2")
check(pick("prettier") == "tier3" and pick("faster") == "tier1", "on Balanced: Prettier is High, Faster is Performance")
on("tier6")
p = pick("prettier")
check(p.startswith("none") and "Showcase" in p, "on Showcase: nothing prettier, and it names Showcase (%r)" % p)
check(pick("faster") == "look:beautiful", "on Showcase: Faster is Beautiful")
on("look:laptop")
f = pick("faster")
check(f.startswith("none") and "Laptop" in f, "on Laptop: nothing faster, and it names Laptop (%r)" % f)
check(pick("prettier") == "tier1", "on Laptop: Prettier is Performance")
on("look:moody")
check(pick("prettier") == "tier6" and pick("faster") == "tier4", "on Moody: Prettier is Showcase, Faster is Ultra")
on("look:raid")
check(pick("prettier") == "tier4" and pick("faster") == "tier2", "on Raid & PvP: Prettier is Ultra, Faster is Balanced")
# Every built-in has a place, so none falls back to a guess.
X('MISSING = {}; for _, p in ipairs(NS.ListPresets().builtin) do if not NS.Helper.Step(p.id) then MISSING[#MISSING + 1] = p.id end end')
check(E('#MISSING') == 0, "every built-in preset has a step on the ladder (%s)" % list(E('MISSING').values()))

# The ladder is cheapest first when measured from the settings themselves.
X('LV = {}; for i, id in ipairs(NS.Helper.LADDER) do LV[i] = NS.Helper.Level(NS.PresetValues(id)) end')
lv = [E('LV[%d]' % i) for i in range(1, E('#LV') + 1)]
check(all(lv[i] < lv[i + 1] for i in range(len(lv) - 1)), "each step up the ladder measures higher (%s)" % [round(v, 2) for v in lv])

# A preset you changed since counts as your own settings: measured, not taken by name.
on("tier4")
X('C_CVar.SetCVar("graphicsShadowQuality", "1")')
check(E('(select(2, NS.OnPreset()))') > 0 and E('(NS.Helper.Where())') is None, "changed since: placed by measuring, not by name")

# The game holding render scale at 100% (since 14 Nov 2026): Ultra's settings at 100% tie with
# Beautiful and Showcase there, so Prettier still offers the next step, Beautiful.
X('REALMAX = GetMaxRenderScale; GetMaxRenderScale = function() return 1 end')
X('local v = NS.PresetValues("tier4"); v.RenderScale = "1"; NS.ApplyValues(v)')
unknown()
check(pick("prettier") == "look:beautiful" and pick("faster") == "tier3", "render scale held at 100%%, on Ultra's settings: Prettier is Beautiful, Faster is High (%s, %s)" % (pick("prettier"), pick("faster")))
X('GetMaxRenderScale = REALMAX')

# What a pick changes, said before Apply.
X('wipe(NS.db.extras)')
on("tier3")
X('N, UP, DOWN = NS.Helper.Changes("tier4")')
ups = list(E('UP').values())
check(E('N') > 0 and "render scale" in ups and "shadow quality" in ups and E('#DOWN') == 0, "High to Ultra: settings go up, none down (%s)" % ups)
# A render scale override stays through a quality level (Core.lua), so it isn't said to change.
X('NS.db.extras.renderScale = 1.5; C_CVar.SetCVar("RenderScale", "1.5")')
X('N2, UP2, DOWN2 = NS.Helper.Changes("tier4")')
check("render scale" not in list(E('UP2').values()) + list(E('DOWN2').values()) and E('N2') == E('N') - 1, "with a render scale override, a quality level doesn't list render scale")
X('NS.ApplyPresetById("tier4")')
check(E('NS.Helper.Now("RenderScale")') == "1.5", "and applying it really keeps the override (checked, not assumed)")
X('wipe(NS.db.extras)')
check(E('NS.Helper.List({ "a", "b", "c", "d", "e" })') == "a, b, c and 2 more" and E('NS.Helper.List({ "a", "b" })') == "a and b", "a list says the first three and how many more")
check(E('NS.Helper.Lower("SSAO")') == "SSAO" and E('NS.Helper.Lower("Shadow quality")') == "shadow quality", "a name in a sentence keeps SSAO in capitals")

# 4. The strip: one question, three answers.
click(B)
check(E(S + '.shown') is True, "pressing it opens the strip")
check(E(S + '.title.text') == "What matters more to you?", "it asks one question (%r)" % E(S + '.title.text'))
answers = [E(S + '.%s.text' % k) for k in ("prettier", "faster", "auto")]
check(answers == ["Prettier", "Faster", "Let Eye Candy pick"] and all(E(S + '.%s.shown' % k) for k in ("prettier", "faster", "auto")), "three answers: %s" % answers)
check(E(S + '.apply.shown') is not True, "no Apply until there is a pick")
body = E(S + '.body.text')
check("Nothing changes until you press Apply" in body and "Autotune" in body, "it says what each answer does, on the screen (%r)" % body)
# The strip sits under the heading and the rows start below it.
X('FIRST = 1e9; for _, r in ipairs(%s.rows) do if r.shown and r.p.group == "Tiers" and r.top < FIRST then FIRST = r.top end end' % P)
check(E('FIRST') >= E(S + '.top') + E(S + '.h') + 8, "the quality level rows start 8 below the strip")

# Faster: one preset, what it changes, then Apply.
on("tier4")
X('NS.RefreshUI()')
click(S + '.faster')
check(E(S + '.title.text') == "Faster: High", "Faster on Ultra suggests High (%r)" % E(S + '.title.text'))
body = E(S + '.body.text')
check("Lower:" in body and "Changes up to" in body and "Back to before" in body, "it says what goes down and how many change (%r)" % body)
check(E(S + '.apply.shown') is True and E(S + '.apply.text') == "Apply High", "Apply names the preset")
check(E('(NS.OnPreset()).id') == "tier4", "nothing changes before Apply")
click(S + '.apply')
check(E('(NS.OnPreset()).id') == "tier3" and E('NS.BackSteps()[1].name') == "High", "Apply puts High on, as today's newest step")
check(E(S + '.title.text') == "Now on High" and E(S + '.body.text') == "To undo it, press Back on the top row under What you did today.", "the strip says it is on and how to undo it (%r)" % E(S + '.body.text'))
check("Changes up to " in body and " settings. Back to before undoes it." in body, "the pick text says it changes up to N settings (%r)" % body)
check(E(S + '.apply.shown') is not True, "no Apply once it is on")
# A pick that changes nothing says so, with no count.
X('REALCH = NS.Helper.Changes; NS.Helper.Changes = function() return 0, {}, {} end')
click(S + '.faster')
b0 = E(S + '.body.text') or ""
check(b0.endswith("Nothing would change.") and "Changes up to " not in b0, "a pick that changes nothing says Nothing would change (%r)" % b0)
X('NS.Helper.Changes = REALCH')

# In a fight Apply waits, says so, and goes on when the fight ends.
click(S + '.again')
check(E(S + '.title.text') == "What matters more to you?", "Ask again goes back to the question")
click(S + '.prettier')
check(E(S + '.title.text') == "Prettier: Ultra", "Prettier on High suggests Ultra")
X('INCOMBAT = true')
click(S + '.apply')
check(E('(NS.OnPreset()).id') == "tier3", "in a fight nothing changes")
check("Waiting for the fight to end" in E(S + '.body.text') and "|cff9d9d9d" in E(S + '.body.text'), "it says in grey that it waits for the fight to end")
check(E(S + '.apply.shown') is not True, "Apply hides while it waits")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(E('(NS.OnPreset()).id') == "tier4" and E(S + '.title.text') == "Now on Ultra", "the fight ends: Ultra goes on")

# Close while waiting: nothing goes on after the fight.
click(S + '.again')
click(S + '.faster')
X('INCOMBAT = true')
click(S + '.apply')
click(S + '.close')
check(E(S + '.shown') is not True, "Close shuts the strip")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(E('(NS.OnPreset()).id') == "tier4", "a wait that was closed does nothing after the fight")

# Leaving the tab closes it too (the strip hides with its page), and the wait goes with it.
click(B)
click(S + '.faster')
X('INCOMBAT = true')
click(S + '.apply')
X('%s.scripts.OnHide(%s)' % (S, S))
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED"); NS.RefreshUI()')
check(E('(NS.OnPreset()).id') == "tier4" and E(S + '.shown') is not True, "hidden with the tab: closed, and nothing goes on after the fight")

# Pressing the button again closes the strip.
click(B)
click(B)
check(E(S + '.shown') is not True, "the button closes an open strip")

# The top of the ladder: no Apply, and the line names the preset.
on("tier6")
click(B)
click(S + '.prettier')
check(E(S + '.apply.shown') is not True and "Showcase" in E(S + '.body.text'), "nothing prettier than Showcase: no Apply, and it says why (%r)" % E(S + '.body.text'))
click(S + '.close')

# 5. Let Eye Candy pick: the Experimental tab, Best balance and Best look, nothing started.
X('NS.db.autotuneGoal = { mode = "target", goal = 120, style = "raid", from = "tier3" }')
before = E('(NS.OnPreset()).id')
click(B)
click(S + '.auto')
check(E('EyeCandyMainFrame.tab') == "autotune", "it opens the Experimental tab")
check(E('NS.db.autotuneGoal.mode') == "balance" and E('NS.db.autotuneGoal.style') == "look" and E('NS.db.autotuneGoal.from') is None, "with Best balance and Best look from the lowest settings picked")
check(E('NS.Autotune.IsRunning()') is False and E('(NS.OnPreset()).id') == before, "it starts nothing and changes no setting")
msg = E('NS.Autotune.message') or ""
check("Press Start" in msg and "lowest settings" in msg and E('NS.Autotune.messageKind') == "done", "the tab's line names all three picks and says to press Start (%r)" % msg)
how = open(addon + 'AutotuneTab.lua', encoding='utf-8').read()
check("quiet" not in msg and "somewhere busy" in how, "where to stand is left to the tab's own text (Best look: somewhere busy)")
# The line goes once the goal is changed on the tab (its Pick() saves a new table).
X('NS.db.autotuneGoal = { mode = "target", goal = 60, style = "look" }; NS.RefreshUI()')
check(E('NS.Autotune.message') is None, "changing the goal on the tab takes the line away")

# While Autotune runs: the tab opens, the goal stays.
X('NS.ShowTab("presets"); REALRUN = NS.Autotune.IsRunning; NS.Autotune.IsRunning = function() return true end')
X('NS.db.autotuneGoal = { mode = "target", goal = 144, style = "smooth" }')
click(B)
click(S + '.auto')
check(E('EyeCandyMainFrame.tab') == "autotune" and E('NS.db.autotuneGoal.goal') == 144 and E('NS.db.autotuneGoal.style') == "smooth", "while Autotune runs it only opens the tab, the goal untouched")
X('NS.Autotune.IsRunning = REALRUN; NS.ShowTab("presets")')

# A refused Apply says why in the strip, in red.
on("tier3")
X('REALAPPLY = NS.ApplyPresetById; NS.ApplyPresetById = function() return false, "The game said no." end')
click(B)
click(S + '.prettier')
click(S + '.apply')
body = E(S + '.body.text')
check("|cffff4040" in body and "Ultra didn't apply. The game said no." in body, "a refused Apply says why in the strip, in red (%r)" % body)
X('NS.ApplyPresetById = REALAPPLY')
click(S + '.close')

# Every body the strip showed above, built from pieces, has no em-dash.
X('NS.Helper.Set(EyeCandyMainFrame.pages.presets, "ask")')
for state in ("prettier", "faster"):
    click(S + '.again')
    click(S + '.' + state)
    check('—' not in E(S + '.body.text') and '—' not in E(S + '.title.text'), "no em-dash in the %s strip" % state)
click(S + '.close')

# 6. Words (docs/ui-rules.md): no em-dash, no tier, CVar or LOD in anything the strip says.
for word in ("—", "tier", "CVar", "LOD", "profile", "revert"):
    for line in [l for l in src.splitlines() if '"' in l and not l.strip().startswith('--')]:
        for piece in line.split('"')[1::2]:
            if ' ' in piece and (word in piece if not word.isalpha() else re.search(r'\b%s\b' % word, piece, re.I)):
                check(False, "player text says %r: %r" % (word, piece))
check(msg.count('—') == 0, "no em-dash in the Autotune line")
done()
