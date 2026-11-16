"""Photo mode on the Experimental tab (16 Nov 2026).
Run: python tests/test_photo_mode.py"""
from lib import boot, chat, check, done

# The game's screenshot, the UI and the settings the Screenshot preset sets that the stand-in game lacks.
PRE = """
C_CVar.RegisterCVar("cameraFov", "90"); C_CVar.RegisterCVar("bloomUserMult", "1"); C_CVar.RegisterCVar("Contrast", "50")
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
CANHIDE = true
function SetUIVisibility(v) if CANHIDE then UIParent.shown = v end end
SHOTS = 0
function Screenshot() SHOTS = SHOTS + 1 end
"""
lua = boot(PRE)
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
X("PM = NS.PhotoMode")
GOLD, GREY, RED = "|cffffd100", "|cff9d9d9d", "|cffff4040"


def cv(name):
    return E("GetCVar(%r)" % name)


# --- The wait for the new settings (pure) ---------------------------------------------------------
# frames: a list of (count, seconds a frame). Returns (settled, waited, frames) at the first true.
X("""function WAIT(plan)
  local s = { waited = 0, frames = 0, wn = 0, wt = 0 }
  for _, p in ipairs(plan) do
    for i = 1, p[1] do if PM.Settle(s, p[2]) then return true, s.waited, s.frames end end
  end
  return false, s.waited, s.frames
end""")
X("OK, T, N = WAIT({ { 1000, 1/60 } })")
check(E("OK") and 2 <= E("T") < 2.6, "steady frames: it waits the least, 2 seconds, then stops (%.2f s)" % E("T"))
check(E("N") == round(E("T") * 60), "and counts the frames it waited (%d)" % E("N"))
X("PLAN = {}; for i = 1, 3 do PLAN[#PLAN + 1] = { 15, 1/30 }; PLAN[#PLAN + 1] = { 30, 1/60 } end")
X("PLAN[#PLAN + 1] = { 1000, 1/60 }; OK, T = WAIT(PLAN)")
check(E("OK") and 3.4 < E("T") < 4.1, "frames still changing after 2 seconds: it waits until they settle (%.2f s)" % E("T"))
X("PLAN = {}; for i = 1, 40 do PLAN[#PLAN + 1] = { 15, 1/30 }; PLAN[#PLAN + 1] = { 30, 1/60 } end; OK, T = WAIT(PLAN)")
check(E("OK") and 6 <= E("T") < 6.1, "frames that never settle: it stops at 6 seconds (%.2f s)" % E("T"))

# --- The tab ---------------------------------------------------------------------------------------
X("NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
labels = [E(P + ".partButtons")[i].label for i in range(1, E("#" + P + ".partButtons") + 1)]
check(labels == ["Autotune", "Eye test", "Photo mode"], "the Experimental tab has a Photo mode button (%s)" % labels)
X(P + ".partButtons[3].scripts.OnClick()")
PP = P + ".photo"
check(E(P + ".parts.photo.shown") and E(PP + ".head.label.text") == "Photo mode" and E(PP + ".take.text") == "Take photo",
      "Photo mode shows its own page, with Take photo")
check("Screenshot preset" in E(PP + ".why.text") and "Esc stops it" in E(PP + ".how.text"), "it says what it does, and what stops it")


def frames(n, dt=1 / 60):
    X("for i = 1, %d do PM.frame.scripts.OnUpdate(PM.frame, %r) end" % (n, dt))


def take():
    X("SHOTS = 0; SetCVar('graphicsShadowQuality', 5); SetCVar('cameraFov', 70); " + PP + ".take.scripts.OnClick()")


# --- Refusals show in red under Take photo ----------------------------------------------------------
X("INCOMBAT = true; " + PP + ".take.scripts.OnClick(); INCOMBAT = false")
check(E(PP + ".status.text").startswith(RED) and "fight" in E(PP + ".status.text") and not E("PM.IsOn()"),
      "in a fight it is refused, in red")
X("local s = Screenshot; Screenshot = nil; " + PP + ".take.scripts.OnClick(); Screenshot = s")
check("doesn't let addons" in E(PP + ".status.text") and not E("PM.IsOn()"), "with no Screenshot in the game it is refused")
X("NS.EyeTest.Start(); " + PP + ".take.scripts.OnClick()")
check("eye test" in E(PP + ".status.text") and not E("PM.IsOn()"), "during the eye test it is refused")
X("NS.EyeTest.Stop('you pressed Stop')")
X("CANHIDE = false; SetCVar('cameraFov', 70); " + PP + ".take.scripts.OnClick(); CANHIDE = true")
check("No photo was taken" in E(PP + ".status.text") and not E("PM.IsOn()") and cv("cameraFov") == "70"
      and E("NS.IsPeeking()") is False and E("EyeCandyMainFrame.shown"),
      "when the game's UI won't hide, no photo, your settings stay and the window comes back")

# --- A photo -----------------------------------------------------------------------------------------
take()
check(E("PM.IsOn()") and E("EyeCandyDB.photo.before.graphicsShadowQuality") == "5", "Take photo saves your settings first")
check(cv("cameraFov") == "90" and cv("graphicsDepthEffects") == "3", "the Screenshot preset's values go on")
check(E("UIParent.shown") is False and not E("EyeCandyMainFrame.shown"), "the game's UI and Eye Candy's window hide")
check(not E("EyeCandyPeekFrame and EyeCandyPeekFrame.shown"), "with no Back bar in the picture")
frames(60)
check(E("SHOTS") == 0, "no photo before the new settings have had time to settle")
frames(120)
check(E("SHOTS") == 1, "then one photo")
X('FIRE("SCREENSHOT_SUCCEEDED")')
st = E(PP + ".status.text")
check(not E("PM.IsOn()") and cv("graphicsShadowQuality") == "5" and cv("cameraFov") == "70" and E("EyeCandyDB.photo") is None,
      "once saved, your settings are back")
check(E("UIParent.shown") and E("EyeCandyMainFrame.shown") and E("NS.IsPeeking()") is False, "and the UI and the window")
check("Photo saved" in st and "_forever_" in st and "Screenshots" in st and "frames" in st, "it says where the photo is and how many frames it waited (%r)" % st)
check(E("PM.last.frames") >= 120, "the frames it waited are kept")

take()
frames(200)
X('FIRE("SCREENSHOT_FAILED")')
check(E(PP + ".status.text").startswith(RED) and "couldn't save" in E(PP + ".status.text") and cv("cameraFov") == "70",
      "a failed photo says so in red, settings back")
take()
frames(200)
frames(400)
check(not E("PM.IsOn()") and E(PP + ".status.text").startswith(GREY) and "didn't say" in E(PP + ".status.text")
      and cv("cameraFov") == "70", "no word from the game in 5 seconds: it says where to look, settings back")

# --- Endings: each puts your settings back, with no photo --------------------------------------------
take()
frames(30)
X('FIRE("PLAYER_REGEN_DISABLED")')
check(not E("PM.IsOn()") and cv("cameraFov") == "70" and E("UIParent.shown") and "fight" in E(PP + ".status.text")
      and "No photo" in E(PP + ".status.text"), "a fight stops it, UI and settings back")
X('FIRE("PLAYER_REGEN_ENABLED")')
frames(300)
check(E("SHOTS") == 0, "and no photo is taken after")
take()
X('FIRE("PLAYER_LEAVING_WORLD")')
check(not E("PM.IsOn()") and cv("cameraFov") == "70", "a loading screen stops it, settings back")
take()
X("UIParent.shown = true; UIParent.hooks.OnShow(UIParent)")
frames(1)
check(not E("PM.IsOn()") and cv("cameraFov") == "70" and E("SHOTS") == 0, "Esc brings the UI back: no photo, settings back")
take()
X("C_OK, C_ERR = NS.ToggleCompare(); A_OK, A_ERR = NS.Autotune.Start('balance'); E_OK, E_ERR = NS.EyeTest.Start()")
check(E("C_OK") is None and E("A_OK") is False and E("E_OK") is None and "Photo mode" in E("C_ERR") and E("PM.IsOn()"),
      "Compare, Autotune and the eye test don't start during a photo")
check(E("NS.FPS.Still({})") is False, "the FPS reader measures no preset during a photo")
X("NS.PatchWatchLogout()")
check(E("EyeCandyDB.patchWatch.snap.values.cameraFov") == "70", "the patch warning's copy at logout holds your settings, not the photo's")
X("NS.ApplyAll()")
check(not E("PM.IsOn()") and "another setting" in E(PP + ".status.text"), "another Eye Candy apply stops it first")

# A fight already locked: the settings wait for its end, in grey.
take()
X("INCOMBAT = true; PM.Stop('a fight started')")
check(cv("cameraFov") == "90" and E(PP + ".status.text").startswith(GREY), "in a locked fight they wait, in grey")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(cv("cameraFov") == "70" and E("EyeCandyDB.photo") is None, "and come back when it ends")

# --- Still saved at the next login: it puts them back ------------------------------------------------
lua2 = boot(PRE + "EyeCandyDB = { photo = { before = { cameraFov = '75' } } }")
lua2.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(lua2.eval("GetCVar('cameraFov')") == "75" and lua2.eval("EyeCandyDB.photo") is None
      and any("didn't finish" in m for m in chat(lua2)), "a photo still saved at the next login puts your settings back and says so")

done()
