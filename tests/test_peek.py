"""Peek and Compare ("see changes live").

Run alone: python tests/test_peek.py
"""
from lib import boot, chat, check, done

# UIParent, WorldFrame and SetUIVisibility, set up before the addon loads. Like the game, showing
# the UI fires UIParent's OnShow hook. Each frame remembers its parent.
PRE = """
local cf = CreateFrame
function CreateFrame(kind, name, parent, template) local f = cf(kind, name, parent, template); f.parent = parent; return f end
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
UICALLS = {}
function SHOWUI() UIParent.shown = true; if UIParent.hooks.OnShow then UIParent.hooks.OnShow(UIParent) end end
function SetUIVisibility(v) UICALLS[#UICALLS + 1] = v; if v then SHOWUI() else UIParent.shown = false end end
function SER(v)
  if type(v) == "table" then
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = k end
    table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
    local o = {}
    for _, k in ipairs(keys) do o[#o + 1] = "[" .. SER(k) .. "]=" .. SER(v[k]) end
    return "{" .. table.concat(o, ",") .. "}"
  elseif type(v) == "string" then return string.format("%q", v) end
  return tostring(v)
end
"""


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)] if t is not None else []


def start(svdb=""):
    lua = boot(PRE + svdb)
    lua.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
    return lua


# ---------------------------------------------------------------- Peek
lua = start()
ev = lua.eval
lua.execute('NS.ToggleMain(); ASK = CreateFrame("Frame", "EyeCandyAskFrame"); ASK:Show(); CHAT = {}')
check(ev('EyeCandyMainFrame:IsShown()') and not ev('EyeCandyExportFrame and EyeCandyExportFrame:IsShown()'), "setup: the main window is open, export closed")
check(ev('NS.TogglePeek()') is True and ev('NS.IsPeeking()'), "Peek starts")
check(lst(ev('UICALLS')) == [False] and not ev('UIParent:IsShown()'), "Peek hides the game's UI with SetUIVisibility(false), what Alt+Z calls")
check(not ev('EyeCandyMainFrame:IsShown()') and not ev('ASK:IsShown()'), "Peek hides every open Eye Candy window")
check(ev('EyeCandyPeekFrame:IsShown()') and ev('EyeCandyPeekFrame.parent == WorldFrame'), "a Back bar shows, on WorldFrame, which stays visible while the UI is hidden")
check(chat(lua) == [], "Peek says nothing when it works (chat is hidden anyway)")
lua.execute('EyeCandyPeekFrame.button.scripts.OnClick()')
check(not ev('NS.IsPeeking()') and ev('UIParent:IsShown()') and lst(ev('UICALLS')) == [False, True], "Back puts the game's UI back")
check(ev('EyeCandyMainFrame:IsShown()') and ev('ASK:IsShown()') and not ev('EyeCandyExportFrame and EyeCandyExportFrame:IsShown()'), "Back reopens exactly the windows that were open")
check(not ev('EyeCandyPeekFrame:IsShown()'), "the Back bar goes away")

lua.execute('SlashCmdList.EYECANDY("peek")')
check(ev('NS.IsPeeking()') and not ev('UIParent:IsShown()'), "/ec peek starts it")
lua.execute('SlashCmdList.EYECANDY("peek")')
check(not ev('NS.IsPeeking()') and ev('UIParent:IsShown()') and ev('EyeCandyMainFrame:IsShown()'), "/ec peek again ends it")

# Esc with the UI hidden: Blizzard shows UIParent and calls SetUIVisibility(true) itself (Game.lua).
lua.execute('UICALLS = {}; NS.TogglePeek(); SHOWUI(); SetUIVisibility(true)')
check(not ev('NS.IsPeeking()') and ev('EyeCandyMainFrame:IsShown()') and ev('ASK:IsShown()'), "Esc (or Alt+Z) ends the peek and reopens the windows")
check(lst(ev('UICALLS')) == [False, True] and not ev('EyeCandyPeekFrame:IsShown()'), "after Esc, Peek doesn't call SetUIVisibility again; the Back bar goes")

lua.execute('INCOMBAT = true; R1, R2 = NS.TogglePeek(); INCOMBAT = false')
check(ev('R1') is None and "combat" in ev('R2') and not ev('NS.IsPeeking()'), "Peek refuses in combat, with a plain reason")
check(ev('EyeCandyMainFrame:IsShown()') and ev('UIParent:IsShown()'), "a refused Peek hides nothing")
lua.execute('SlashCmdList.EYECANDY("peek"); INCOMBAT = true; R1 = NS.TogglePeek(); INCOMBAT = false')
check(ev('R1') is True and not ev('NS.IsPeeking()') and ev('UIParent:IsShown()'), "Back still works in combat: the UI comes back")
lua.execute('SlashCmdList.EYECANDY("peek"); CHAT = {}; FIRE("PLAYER_REGEN_DISABLED")')
check(not ev('NS.IsPeeking()') and ev('UIParent:IsShown()') and ev('EyeCandyMainFrame:IsShown()'), "combat starting ends the peek: UI and windows back")
check(any("combat" in x for x in chat(lua)), "and says why in chat")
lua.execute('FIRE("PLAYER_REGEN_DISABLED")')
check(chat(lua) == [], "combat with no peek says nothing")
check(ev('(function() for _, n in ipairs(UISpecialFrames) do if n == "EyeCandyPeekFrame" then return true end end end)()'), "the Back bar is closed by Esc like any window")

# Review finding 4: combat had already locked the UI, so showing it fails. The Back bar stays with a way out.
lua.execute('SlashCmdList.EYECANDY("peek"); REALSHOW = UIParent.Show; UIParent.Show = function() error("blocked") end; REALSUV = SetUIVisibility; SetUIVisibility = function() end')
lua.execute('INCOMBAT = true; R1, R2 = NS.TogglePeek()')
check(ev('R1') is None and "Esc or Alt+Z" in ev('R2') and ev('NS.IsPeeking()'), "locked by combat: Back says to press Esc or Alt+Z, and Peek stays on")
check(ev('EyeCandyPeekFrame:IsShown()') and "Alt+Z" in ev('EyeCandyPeekFrame.text.text') and not ev('EyeCandyMainFrame:IsShown()'), "the Back bar stays up with that message")
lua.execute('FIRE("PLAYER_REGEN_DISABLED")')
check(ev('NS.IsPeeking()') and ev('EyeCandyPeekFrame:IsShown()'), "combat starting while locked keeps the Back bar up")
lua.execute('UIParent.Show = REALSHOW; SetUIVisibility = REALSUV; INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(not ev('NS.IsPeeking()') and ev('UIParent:IsShown()') and ev('EyeCandyMainFrame:IsShown()') and not ev('EyeCandyPeekFrame:IsShown()'), "the end of the fight brings the UI and windows back")
lua.execute('SlashCmdList.EYECANDY("peek"); UIParent.Show = function() error("blocked") end; SetUIVisibility = function() end; INCOMBAT = true; NS.TogglePeek()')
lua.execute('UIParent.Show = REALSHOW; SetUIVisibility = REALSUV; SHOWUI(); INCOMBAT = false')
check(not ev('NS.IsPeeking()') and ev('EyeCandyMainFrame:IsShown()') and not ev('EyeCandyPeekFrame:IsShown()'), "locked by combat, Esc (Blizzard's own key) still ends it")

# Review finding 6: the UI was already hidden with Alt+Z. Back must not bring it back.
lua.execute('UICALLS = {}; UIParent.shown = false; NS.TogglePeek()')
check(ev('NS.IsPeeking()') and lst(ev('UICALLS')) == [] and ev('EyeCandyPeekFrame.text.text') == "Esc also works", "UI already hidden: Peek doesn't call SetUIVisibility, and the bar has its usual text")
lua.execute('NS.TogglePeek()')
check(not ev('NS.IsPeeking()') and not ev('UIParent:IsShown()') and lst(ev('UICALLS')) == [], "Back leaves the UI hidden, as the player had it")
lua.execute('UIParent.shown = true')

# Review finding 5: the Back bar matches the UI scale (WorldFrame doesn't use it).
lua.execute('UIParent.GetEffectiveScale = function() return 0.64 end; WorldFrame.GetEffectiveScale = function() return 1 end; EyeCandyPeekFrame.SetScale = function(self, s) self.scale = s end; NS.TogglePeek()')
check(abs(ev('EyeCandyPeekFrame.scale') - 0.64) < 1e-9, "the Back bar is scaled like the UI")
lua.execute('NS.TogglePeek()')

# Fallback: SetUIVisibility missing, erroring, or not hiding anything.
for name, fn in [("missing", "nil"), ("erroring", 'function() error("blocked") end'), ("doing nothing", "function() end")]:
    lua.execute('CHAT = {}; SetUIVisibility = %s' % fn)
    ok = ev('NS.TogglePeek()')
    check(ok is True and ev('NS.IsPeeking()') and ev('UIParent:IsShown()') and not ev('EyeCandyMainFrame:IsShown()'),
          "SetUIVisibility %s: only Eye Candy's windows are hidden" % name)
    check(any("couldn't hide the game's UI" in x for x in chat(lua)), "SetUIVisibility %s: it says so in chat" % name)
    # Esc in the fallback closes the Back bar like any window (CloseSpecialWindows hides it).
    lua.execute('EyeCandyPeekFrame:Hide(); EyeCandyPeekFrame.scripts.OnHide(EyeCandyPeekFrame)')
    check(not ev('NS.IsPeeking()') and ev('EyeCandyMainFrame:IsShown()'), "SetUIVisibility %s: Esc ends it and the windows come back" % name)

# ---------------------------------------------------------------- Compare
lua = start()
ev = lua.eval
g = lambda n: ev('GetCVar("%s")' % n)
nb = lambda: len(lst(ev('NS.ListBackups()')))
choices = lambda: ev('SER({ EyeCandyDB.tiers, EyeCandyDB.extras, EyeCandyDB.advanced, EyeCandyDB.look or false })')

lua.execute('R1, R2 = NS.ToggleCompare()')
check(ev('R1') is None and "Nothing to compare yet" in ev('R2') and not ev('NS.IsComparing()'), "with no preset applied yet, Compare says there is nothing to compare yet")
check(ev('NS.CompareLabel()') is None, "no label when not comparing")
lua.execute('SlashCmdList.EYECANDY("preset cinematic"); CHAT = {}')
before, now = "7000", g("farclip")
check(now != before and ev('NS.BeforeRecord().name') == "Cinematic", "setup: Cinematic changed farclip and is today's newest step")
n0, c0 = nb(), choices()

check(ev('NS.ToggleCompare()') is True and ev('NS.IsComparing()'), "Compare starts")
check(g("farclip") == before and ev('NS.CompareLabel()') == "Showing: before Cinematic", "it shows the settings from before Cinematic, labelled")
check(ev('EyeCandyDB.compare.now.farclip') == now, "while showing before, the saved data holds now")
lua.execute('NS.ToggleCompare()')
check(g("farclip") == now and ev('NS.CompareLabel()') == "Showing: now" and ev('NS.IsComparing()'), "flip: back to now, still comparing")
check(ev('EyeCandyDB.compare') is None, "showing now, the saved flag is cleared")
lua.execute('NS.ToggleCompare()')
check(g("farclip") == before, "flip again: before")
check(nb() == n0, "flipping takes no backups")
check(choices() == c0, "flipping leaves Eye Candy's own choices (tiers, extras, dials, Look) alone")

lua.execute('INCOMBAT = true; R1, R2 = NS.ToggleCompare(); INCOMBAT = false')
check(ev('R1') is None and "combat" in ev('R2') and g("farclip") == before, "a flip in combat is refused and changes nothing")
lua.execute('FIRE("PLAYER_REGEN_DISABLED")')
check(g("farclip") == now and not ev('NS.IsComparing()') and ev('EyeCandyDB.compare') is None, "combat starting ends compare on now")
check(any("combat" in x for x in chat(lua)), "and says so")

lua.execute('NS.ToggleCompare(); INCOMBAT = true; FIRE("PLAYER_REGEN_DISABLED")')
check(g("farclip") == before and any("after the fight" in x for x in chat(lua)), "if settings are already locked, it waits for the fight to end")
lua.execute('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(g("farclip") == now and not ev('NS.IsComparing()') and ev('EyeCandyDB.compare') is None, "after the fight it lands on now")

lua.execute('INCOMBAT = true; R1, R2 = NS.ToggleCompare(); INCOMBAT = false')
check(ev('R1') is None and "combat" in ev('R2') and not ev('NS.IsComparing()'), "Compare refuses to start in combat")

lua.execute('NS.ToggleCompare(); CHAT = {}')
check(ev('NS.StopCompare()') is True and g("farclip") == now and not ev('NS.IsComparing()'), "StopCompare ends on now")
lua.execute('SlashCmdList.EYECANDY("compare stop")')
check(any("isn't on" in x for x in chat(lua)), "compare stop when it's off says so")
lua.execute('SlashCmdList.EYECANDY("compare")')
check(g("farclip") == before and any("Showing: before Cinematic" in x for x in chat(lua)), "/ec compare starts it and prints the label")
lua.execute('SlashCmdList.EYECANDY("compare")')
check(g("farclip") == now and any("Showing: now" in x for x in chat(lua)), "/ec compare again flips")
lua.execute('SlashCmdList.EYECANDY("compare stop")')
check(not ev('NS.IsComparing()') and any("ended" in x for x in chat(lua)), "/ec compare stop ends it")

# A change made while comparing is the player's: it joins now.
lua.execute('NS.ToggleCompare(); SetCVar("farclip", "8000")')
lua.execute('NS.ToggleCompare()')
check(g("farclip") == "8000", "a setting changed while showing before is kept as now")
lua.execute('NS.ToggleCompare()')
check(g("farclip") == before, "and before is still before")
lua.execute('NS.StopCompare()')
check(g("farclip") == "8000", "ending lands on the new now")
lua.execute('SetCVar("farclip", "%s")' % now)

# Logout (and /reload) while showing before: now goes back first.
lua.execute('NS.ToggleCompare(); FIRE("PLAYER_LOGOUT")')
check(g("farclip") == now and ev('EyeCandyDB.compare') is None and not ev('NS.IsComparing()'), "logout or /reload while showing before puts now back")

# /reload in combat: settings are locked, so the saved flag carries now (with any change) to the next load.
lua.execute('NS.ToggleCompare(); SetCVar("weatherDensity", "0"); INCOMBAT = true; FIRE("PLAYER_LOGOUT"); INCOMBAT = false')
check(g("farclip") == before and ev('EyeCandyDB.compare.now.farclip') == now, "logout in combat leaves before showing and saves now")
check(ev('EyeCandyDB.compare.now.weatherDensity') == "0", "a change made while showing before is in the saved now")
saved = ev('SER(EyeCandyDB)')

# The next load (new game state, like a /reload): the client still has before. Now goes back at login.
lua = boot(PRE + 'EyeCandyDB = ' + saved + '; SetCVar("farclip", "%s")' % before)
ev = lua.eval
check(ev('GetCVar("farclip")') == before and ev('EyeCandyDB.compare') is not None, "setup: the next load starts on before, with the flag")
lua.execute('FIRE("PLAYER_LOGIN")')
check(ev('GetCVar("farclip")') == now and ev('GetCVar("weatherDensity")') == "0" and ev('EyeCandyDB.compare') is not None, "the next load puts now back at once, and keeps the flag until the game settles")
# Review finding 1: account settings from the server land a moment after login and overwrite some.
lua.execute('SetCVar("farclip", "%s"); RUNTIMERS()' % before)
check(ev('GetCVar("farclip")') == now and ev('EyeCandyDB.compare') is None, "once settled it puts now back again, then clears the flag")
check(any("back to now" in x for x in chat(lua)), "and says so")
check(not ev('NS.IsComparing()'), "and compare is off")

lua = boot(PRE + 'EyeCandyDB = ' + saved + '; SetCVar("farclip", "%s"); INCOMBAT = true' % before)
ev = lua.eval
lua.execute('FIRE("PLAYER_LOGIN")')
check(ev('GetCVar("farclip")') == before and ev('EyeCandyDB.compare') is not None, "a load in combat waits (no settings change in combat)")
lua.execute('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(ev('GetCVar("farclip")') == now and ev('EyeCandyDB.compare') is None, "after the fight it puts now back")

# Nothing changed since the last preset's "before" record (a preset that changes nothing).
lua = start()
ev = lua.eval
lua.execute('SlashCmdList.EYECANDY("preset cinematic"); SlashCmdList.EYECANDY("preset cinematic"); R1, R2 = NS.ToggleCompare()')
check(ev('R1') is None and "same as before your last preset" in ev('R2') and not ev('NS.IsComparing()'), "nothing changed since before the last preset: it says so")
lua.execute('SetCVar("farclip", "9000"); SlashCmdList.EYECANDY("preset cinematic"); SetCVar("farclip", "9500")')
check(ev('NS.ToggleCompare()') is True and ev('GetCVar("farclip")') == "9000", "it uses the record from before the newest preset")
check(ev('NS.CompareLabel()') == "Showing: before Cinematic", "labelled with that preset's name")
lua.execute('NS.StopCompare(); SlashCmdList.EYECANDY("apply")')
check(ev('NS.BeforeRecord().name') == "Cinematic", "Apply leaves the preset's step alone, so Compare still means before the last preset")
check(len(lst(ev('NS.ListBackups()'))) == 1, "and none of it added a backup row")

# Review finding 3: a backup or restore while before is showing ends compare on now first,
# so the backup records your real settings.
lua = start()
ev = lua.eval
g = lambda n: ev('GetCVar("%s")' % n)
lua.execute('SlashCmdList.EYECANDY("preset cinematic"); CHAT = {}')
now = g("farclip")
lua.execute('NS.ToggleCompare(); SlashCmdList.EYECANDY("look moody"); CHAT = {}')
b0 = ev('NS.BeforeRecord()')
check(not ev('NS.IsComparing()') and b0['name'] == "Moody" and b0['values']['farclip'] == now and b0['values']['Gamma'] == "1", "a preset while showing before ends compare first; its 'before' record holds now, not before")
check(g("Gamma") == "0.9", "setup: Moody set Gamma to 0.9 (Cinematic has 1)")
lua.execute('NS.ToggleCompare()')
check(ev('NS.IsComparing()') and g("Gamma") == "1", "compare then shows before Moody")
lua.execute('NS.CreateBackup("manual", "Mine")')
b0 = lst(ev('NS.ListBackups()'))[0]
check(not ev('NS.IsComparing()') and b0['label'] == "Mine" and b0['values']['Gamma'] == "0.9" and g("Gamma") == "0.9", "a manual backup while showing before ends compare first and holds now")
lua.execute('SlashCmdList.EYECANDY("look moody"); NS.ToggleCompare(); NS.RestoreBackupById(NS.OriginalBackup().id); CHAT = {}')
check(not ev('NS.IsComparing()') and g("Gamma") == ev('NS.OriginalBackup().values.Gamma') and ev('EyeCandyDB.compare') is None, "a restore while showing before ends compare first, then restores")
lua.execute('SlashCmdList.EYECANDY("look moody"); NS.ToggleCompare(); SlashCmdList.EYECANDY("back")')
check(not ev('NS.IsComparing()') and g("Gamma") == ev('NS.OriginalBackup().values.Gamma') and ev('EyeCandyDB.compare') is None, "Back while showing before ends compare first, then goes back")
lua.execute('SlashCmdList.EYECANDY("look moody"); NS.ToggleCompare(); SlashCmdList.EYECANDY("apply")')
check(not ev('NS.IsComparing()') and g("Gamma") == "0.9", "Apply while showing before ends compare first, so it applies over now")

done()
