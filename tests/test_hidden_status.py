"""The Hidden tab's status words for the Extras: Sharpness shows the real value (its bar runs
backwards), and a value the game refused is said on the row, not "see chat".
Run: python tests/test_hidden_status.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('function EXROW(key) for _, r in ipairs(NS.extraRows) do if r.ex.key == key then return r end end end')
X('C_CVar.RegisterCVar("RenderScale", "1"); C_CVar.RegisterCVar("ResampleSharpness", "0.2")')
X('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden")')


def status(key, extra, cvar, value):
    X('NS.db.extras.%s = %s; SetCVar("%s", "%s"); NS.RefreshUI()' % (key, extra, cvar, value))
    return E('EXROW("%s").status.text' % key) or ""


s = status("sharpness", "0.5", "ResampleSharpness", "0.5")
check(s == "now 0.5", "Sharpness 0.5 with the game at 0.5 says now 0.5, not 1.5 (%r)" % s)
s = status("sharpness", "-1", "ResampleSharpness", "-1")
check(s == "now Off", "Sharpness Off says now Off (%r)" % s)
s = status("sharpness", "nil", "ResampleSharpness", "0.5")
check(s.endswith("now 0.5"), "Sharpness not set by Eye Candy shows the game's 0.5 (%r)" % s)
s = status("sharpness", "0.5", "ResampleSharpness", "1.5")
check("the game kept 1.5" in s and "see chat" not in s, "a refused Sharpness says what the game kept (%r)" % s)

s = status("renderScale", "1.75", "RenderScale", "1")
check("the game kept 100%" in s and "Restart" not in s, "a refused render scale says what the game kept, on the row, with no guess at why (%r)" % s)
check("see chat" not in s, "and doesn't send you to chat")
check("ff4040" in s, "refused is drawn in its own red, not Cinematic's colour")
s = status("renderScale", "1.75", "RenderScale", "1.75")
check(s == "now 175%", "render scale the game took says now 175%% (%r)" % s)

# A value you just picked is waiting for Apply, not refused (review of this fix).
X('SetCVar("ResampleSharpness", "0.5"); NS.SetExtra(EXROW("sharpness").ex, 0.8)')
s = E('EXROW("sharpness").status.text')
check("not applied yet" in s and "kept" not in s and "ff4040" not in s, "a Sharpness you just picked says not applied yet, not red (%r)" % s)
X('NS.ApplyAll(false, true); NS.RefreshUI()')
s = E('EXROW("sharpness").status.text')
check(s.startswith("now 0.8"), "after Apply it says now 0.8 (%r)" % s)

# The refusal is said on the row; any other note says "1 note" or its own reason, never "see chat".
X('NS.lastReport = { ["extra:renderScale"] = { applied = 0, notes = 1 } }')
s = status("renderScale", "1.75", "RenderScale", "1")
check("kept" in s and "see chat" not in s, "a refusal alone doesn't send you to chat (%r)" % s)
X('NS.lastReport = { ["extra:renderScale"] = { applied = 0, notes = 2 } }')
s = status("renderScale", "1.75", "RenderScale", "1")
check("kept" in s and "see chat" not in s and "1 note" in s and "note(s)" not in s, "a refusal plus another note says 1 note, not see chat (%r)" % s)

# A setting the game doesn't have says why on the row (rule 6), for an Extra and for a level.
X('REALEXISTS = NS.Exists; NS.db.extras.sharpness = 0.5; NS.db.extras.renderScale = nil; SetCVar("ResampleSharpness", "0.5")')
X('local ex = EXROW("sharpness").ex; NS.Exists = function(c) return c ~= ex.cvar and REALEXISTS(c) end')
X('NS.lastReport = { ["extra:sharpness"] = { applied = 0, notes = 1 } }; NS.RefreshUI()')
s = E('EXROW("sharpness").status.text')
check("not in this game" in s and "see chat" not in s and "note(s)" not in s, "an Extra the game lacks says so on the row (%r)" % s)

X('NS.Exists = REALEXISTS')
X('TROW = NS.tierRows[1]; NS.db.tiers[TROW.cat.key] = 3; TCV = nil; '
  'for _, x in ipairs(TROW.cat.cvars) do if not x.scale and x[3][3] ~= nil then TCV = x break end end')
X('NS.Exists = function(c) return c ~= TCV[1] and REALEXISTS(c) end')
X('NS.lastReport = { [TROW.cat.key] = { applied = 2, notes = 1 } }; NS.RefreshUI()')
s = E('TROW.status.text')
check("not in this game" in s and "see chat" not in s and "note(s)" not in s, "a level with a setting the game lacks says so on the row (%r)" % s)
X('NS.Exists = REALEXISTS; NS.db.tiers[TROW.cat.key] = 0; NS.lastReport = { [TROW.cat.key] = { applied = 2, notes = 2 } }; NS.RefreshUI()')
s = E('TROW.status.text')
check("2 notes" in s and "note(s)" not in s, "when the reason can't be worked out it says how many notes (%r)" % s)
done()
