"""The eye test on the Experimental tab, and the row of buttons that picks a part of the tab (16 Nov 2026).
Run: python tests/test_eye_test.py"""
from lib import boot, chat, check, done

# The settings the eye test flips that the stand-in game doesn't have yet, at their game defaults.
PRE = """
C_CVar.RegisterCVar("cameraFov", "90"); C_CVar.RegisterCVar("bloomUserMult", "1"); C_CVar.RegisterCVar("Contrast", "50")
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
function SetUIVisibility(v) UIParent.shown = v end
"""
lua = boot(PRE)
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
X("ET = NS.EyeTest; ET.random = function() return 1 end")
GOLD, WHITE, GREY, RED = "|cffffd100", "|cffffffff", "|cff9d9d9d", "|cffff4040"


def cv(name):
    return E("GetCVar(%r)" % name)


# --- The rounds ------------------------------------------------------------------------------------
n = E("#ET.ROUNDS")
names = [E("ET.ROUNDS")[i].name for i in range(1, n + 1)]
check(n == 10, "ten rounds (%s)" % names)
X("RESOLVED = 0; for _, r in ipairs(ET.ROUNDS) do if ET.Resolve(r) then RESOLVED = RESOLVED + 1 end end")
check(E("RESOLVED") == 10, "every round has two different sides on a PC that has all its settings")
# Each pair is far apart: a menu setting at least 3 steps, the rest at least a fifth of the value.
far = True
for i in range(1, n + 1):
    X("R = ET.ROUNDS[%d]" % i)
    X("A, B = ET.Resolve(R)")
    for cvar in list(E("A").keys()):
        a, b = float(E("A")[cvar]), float(E("B")[cvar])
        gap = abs(a - b)
        if cvar.startswith("graphics"):
            far = far and gap >= 3
        else:
            far = far and gap >= 0.2 * max(abs(a), abs(b))
check(far, "each pair is far enough apart to see: menu settings 3 steps or more, the rest a fifth or more")

# A setting this game lacks, or a pair that comes out the same, is no round.
X("SAVED = C_CVar.GetCVarInfo; C_CVar.GetCVarInfo = function(n) if n == 'cameraFov' then return nil end return SAVED(n) end")
check(E("ET.Resolve(ET.ROUNDS[2])") is None, "a round whose setting this game lacks is skipped")
X("C_CVar.GetCVarInfo = SAVED")
X("SUPPORTED_MAX.graphicsSSAO = 0")
check(E("ET.Resolve(ET.ROUNDS[8])") is None, "a round whose sides both step down to the same value is skipped")
X("SUPPORTED_MAX.graphicsSSAO = nil")
X("local hi = GetMaxRenderScale; GetMaxRenderScale = function() return 0.7 end; RS = ET.Resolve(ET.ROUNDS[6]); GetMaxRenderScale = hi")
check(E("RS") is None, "render scale clamped to the same value on both sides is skipped")

# --- The tab: a row of buttons picks the part ----------------------------------------------------------
X("NS.ShowTab('autotune'); EyeCandyMainFrame.shown = true; NS.RefreshUI()")
P = "EyeCandyMainFrame.pages.autotune"
labels = [E(P + ".partButtons")[i].label for i in range(1, E("#" + P + ".partButtons") + 1)]
check(labels[:2] == ["Autotune", "Eye test"], "the Experimental tab has a button for each part (%s)" % labels)
check(E(P + ".partButtons[1].text").startswith(GOLD) and E(P + ".partButtons[2].text").startswith(WHITE),
      "Autotune shows first, its button gold")
check(E(P + ".parts.autotune.shown") and not E(P + ".parts.eye.shown") and E(P + ".head.label.text") == "Autotune",
      "Autotune's page shows, the eye test's is hidden")
X(P + ".partButtons[2].scripts.OnClick()")
check(E("EyeCandyDB.experimentPart") == "eye" and E(P + ".parts.eye.shown") and not E(P + ".parts.autotune.shown")
      and E(P + ".partButtons[2].text").startswith(GOLD), "Eye test shows its own page, remembered")
EP = P + ".eye"
check(E(EP + ".head.label.text") == "Eye test" and E(EP + ".head.note.text") == "Experimental", "its heading comes from ns.Header")
check("1 or 2" in E(EP + ".why.text") and "puts your settings back" in E(EP + ".how.text"),
      "it says what it is, and what ends it")
check(E(EP + ".start.shown") and not E(EP + ".roundHead.shown") and not E(EP + ".resultHead.shown"),
      "before it starts: only Start")
X("NS.Helper.LetEyeCandyPick()")
check(E("EyeCandyDB.experimentPart") == "autotune" and E(P + ".parts.autotune.shown") and not E(P + ".parts.eye.shown"),
      "Help me pick's Let Eye Candy pick shows Autotune's part, not the last one looked at")
X(P + ".partButtons[2].scripts.OnClick()")

# --- Refusals show in red under Start --------------------------------------------------------------
X("INCOMBAT = true; " + EP + ".start.scripts.OnClick(); INCOMBAT = false")
check(E(EP + ".status.text").startswith(RED) and "fight" in E(EP + ".status.text") and not E("ET.IsOn()"),
      "Start in a fight is refused, in red, in the window")
X("EyeCandyDB.autotune = { before = {} }; " + EP + ".start.scripts.OnClick(); EyeCandyDB.autotune = nil")
check("Back to before Autotune" in E(EP + ".status.text") and not E("ET.IsOn()"),
      "Start while Autotune has your settings is refused and says what to do")

# --- A round -------------------------------------------------------------------------------------
X("SetCVar('graphicsShadowQuality', 5); SetCVar('cameraFov', 82); SetCVar('bloomUserMult', 0.5)")
# Sides are picked at random when the test starts: here only round 3's are swapped.
X("CALLS = 0; ET.random = function() CALLS = CALLS + 1; return CALLS == 3 and 2 or 1 end")
X(EP + ".start.scripts.OnClick()")
check(E("ET.IsOn()") and E("EyeCandyDB.eyeTest.before.graphicsShadowQuality") == "5", "Start saves your settings first")
check(E(EP + ".roundHead.label.text") == "Round 1 of 10: Shadows" and "Showing 1" in E(EP + ".roundText.text"),
      "round 1 names the setting and says side 1 is on")
check(cv("graphicsShadowQuality") == "1" and E(EP + ".show[1].text").startswith(GOLD), "side 1 is on, its button gold")
check(not E(EP + ".start.shown") and E(EP + ".stop.shown"), "Start makes way for Stop eye test")
check(E("NS.RunningNote()") == "Eye test is changing your settings", "the title and the card say the eye test has your settings")
X(EP + ".picks[1].scripts.OnClick()")
check(E("ET.State().i") == 1 and E(EP + ".status.text").startswith(RED) and "Show 2" in E(EP + ".status.text"),
      "an answer before seeing both is refused, in red")
X(EP + ".show[2].scripts.OnClick()")
check(cv("graphicsShadowQuality") == "4" and "Showing 2" in E(EP + ".roundText.text"), "Show 2 flips to side 2")
X(EP + ".show[1].scripts.OnClick()")
check(cv("graphicsShadowQuality") == "1", "and back to 1, as often as you like")
X(EP + ".picks[2].scripts.OnClick()")
check(cv("graphicsShadowQuality") == "4" and E("ET.State().i") == 2 and E(EP + ".roundHead.label.text") == "Round 2 of 10: Field of view",
      "2 is better keeps side 2 on and goes to round 2")
X(EP + ".show[2].scripts.OnClick()")
X("INCOMBAT = true; A_OK, A_ERR = ET.Answer('same'); INCOMBAT = false")
check(E("A_OK") is None and "fight" in E("A_ERR") and E("ET.State().i") == 2, "an answer in a fight is refused")
# A menu value flipped in a round can reset hidden settings: an answer puts yours back.
X("SetCVar('graphicsTextureResolution', 0)")
X(EP + ".picks[3].scripts.OnClick()")
check(cv("cameraFov") == "82", "Same to me keeps your own setting")
check(cv("graphicsTextureResolution") == "2", "an answer puts back your other settings the round changed")
check(E("ET.Answers().cameraFov") is None, "Same to me adds nothing to the answers, so your own value stays")
X("ET.Show(1)")
check(cv("bloomUserMult") == "1", "with the sides swapped at random, side 1 is the second value")
X("ET.Show(2); ET.Answer(1)")
check(cv("bloomUserMult") == "1", "and picking 1 keeps it")
for i in range(4, 11):
    X("ET.Show(1); ET.Show(2); ET.Answer(2)")
check(E("ET.State().phase") == "result" and E(EP + ".resultHead.shown") and not E(EP + ".roundHead.shown"),
      "after the last round, your answers show")
res = E(EP + ".result.text")
check("on now" in res and "Shadows:" in res and "the same to you" in res and "Sharpening: Strong" in res,
      "the answers list each round, the same-to-you one too (%s)" % res.replace("\n", " | "))
check(E("NS.RunningNote()") == "Eye test's answers are on, not saved yet", "the title says the answers are on but not saved")

# --- Save as preset ------------------------------------------------------------------------------------
X(EP + ".name.GetText = function(self) return self.text end")
check(E(EP + ".name.text") == "Eye test", "the name box offers a free name")
X(EP + ".name:SetText('Balanced'); " + EP + ".save.scripts.OnClick()")
check(E(EP + ".saveText.text").startswith(RED) and E("ET.IsOn()") and cv("graphicsShadowQuality") == "4",
      "a name taken by a built-in is refused in red under the box, and nothing changes")
X(EP + ".name:SetText('My eyes'); " + EP + ".save.scripts.OnClick()")
X("MINE = NS.FindPresetByName('My eyes')")
check(E("MINE ~= nil") and E("MINE.values.graphicsShadowQuality") == "4" and E("MINE.values.cameraFov") == "82",
      "Save as preset saves the answers, and your own value where you said the same")
check(E("MINE.values.graphicsTextureResolution") == "2" and "eye test" in E("MINE.desc"), "everything else is your own, with a note")
check(not E("ET.IsOn()") and E("EyeCandyDB.eyeTest") is None and E("NS.OnPreset().id") == E("MINE.id"),
      "the preset goes on, and the eye test lets go")
check("My eyes" in E(EP + ".status.text") and E(EP + ".start.shown"), "it says so, and Start is back")

# --- Endings: each puts your settings back --------------------------------------------------------------
def begin():
    X("ET.random = function() return 1 end; SetCVar('graphicsShadowQuality', 5); " + EP + ".start.scripts.OnClick()")


begin()
X('FIRE("PLAYER_REGEN_DISABLED")')
check(not E("ET.IsOn()") and cv("graphicsShadowQuality") == "5" and "fight" in E(EP + ".status.text"),
      "a fight ends it and puts your settings back")
X('FIRE("PLAYER_REGEN_ENABLED")')
begin()
X('FIRE("PLAYER_LEAVING_WORLD")')
check(not E("ET.IsOn()") and cv("graphicsShadowQuality") == "5", "a loading screen ends it and puts your settings back")
begin()
X("EyeCandyMainFrame.hooks.OnHide(EyeCandyMainFrame)")
check(not E("ET.IsOn()") and cv("graphicsShadowQuality") == "5", "closing the window ends it and puts your settings back")
begin()
X("NS.TogglePeek(); EyeCandyMainFrame.hooks.OnHide(EyeCandyMainFrame)")
check(E("ET.IsOn()"), "Peek hides the window without ending it")
X("NS.TogglePeek()")
X("SNAP = nil; local snap = NS.SnapshotGameMenu; NS.SnapshotGameMenu = function() SNAP = GetCVar('graphicsShadowQuality') end")
X("SettingsPanel.hooks.OnShow(SettingsPanel)")
check(not E("ET.IsOn()") and cv("graphicsShadowQuality") == "5", "opening Options ends it and puts your settings back")
check(E("SNAP") == "5", "and the game menu's values are noted again with yours back, so closing Options keeps nothing of the test's")
begin()
X("NS.ApplyPresetById('tier1')")
check(not E("ET.IsOn()") and E("NS.BeforeRecord().values.graphicsShadowQuality") == "5",
      "a preset applied mid-test ends it first, so its Back to before holds your settings, not the test's")
begin()
X("STOPPED = NS.ToggleCompare and select(2, NS.ToggleCompare()); AT_OK, AT_ERR = NS.Autotune.Start('balance')")
check("eye test" in (E("STOPPED") or "") and E("AT_OK") is False and "eye test" in E("AT_ERR") and E("ET.IsOn()"),
      "Compare and Autotune don't start during the test")
X("NS.ApplyAll()")
check(not E("ET.IsOn()") and "another setting" in E(EP + ".status.text"), "another Eye Candy apply ends it first")
check(E("NS.FPS.Still({})") is True, "standing still with no test on, the FPS reader may measure a preset")
begin()
check(E("NS.FPS.Still({})") is False, "during the test it doesn't, so no preset's FPS is measured on the test's values")
X("NS.PatchWatchLogout()")
check(cv("graphicsShadowQuality") == "1" and E("EyeCandyDB.patchWatch.snap.values.graphicsShadowQuality") == "5",
      "the patch warning's copy at logout holds your settings, not the test's")
X(EP + ".stop.scripts.OnClick()")
check(not E("ET.IsOn()") and cv("graphicsShadowQuality") == "5", "Stop eye test puts your settings back")

# A fight already locked: the settings wait for its end, and the window says so in grey.
begin()
X("INCOMBAT = true; ET.Stop('a fight started')")
check(cv("graphicsShadowQuality") == "1" and E(EP + ".status.text").startswith(GREY)
      and E("NS.RunningNote()") == "Eye test puts your settings back after the fight", "in a fight they wait, in grey")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(cv("graphicsShadowQuality") == "5" and E("EyeCandyDB.eyeTest") is None, "and come back when it ends")

# A fight at the answers: settings back, the answers kept for Save.
begin()
for i in range(10):
    X("ET.Show(1); ET.Show(2); ET.Answer(2)")
X('FIRE("PLAYER_REGEN_DISABLED")')
check(cv("graphicsShadowQuality") == "5" and E("ET.State().phase") == "result" and "still saves" in E(EP + ".status.text"),
      "a fight at the answers puts your settings back and keeps the answers")
check(not E(EP + ".back.shown") and E(EP + ".start.shown"), "Back to before eye test goes, since nothing is left to undo")
X('FIRE("PLAYER_REGEN_ENABLED"); ' + EP + ".name:SetText('After the fight'); " + EP + ".save.scripts.OnClick()")
check(E("NS.FindPresetByName('After the fight').values.graphicsShadowQuality") == "4" and cv("graphicsShadowQuality") == "4",
      "Save as preset still saves the answers after the fight and puts them on")

# Back to before eye test at the answers.
begin()
for i in range(10):
    X("ET.Show(1); ET.Show(2); ET.Answer(2)")
X(EP + ".back.scripts.OnClick()")
check(cv("graphicsShadowQuality") == "5" and E("ET.State()") is None, "Back to before eye test puts your settings back and forgets the answers")

# The city switch waits while the test has your settings, and lowers yours once they are back.
X("""MAPS = { [13] = { mapType = 2, parentMapID = 947, flags = 0 }, [84] = { mapType = 3, parentMapID = 13, flags = 0 },
  [37] = { mapType = 3, parentMapID = 13, flags = 0 } }
MAP = 37
C_Map = { GetBestMapForUnit = function() return MAP end, GetMapInfo = function(id) local m = MAPS[id]
  if m then return { mapID = id, name = "map", mapType = m.mapType, parentMapID = m.parentMapID, flags = m.flags } end end }
C_PvP = { GetZonePVPInfo = function() return nil end }
function IsInInstance() return false, "none" end""")
X("SetCVar('graphicsViewDistance', 9); NS.SetAutoSituation('city', true)")
begin()
X("ET.Show(1); ET.Show(2); ET.Answer(2); ET.Show(1); ET.Show(2); ET.Answer(2); ET.Show(1); ET.Show(2); ET.Answer(2)")
X("ET.Show(1); ET.Show(2); ET.Answer(2); ET.Show(1)")
check(cv("graphicsViewDistance") == "4", "round 5 shows view distance 4")
X('ET.Show(2); MAP = 84; FIRE("ZONE_CHANGED_NEW_AREA"); FIRE("ZONE_CHANGED"); RUNTIMERS()')
check(cv("graphicsViewDistance") == "9" and E("NS.ActiveSituationName()") is None, "walking into a city during the test changes nothing in it")
X(EP + ".stop.scripts.OnClick()")
check(E("NS.ActiveSituationName()") == "Capital city" and cv("graphicsViewDistance") == "7",
      "once your settings are back, the city switch lowers yours")
X('MAP = 37; FIRE("ZONE_CHANGED_NEW_AREA"); RUNTIMERS(); NS.SetAutoSituation("city", false)')
check(cv("graphicsViewDistance") == "9", "and puts yours back when you leave")

# --- A test still saved at the next login: it puts them back -------------------------------------------
lua2 = boot(PRE + "EyeCandyDB = { eyeTest = { before = { graphicsShadowQuality = '2' } } }")
lua2.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(lua2.eval("GetCVar('graphicsShadowQuality')") == "2" and lua2.eval("EyeCandyDB.eyeTest") is None
      and any("didn't finish" in m for m in chat(lua2)), "a test still saved at the next login puts your settings back and says so")

done()
