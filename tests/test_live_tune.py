"""Steady FPS on the Experimental tab (16 Nov 2026): it lowers render scale a little when FPS stays low,
and raises it again when FPS comes back, with few changes and a long gap between them.
Run: python tests/test_live_tune.py"""
from lib import boot, check, done

PRE = """
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
function SetUIVisibility(v) UIParent.shown = v end
function Screenshot() end
"""
lua = boot(PRE)
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
X("SF = NS.SteadyFPS")
RED = "|cffff4040"

# --- The steps (pure) -------------------------------------------------------------------------------
# RUN(s, seconds, fps, opts): readings every half second at fps. opts: goal (60), free (true), long (a normal
# frame), top (an FPS cap), vsync. Returns the changes made, each { at, to, why }.
X("""function RUN(s, secs, fps, o)
  o = o or {}
  local out = {}
  for i = 1, math.floor(secs * 2 + 0.5) do
    local f = type(fps) == "function" and fps(s) or fps
    local r = { now = f, raw = f, frames = f * 0.5, seconds = 0.5, long = o.long or 1 / f, goal = o.goal or 60,
      free = o.free ~= false, top = o.top, vsync = o.vsync }
    local to, why = SF.Step(s, r)
    if to then out[#out + 1] = { at = s.clock, to = to, why = why } end
  end
  return out
end
function N(t) return #t end""")


def run(secs, fps, opts="nil"):
    X("C = RUN(S, %r, %s, %s)" % (secs, fps, opts))
    return [(E("C[%d].at" % i), E("C[%d].to" % i), E("C[%d].why" % i)) for i in range(1, E("N(C)") + 1)]


X("S = SF.New(1)")
check(run(4.5, 50) == [], "FPS under the goal for less than 5 seconds: nothing changes")
c = run(1, 50)
check(c == [(5.0, 0.95, "lower")], "after 5 seconds under it: one step lower, 5%% (%s)" % c)
c = run(29, 50)
check(all(w != "lower" for _, _, w in c) and E("S.stuck"), "the step didn't help (FPS the same): it stops lowering (%s)" % c)
c = run(1, 50)
check(c == [(35.0, 1, "back")], "and puts that step back, but only once the 30 second gap is over (%s)" % c)
check(run(300, 50) == [], "then nothing more here, however long FPS stays low")
X("SF.NewPlace(S)")
check(not E("S.stuck") and run(6, 50)[0][2] == "lower", "a new place (a loading screen) lets it try again")

# A step that helps: FPS goes from 50 to 58, inside the band (54 to 75 for a goal of 60).
X("S = SF.New(1); HELPED = function(s) return s.scale < 1 and 58 or 50 end")
c = run(60, "HELPED")
check(c == [(5.0, 0.95, "lower")] and not E("S.stuck"), "a step that helps stays, and nothing else changes (%s)" % c)
# The step helps, then FPS falls again at 12 seconds: the next step waits for the 30 second gap.
X("""S = SF.New(1); LOWER = function(s)
  if s.scale > 0.99 then return 50 elseif s.scale > 0.94 then return s.clock < 12 and 58 or 48 end
  return 58
end""")
c = run(60, "LOWER")
check(c == [(5.0, 0.95, "lower"), (35.0, 0.9, "lower")], "FPS falls again soon after: the next step comes 30 seconds after the last (%s)" % c)

X("S = SF.New(1)")
check(run(3, 50) == [] and run(30, 60) == [] and run(3, 50) == [], "short dips (3 seconds) never change anything")

# Coming back up, never past your own value.
X("S = SF.New(1); S.scale = 0.9")
c = run(4.5, 80)
check(c == [], "FPS well over the goal for under 5 seconds: nothing yet")
c = run(120, 80)
check([x[1:] for x in c] == [(0.95, "raise"), (1, "raise")] and c[1][0] - c[0][0] >= 30,
      "well over it: one step up at a time, 30 seconds apart, and never past your own (%s)" % c)

# Up, then down again: it stops raising there, so it never goes up and down all day.
X("S = SF.New(1); S.scale = 0.9; PINGPONG = function(s) return s.scale > 0.9 and 50 or 80 end")
c = run(200, "PINGPONG")
check([x[1:] for x in c] == [(0.95, "raise"), (0.9, "lower")], "a raise that drops FPS too far is undone once, then it stays (%s)" % c)

X("S = SF.New(1); S.scale = 0.7")
check(run(100, 30) == [], "never under 70%")
X("S = SF.New(0.65)")
check(run(100, 30) == [], "your own render scale under 70%: nothing to lower")

# A fight, Autotune or anything else changing settings: no change, and the 5 seconds start again after.
X("S = SF.New(1)")
c = run(4, 50) + run(1, 50, "{ free = false }") + run(4, 50)
check(c == [], "time under the goal starts again after it was held back (%s)" % c)
check(run(2, 50, "{ free = false }") == [] and run(5, 50, "{ free = false }") == [], "while held back it never changes anything")

# The hitch from a change: the longest frame just after it.
X("S = SF.New(1)")
run(5, 50)
run(0.5, 50, "{ long = 0.2 }")
run(3, 50)
check(abs(E("S.biggest") - 0.2) < 1e-9 and abs(E("S.normal") - 0.02) < 1e-9 and E("S.changes") == 1,
      "the longest frame in the 2 seconds after a change is kept, with a normal frame then, and the count")
run(5, 50, "{ long = 0.5 }")
check(abs(E("S.biggest") - 0.2) < 1e-9, "a long frame later (not just after a change) is not counted as its hitch")

# FPS held at a cap: Vertical Sync, or an FPS limit.
X("S = SF.New(1); S.scale = 0.9")
c = run(30, 60, "{ vsync = true }")
check(len(c) == 1 and c[0][2] == "raise", "with Vertical Sync, FPS held at the goal counts as room to raise (%s)" % c)
X("S = SF.New(1)")
check(run(40, 50, "{ top = 50 }") == [], "an FPS limit of 50 under a goal of 60: 50 FPS is as good as it gets, so nothing is lowered")

# Someone else changed it.
X("S = SF.New(1); S.scale = 0.9; SF.Adopt(S, 0.8)")
check(E("S.own") == 0.8 and E("S.scale") == 0.8, "a render scale set by you is your new own value")
c = run(25, 30) + run(10, 30)
check(c == [(30.0, 0.75, "lower")], "and it counts as a change: the next one waits the 30 second gap (%s)" % c)

# --- The tab -----------------------------------------------------------------------------------------
X("NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
labels = [E(P + ".partButtons")[i].label for i in range(1, E("#" + P + ".partButtons") + 1)]
check(labels == ["Autotune", "Eye test", "Photo mode", "Steady FPS"], "the Experimental tab has a Steady FPS button (%s)" % labels)
X(P + ".partButtons[4].scripts.OnClick()")
SP = P + ".steady"
check(E(P + ".parts.steady.shown") and E(SP + ".head.label.text") == "Steady FPS" and E(SP + ".toggle.text") == "Turn on",
      "Steady FPS shows its own page, off, with Turn on")
check("may cause hitching" in E(SP + ".how.text") and "30 seconds" in E(SP + ".how.text"),
      "it names the game's own one and why not, and says how often it may change")
check(not E("NS.FPS.IsWatching('steady')") and E("not (EyeCandyDB.steady and EyeCandyDB.steady.on)"), "off by default: it isn't watching FPS")


def tick(secs, fps, long=None):
    # Frames through the FPS reader itself, as the game would run them.
    dt = 1 / fps
    n = int(round(secs * fps))
    if long:
        X("NS.FPS.Tick(%r)" % long)
    X("for i = 1, %d do NS.FPS.Tick(%r) end" % (n, dt))


def cv(name):
    return E("GetCVar(%r)" % name)


X("SetCVar('RenderScale', 1); SetCVar('useMaxFPS', 0); SetCVar('vsync', 0)")
X(SP + ".toggle.scripts.OnClick()")
check(E("NS.FPS.IsWatching('steady')") and E("EyeCandyDB.steady.on") and E(SP + ".toggle.text") == "Turn off",
      "Turn on starts watching FPS, and is saved")
tick(4, 50)
check(cv("RenderScale") == "1", "4 seconds of low FPS: render scale stays")
tick(2, 50)
check(abs(float(cv("RenderScale")) - 0.95) < 1e-6 and abs(E("EyeCandyDB.steady.set") - 0.95) < 1e-6,
      "after 5 seconds it lowers render scale one step, and saves what it set")
st = E(SP + ".status.text")
check("95% now" in st and "Yours is 100%" in st,"the page shows the render scale now and your own (%r)" % st)

# Backups, presets and Back see your own render scale, not the lowered one.
check(E("NS.SituationValue('RenderScale', GetCVar('RenderScale'))") in ("1", 1), "your own value for backups and Back is 100%")
check(E("NS.SituationValue('graphicsShadowQuality', '3')") == "3", "other settings are left alone")
check(E("NS.PatchWatch.Own('RenderScale', GetCVar('RenderScale'))") == "1", "the patch warning's copy keeps your own")
check(E("NS.FPS.Still({})") is False, "the FPS a preset gave isn't measured while render scale is lowered")

# A fight, Autotune: nothing changes.
X("INCOMBAT = true")
tick(40, 30)
check(abs(float(cv("RenderScale")) - 0.95) < 1e-6, "in a fight it never changes anything")
X("INCOMBAT = false")

# You change it yourself.
X("SetCVar('RenderScale', 0.8)")
tick(1, 60)
check(E("EyeCandyDB.steady.own") == 0.8 and E("EyeCandyDB.steady.set") is None, "you set 80% yourself: that is your own now")
tick(31, 40)
check(abs(float(cv("RenderScale")) - 0.75) < 1e-6, "low FPS: it lowers from your new own, after the 30 second gap")
tick(70, 120)
check(abs(float(cv("RenderScale")) - 0.8) < 1e-6, "FPS back: it raises to your 80%, never past it")

# Turn off puts your own back.
X("SetCVar('RenderScale', 1)")
tick(1, 60)
tick(40, 40)
check(float(cv("RenderScale")) < 1, "lowered again")
X(SP + ".toggle.scripts.OnClick()")
check(cv("RenderScale") == "1" and not E("NS.FPS.IsWatching('steady')") and not E("EyeCandyDB.steady.on"),
      "Turn off puts your own render scale back and stops watching")

# Logout and the next login.
X(SP + ".toggle.scripts.OnClick()")
tick(6, 40)
check(float(cv("RenderScale")) < 1, "on again, lowered again")
X('FIRE("PLAYER_LOGOUT")')
check(cv("RenderScale") == "1" and E("EyeCandyDB.steady.set") is None, "logging out puts your own back, so the game saves yours")
X("SetCVar('RenderScale', 0.85); EyeCandyDB.steady.set = 0.85; EyeCandyDB.steady.own = 1")
X('FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(cv("RenderScale") == "1" and E("NS.FPS.IsWatching('steady')"), "a login with it still lowered (a crash) puts your own back, and it carries on")

# Autotune and the others hold it back, even after FPS was already low for 4 seconds.
tick(4, 30)
X("NS.Autotune.IsRunning = function() return true end")
tick(60, 30)
check(cv("RenderScale") == "1", "while Autotune runs it never changes anything")
X("NS.Autotune.IsRunning = function() return false end")

# A step that doesn't help: the page says it stopped, and why.
tick(6, 30)
check(float(cv("RenderScale")) < 1, "low FPS again: it lowers")
tick(10, 30)
st = E(SP + ".status.text")
check("Lowering didn't help here, so it stopped" in st, "FPS no better after the step: the page says it stopped, and why (%r)" % st)
check("Biggest hitch from a change:" in st and "Changes this session:" in st, "and shows the biggest hitch and how many changes")
tick(30, 30)
check(cv("RenderScale") == "1", "once the gap is over, that step goes back")
X(SP + ".toggle.scripts.OnClick()")


def lowered():
    # Off, then on at 100%, then low FPS until it lowers one step (95%).
    X("if NS.SteadyFPS.IsOn() then NS.SteadyFPS.TurnOff() end; SetCVar('RenderScale', 1); NS.SteadyFPS.TurnOn()")
    tick(6, 40)
    return abs(float(cv("RenderScale")) - 0.95) < 1e-6


# Turned off in a fight, then on again in it: the lowered value never becomes yours.
check(lowered(), "lowered to 95%")
X("INCOMBAT = true; " + SP + ".toggle.scripts.OnClick()")
check(cv("RenderScale") == "0.95" and E("EyeCandyDB.steady.afterCombat"), "Turn off in a fight: render scale waits for the fight to end")
X(SP + ".toggle.scripts.OnClick()")
check(E("NS.SteadyFPS.IsOn()") and E("EyeCandyDB.steady.set") == 0.95, "on again in the fight: it carries on from 95%")
X("INCOMBAT = false")
tick(2, 60)
check(E("EyeCandyDB.steady.own") == 1, "after the fight your own is still 100%, not 95%")
X(SP + ".toggle.scripts.OnClick()")
check(cv("RenderScale") == "1", "and Turn off puts it back")

# Turned off while Autotune has render scale: what Autotune puts back is your own.
check(lowered(), "lowered again")
X("RUNNING = true; NS.Autotune.IsRunning = function() return RUNNING end")
X("EyeCandyDB.autotune = { before = { RenderScale = '0.95' } }; SetCVar('RenderScale', 0.6)")
X("NS.SteadyFPS.TurnOff()")
check(E("EyeCandyDB.autotune.before.RenderScale") == "1" and cv("RenderScale") == "0.6",
      "Turn off during Autotune: Autotune will put back your own, and its test value stays for now")
X("SetCVar('RenderScale', EyeCandyDB.autotune.before.RenderScale); EyeCandyDB.autotune = nil; RUNNING = false")
tick(1, 60)
check(cv("RenderScale") == "1" and E("EyeCandyDB.steady.set") is None, "Autotune ends: yours, and nothing left to put back")

# Turned off while Compare shows its own copy: once Compare puts the lowered value back, yours goes back.
check(lowered(), "lowered again")
X("CMP = true; local c = NS.IsComparing; NS.IsComparing = function() return CMP end; ORIG_CMP = c")
X("SetCVar('RenderScale', 1); NS.SteadyFPS.TurnOff()")
check(cv("RenderScale") == "1" and E("EyeCandyDB.steady.set") == 0.95, "Turn off during Compare: it waits")
X("SetCVar('RenderScale', 0.95); CMP = false; NS.IsComparing = ORIG_CMP")
tick(1, 60)
check(cv("RenderScale") == "1" and E("EyeCandyDB.steady.set") is None, "Compare ends on the lowered value: your own goes back")

# Turn on is refused while something else has your settings.
X("EyeCandyDB.photo = { before = {} }; " + SP + ".toggle.scripts.OnClick()")
st = E(SP + ".status.text")
check(not E("NS.SteadyFPS.IsOn()") and RED in st and "photo mode has your settings" in st, "Turn on while photo mode has your settings: refused, in red (%r)" % st)
X("EyeCandyDB.photo = nil")

# A preset that sets the very value it had lowered to: that is yours now.
check(lowered(), "lowered again")
X("local pv = NS.PresetValues; NS.PresetValues = function() return { RenderScale = '0.95' } end; NS.NoteOnPreset({ id = 'x' }); NS.PresetValues = pv")
check(E("EyeCandyDB.steady.own") == 0.95 and E("EyeCandyDB.steady.set") is None, "a preset setting 95% makes 95% yours")
X("NS.SteadyFPS.TurnOff()")
check(cv("RenderScale") == "0.95", "so Turn off leaves it")

# The waiting line names what holds it back.
X("SetCVar('RenderScale', 1); NS.SteadyFPS.TurnOn(); EyeCandyDB.eyeTest = { before = {} }")
tick(1, 60)
check("Waiting: the eye test has your settings." in E(SP + ".status.text"), "the page says what it waits for")
X("EyeCandyDB.eyeTest = nil; NS.SteadyFPS.TurnOff()")

done()
