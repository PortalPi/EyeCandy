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
# A small world for the city switch (as tests/test_situations_auto.py): 84 Stormwind, 37 Elwynn.
MAPS = """
MAPS = { [13] = { mapType = 2, parentMapID = 947, flags = 0 }, [84] = { mapType = 3, parentMapID = 13, flags = 0 },
  [37] = { mapType = 3, parentMapID = 13, flags = 0 } }
MAP = 37
C_Map = {
  GetBestMapForUnit = function(unit) return MAP end,
  GetMapInfo = function(id) local m = MAPS[id]; if m then return { mapID = id, name = "map", mapType = m.mapType, parentMapID = m.parentMapID, flags = m.flags } end end,
}
C_PvP = { GetZonePVPInfo = function() return nil end }
function IsInInstance() return false, "none" end
"""
lua = boot(PRE)
E, X = lua.eval, lua.execute
X(MAPS)
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
X("OK, T = WAIT({ { 110, 1/60 }, { 1, 0.2 }, { 1000, 1/60 } })")
check(E("OK") and 2.6 < E("T") < 3.2, "one long frame (the game still loading) at 2 seconds: it waits for two even windows after it (%.2f s)" % E("T"))
X("PLAN = {}; for i = 1, 20 do PLAN[#PLAN + 1] = { 30, 1/60 }; PLAN[#PLAN + 1] = { 28, 1/56 } end; OK, T = WAIT(PLAN)")
check(E("OK") and E("T") < 2.6, "ordinary jitter (60 then 56 FPS) doesn't hold it up to the 6 second cap (%.2f s)" % E("T"))

# --- The tab ---------------------------------------------------------------------------------------
X("NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
labels = [E(P + ".partButtons")[i].label for i in range(1, E("#" + P + ".partButtons") + 1)]
check(labels[:3] == ["Autotune", "Eye test", "Photo mode"], "the Experimental tab has a Photo mode button (%s)" % labels)
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
X("NS.TogglePeek(); NS.TogglePeek(); EyeCandyMainFrame.shown = true")  # Peek once first, so its Back bar exists
check(E("EyeCandyPeekFrame ~= nil") and not E("EyeCandyPeekFrame.shown"), "Peek's Back bar exists, hidden")
take()
check(E("PM.IsOn()") and E("EyeCandyDB.photo.before.graphicsShadowQuality") == "5", "Take photo saves your settings first")
check(cv("cameraFov") == "90" and cv("graphicsDepthEffects") == "3", "the Screenshot preset's values go on")
check(E("UIParent.shown") is False and not E("EyeCandyMainFrame.shown"), "the game's UI and Eye Candy's window hide")
check(not E("EyeCandyPeekFrame.shown") and E("NS.IsPeeking()"), "with no Back bar in the picture")
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
frames(200)
X("UIParent.shown = true; UIParent.hooks.OnShow(UIParent)")
frames(1)
X('FIRE("SCREENSHOT_SUCCEEDED")')
check("Photo saved" in E(PP + ".status.text") and "may be in it" in E(PP + ".status.text") and cv("cameraFov") == "70",
      "Esc while the game takes the photo: it says the UI may be in it")
X("RAWERR = NS.ApplyValues; NS.ApplyValues = function() error('broken') end")
X(PP + ".take.scripts.OnClick(); NS.ApplyValues = RAWERR")
check(E(PP + ".status.text").startswith(RED) and "couldn't go on" in E(PP + ".status.text") and not E("PM.IsOn()")
      and cv("cameraFov") == "70" and E("EyeCandyDB.photo") is None, "an error putting the preset on is refused in red, no Lua error, settings back")

# The city switch waits during a photo, and lowers your own settings once they are back.
X("SetCVar('graphicsViewDistance', 9); NS.SetAutoSituation('city', true)")
take()
vd = cv("graphicsViewDistance")
X('MAP = 84; FIRE("ZONE_CHANGED_NEW_AREA"); FIRE("ZONE_CHANGED"); RUNTIMERS()')
check(cv("graphicsViewDistance") == vd and E("NS.ActiveSituationName()") is None, "walking into a city during a photo changes nothing in it")
frames(200)
X('FIRE("SCREENSHOT_SUCCEEDED")')
check(E("NS.ActiveSituationName()") == "Capital city" and cv("graphicsViewDistance") == "7",
      "once your settings are back, the city switch lowers yours")
X('MAP = 37; FIRE("ZONE_CHANGED_NEW_AREA"); RUNTIMERS()')
check(cv("graphicsViewDistance") == "9", "and puts yours back when you leave")
X("NS.SetAutoSituation('city', false)")

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

# --- What the photo uses: My settings now ------------------------------------------------------------------
X("PM.Stop('test')")
check(E("PM.Choice()") == "screenshot" and E(PP + ".shotChoice.text").startswith(GOLD), "the Screenshot preset is the default choice, shown in gold")
X(PP + ".mine.scripts.OnClick()")
check(E("EyeCandyDB.photoChoice") == "mine" and E(PP + ".mine.text").startswith(GOLD) and "your settings as they are" in E(PP + ".choiceText.text"),
      "My settings now is remembered, and the page says what the photo uses")
take()
check(E("PM.IsOn()") and E("EyeCandyDB.photo") is None and cv("cameraFov") == "70" and cv("graphicsShadowQuality") == "5",
      "with My settings now no setting changes and nothing is saved")
check(E("UIParent.shown") is False and E("NS.IsPeeking()"), "but the UI hides")
frames(10)
check(E("SHOTS") == 0, "it waits a moment for the UI to hide")
frames(20)
check(E("SHOTS") == 1, "then takes the photo, with no wait for settings")
X('FIRE("SCREENSHOT_SUCCEEDED")')
st = E(PP + ".status.text")
check(not E("PM.IsOn()") and E("UIParent.shown") and cv("cameraFov") == "70" and "Photo saved" in st and "waited" not in st,
      "and the UI comes back (%r)" % st)
take()
X('FIRE("PLAYER_REGEN_DISABLED")')
check(not E("PM.IsOn()") and E("UIParent.shown") and cv("cameraFov") == "70", "a fight still stops it and brings the UI back")
X(PP + ".shotChoice.scripts.OnClick()")
check(E("EyeCandyDB.photoChoice") == "screenshot", "the Screenshot preset choice is remembered too")

# --- Change it: the photo settings go on, you adjust them, Save or Cancel ----------------------------------
X("SetCVar('graphicsShadowQuality', 5); SetCVar('cameraFov', 70); EyeCandyDB.advanced = { Contrast = '55' }; SetCVar('Contrast', 55)")
check(E(PP + ".change.shown") and not E(PP + ".save.shown"), "Change it shows, Save as my photo settings does not")
X(PP + ".change.scripts.OnClick()")
check(E("PM.IsEditing()") and cv("cameraFov") == "90" and cv("graphicsDepthEffects") == "3" and E("EyeCandyDB.photo.before.cameraFov") == "70",
      "Change it saves your settings, then puts the Screenshot preset on")
check(E(PP + ".save.shown") and E(PP + ".cancel.shown") and not E(PP + ".take.shown") and not E(PP + ".change.shown"),
      "the page shows Save as my photo settings and Cancel, and no Take photo")
check("Standard and Hidden" in E(PP + ".editText.text") and "Cancel" in E(PP + ".editText.text"), "it says photo settings are on and how to finish")
check("Photo settings are on" in E("NS.RunningNote()"), "the window title says photo settings are on")
check(E("UIParent.shown") and E("EyeCandyMainFrame.shown"), "the UI stays: you adjust in the window")
X("OK, ERR = NS.SetAdvanced('cameraFov', '80'); NS.SetAdvanced('Contrast', '60')")
check(E("OK") and E("PM.IsEditing()") and cv("cameraFov") == "80", "a change on the Hidden tab doesn't end the edit")
X("NS.ApplyAll(false, true)")
check(E("PM.IsEditing()"), "nor does Apply")
X("PM.Take_OK, PM.Take_ERR = PM.Take()")
check(E("PM.Take_OK") is None and "Cancel" in E("PM.Take_ERR") and E("PM.IsEditing()"), "Take photo is refused during the edit")
X("C_OK, C_ERR = NS.ToggleCompare(); A_OK = NS.Autotune.Start('balance'); E_OK = NS.EyeTest.Start()")
check(E("C_OK") is None and E("A_OK") is False and E("E_OK") is None and E("PM.IsEditing()"), "Compare, Autotune and the eye test don't start during the edit")
check(E("NS.FPS.Still({})") is False, "the FPS reader measures no preset during the edit")
X("NS.PatchWatchLogout()")
check(E("EyeCandyDB.patchWatch.snap.values.cameraFov") == "70", "the patch warning's copy at logout holds your settings, not the photo ones")
check(E("NS.UpdateSituations()") is None and E("EyeCandyDB.photo ~= nil"), "the city switch waits during the edit")
X(PP + ".save.scripts.OnClick()")
check(not E("PM.IsEditing()") and E("EyeCandyDB.photo") is None and cv("cameraFov") == "70" and cv("Contrast") == "55",
      "Save as my photo settings puts your own settings back")
check(E("EyeCandyDB.advanced.Contrast") == "55" and E("EyeCandyDB.advanced.cameraFov") is None,
      "and your own choices (the Hidden tab's dials), not the ones you tried")
check(E("EyeCandyDB.photoSettings.values.cameraFov") == "80" and E("EyeCandyDB.photoSettings.values.Contrast") == "60",
      "what was on is kept as your photo settings")
check("Saved as your photo settings" in E(PP + ".status.text") and "Your settings are back" in E(PP + ".status.text")
      and "saved" in E(PP + ".choiceText.text") and E(PP + ".reset.shown"), "it says so, and the page names the saved settings")
take()
check(cv("cameraFov") == "80" and cv("Contrast") == "60", "a photo with the Screenshot choice now uses your photo settings")
frames(200)
X('FIRE("SCREENSHOT_SUCCEEDED")')
check(cv("cameraFov") == "70" and cv("Contrast") == "55" and E("EyeCandyDB.photo") is None, "and your settings come back after it")

# Cancel keeps nothing. Change it starts from the saved photo settings.
X(PP + ".change.scripts.OnClick()")
check(cv("cameraFov") == "80", "Change it starts from your saved photo settings")
X("NS.SetAdvanced('cameraFov', '65'); NS.SetStandard('graphicsShadowQuality', 2)")
X(PP + ".cancel.scripts.OnClick()")
check(not E("PM.IsEditing()") and cv("cameraFov") == "70" and cv("graphicsShadowQuality") == "5" and E("EyeCandyDB.photo") is None
      and E("EyeCandyDB.photoSettings.values.cameraFov") == "80" and E("EyeCandyDB.advanced.cameraFov") is None,
      "Cancel puts your settings back and keeps the saved ones as they were")
check("Nothing was saved" in E(PP + ".status.text"), "and says nothing was saved")
X(PP + ".reset.scripts.OnClick()")
check(E("EyeCandyDB.photoSettings") is None and not E(PP + ".reset.shown"), "Back to Screenshot preset forgets the saved photo settings")
take()
check(cv("cameraFov") == "90", "and the photo uses the Screenshot preset again")
frames(200)
X('FIRE("SCREENSHOT_SUCCEEDED")')

# Backups and the rest see your settings: they end the edit first.
X(PP + ".change.scripts.OnClick()")
X("ENTRY = NS.CreateBackup('manual', 'during edit')")
check(not E("PM.IsEditing()") and cv("cameraFov") == "70" and E("ENTRY.values.cameraFov") == "70" and E("EyeCandyDB.photo") is None,
      "a backup during the edit ends it first, so it holds your settings")
check("another setting changed" in E(PP + ".status.text"), "and the page says why")
X(PP + ".change.scripts.OnClick()")
X("NS.GoBack()")
check(not E("PM.IsEditing()") and cv("cameraFov") == "70", "Back ends the edit first")

# --- An edit cut short -------------------------------------------------------------------------------------
X(PP + ".change.scripts.OnClick()")
X('FIRE("PLAYER_LEAVING_WORLD")')
check(not E("PM.IsEditing()") and cv("cameraFov") == "70" and E("EyeCandyDB.photo") is None and "loading screen" in E(PP + ".status.text"),
      "a loading screen cancels the edit, your settings back")
X(PP + ".change.scripts.OnClick()")
X('FIRE("PLAYER_LOGOUT")')
check(not E("PM.IsEditing()") and cv("cameraFov") == "70" and E("EyeCandyDB.photo") is None, "so does a logout or /reload")
X(PP + ".change.scripts.OnClick()")
X('FIRE("PLAYER_REGEN_DISABLED")')
check(not E("PM.IsEditing()") and cv("cameraFov") == "70" and "fight" in E(PP + ".status.text"), "a fight cancels it, your settings back")
X("INCOMBAT = true; " + PP + ".change.scripts.OnClick()")
check(not E("PM.IsEditing()") and E(PP + ".status.text").startswith(RED) and "fight" in E(PP + ".status.text") and cv("cameraFov") == "70",
      "Change it in a fight is refused, in red, and changes nothing")
X("INCOMBAT = false; " + PP + ".change.scripts.OnClick(); INCOMBAT = true; PM.CancelEdit('a fight started')")
check(cv("cameraFov") == "90" and E(PP + ".status.text").startswith(GREY) and "after the fight" in E("NS.RunningNote()"),
      "in a locked fight your settings wait, in grey, and the title says so")
X("PM.T_OK, PM.T_ERR = PM.Change()")
check(E("PM.T_OK") is None and "fight" in E("PM.T_ERR"), "no new edit starts while they wait")
X("INCOMBAT = false; PM.T_OK, PM.T_ERR = PM.Change()")
check(E("PM.T_OK") is None and "putting your settings back" in E("PM.T_ERR") and cv("cameraFov") == "90",
      "nor once the lockdown is over but the put-back hasn't run")
X("INCOMBAT = true")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(cv("cameraFov") == "70" and E("EyeCandyDB.photo") is None and E("EyeCandyDB.advanced.Contrast") == "55",
      "they come back when the fight ends, with your choices")
X("SetCVar('cameraFov', 70)")
lua3 = boot(PRE + "EyeCandyDB = { advanced = { Contrast = '60' }, photo = { editing = true, before = { cameraFov = '75' }, state = { tiers = {}, extras = {}, advanced = { Contrast = '50' } } } }")
lua3.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(lua3.eval("GetCVar('cameraFov')") == "75" and lua3.eval("EyeCandyDB.photo") is None and lua3.eval("EyeCandyDB.advanced.Contrast") == "50"
      and any("didn't finish" in m for m in chat(lua3)), "an edit still saved at the next login puts your settings and choices back")

# --- Review fixes: what an edit must not let through ---------------------------------------------------
X("EyeCandyDB.keepApplied = true; PM.Change(); EyeCandyDB.keepApplied = false; PM.CancelEdit()")
check(E("EyeCandyDB.keepApplied") == True, "Keep my settings applied, changed during the edit, comes back with Cancel")
X("PM.Change(); SP_OK, SP_ERR = NS.SaveCurrentAsPreset('Photo try')")
check(E("SP_OK") is None and "photo settings are on" in E("SP_ERR"), "Save my settings as a preset is refused while the photo settings are on")
X("PM.CancelEdit(); SP_OK = NS.SaveCurrentAsPreset('After the edit')")
check(E("SP_OK") is not None, "and works again once they are gone")
X("EyeCandyDB.autotune = { before = {} }; AT_OK, AT_ERR = PM.Change(); EyeCandyDB.autotune = nil")
check(E("AT_OK") is None and "Autotune has your settings" in E("AT_ERR") and not E("PM.IsEditing()"),
      "Change it waits while an Autotune result is still to keep or undo")
X(PP + ".take.scripts.OnClick(); SC = PM.SetChoice('screenshot')")
check(E("SC") is None and "Wait a few seconds" in E("PM.message"), "picking during a photo says to wait, not nothing")
X("PM.Stop('test'); SetCVar('cameraFov', 70)")

# --- Still saved at the next login: it puts them back ------------------------------------------------
lua2 = boot(PRE + "EyeCandyDB = { photo = { before = { cameraFov = '75' } } }")
lua2.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(lua2.eval("GetCVar('cameraFov')") == "75" and lua2.eval("EyeCandyDB.photo") is None
      and any("didn't finish" in m for m in chat(lua2)), "a photo still saved at the next login puts your settings back and says so")

done()
