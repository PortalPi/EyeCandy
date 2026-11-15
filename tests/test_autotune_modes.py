"""Autotune's ways of tuning (15 Nov 2026): Best look, Raid ready, Smooth, Sharpest picture, Cool and quiet.
Run: python tests/test_autotune_modes.py"""
import os
from lib import boot, chat, check, done

lua = boot()
E, X = lua.eval, lua.execute
X(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autotune_sim.lua'), encoding='utf-8').read())

keys = [E("AT.STYLES")[i].key for i in range(1, E("#AT.STYLES") + 1)]
names = [E("AT.STYLES")[i].name for i in range(1, E("#AT.STYLES") + 1)]
check(keys == ["look", "raid", "smooth", "sharp", "cool"] and
      names == ["Best look", "Raid ready", "Smooth", "Sharpest picture", "Cool and quiet"],
      "five ways of tuning, Best look first (%s)" % names)
check(E("AT.NewRun('target', 60, { exists = function() return true end, supported = function() return true end }).style.key") == "look",
      "with no way given, a run tunes for Best look, as before")


def sim(mode, goal, style):
    X("RES = { SIM(%r, %s, { style = %r }) }" % (mode, goal if goal else "nil", style))
    return E("RES[1]"), E("RES[2]"), E("RES[4]"), E("MODEL()")


# --- Raid ready: much more spare FPS ---------------------------------------------------------
X("BASE = 300; KNOBCOST(0.04); SLOWF = nil")
a1, _, _, look = sim("target", 120, "look")
a2, _, run, raid = sim("target", 120, "raid")
check(a2.done == "finished" and raid >= 180, "Raid ready at 120 keeps 50%% spare: %.0f FPS in a quiet spot" % raid)
check(look < raid, "Raid ready leaves more spare than Best look (%.0f against %.0f)" % (raid, look))
X("BASE = 160; COST = {}")
a, _, _, _ = sim("target", 120, "raid")
check(a.done == "unreachable", "a PC at 160 FPS at its lowest can't keep raid spare for 120 (it needs 180), and says so")
check(E("(AT.Line(AT.NewRun('target', 100, { exists = function() return true end, supported = function() return true end }, 'raid')))") == 150,
      "Raid ready's line is 1.5 times the goal")
X("RR = AT.NewRun('target', 100, { exists = function() return true end, supported = function() return true end }, 'raid'); RR.cpuBound = true")
X("L1, L2 = AT.Line(RR, RR.byKey.view)")
line, slow = E("L1"), E("L2")
check(abs(line - 180) < 1e-9 and abs(slow - 100) < 1e-9,
      "on a CPU-bound PC, raid spare is bigger still for the settings that load the CPU, and the slowest frames hold the goal itself")

# --- Smooth: judged by the slowest frames -------------------------------------------------------
check(E("AT.Verdict('target', 120, { fps = 160, slow = 110, low = 100, steady = true }, nil, nil, { line = 132, slowLine = 120, lowLine = 84 })") == "fail",
      "slow frames under the goal fail Smooth, even at 160 on average")
check(E("AT.Verdict('target', 120, { fps = 160, slow = 125, low = 70, steady = true }, nil, nil, { line = 132, slowLine = 120, lowLine = 84 })") == "fail",
      "the slowest 1% far under the goal fails Smooth too")
check(E("AT.Verdict('target', 120, { fps = 160, slow = 125, low = 90, steady = true }, nil, nil, { line = 132, slowLine = 120, lowLine = 84 })") == "pass",
      "slow frames over the goal pass")
check(E("AT.Verdict('target', 120, { fps = 160, slow = 121, low = 90, steady = true }, nil, nil, { line = 132, slowLine = 120, lowLine = 84, slowFirst = true })") == "again",
      "with Smooth, a close call is judged on the slow frames: measured again")
# A PC whose slowest 5% run at 80% of the average.
X("BASE = 300; KNOBCOST(0.04); SLOWF = function(f) return f * 0.8 end")
_, _, _, look = sim("target", 120, "look")
a, _, run, smooth = sim("target", 120, "smooth")
check(a.done == "finished" and smooth * 0.8 >= 120, "Smooth holds the slowest frames at the goal (%.0f FPS, slow frames %.0f)" % (smooth, smooth * 0.8))
check(look * 0.8 < 120, "where Best look lets them dip under it (%.0f)" % (look * 0.8))
X("SLOWF = nil")
# A PC whose slowest 1% run at half the average: Smooth holds them at 70% of the goal, Best look doesn't look.
X("LOWF = function(f) return f * 0.5 end")
_, _, _, look = sim("target", 120, "look")
a, _, _, smooth = sim("target", 120, "smooth")
check(a.done == "finished" and smooth * 0.5 >= 84 and look * 0.5 < 84,
      "Smooth holds the slowest 1%% at 70%% of the goal (%.0f), where Best look doesn't (%.0f)" % (smooth * 0.5, look * 0.5))
X("LOWF = nil")
check(E("AT.Verdict('target', 120, { fps = 200, slow = 150, low = 85, steady = true }, nil, nil, { line = 132, slowLine = 120, lowLine = 84, slowFirst = true })") == "again",
      "with Smooth, the slowest 1% near its line is a close call too")
check(E("AT.STYLE.smooth.sample") == 6, "Smooth measures for 6 seconds, so the slowest 1% has frames to stand on")
X("SM = AT.NewRun('target', 60, { exists = function() return true end, supported = function() return true end }, 'smooth'); SM.try = { knob = SM.knobs[1], index = 2 }")
check(not E("AT.Early(SM, { fps = 300, slow = 300, frames = 200 })"), "Smooth never stops a sample early on a pass")
check(E("AT.Early(SM, { fps = 30, slow = 30, frames = 200 })"), "but a clear miss still stops early")

# --- Sharpest picture: clarity first -------------------------------------------------------------
X("BASE = 300; KNOBCOST(0.04)")
_, tries, run, _ = sim("target", 60, "sharp")
clear = [E("AT.KNOB_BY_CVAR")[tries[i].cvar].clear for i in range(1, len(tries) + 1)]
first_other = clear.index(None) if None in clear else len(clear)
check(first_other > 0 and all(clear[:first_other]) and not any(clear[first_other:]),
      "every clarity setting is tried before any other (%d clarity tries first)" % first_other)
cvars = {tries[i].cvar for i in range(1, len(tries) + 1)}
check("ffxAntiAliasingMode" in cvars and "ResampleAlwaysSharpen" in cvars, "Sharpest picture tries anti-aliasing and sharpening")
_, tries, _, _ = sim("target", 60, "look")
cvars = {tries[i].cvar for i in range(1, len(tries) + 1)}
check("ffxAntiAliasingMode" not in cvars and "ResampleAlwaysSharpen" not in cvars, "Best look leaves anti-aliasing and sharpening alone, as before")
# Over 100% render scale comes straight after the clarity settings, not after everything.
order = [tries[i] for i in range(1, len(tries) + 1)]
_, tries, _, _ = sim("target", 60, "sharp")
up = [i for i in range(1, len(tries) + 1) if tries[i].cvar == "RenderScale" and tries[i].value > 1]
other = [i for i in range(1, len(tries) + 1) if not E("AT.KNOB_BY_CVAR")[tries[i].cvar].clear]
check(up and other and up[0] < other[0], "render scale over 100%% is tried before fog, shadows and the rest")
# A tight PC: Sharpest picture spends the spare on clarity, Best look on its best look per cost.
X("BASE = 160; KNOBCOST(0.06)")
sim("target", 120, "look")
look_state = (E("tonumber(STATE.RenderScale)"), E("tonumber(STATE.textureFilteringMode)"), E("tonumber(STATE.graphicsComputeEffects)"))
sim("target", 120, "sharp")
sharp_state = (E("tonumber(STATE.RenderScale)"), E("tonumber(STATE.textureFilteringMode)"), E("tonumber(STATE.graphicsComputeEffects)"))
check(sharp_state[0] >= look_state[0] and sharp_state[1] >= look_state[1] and sharp_state[2] <= look_state[2],
      "on a tight PC, clarity ends at least as high and fog at least as low (%s against %s)" % (sharp_state, look_state))
# Anti-aliasing only offers what the game says this PC can do (CMAA and CMAA 2 from AntiAliasingSupported).
X("function AntiAliasingSupported() return true, true, false end")
check(E("AT.Supported('ffxAntiAliasingMode', 3)") and not E("AT.Supported('ffxAntiAliasingMode', 4)"),
      "CMAA 2 is skipped where the game says it can't")
X("AntiAliasingSupported = nil")

# --- The run in the game ------------------------------------------------------------------------
X("GAME_SETUP()")
X("C_CVar.RegisterCVar('maxFPS', '120'); C_CVar.RegisterCVar('useMaxFPS', '0'); C_CVar.RegisterCVar('ResampleAlwaysSharpen', '0'); C_CVar.RegisterCVar('ffxAntiAliasingMode', '4')")
X("SetCVar('maxFPS', '144'); SetCVar('useMaxFPS', '0')")
X("BASE = 300; COST = { graphicsShadowQuality = { ['5'] = 0.2 } }")

# Cool and quiet needs a number to cap at.
ok, why = E("AT.Start('balance', nil, 'cool')")
check(not ok and why == "Cool and quiet needs an FPS goal. Pick one above.", "Cool and quiet with Best balance is refused, and says why")

ok = E("AT.Start('target', 60, 'cool')")
check(ok and E("EyeCandyDB.autotune.style") == "cool" and E("EyeCandyDB.autotune.before.maxFPS") == "144",
      "a run remembers its way of tuning, and your FPS cap from before")
X("PLAY()")
check(E("AT.result") is not None and E("GetCVar('useMaxFPS')") == "1" and E("GetCVar('maxFPS')") == "60" and E("AT.result.fpsCap") == 60,
      "Cool and quiet turns the game's FPS cap on at the goal when it's done")
check(E("AT.result.name") == "Autotune 60 FPS cool and quiet", "its preset name says the way it was tuned (%s)" % E("AT.result.name"))
X("AT.PutBack()")
check(E("GetCVar('useMaxFPS')") == "0" and E("GetCVar('maxFPS')") == "144", "Back to before Autotune puts your old FPS cap back")

E("AT.Start('target', 60, 'cool')")
X("PLAY(); AT.Keep()")
p = E("NS.FindPresetByName('Autotune 60 FPS cool and quiet')")
check(p is not None and E("GetCVar('useMaxFPS')") == "1" and E("GetCVar('maxFPS')") == "60",
      "Save as preset keeps the cap on after the preset goes on")
msg = E("AT.message") or ""
check("capped at 60" in msg and "Standard tab" in msg, "Save as preset says FPS is capped, as your own setting (%s)" % msg)
check(p is not None and "capped" not in (p['desc'] or ""),
      "the preset's note leaves the cap out: it goes with a copy or a share code, where it isn't true (%s)" % (p and p['desc']))
X("SetCVar('maxFPS', '144'); SetCVar('useMaxFPS', '0')")
# Stopped part way: the cap from before comes back with everything else.
E("AT.Start('target', 60, 'cool')")
X("PLAY(50); AT.Stop('a test')")
check(not E("AT.IsRunning()") and E("GetCVar('useMaxFPS')") == "0" and E("GetCVar('maxFPS')") == "144", "stopping part way puts your FPS cap back")
# The game may keep another number (its menu slider stops at 200): a cap under the goal would undo the tune.
X("local set = SetCVar; function SetCVar(n, v) if n == 'maxFPS' and tonumber(v) > 200 then v = '200' end return set(n, v) end")
X("BASE = 1000; COST = {}")
E("AT.Start('target', 240, 'cool')")
X("PLAY()")
check(E("AT.result.fpsCap") is None and E("AT.result.capKept") == 200 and E("AT.result.capAsked") == 240
      and E("GetCVar('useMaxFPS')") == "0" and E("GetCVar('maxFPS')") == "144",
      "if the game keeps a cap under the goal, yours goes back and the result knows")
X("AT.PutBack(true); BASE = 300; COST = { graphicsShadowQuality = { ['5'] = 0.2 } }")

# Raid ready's unreachable message says why.
X("BASE = 160; COST = {}")
E("AT.Start('target', 120, 'raid')")
X("PLAY()")
msg = E("AT.message") or ""
check("Raid ready" in msg and "180" in msg, "an unreachable Raid ready goal says the spare it needs (%s)" % msg)
X("BASE = 300; COST = { graphicsShadowQuality = { ['5'] = 0.2 } }")

# --- The tab ------------------------------------------------------------------------------------
X("local button = NS.Button; NS.Button = function(p, t, w, f) local b = button(p, t, w, f); b.builtW = w; return b end")
X("NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
GOLD, WHITE, RED = "|cffffd100", "|cffffffff", "|cffff4040"
check(E(P + ".styleHead.label.text") == "Tune for", "a Tune for heading")
labels = [E(P + ".styles")[i].label for i in range(1, E("#" + P + ".styles") + 1)]
check(labels == names, "five buttons under it, Best look first (%s)" % labels)
width = sum(E(P + ".styles")[i].builtW for i in range(1, len(labels) + 1)) + 4 * (len(labels) - 1)
check(width <= E("NS.ROW_W") - 16, "the five fit on one line (%d px)" % width)
check(E(P + ".styles[1].text").startswith(GOLD) and E(P + ".styles[2].text").startswith(WHITE), "Best look is chosen first, in gold")
check(E(P + ".styleText.text").startswith("The best look that holds your goal."), "and the line under it says what it does")

goal = lambda g: P + ".goals[%d]" % ([E(P + ".goals")[i].label for i in range(1, E("#" + P + ".goals") + 1)].index(g) + 1)
X(goal("120 FPS") + ".scripts.OnClick()")
X(P + ".styles[2].scripts.OnClick()")
check(E("EyeCandyDB.autotuneGoal.style") == "raid" and E("EyeCandyDB.autotuneGoal.goal") == 120,
      "picking Raid ready remembers it and keeps the goal")
check(E(P + ".styles[2].text").startswith(GOLD) and "big fight" in E(P + ".styleText.text"), "Raid ready shows gold, and its line says why")
X(goal("Best balance") + ".scripts.OnClick()")
check(E("EyeCandyDB.autotuneGoal.style") == "raid", "picking another goal keeps the way of tuning")

# Cool and quiet with Best balance: the line says so before you press Start, and Start says it in red.
X(P + ".styles[5].scripts.OnClick()")
check("needs an FPS goal" in E(P + ".styleText.text"), "Cool and quiet with Best balance says it needs an FPS goal")
X(P + ".start.scripts.OnClick(); NS.RefreshUI()")
st = E(P + ".status.text")
check(not E("AT.IsRunning()") and st.startswith(RED) and "needs an FPS goal" in st, "and Start is refused in red")

X(goal("60 FPS") + ".scripts.OnClick()")
X(P + ".styles[3].scripts.OnClick()")
X(P + ".start.scripts.OnClick()")
check(E("AT.IsRunning()") and E("EyeCandyDB.autotune.style") == "smooth", "Start runs the way picked")
X("PLAY(); NS.RefreshUI()")
res = E(P + ".result.text")
check("Smooth" in res and "slowest frames" in res, "the result says how it was tuned")
X("AT.PutBack(true); NS.RefreshUI()")

# A saved goal from before the ways of tuning (no style) is Best look.
X("EyeCandyDB.autotuneGoal = { mode = 'target', goal = 60 }; NS.RefreshUI()")
check(E(P + ".styles[1].text").startswith(GOLD) and E(goal("60 FPS") + ".text").startswith(GOLD),
      "a goal saved before Tune for existed keeps its goal, on Best look")

# The page is as tall as everything on it, the Tune for block included.
X("CONTENT = " + P + ".content; CONTENT.SetHeight = function(self, h) self.h = h end; NS.RefreshUI()")
base = E("CONTENT.h")
X(P + ".styleText.GetStringHeight = function() return 300 end; NS.RefreshUI()")
check(E("CONTENT.h") > base, "a wrapped Tune for line makes the page taller")
X(P + ".styleText.GetStringHeight = nil; NS.RefreshUI()")

# Raid ready where a cap holds FPS at the goal: no spare can be kept, and the result doesn't claim 50%.
X("BASE = 60; COST = {}")
E("AT.Start('target', 60, 'raid')")
X("PLAY(); NS.RefreshUI()")
res = E(P + ".result.text") or ""
check(E("AT.result.cap") == 60 and "couldn't keep spare" in res and "50%" not in res,
      "Raid ready under a 60 FPS cap says it couldn't keep spare (%s)" % res)
X("AT.PutBack(true)")

done()
