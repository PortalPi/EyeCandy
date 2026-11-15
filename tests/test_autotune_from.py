"""Autotune from a preset (15 Nov 2026): start from a Look, a quality level or your own preset, keep what
makes it that preset, and lower the costly rest until the goal holds.
Run: python tests/test_autotune_from.py"""
import os
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autotune_sim.lua'), encoding='utf-8').read())


def keys(t):
    return sorted(k for k in (t or {}).keys() if t[k])


# --- What is kept ------------------------------------------------------------------------------
check(keys(E("AT.Essence('look:moody', {})")) == ["compute", "depth", "ssao"], "Moody keeps its ambient occlusion, soft edges and fog")
check(keys(E("AT.Essence('look:crisp', {})")) == ["filtering", "scale", "textures"], "Crisp keeps its clarity")
check(keys(E("AT.Essence('look:classic', {})")) == [], "Classic keeps only the settings Autotune doesn't tune")
# The fair rule: a setting clearly higher than the preset's others is its point.
X("""HIGHTEX = { graphicsTextureResolution = '2', textureFilteringMode = '3', graphicsLightMode = '1', graphicsComputeEffects = '2',
  graphicsShadowQuality = '2', graphicsSSAO = '1', graphicsDepthEffects = '1', graphicsLiquidDetail = '1',
  graphicsViewDistance = '5', graphicsEnvironmentDetail = '5', graphicsGroundClutter = '5', graphicsParticleDensity = '2',
  RenderScale = '0.7' }""")
check(keys(E("AT.Essence('user:1', HIGHTEX)")) == ["textures"], "your preset with textures far above its other settings keeps them (%s)" % keys(E("AT.Essence('user:1', HIGHTEX)")))
X("""EVEN = {}
for _, d in ipairs(AT.KNOBS) do if not d.after and not d.only then EVEN[d.cvar] = tostring(d.steps[math.ceil(#d.steps / 2)][1]) end end""")
check(keys(E("AT.Essence('tier3', EVEN)")) == [], "a preset with every setting about level keeps nothing in particular, and trims evenly")

# --- The run, on the pretend PC -----------------------------------------------------------------
# A preset with every setting at its top.
X("""TOP = { ResampleQuality = '3', cameraFov = '90' }
for _, d in ipairs(AT.KNOBS) do if not d.after and not d.only then TOP[d.cvar] = tostring(d.steps[#d.steps][1]) end end""")


def sim(mode, goal, keep=None, style=None, values="TOP"):
    X("RES = { SIM(%r, %s, { style = %s, from = { values = %s, keep = %s } }) }" % (
        mode, goal if goal else "nil", repr(style) if style else "nil", values, keep or "{}"))
    return E("RES[1]"), E("RES[2]"), E("RES[4]"), E("MODEL()")


X("BASE = 600; KNOBCOST(0.04)")
a, tries, run, fps = sim("target", 60)
check(a.done == "finished" and len(tries) == 0 and fps >= 66, "a preset that holds the goal as it is: nothing trimmed (%.0f FPS)" % fps)
check(E("STATE.graphicsShadowQuality") == "5" and E("STATE.cameraFov") == "90" and E("STATE.ResampleQuality") == "3",
      "the preset's own values are on, the ones Autotune doesn't tune too")
check(E("RES[4].phase") != "floor" and E("#AT.Changes(RES[4])") == 0, "it never drops to the lowest settings first, and lists no changes")

X("BASE = 220")
a, tries, run, fps = sim("target", 120, keep="{ ssao = true, depth = true, compute = true }")
check(a.done == "finished" and fps >= 132, "a preset that misses is trimmed until the goal holds (%.0f FPS)" % fps)
check(all(tries[i].trim for i in range(1, len(tries) + 1)), "every try is one step down: it never raises a preset above itself")
check(E("STATE.graphicsSSAO") == E("TOP.graphicsSSAO")
      and E("STATE.graphicsDepthEffects") == E("TOP.graphicsDepthEffects") and E("STATE.graphicsComputeEffects") == E("TOP.graphicsComputeEffects"),
      "the kept settings are never trimmed")
# The cheapest look for the FPS goes first: the first trim is the step with the least look for its cost.
X("""FIRST = nil; LEAST = nil
for _, kn in ipairs(RES[4].knobs) do
  local d = kn.def
  if not ({ ssao = 1, depth = 1, compute = 1 })[d.key] and #d.steps > 1 then
    local s = d.steps[#d.steps]; local r = s[2] / math.max(s[3], 0.01)
    if not LEAST or r < LEAST then LEAST, FIRST = r, d.cvar end
  end
end""")
check(tries[1].cvar == E("FIRST"), "the first trim takes the least look for its cost (%s, want %s)" % (tries[1].cvar, E("FIRST")))
ch = E("AT.Changes(RES[4])")
check(len(ch) > 0 and all(ch[i].before is not None for i in range(1, len(ch) + 1)), "the changes are listed from the preset's values")

X("BASE = 80")
a, _, _, _ = sim("target", 120, keep="{ ssao = true, depth = true, compute = true }")
check(a.done == "unreachable" and a.trimmed, "nothing left to trim and still missing: it can't be reached, and says it trimmed everything")

# A value that isn't one of Autotune's steps is the start, exactly (Laptop's 75% render scale).
X("BASE = 600; ODD = {}; for k, v in pairs(TOP) do ODD[k] = v end; ODD.RenderScale = '0.75'")
sim("target", 60, values="ODD")
check(E("tonumber(STATE.RenderScale)") == 0.75, "a preset at 75%% render scale starts at 75%%, not a step near it")
X("BASE = 160")
_, tries, _, _ = sim("target", 120, values="ODD", keep="{ ssao = true, depth = true, compute = true, textures = true, filtering = true, view = true, environment = true, clutter = true, particles = true, light = true, shadows = true, liquid = true, pbr = true, vrs = true }")
check(len(tries) > 0 and tries[1].cvar == "RenderScale" and abs(tries[1].value - 0.7) < 1e-9, "its first trim goes down to the next step (70%)")
# Render scale over 100% in a preset is its top step, and can be trimmed back to 100%.
X("BASE = 600; UP = {}; for k, v in pairs(TOP) do UP[k] = v end; UP.RenderScale = '1.5'")
sim("target", 60, values="UP")
check(E("tonumber(STATE.RenderScale)") == 1.5, "a preset over 100%% render scale starts there")

# Sharpest picture from a preset trims the clear settings last.
# At 150, every other setting at its lowest still misses 120, so some clear ones go too.
X("BASE = 150; KNOBCOST(0.04)")
_, tries, _, _ = sim("target", 120, style="sharp")
clear = [bool(E("AT.KNOB_BY_CVAR")[tries[i].cvar].clear) for i in range(1, len(tries) + 1)]
check(True in clear and False in clear and clear.index(True) > max(i for i, c in enumerate(clear) if not c),
      "Sharpest picture trims every other setting before a clear one (%s)" % clear)

# Best balance from a preset: hold 60, then lower a setting only where it gains more than its look is worth.
X("BASE = 600; KNOBCOST(0.04); COST.graphicsShadowQuality['5'] = COST.graphicsShadowQuality['5'] + 0.6")
a, tries, run, fps = sim("balance", None)
check(a.done == "finished" and E("tonumber(STATE.graphicsShadowQuality)") == 4, "Best balance lowers a setting that costs a lot for its look")
check(E("tonumber(STATE.graphicsTextureResolution)") == 2, "and leaves one that costs little")
check(E("tonumber(STATE.RenderScale)") == 1, "and never lowers render scale for FPS it doesn't need")

# A cap at the goal (Vertical Sync) is not a miss: a step lower that gains nothing goes back, and a test at
# the lowest settings shows the cap.
X("BASE = 600; KNOBCOST(0.04); CAP = 60")
a, tries, _, _ = sim("target", 60)
check(a.done == "finished" and len(tries) == 1 and E("#AT.Changes(RES[4])") == 0,
      "a preset held at a 60 FPS cap holds a 60 goal, with nothing lowered (%s, %d tries)" % (a.done, len(tries)))
a, _, _, _ = sim("target", 120)
check(a.done == "unreachable" and a.cap == 60, "and a 120 goal over that cap can't be reached")
X("CAP = nil")
# A heavy preset that just happens to run at an even 60 is not a cap: lowering lifts it.
X("""KNOBCOST(0.04); STATE = TOP; BASE = 1; BASE = 60 / MODEL()
REAL_MEASURE = MEASURE; function MEASURE(n, o) local m = REAL_MEASURE(n, o); m.spread = 0.004; return m end""")
a, tries, run, fps = sim("target", 100)
check(a.done == "finished" and fps >= 110, "a preset at an even 60 FPS is lowered to a 100 goal, not stopped as capped (%s, %.0f FPS)" % (a.done, fps))
X("MEASURE = REAL_MEASURE")

# --- The run in the game ------------------------------------------------------------------------
X("GAME_SETUP()")
# Moody runs at 102 FPS here; shadows one step down makes 139, over 120's line. The pretend PC's frames are
# perfectly even, so neither may sit near a refresh rate (it would look like a cap).
X("BASE = 460; COST = { graphicsShadowQuality = { ['5'] = 1.5, ['4'] = 0.3 }, graphicsComputeEffects = { ['4'] = 2 } }")
X("MOODY = NS.PresetValues('look:moody')")
ok, why = E("AT.Start('target', 120, nil, 'user:gone')")
check(not ok and "gone" in why, "a preset that's gone is refused, and says so (%s)" % why)
# One of Moody's values Autotune doesn't tune, set to something else first.
X("""OTHER = nil
local tuned = {}; for _, d in ipairs(AT.KNOBS) do tuned[d.cvar] = true end
for cvar, v in pairs(MOODY) do if not OTHER and not tuned[cvar] and NS.Exists(cvar) and tonumber(v) then OTHER = cvar end end
OTHERWAS = tostring(tonumber(MOODY[OTHER]) + 1); SetCVar(OTHER, OTHERWAS)""")
ok = E("AT.Start('target', 120, nil, 'look:moody')")
check(ok and E("EyeCandyDB.autotune.from") == "look:moody", "a run remembers the preset it started from")
X("PLAY()")
check(E("AT.result") is not None and E("AT.result.name") == "Moody for 120 FPS", "its result is named for the preset (%s)" % E("AT.result and AT.result.name"))
check(E("tonumber(GetCVar(OTHER))") == E("tonumber(MOODY[OTHER])"), "Moody's own values are on, the ones Autotune doesn't tune too (%s)" % E("OTHER"))
check(E("tonumber(GetCVar('graphicsComputeEffects'))") == E("tonumber(MOODY.graphicsComputeEffects)"), "Moody's fog is kept, costly or not")
X("AT.PutBack()")
check(E("GetCVar(OTHER)") == E("OTHERWAS"), "Back to before Autotune puts your own settings back")
E("AT.Start('target', 120, nil, 'look:moody')")
X("PLAY(); AT.Keep()")
p = E("NS.FindPresetByName('Moody for 120 FPS')")
check(p is not None and E("tonumber(NS.FindPresetByName('Moody for 120 FPS').values[OTHER])") == E("tonumber(MOODY[OTHER])"),
      "Save as preset keeps Moody's values for what wasn't tuned, not yours from before")
check(p is not None and "Moody" in (p['desc'] or ""), "the preset's note says what it started from (%s)" % (p and p['desc']))

# --- The tab ------------------------------------------------------------------------------------
X("NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
GOLD = "|cffffd100"
check(E(P + ".fromHead.label.text") == "Start from", "a Start from heading")
X("""ITEMS = {}
local root = { CreateRadio = function(self, text, isSel, click) ITEMS[#ITEMS + 1] = { text = text, sel = isSel, click = click }; return {} end }
%s.fromMenu(nil, root)""" % P)
items = [E("ITEMS")[i].text for i in range(1, E("#ITEMS") + 1)]
check(items[0] == "Lowest settings" and "Moody" in items and "Performance" in items and "Moody for 120 FPS" in items,
      "it lists Lowest settings first, then the quality levels, Looks and your presets (%s)" % items)
check(E("ITEMS[1].sel()") and "lowest settings" in E(P + ".fromText.text"), "Lowest settings is picked first, as before")
X("for _, it in ipairs(ITEMS) do if it.text == 'Moody' then it.click() end end")
check(E("EyeCandyDB.autotuneGoal.from") == "look:moody", "picking Moody remembers it")
txt = E(P + ".fromText.text")
check("Moody" in txt and "until your goal holds" in txt, "and the line under it says what it keeps (%s)" % txt)
X(P + ".styles[2].scripts.OnClick()")
check(E("EyeCandyDB.autotuneGoal.from") == "look:moody", "picking a way of tuning keeps the preset")
X(P + ".styles[1].scripts.OnClick()")
X(P + ".start.scripts.OnClick()")
check(E("AT.IsRunning()") and E("EyeCandyDB.autotune.from") == "look:moody", "Start starts from it")
X("PLAY(); NS.RefreshUI()")
check("Started from Moody" in (E(P + ".result.text") or ""), "the result says what it started from")
X("AT.PutBack(true)")
X("EyeCandyDB.autotuneGoal = { mode = 'target', goal = 60, from = 'user:gone' }; NS.RefreshUI()")
check("lowest settings" in E(P + ".fromText.text"), "a preset that's gone falls back to Lowest settings")
X("CONTENT = " + P + ".content; CONTENT.SetHeight = function(self, h) self.h = h end; NS.RefreshUI()")
base = E("CONTENT.h")
X(P + ".fromText.GetStringHeight = function() return 300 end; NS.RefreshUI()")
check(E("CONTENT.h") > base, "a wrapped Start from line makes the page taller")
X(P + ".fromText.GetStringHeight = nil; NS.RefreshUI()")

done()
