"""Autotune (experimental tab): the tuning logic, then the run in the game.
Run: python tests/test_autotune.py"""
import os
from lib import boot, chat, check, done

lua = boot()
E, X = lua.eval, lua.execute

# A pretend PC (tests/autotune_sim.lua): MODEL, MEASURE, KNOBCOST and SIM, then GAME_SETUP for the run in the game.
X(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autotune_sim.lua'), encoding='utf-8').read())

# --- Judging one measurement --------------------------------------------------
X("T = {} for i = 1, 400 do T[i] = 0.01 end")
s = E("AT.Stats(T)")
check(abs(s.fps - 100) < 1e-6 and s.steady, "400 frames of 10 ms: 100 FPS, steady")
X("T = {} for i = 1, 380 do T[i] = 0.01 end for i = 381, 400 do T[i] = 0.1 end")
s = E("AT.Stats(T)")
check(s.fps < 70 and s.low < 20, "slow frames pull the average and the low down")
check(E("AT.Stats({}).fps") == 0, "no frames: 0 FPS, never a divide by zero")

check(E("AT.Verdict('target', 120, { fps = 160, steady = true })") == "pass", "160 FPS meets a 120 goal")
check(E("AT.Verdict('target', 120, { fps = 100, steady = true })") == "fail", "100 FPS misses a 120 goal")
check(E("AT.Verdict('target', 120, { fps = 120, steady = true })") == "fail",
      "exactly 120 misses: the goal needs 10% to spare, because cities and fights run slower")
check(E("AT.Verdict('target', 120, { fps = 131, steady = true })") == "again",
      "131 FPS is too close to the 132 line to call: measure again")
check(E("AT.Verdict('target', 120, { fps = 131, steady = true, again = true })") == "fail",
      "a second close call is judged as it is")
check(E("AT.Verdict('target', 120, { fps = 200, steady = false })") == "again", "a jerky measurement is measured again")

# --- A target run on a fast PC ------------------------------------------------
X("""
BASE = 300
COST = {
  graphicsComputeEffects = { ["2"] = 0.1, ["3"] = 0.25, ["4"] = 0.6 },
  graphicsShadowQuality = { ["3"] = 0.1, ["4"] = 0.2, ["5"] = 0.35 },
  RenderScale = { ["0.7"] = 0.1, ["0.8"] = 0.2, ["0.9"] = 0.3, ["1"] = 0.4, ["1.25"] = 0.9, ["1.5"] = 1.6 },
  graphicsTextureResolution = { ["2"] = 0.01 },
}
""")
action, tries, n, run = E("SIM('target', 120)")
final = E("MODEL()")
check(action.done == "finished", "a reachable goal finishes")
check(final >= 132, "the settings left on meet the goal with 10%% to spare (%.0f FPS)" % final)
check(E("STATE.graphicsTextureResolution") == 2, "cheap good-looking settings end at the top (textures)")
check(E("STATE.graphicsComputeEffects") < 4, "the costly top step of compute effects is left off")
check(E("STATE.RenderScale") >= 1, "render scale reaches 100% before costly extras")
check(n <= E("AT.MAX_TRIES"), "it stays within the measurement limit (%d)" % n)

# Render scale over 100% is only tried after every other setting is done.
X("""
ORDER = {}
local _, tries = SIM('target', 60)
for i, t in ipairs(tries) do ORDER[i] = t end
""")
order = E("ORDER")
first_up = None
for i in range(1, len(order) + 1):
    t = order[i]
    if t.cvar == "RenderScale" and t.value > 1:
        first_up = i
        break
later = [order[i].cvar for i in range(first_up + 1, len(order) + 1)] if first_up else []
check(first_up is not None and all(c == "RenderScale" for c in later),
      "render scale over 100% comes last, after every other setting")

# A raise that fails is put back before the next setting is tried.
X("""
BASE = 200
COST = { graphicsComputeEffects = { ["2"] = 5, ["3"] = 5, ["4"] = 5 } }
""")
action, tries, n, run = E("SIM('target', 120)")
check(E("STATE.graphicsComputeEffects") == 1, "a setting that always misses stays at its lowest")
check(E("MODEL()") >= 132, "and the goal still holds at the end")

# --- A goal the PC can't reach ------------------------------------------------
X("BASE = 100; COST = {}")
action, tries, n, run = E("SIM('target', 120)")
check(action.done == "unreachable", "lowest settings at 100 FPS: 120 can't be reached")
check(abs(action.best - 100) < 1, "it says the best this spot reached")

# --- Settings the GPU or the client don't support ------------------------------
X("BASE = 400; COST = {}")
X("""
SEEN = {}
local _, tries = SIM('target', 60, {
  supported = function(cvar, v) return not (cvar == "graphicsParticleDensity" and v > 3) end,
  exists = function(cvar) return cvar ~= "vrsValar" end,
})
for _, t in ipairs(tries) do SEEN[t.cvar .. "=" .. tostring(t.value)] = true end
""")
check(not E("SEEN['graphicsParticleDensity=4']") and not E("SEEN['graphicsParticleDensity=5']"),
      "values the GPU can't do are never tried")
check(not any(str(k).startswith("vrsValar") for k in E("SEEN").keys()), "a setting missing from this client is left out")
check(E("STATE.graphicsParticleDensity") == 3, "the top value it can do is used")

# --- Close calls are measured twice and averaged --------------------------------
X("BASE = 300; COST = { RenderScale = { ['1'] = 1.29 } }")  # 300 / 2.29 = 131: close to the 132 line
action, tries, n, run = E("SIM('target', 120)")
x = E("""(function() local c = 0 for _, t in ipairs(select(2, SIM('target', 120))) do
  if t.cvar == 'RenderScale' and t.value == 1 then c = c + 1 end end return c end)()""")
check(x == 1, "a close call measures again without changing anything")

# --- Best balance -------------------------------------------------------------
X("""
BASE = 250
COST = {
  graphicsTextureResolution = { ["2"] = 0.01 },
  graphicsComputeEffects = { ["2"] = 0.4, ["3"] = 0.8, ["4"] = 1.5 },
  RenderScale = { ["0.7"] = 0.02, ["0.8"] = 0.04, ["0.9"] = 0.06, ["1"] = 0.08, ["1.25"] = 0.5, ["1.5"] = 1 },
}
""")
action, tries, n, run = E("SIM('balance')")
check(action.done == "finished", "best balance finishes")
check(E("STATE.graphicsTextureResolution") == 2, "balance keeps a step that costs almost nothing")
check(E("STATE.graphicsComputeEffects") == 1, "balance skips a step that costs a lot for a little look")
check(E("STATE.RenderScale") == 1, "balance takes render scale to 100% when it is cheap, but not past it here")
check(E("MODEL()") >= 66, "balance never goes under 60 FPS (with 10% to spare)")

X("BASE = 50; COST = {}")
action, tries, n, run = E("SIM('balance')")
check(action.done == "unreachable", "balance on a PC under 60 FPS at its lowest says so")

# --- Measurement limit --------------------------------------------------------
X("BASE = 300; COST = {}; AT.MAX_TRIES_SAVED = AT.MAX_TRIES; AT.MAX_TRIES = 6")
action, tries, n, run = E("SIM('target', 60)")
check(action.done == "time" and n <= 6, "it stops at the measurement limit")
check(E("MODEL()") >= 66, "and what it leaves on still met the goal")
X("AT.MAX_TRIES = AT.MAX_TRIES_SAVED")

# --- The list of changes, with what each cost --------------------------------------
X("""
BASE = 300
COST = { graphicsShadowQuality = { ["5"] = 0.2 } }
""")
X("RES = { SIM('target', 60, { current = { graphicsShadowQuality = 3 } }) }")
changes = E("AT.Changes(RES[4])")
row = None
for i in range(1, len(changes) + 1):
    if changes[i].cvar == "graphicsShadowQuality":
        row = changes[i]
check(row is not None and row.before == 3 and row.after == 5, "changes list each setting from before to after")
check(row is not None and row.cost is not None and row.cost > 0, "and the FPS its last raise cost")
check(row is not None and row.ms is not None and row.ms > 0, "and the time a frame it cost, so the costs compare fairly")

# --- The critic's findings (16 Nov 2026) --------------------------------------------
# One long frame (a shader compile or a texture loading) is left out of the average and marks a hitch.
X("T = {} for i = 1, 399 do T[i] = 0.01 end T[400] = 0.3")
s = E("AT.Stats(T)")
check(abs(s.fps - 100) < 0.5 and s.hitch, "one long frame is left out of the average, and marked as a hitch")
X("T = {} for i = 1, 400 do T[i] = 0.01 end")
s = E("AT.Stats(T)")
check(s.spread < 1e-6 and abs(s.slow - 100) < 1e-6 and not s.hitch, "even frames: no spread, no hitch, the slow frames as fast as the rest")

# The slow frames must hold up as well as the average.
check(E("AT.Verdict('target', 120, { fps = 160, slow = 90, steady = true })") == "fail",
      "160 FPS on average but slow frames at 90: misses a 120 goal")
check(E("AT.Verdict('target', 120, { fps = 160, slow = 110, steady = true })") == "pass", "slow frames at 110 hold a 120 goal")

# A cap at the screen's refresh rate (Vertical Sync).
check(E("AT.Cap({ fps = 60.2, spread = 0.004 })") == 60, "a steady 60 FPS is a cap at 60")
check(E("AT.Cap({ fps = 143.5, spread = 0.004 })") == 144, "a steady 143.5 is a cap at 144")
check(E("AT.Cap({ fps = 60.2, spread = 0.08 })") is None, "an uneven 60 is not a cap")
check(E("AT.Cap({ fps = 70, spread = 0.004 })") is None, "a steady 70 is not a refresh rate")
check(E("AT.Cap({ fps = 60.2, spread = 0.03 }, true)") == 60, "with Vertical Sync on, a little more spread still counts")

X("BASE = 200; COST = { graphicsShadowQuality = { ['4'] = 0.5, ['5'] = 3 } }; CAP = 60")
action, tries, n, run = E("SIM('target', 60)")
check(action.done == "finished" and run.cap == 60, "with FPS held at 60, a 60 FPS goal is tuned, not called unreachable")
check(min(E("MODEL()"), 60) >= 60 * 0.97 and E("STATE.graphicsShadowQuality") == 4,
      "and it raises settings while FPS stays at the cap, and stops when it would fall under it")
action, tries, n, run = E("SIM('target', 120)")
check(action.done == "unreachable" and action.cap == 60, "a 120 goal with FPS held at 60 can't be reached, and it says the cap")
action, tries, n, run = E("SIM('balance')")
check(action.done == "finished", "best balance with FPS held at 60 finishes")
X("CAP = nil")

# Best balance on a PC whose graphics card sets the limit: render scale reaches 100% when 100% holds 60 FPS.
X("BASE = 200; COST = { RenderScale = { ['0.7'] = 0.361, ['0.8'] = 0.778, ['0.9'] = 1.25, ['1'] = 1.778, ['1.25'] = 3.34, ['1.5'] = 5.25 } }")
action, tries, n, run = E("SIM('balance')")
check(E("STATE.RenderScale") == 1 and E("MODEL()") >= 66, "best balance takes render scale to 100%% when it holds 60 FPS (%.0f FPS)" % E("MODEL()"))

# A goal on a mid PC with every setting costing what KNOBS guesses: lighting isn't starved by clutter and view distance.
X("BASE = 150; KNOBCOST(0.04)")
action, tries, n, run = E("SIM('target', 90)")
check(action.done == "finished" and n <= E("AT.MAX_TRIES"), "a goal on a mid PC finishes within the limit (%d measurements)" % n)
check(E("STATE.graphicsLightMode") >= 1 and E("MODEL()") >= 99, "lighting's good first step is taken, and the goal holds")
goal_n = n

# Best balance with every step free isn't measured twice for each: a free step is not a close call.
X("BASE = 300; COST = {}")
action, tries, n, run = E("SIM('balance')")
check(action.done == "finished" and n <= E("AT.MAX_TRIES"), "best balance with free steps finishes within the limit (%d measurements)" % n)

# A PC whose CPU sets the limit: render scale is free, and the settings that load the CPU keep more spare.
X("""SPLIT = { cpu = 12, gpu = 4, cpuCost = { graphicsViewDistance = { ['5'] = 0.6, ['7'] = 1.2, ['9'] = 2.5 } } }""")
action, tries, n, run = E("SIM('target', 60)")
check(run.cpuBound is True and E("STATE.RenderScale") >= 1, "a CPU-bound PC is spotted, and render scale goes to 100% or more")
check(E("STATE.graphicsViewDistance") == 7, "view distance keeps 25%% spare on a CPU-bound PC (%.0f FPS at 9 would pass 66, not 75)" % (1000 / 14.5))
X("""SPLIT = { cpu = 4, gpu = 12 }""")
action, tries, n, run = E("SIM('target', 60)")
check(not run.cpuBound, "a PC whose graphics card sets the limit is not called CPU-bound")
X("SPLIT = nil")

# The PC slows as the run goes on (it warms up): the kept settings are measured again, and the result holds at the end.
X("BASE = 150; KNOBCOST(0.04)")
action, tries, n, run = E("SIM('target', 60, { noise = function(n) return 1 - 0.004 * n end })")
check(action.done in ("finished", "time") and E("LASTM.fps") >= 66, "with the PC slowing, the last measurement still meets the goal (%.0f FPS)" % E("LASTM.fps"))
check(run.finalDone or action.done == "time", "the result is measured once more at the end")
# Review finding 1: a check on the way is judged loosely, so it never stands in for the last one.
X("AT.RECHECK_SAVED = AT.RECHECK; AT.RECHECK = 3")
action, tries, n, run = E("SIM('target', 60, { noise = function(n) return 1 - 0.004 * n end })")
# run.last is what the last check judged (two close looks averaged) and what the result reports.
check(run.last.fps >= 66 and run.finalDone, "with checks often, the last one is still judged in full (%.1f FPS)" % run.last.fps)
X("AT.RECHECK = AT.RECHECK_SAVED")
# Review finding 2: a PC that drops at the end can't undo raise after raise past the limit.
action, tries, n, run = E("SIM('target', 60, { noise = function(n) return n > 30 and 0.7 or 1 end })")
check(n <= E("AT.MAX_TRIES") + 5, "a drop at the end stops undoing raises at the limit (%d measurements)" % n)
# Review finding 6: a run that ends just under the limit with nothing left to try is finished, not out of time.
X("BASE = 300; COST = {}")
action, tries, n, run = E("SIM('balance')")
X("AT.MAX_TRIES_SAVED = AT.MAX_TRIES; AT.MAX_TRIES = %d" % (n + 1))
action, tries, n2, run = E("SIM('balance')")
check(action.done == "finished", "a run that needs one under the limit is finished, not cut short")
X("AT.MAX_TRIES = AT.MAX_TRIES_SAVED")
# Review findings 4 and 5: a PC that happens to run evenly near 90 isn't a cap, and 180 Hz is a refresh rate.
check(E("AT.Cap({ fps = 90, spread = 0.01 })") is None, "without Vertical Sync, frames 1% uneven at 90 aren't a cap")
check(E("AT.Cap({ fps = 180, spread = 0.004 })") == 180, "180 Hz is a refresh rate too")

# A sample far from the line stops early.
X("ER = AT.NewRun('target', 120, { exists = function() return true end, supported = function() return true end }); ER.try = { knob = ER.knobs[1], index = 2 }")
check(E("AT.Early(ER, { fps = 90, frames = 200 })"), "a sample far under the line stops early")
check(not E("AT.Early(ER, { fps = 130, frames = 200 })"), "a sample near the line runs its full time")
check(E("AT.Early(ER, { fps = 200, frames = 200 })"), "with a goal, a sample far over the line stops early too")

check(E("AT.CAPS.useMaxFPSBk") == 0, "the background FPS limit is lifted too, so switching windows can't spoil a run")

# --- The goals (15 Nov 2026: add 30, 75, 144 and 180, drop 90) -----------------------------
GOALS = [30, 60, 75, 120, 144, 165, 180, 240]
check([E("AT.GOALS")[i] for i in range(1, E("#AT.GOALS") + 1)] == GOALS,
      "the goals are 30, 60, 75, 120, 144, 165, 180 and 240 FPS, in that order")
# A slow PC (a laptop) at 30 FPS: tuned, not called unreachable, and the goal holds with 10% to spare.
X("BASE = 45; KNOBCOST(0.04)")
action, tries, n, run = E("SIM('target', 30)")
check(action.done == "finished" and E("MODEL()") >= 33, "a 30 FPS goal on a PC that runs 45 at its lowest is tuned (%.0f FPS)" % E("MODEL()"))
# A screen at 144 Hz or 75 Hz with Vertical Sync: a goal at that rate is judged just under it, not missed.
for hz in (75, 144, 180):
    X("BASE = 400; COST = { graphicsShadowQuality = { ['5'] = 0.2 } }; CAP = %d" % hz)
    action, tries, n, run = E("SIM('target', %d)" % hz)
    check(action.done == "finished" and run.cap == hz, "with FPS held at %d, a %d FPS goal is tuned" % (hz, hz))
X("CAP = nil")

# --- The run in the game ------------------------------------------------------
# The pretend PC now reads the game's settings, and frames arrive through the run's OnUpdate.
X("GAME_SETUP()")
PLAY = lambda n=None: X("PLAY(%s)" % (n or "nil"))
X("""
BASE = 300
COST = {
  graphicsComputeEffects = { ["2"] = 0.1, ["3"] = 0.25, ["4"] = 0.6 },
  graphicsShadowQuality = { ["3"] = 0.1, ["4"] = 0.2, ["5"] = 0.35 },
  RenderScale = { ["0.7"] = 0.1, ["0.8"] = 0.2, ["0.9"] = 0.3, ["1"] = 0.4, ["1.25"] = 0.9, ["1.5"] = 1.6 },
}
""")
BEFORE = {c: E("GetCVar('%s')" % c) for c in
          ("graphicsShadowQuality", "graphicsComputeEffects", "RenderScale", "graphicsViewDistance", "useTargetFPS")}

X("INCOMBAT = true")
ok, why = E("AT.Start('target', 120)")
check(not ok and "fight" in why, "it won't start in a fight")
X("INCOMBAT = false; MOVING = true")
ok, why = E("AT.Start('target', 120)")
check(not ok and "still" in why, "it won't start while moving")
X("MOVING = false; CHAT = {}")

ok = E("AT.Start('target', 120)")
check(ok and E("AT.IsRunning()"), "it starts standing still out of a fight")
check(E("EyeCandyDB.autotune.before.graphicsShadowQuality") == "5", "your settings from before are saved first")
check(E("GetCVar('useTargetFPS')") == "0", "target FPS is off while measuring (it would change settings by itself)")
PLAY(20)
check(E("AT.progress.count") >= 1, "progress shows which measurement it is on")
PLAY()
check(not E("AT.IsRunning()") and E("AT.result") is not None, "the run finishes with a result")
check(E("GetCVar('useTargetFPS')") == "1", "the FPS settings it lifted are put back at the end")
check(E("GAMEFPS()") >= 132, "the result left on meets the goal (%.0f FPS)" % E("GAMEFPS()"))
check(E("EyeCandyDB.autotune.result") is True, "the way back stays saved until you choose")
check(any("Autotune is done" in m for m in chat(lua)), "it says in chat that it is done")
tuned = E("GetCVar('graphicsShadowQuality')")

ok = E("AT.Keep()")
p = E("NS.FindPresetByName('Autotune 120 FPS')")
check(ok and p is not None, "Keep saves the result as your preset \"Autotune 120 FPS\"")
check(p is not None and p['desc'] == "Tested in Trade District, Stormwind City at 62.1, 70.4, facing north-west. "
      "Field of view 90, camera distance 15. A wider view or a camera further out draws more.",
      "the preset's tooltip says where it was tested, which way you faced, and the camera (%s)" % (p and p['desc']))
check(E("AT.PlaceText({ zone = 'The Stockade', fov = 90 })") ==
      "Tested in The Stockade. Field of view 90. A wider view or a camera further out draws more.",
      "in an instance, with no position or facing from the game, it says what it has")
check(E("AT.PlaceText({})") is None, "with nothing from the game, no line at all")
check(p is not None and p['values']['graphicsShadowQuality'] == tuned, "the preset holds the tuned values")
check(E("GetCVar('graphicsShadowQuality')") == tuned and E("EyeCandyDB.autotune") is None,
      "Keep leaves the result on and clears the way back")

# Once more for the same goal: a second preset, never over the first.
E("AT.Start('target', 120)")
PLAY()
E("AT.Keep()")
check(E("NS.FindPresetByName('Autotune 120 FPS (2)')") is not None, "a second run for the same goal gets its own name")

# Back to before Autotune.
X("NS.ApplyValues({ graphicsShadowQuality = '2', RenderScale = '1' })")
E("AT.Start('target', 60)")
PLAY()
E("AT.PutBack()")
check(E("GetCVar('graphicsShadowQuality')") == "2" and E("EyeCandyDB.autotune") is None,
      "Back to before Autotune puts your settings back and clears the way back")

def stopped_by(what, at, word):
    X("NS.ApplyValues({ graphicsShadowQuality = '4', graphicsViewDistance = '7', RenderScale = '1' }); CHAT = {}")
    E("AT.Start('target', 60)")
    X("PLAY(nil, function(i) if i == 3000 then %s end end)" % at)
    msgs = chat(lua)
    check(not E("AT.IsRunning()") and E("GetCVar('graphicsShadowQuality')") == "4"
          and E("GetCVar('graphicsViewDistance')") == "7" and E("EyeCandyDB.autotune") is None
          and any(word in m for m in msgs),
          "%s stops it and puts your settings back" % what)
    X("MOVING = false; INCOMBAT = false; FACING = 1.0; ZOOM = 15; MOUSELOOK = false; MOUSEDOWN = false; SettingsPanel.shown = false")

stopped_by("moving", "MOVING = true", "you moved")
stopped_by("the fight event", "FIRE('PLAYER_REGEN_DISABLED')", "a fight")
stopped_by("a loading screen", "FIRE('PLAYER_LEAVING_WORLD')", "loading screen")
stopped_by("turning", "FACING = 2.0", "you turned")
stopped_by("zooming the camera", "ZOOM = 20", "zoomed the camera")
stopped_by("dragging the camera", "MOUSELOOK = true", "moved the camera")
stopped_by("holding the left button on the world", "MOUSEDOWN = true", "moved the camera")

# A quick click on the world (picking a target) is not a camera drag.
E("AT.Start('target', 60)")
X("PLAY(4000, function(i) MOUSEDOWN = i >= 3000 and i < 3005 end); MOUSEDOWN = false")
check(E("AT.IsRunning()"), "a quick click on the world doesn't stop it")
X("AT.Stop('test')")
# A camera still easing after a scroll when Start is pressed is not a zoom: the distance is read once it settles.
X("ZOOM = 10")
E("AT.Start('target', 60)")
X("PLAY(nil, function(i) if i <= 50 then ZOOM = 10 + i * 0.1 end end)")
check(E("AT.result") is not None and E("AT.result.place.zoom") == 15,
      "a camera still easing at Start doesn't stop it, and the distance recorded is where it came to rest")
X("AT.PutBack(true); ZOOM = 15")
check(E("AT.PlaceText({ zone = 'Elwynn Forest' })") == "Tested in Elwynn Forest.", "with only the zone, just the zone")
stopped_by("opening Options", "SettingsPanel.shown = true", "Options")
stopped_by("another Eye Candy change", "NS.ApplyAll(false, true)", "another setting")

# A fight: the run stops at once, but your settings only come back after the fight.
X("NS.ApplyValues({ graphicsShadowQuality = '4' }); CHAT = {}")
E("AT.Start('target', 60)")
X("PLAY(nil, function(i) if i == 3000 then INCOMBAT = true end end)")
check(not E("AT.IsRunning()") and E("GetCVar('graphicsShadowQuality')") != "4" and E("EyeCandyDB.autotune") is not None,
      "a fight stops the run, but nothing changes during the fight, and the way back is kept")
check(not E("AT.PutBack()"), "Back to before Autotune waits too: it refuses in a fight")
X("INCOMBAT = false; CHAT = {}; FIRE('PLAYER_REGEN_ENABLED')")
check(E("GetCVar('graphicsShadowQuality')") == "4" and E("EyeCandyDB.autotune") is None
      and any("fight is over" in m for m in chat(lua)), "when the fight ends, your settings come back")

# A menu value can reset hidden values (the game does this for view distance). They come back too.
X("""
local set = SetCVar
function SetCVar(n, v) local r = set(n, v); if n == "graphicsViewDistance" then set("farclip", "5000") end return r end
NS.ApplyValues({ farclip = '7000', graphicsViewDistance = '7' })
""")
E("AT.Start('target', 60)")
X("PLAY(nil, function(i) if i == 9000 then MOVING = true end end); MOVING = false")
check(E("GetCVar('farclip')") == "7000" and E("GetCVar('graphicsViewDistance')") == "7",
      "a hidden value a menu value reset is put back as well")
E("AT.Start('target', 60)")
X("PLAY()")
check(E("GetCVar('farclip')") == "5000", "(the pretend game did reset it during the run)")
E("AT.Keep()")
kept = E("NS.FindPresetByName('Autotune 60 FPS')")
check(kept is not None and kept['values']['farclip'] == "7000" and E("GetCVar('farclip')") == "7000",
      "Keep's preset holds your hidden values, not the ones the run reset")

# In a city with the city switch on: Keep saves your own value, not the one the switch lowered.
X("""
NS.ApplyValues({ entityLodDist = '40' }); SetCVar('entityLodDist', '10')
EyeCandyDB.situationActive = { key = 'city', set = { entityLodDist = { was = '40', now = '10' } } }
""")
E("AT.Start('target', 60)")
X("PLAY()")
E("AT.Keep()")
kept = E("NS.FindPresetByName('Autotune 60 FPS (2)')")
check(kept is not None and kept['values']['entityLodDist'] == "40",
      "in a city, Keep's preset holds your own value, not the one the city switch lowered")
X("EyeCandyDB.situationActive = nil")

# A backup taken mid-run (a preset applied, or Create backup) holds your settings, not the run's.
X("NS.ApplyValues({ graphicsShadowQuality = '4' }); BACKUP = nil")
E("AT.Start('target', 60)")
X("PLAY(nil, function(i) if i == 3000 then BACKUP = NS.CreateBackup('manual', 'Mid run') end end)")
check(E("BACKUP") is not None and E("BACKUP['values'].graphicsShadowQuality") == "4" and not E("AT.IsRunning()"),
      "a backup mid-run stops the run first, so it holds your settings")

# A finished result not kept before a reload is thrown away, and says so.
E("AT.Start('target', 60)")
X("PLAY(); CHAT = {}; FIRE('PLAYER_ENTERING_WORLD', false, true)")
check(E("EyeCandyDB.autotune") is None and any("didn't save" in m for m in chat(lua)),
      "a result not kept before a reload goes back, and says you didn't keep it")

# Keep when the preset can't be put on: says so, and leaves your own settings on.
X("NS.ApplyValues({ graphicsShadowQuality = '4' })")
E("AT.Start('target', 60)")
X("PLAY(); local apply = NS.ApplyPresetById; NS.ApplyPresetById = function() return false end; AT.Keep(); NS.ApplyPresetById = apply")
check("couldn't be applied" in (E("AT.message") or "") and E("GetCVar('graphicsShadowQuality')") == "4",
      "if Keep can't put the preset on, it says so and your settings stay")

# An event this client doesn't know must not stop the others being heard.
odd = boot("""
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "RegisterEvent" then return function(self, ev) if ev == "PLAYER_STARTED_MOVING" then error("unknown event") end end end
  return index(t, k)
end
EyeCandyDB = { autotune = { before = { graphicsShadowQuality = '3' } } }
""")
odd.execute("SetCVar('graphicsShadowQuality', '1'); FIRE('PLAYER_ENTERING_WORLD', true, false)")
check(odd.eval("GetCVar('graphicsShadowQuality')") == "3", "an unknown event name doesn't stop the login restore")

# A crash mid-run (no events, the run's memory gone): the next login puts your settings back.
other = boot("EyeCandyDB = { autotune = { before = { graphicsShadowQuality = '3' }, mode = 'target', goal = 60 } }")
other.execute("SetCVar('graphicsShadowQuality', '1'); CHAT = {}; FIRE('PLAYER_ENTERING_WORLD', true, false)")
check(other.eval("GetCVar('graphicsShadowQuality')") == "3" and other.eval("EyeCandyDB.autotune") is None
      and any("didn't finish" in m for m in chat(other)), "after a crash mid-run, the next login puts your settings back")

# A goal this PC can't reach.
X("NS.ApplyValues({ graphicsShadowQuality = '3' }); BASE = 100")
E("AT.Start('target', 240)")
PLAY()
msg = E("AT.message") or ""
check("can't be reached" in msg and "FPS stayed at 100" in msg and msg.count("Vertical Sync") == 1,
      "an unreachable goal says so, and names the cap once (%s)" % msg)
check(E("GetCVar('graphicsShadowQuality')") == "3" and E("EyeCandyDB.autotune") is None,
      "and puts your settings back")

# Review finding 3: the cap note only when the cap changed how the goal was judged.
X("NS.ApplyValues({ graphicsShadowQuality = '3' }); BASE = 144")
E("AT.Start('target', 60)")
PLAY()
check(E("AT.result") is not None and E("AT.result.cap") is None, "a 60 goal under a 144 cap was judged as usual, so no cap note")
X("AT.PutBack(true); BASE = 60")
E("AT.Start('target', 60)")
PLAY()
check(E("AT.result") is not None and E("AT.result.cap") == 60, "a 60 goal at a 60 cap says so")
X("AT.PutBack(true)")

# What the game tells about the PC.
m = E("AT.Machine()")
check(m.gpu == "NVIDIA GeForce RTX 3090" and m.width == 2560 and m.vsync is True, "it reads the GPU, the screen and vsync")

# --- The Experimental tab -----------------------------------------------------------
# Each button's width as the tab asks ns.Button for it (the harness keeps no frame sizes).
X("local button = NS.Button; NS.Button = function(p, t, w, f) local b = button(p, t, w, f); b.builtW = w; return b end")
X("BASE = 300; CHAT = {}; NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
check(E(P + ".built") and E("EyeCandyMainFrame.tabButtons.autotune.text") == "Experimental",
      "the Experimental tab is there and builds")
pc = E(P + ".pc.text")
check("RTX 3090" in pc and "2560 x 1440" in pc and "Vertical Sync is on" in pc and "CPU" in pc,
      "Your PC shows the GPU, the window, vsync, and says what the game won't tell")
check("best" in E(P + ".goalText.text").lower() or "worth" in E(P + ".goalText.text"), "with no goal picked, it starts on Best balance")

labels = [E(P + ".goals")[i].label for i in range(1, E("#" + P + ".goals") + 1)]
check(labels == ["%d FPS" % g for g in GOALS] + ["Best balance"], "nine goal buttons, slowest first, then Best balance (%s)" % labels)
width = sum(E(P + ".goals")[i].builtW for i in range(1, len(labels) + 1)) + 4 * (len(labels) - 1)
check(width <= E("NS.ROW_W") - 16, "the nine goal buttons fit on one line (%d of %d px)" % (width, E("NS.ROW_W") - 16))
G120 = P + ".goals[%d]" % (labels.index("120 FPS") + 1)
X(G120 + ".scripts.OnClick()")
check(E("EyeCandyDB.autotuneGoal.goal") == 120 and "120 FPS" in E(P + ".goalText.text"), "picking 120 FPS remembers it and says what it means")
X(P + ".start.scripts.OnClick()")
check(E("AT.IsRunning()") and E(P + ".start.text") == "Stop", "Start starts it, and the button becomes Stop")
X("PLAY(1000)")
check("measurement" in E(P + ".status.text") and "mouse" in E(P + ".status.text"), "the status says which measurement and not to touch anything")
X(P + ".start.scripts.OnClick()")
check(not E("AT.IsRunning()") and "pressed Stop" in E(P + ".status.text"), "Stop stops it and says your settings are back")

X(P + ".start.scripts.OnClick(); PLAY(); NS.RefreshUI()")
res = E(P + ".result.text")
check(E(P + ".keep.shown") and "FPS before" in res and " to " in res, "the result shows before and after, and each change")
X(P + ".putBack.scripts.OnClick(); NS.RefreshUI()")
check(not E(P + ".keep.shown") and E("AT.result") is None, "Back to before Autotune clears the result")

# The result's notes, and each cost in FPS at the result's rate (from its time a frame).
check(abs(E("AT.CostFPS(1, 100)") - 1000 / 9 + 100) < 1e-6, "1 ms a frame at 100 FPS costs about 11 FPS")
X("""AT.result = { mode = 'target', goal = 60, name = 'x', before = 60, after = 60, cap = 60, cpuBound = true,
  changes = { { cvar = 'graphicsShadowQuality', before = 1, after = 4, ms = 2 } } }; NS.RefreshUI()""")
res = E(P + ".result.text")
check("FPS stays at 60" in res and "CPU sets the limit" in res and "costs about 8 FPS" in res,
      "the result says when FPS was held at a cap, when the CPU sets the limit, and each cost in FPS")
X("AT.result = nil; NS.RefreshUI()")

# A goal no longer offered (90 FPS, saved before 15 Nov 2026) shows as Best balance: one gold button, and Start uses it.
X("SAVEDGOAL = EyeCandyDB.autotuneGoal; EyeCandyDB.autotuneGoal = { mode = 'target', goal = 90 }; NS.RefreshUI()")
gold = [E(P + ".goals")[i].label for i in range(1, len(labels) + 1) if E(P + ".goals")[i].text.startswith("|cffffd100")]
check(gold == ["Best balance"] and "90" not in E(P + ".goalText.text"), "a saved 90 FPS goal falls back to Best balance (%s)" % gold)
X("EyeCandyDB.autotuneGoal = SAVEDGOAL; NS.RefreshUI()")

# --- The UI rules (docs/ui-rules.md) ----------------------------------------------------
GOLD, WHITE, GREY, RED = "|cffffd100", "|cffffffff", "|cff9d9d9d", "|cffff4040"
check(E(P + ".head.label.text") == "Autotune" and E(P + ".head.note.text") == "Experimental"
      and E(P + ".resultHead.label.text") == "Result", "headings come from ns.Header, and Experimental is a grey note, not a colour of its own")
check(E(G120 + ".text").startswith(GOLD) and E(P + ".goals[1].text").startswith(WHITE),
      "the chosen goal is gold, the others white")
check(E(P + ".keep.text") == "Save as preset" and E(P + ".putBack.text") == "Back to before Autotune",
      "the result's buttons don't share a word with the bar's Keep my settings applied")
# One word for undo (rule 2): "Back to before", never "Put mine back".
X("""AT.result = { mode = 'target', goal = 60, name = 'x', before = 50, after = 60, changes = {} }; NS.RefreshUI()""")
check(E(P + ".putBack.text") == "Back to before Autotune" and "Put mine back" not in E(P + ".result.text"),
      "the undo button is labelled Back to before Autotune, and the result line never calls it anything else")
X("AT.result = nil; NS.RefreshUI()")

# A refusal shows in red, next to Start.
X("MOVING = true; " + P + ".start.scripts.OnClick(); MOVING = false; NS.RefreshUI()")
st = E(P + ".status.text")
check(not E("AT.IsRunning()") and st.startswith(RED) and "Stand still" in st, "Start while moving is refused, in red, in the window")

# The window says Autotune has your settings, and chat stays quiet while the tab is in front.
X("CHAT = {}; " + P + ".start.scripts.OnClick(); PLAY(1000); NS.RefreshUI()")
check(E("NS.AutotuneNote()") == "Autotune is testing settings" and "Testing your settings" in E(P + ".status.text"),
      "while it runs, the note for the title says so, and so does its own row")
X(P + ".start.scripts.OnClick()")
check(not any("Autotune" in m for m in chat(lua)), "with the tab in front, the stop shows there, not in chat")
X(P + ".start.scripts.OnClick(); PLAY(); NS.RefreshUI()")
check(E("NS.AutotuneNote()") == "Autotune's settings are on, not saved yet" and "settings are in use, not saved yet" in E(P + ".result.text"),
      "with a result waiting, the title note and the result both say Autotune's settings are on")

# The page is as tall as everything on it. Every block is chained under the one above, and long lines
# wrap, so each text is measured (GetStringHeight), not counted at 14px a line, and a taller block
# anywhere pushes the page's end down. The harness has no font metrics: stub them.
X("CONTENT = " + P + ".content; CONTENT.SetHeight = function(self, h) self.h = h end; RES = " + P + ".result")
lines = E(P + ".result.text").count("\n") + 1
X("RES.GetStringHeight = nil; NS.RefreshUI()")
base = E("CONTENT.h")
X("RES.GetStringHeight = function() return 0 end; NS.RefreshUI()")
check(E("CONTENT.h") == base, "a measurement of 0 is no measurement: 14px a line is used")
X("RES.GetStringHeight = function() return 410 end; NS.RefreshUI()")
check(E("CONTENT.h") == base - lines * 14 + 410, "with wrapped result lines, the page takes the measured height (%s)" % E("CONTENT.h"))
X("RES.GetStringHeight = nil; NS.RefreshUI()")
for part in ("pc", "goalText", "status", "how", "why"):
    X("%s.%s.GetStringHeight = function() return 300 end; NS.RefreshUI()" % (P, part))
    grown = E("CONTENT.h")
    X("%s.%s.GetStringHeight = nil; NS.RefreshUI()" % (P, part))
    check(grown > base and E("CONTENT.h") == base, "a wrapped %s text above the result makes the page taller, so the result's end stays in reach (%s to %s)" % (part, base, grown))
# Every block counted, nothing assumed: with each text and frame measured, the height is their sum.
X("""for _, k in ipairs({"why", "pc", "goalText", "styleText", "fromText", "status", "how"}) do %s[k].GetStringHeight = function() return 20 end end
RES.GetStringHeight = function() return 100 end
for _, f in ipairs({ %s.goals[1], %s.styles[1], %s.fromPick, %s.start, %s.keep }) do f.GetHeight = function() return 24 end end
NS.RefreshUI()""" % (P, P, P, P, P, P))
H = lambda k: E(P + ".headH." + k)
want = H("head") + 4 + 20 + 16 + H("pc") + 4 + 20 + 16 + H("goal") + 4 + 24 + 8 + 20 \
    + 16 + H("style") + 4 + 24 + 8 + 20 + 16 + H("from") + 4 + 24 + 8 + 20 + 8 + 24 + 8 + 20 + 8 + 20 \
    + 16 + H("result") + 4 + 24 + 8 + 100 + 16
check(E("CONTENT.h") == want, "with every block measured, the page is exactly their sum plus 16px under the last line (%s, want %s)" % (E("CONTENT.h"), want))
X("SAVED_RESULT = AT.result; AT.result = nil; NS.RefreshUI()")
noResult = want - (16 + H("result") + 4 + 24 + 8 + 100)
check(E("CONTENT.h") == noResult, "with no result, its hidden heading, buttons and text are left out: the page ends 16px under the how-to note (%s, want %s)" % (E("CONTENT.h"), noResult))
X("AT.result = SAVED_RESULT; SAVED_RESULT = nil")
X("""for _, k in ipairs({"why", "pc", "goalText", "styleText", "fromText", "status", "how"}) do %s[k].GetStringHeight = nil end
RES.GetStringHeight = nil
for _, f in ipairs({ %s.goals[1], %s.styles[1], %s.fromPick, %s.start, %s.keep }) do f.GetHeight = nil end
NS.RefreshUI()""" % (P, P, P, P, P, P))

# In a fight, Back to before Autotune waits (grey), then happens when the fight ends.
X("INCOMBAT = true; " + P + ".putBack.scripts.OnClick(); NS.RefreshUI()")
st = E(P + ".status.text")
check(st.startswith(GREY) and "Waiting for the fight" in st and E("AT.result") is not None,
      "Back to before Autotune in a fight waits, and says so in grey")
X("INCOMBAT = false; FIRE('PLAYER_REGEN_ENABLED'); NS.RefreshUI()")
check(E("AT.result") is None and E("EyeCandyDB.autotune") is None and not E(P + ".status.text").startswith(GREY)
      and "back as they were" in E(P + ".status.text"), "when the fight ends, your settings go back, and it says so")

# In a fight, Save as preset waits, then saves when the fight ends.
X(P + ".start.scripts.OnClick(); PLAY(); NS.RefreshUI()")
X("INCOMBAT = true; " + P + ".keep.scripts.OnClick(); NS.RefreshUI()")
check(E(P + ".status.text").startswith(GREY) and E("AT.result") is not None, "Save as preset in a fight waits, in grey")
X("INCOMBAT = false; FIRE('PLAYER_REGEN_ENABLED'); NS.RefreshUI()")
check(E("AT.result") is None and "as your preset" in E(P + ".status.text") and E("NS.AutotuneNote()") is None,
      "when the fight ends it saves the preset, and the title note goes")

# A queued Save whose result is gone by the end of the fight leaves no stale waiting line.
X(P + ".start.scripts.OnClick(); PLAY(); NS.RefreshUI()")
X("INCOMBAT = true; " + P + ".keep.scripts.OnClick(); AT.result = nil; INCOMBAT = false; FIRE('PLAYER_REGEN_ENABLED'); NS.RefreshUI()")
check(not E(P + ".status.text").startswith(GREY), "a queued Save with nothing left to save clears its waiting line")
X("AT.PutBack(true)")

done()
