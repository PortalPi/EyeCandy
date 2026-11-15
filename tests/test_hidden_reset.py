"""Reset hidden settings says what it did under its button, not in chat (docs/ui-rules.md rule 6),
and the line goes when you leave the tab.
Run: python tests/test_hidden_reset.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('function CLICK(b) b.scripts.OnClick(b) end')
X('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden")')
P = 'EyeCandyMainFrame.pages.hidden'

X('NS.SetAdvanced("lodObjectCullDist", 5); NS.SetAdvanced("lodObjectMinSize", 1); CHAT = {}')
X('CLICK(%s.resetAll)' % P)
check(E(P + '.resetResult.text') == "" and E(P + '.resetAll.text') != "Reset hidden settings", "the first click asks to confirm and says nothing yet")
X('CLICK(%s.resetAll)' % P)
check(E(P + '.resetResult.text') == "Reset 2 settings.", "the second click says how many it reset, under the button (%r)" % E(P + '.resetResult.text'))
check(E('#CHAT') == 0, "and nothing goes to chat")
check(E('next(NS.db.advanced)') is None, "the settings are handed back")
X('CLICK(%s.resetAll); CLICK(%s.resetAll)' % (P, P))
check("Nothing to reset." in E(P + '.resetResult.text'), "with nothing left it says Nothing to reset (%r)" % E(P + '.resetResult.text'))
X('NS.SetAdvanced("lodObjectCullDist", 5); CLICK(%s.resetAll); CLICK(%s.resetAll)' % (P, P))
check(E(P + '.resetResult.text') == "Reset 1 setting.", "one setting is said in the singular (%r)" % E(P + '.resetResult.text'))
X('CLICK(%s.resetAll)' % P)
check(E(P + '.resetResult.text') == "", "arming again clears the last result")
# The button is armed from the click above, so one more click confirms.
X('NS.SetAdvanced("lodObjectCullDist", 5); INCOMBAT = true; CLICK(%s.resetAll); INCOMBAT = false' % P)
check("Can't reset in a fight." in E(P + '.resetResult.text') and "ff4040" in E(P + '.resetResult.text'), "in a fight it says in red that it can't reset (%r)" % E(P + '.resetResult.text'))
check(E('NS.db.advanced.lodObjectCullDist') == 5, "and in a fight nothing is handed back")
X('FIRE("PLAYER_REGEN_ENABLED")')
check(E(P + '.resetResult.text') == "", "the red line goes when the fight ends (%r)" % E(P + '.resetResult.text'))
X('NS.ShowTab("presets")')
X('local h = %s.hooks.OnHide; if h then h(%s) end' % (P, P))
check(E(P + '.resetResult.text') == "", "leaving the tab clears the line")
done()
