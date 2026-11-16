"""Checks for the four-tab window, minimap button and Options entry (roadmap step 2).
Run: python tests/test_window.py"""
from lib import boot as lib_boot, chat, check, done

# EditBox text: GetText returns what SetText stored.
GETTEXT = """local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end"""

# The hidden CVars the dials use (the harness only has the menu ones).
ADV = """
local reg = { lodObjectCullDist="30", lodObjectMinSize="20", lodObjectSizeScale="1", wmoLodDistScale="1.0", wmoDoodadDist="2000",
 entityLodOffset="10", animFrameSkipLOD="0", entityShadowFadeScale="50", specular="1", componentSpecular="1", componentEmissive="1",
 DepthBasedOpacity="1", assaoRadius="1.85", assaoShadowMult="1.1", assaoShadowPower="1.34", assaoSharpness=".98", assaoBlurPassCount="2",
 assaoDetailShadowStrength="0", assaoHorizonAngleThresh="0.4", assaoFadeOutFrom="50.0", assaoFadeOutTo="300.0", assaoAdaptiveQualityLimit=".45",
 reflectionMode="3", reflectionDownscale="0", rippleDetail="2", particleDensity="100", particleMTDensity="100", particulatesEnabled="1",
 showfootprintparticles="1", volumeFogInterior="1", ffxGlow="1", ffxDeath="1", CMAA2Quality="3", CMAA2ExtraSharpness="0",
 terrainMipLevel="0", worldBaseMip="0", componentTextureLevel="0", SkyCloudLOD="0", preloadStreamingDistObject="64", preloadStreamingDistTerrain="256",
 Contrast="57", Brightness="46", bloomUserMult="1", cameraFov="90" }
for k, v in pairs(reg) do C_CVar.RegisterCVar(k, v) end
function FINDROW(cvar) for _, r in ipairs(NS.advRows) do if r.d[1] == cvar then return r end end end
"""


def boot(svdb=None):
    lua = lib_boot(svdb=svdb)
    lua.execute(GETTEXT)
    return lua


luaW = boot()
luaW.execute(ADV)
luaW.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("")')
W = lambda e: luaW.eval(e)
check(W('EyeCandyMainFrame.shown') == True and W('EyeCandyMainFrame.tab') == "presets", "window opens on the Presets tab")
check(W('EyeCandyMainFrame.pages.presets.usesList') == True and W('EyeCandyMainFrame.pages.presets.rows[1].p.id') == "tier1", "the Presets tab lists the real presets, tiers first")
luaF = boot()
luaF.execute('NS.ListPresets = nil; FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY("")')
check(luaF.eval('EyeCandyMainFrame.pages.presets.usesList') is None and luaF.eval('EyeCandyMainFrame.shown') == True, "without the presets list, the Presets tab shows the tier and Look buttons")
for t in ["standard", "hidden", "backups", "presets"]:
    luaW.execute('NS.ShowTab("%s")' % t)
    shown = [k for k in ["presets", "standard", "hidden", "backups"] if W('EyeCandyMainFrame.pages.%s.shown' % k)]
    check(shown == [t], "tab %s shows only its own page (%s)" % (t, shown))
luaW.execute('SlashCmdList.EYECANDY("")')
check(W('EyeCandyMainFrame.shown') == False, "/ec closes the open window")
luaW.execute('SlashCmdList.EYECANDY("")')
check(W('EyeCandyMainFrame.shown') == True and W('EyeCandyMainFrame.tab') == "presets", "/ec opens it again on Presets")
check(W('#NS.tierRows') == W('#NS.CATEGORIES') and W('#NS.extraRows') == W('#NS.EXTRAS'), "Hidden tab has a tier row per system and every Extra")
bad = W("""(function()
  local bad, tiers = {}, {}
  for _, g in ipairs(NS.ADVANCED) do if g.tier then tiers[g.tier] = (tiers[g.tier] or 0) + 1 end; if not g.name then bad[#bad+1] = "name " .. g.key end end
  for _, c in ipairs(NS.CATEGORIES) do if tiers[c.key] ~= 1 then bad[#bad+1] = "tier " .. c.key end end
  local keys = {} for _, g in ipairs(NS.ADVANCED) do keys[g.key] = true end
  for _, ex in ipairs(NS.EXTRAS) do if not keys[ex.system or ""] then bad[#bad+1] = "extra " .. ex.key end end
  return table.concat(bad, "; ")
end)()""")
check(bad == "", "Hidden tab groups: every tier heads exactly one system, every Extra has a system: " + bad)
# dot on settings changed from the game default
luaW.execute('NS.ShowTab("hidden")')
check(W('FINDROW("groundEffectDist").dot.shown') == True and W('FINDROW("assaoRadius").dot.shown') == False, "dot on changed settings only (grass distance 320 vs 100; AO radius at default)")
# search across Standard and Hidden
counts = luaW.eval('NS.SetSearch("grass")')
check(W('FINDROW("groundEffectDensity").shown') == True and W('FINDROW("assaoRadius").shown') == False, "search 'grass' shows grass dials and hides the rest")
check(counts["hidden"] == 4, "search 'grass': the Grass & Foliage tier row and its 3 dials (%s)" % counts["hidden"])
check("Hidden 4" in W('EyeCandyMainFrame.searchCount.text'), "search shows match counts")
luaW.execute('NS.SetSearch("lodobjectcull")')
check(W('FINDROW("lodObjectCullSize").shown') == True and W('FINDROW("lodObjectCullDist").shown') == True and W('FINDROW("doodadLodScale").shown') == False, "search matches CVar names too")
luaW.execute('NS.SetSearch("")')
check(all(W('NS.advRows[%d].shown' % i) for i in range(1, W('#NS.advRows') + 1)), "clearing the search shows every row again")
check(W('EyeCandyMainFrame.searchCount.text') == "", "no count when the search is empty")
# tier stepper on the Hidden tab still saves the choice
luaW.execute('EyeCandyDB.tiers.water = nil; NS.StepTier(NS.tierRows[4].cat, 1)')
check(W('EyeCandyDB.tiers.water') == 1 and "Performance" in W('NS.tierRows[4].value.text'), "Hidden tab tier stepper sets and shows the tier")
# Backups tab with the real backups code: the Original is listed and Create backup asks for a name
luaW.execute('SlashCmdList.EYECANDY("apply"); NS.ShowTab("backups")')
names = [luaW.eval('EyeCandyMainFrame.pages.backups.rows[%d] and EyeCandyMainFrame.pages.backups.rows[%d].shown ~= false and EyeCandyMainFrame.pages.backups.rows[%d].name.text' % (i, i, i)) for i in range(1, 6)]
check("Original settings" in names, "Backups tab lists the Original backup (%s)" % names)
luaW.execute('EyeCandyMainFrame.createBackup.scripts.OnClick(EyeCandyMainFrame.createBackup)')
check(W('EyeCandyAskFrame.shown') == True, "Create backup asks for a name")
luaW.execute('EyeCandyAskFrame:Hide()')
orig = names.index("Original settings") + 1
luaW.execute('local r = EyeCandyMainFrame.pages.backups.rows[%d]; r.restore.scripts.OnClick(r.restore)' % orig)
check(W('EyeCandyAskFrame.shown') == True and W('EyeCandyAskFrame.textFS.text').startswith("Restore ") and "Back on the Presets tab can undo it today." in W('EyeCandyAskFrame.textFS.text'), "Restore asks first, with the count, and says Back can undo it")
chat(luaW)
luaW.execute('EyeCandyAskFrame.accept.scripts.OnClick(EyeCandyAskFrame.accept)')
check("Restored " in (W('EyeCandyMainFrame.pages.backups.result.text') or "") and W('EyeCandyAskFrame.shown') == False, "accepting restores the backup, and the tab says so")
check(not any("restored" in x.lower() for x in chat(luaW)), "a restore from the window prints nothing to chat")
# Backups tab without the backups list (the guarded fallback): the single Original backup
luaB = boot()
luaB.execute(ADV)
luaB.execute('NS.ListBackups = nil; NS.CreateBackup = nil')
luaB.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY(""); SlashCmdList.EYECANDY("apply"); NS.ShowTab("backups")')
B_ = lambda e: luaB.eval(e)
check(B_('EyeCandyMainFrame.pages.backups.rows[1].name.text') == "Original settings" and ("matches now" in B_('EyeCandyMainFrame.pages.backups.rows[1].info.text') or "differ" in B_('EyeCandyMainFrame.pages.backups.rows[1].info.text')), "without the list, the Backups tab shows the single backup with a change count")
luaB.execute('EyeCandyMainFrame.createBackup.scripts.OnClick(EyeCandyMainFrame.createBackup)')
check(B_('not (EyeCandyAskFrame and EyeCandyAskFrame.shown)') == True, "Create backup does nothing until the backups list exists")
# bottom bar
luaW.execute('EyeCandyMainFrame.keep.scripts.OnClick(EyeCandyMainFrame.keep)')
check(W('EyeCandyDB.keepApplied') == True, "Keep my settings applied checkbox saves")
luaW.execute('SlashCmdList.EYECANDY("adv")')
check(W('EyeCandyMainFrame.tab') == "hidden" and W('EyeCandyMainFrame.shown') == True, "/ec adv opens the Hidden tab")
luaW.execute('SlashCmdList.EYECANDY("hidden")')
check(W('EyeCandyMainFrame.shown') == False, "/ec hidden again closes it")
# minimap button and Options > AddOns
check(W('EyeCandyMinimapButton ~= nil and EyeCandyMinimapButton.shown') == True, "minimap button made at login and shown")
luaW.execute('EyeCandyMinimapButton.scripts.OnClick(EyeCandyMinimapButton, "LeftButton")')
check(W('EyeCandyMainFrame.shown') == True and W('EyeCandyMainFrame.tab') == "presets", "minimap click opens the window on Presets")
luaW.execute('EyeCandyMinimapButton.scripts.OnClick(EyeCandyMinimapButton, "RightButton")')
check(W('EyeCandyMainFrame.tab') == "backups", "minimap right-click opens Backups")
luaW.execute('SlashCmdList.EYECANDY("minimap")')
check(W('EyeCandyMinimapButton.shown') == False and W('EyeCandyDB.minimap.hide') == True, "/ec minimap hides the button and remembers")
luaW.execute('SlashCmdList.EYECANDY("minimap")')
check(W('EyeCandyMinimapButton.shown') == True and W('EyeCandyDB.minimap.hide') == False, "/ec minimap shows it again")
check(W('#SETTINGS_CATEGORIES') == 1 and W('SETTINGS_CATEGORIES[1].name') == "Eye Candy", "Options > AddOns entry registered as Eye Candy")
luaW.execute('NS.optionsPanel.minimapCheck.scripts.OnClick(NS.optionsPanel.minimapCheck)')
check(W('EyeCandyMinimapButton.shown') == True, "Options checkbox drives the minimap button")
toc = open(__import__('lib').addon + 'EyeCandy.toc', encoding='utf-8').read()
func = [l.split(":", 1)[1].strip() for l in toc.splitlines() if l.startswith("## AddonCompartmentFunc:")]
luaW.execute('EyeCandyMainFrame:Hide()')
luaW.execute('%s("EyeCandy", "LeftButton")' % func[0])
check(W('EyeCandyMainFrame.shown') == True, "the game's addon menu entry (.toc AddonCompartmentFunc) opens the window")
luaM = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true, minimap = { hide = true, angle = 90 } }')
luaM.execute('FIRE("PLAYER_LOGIN")')
check(luaM.eval('EyeCandyMinimapButton.shown') == False and luaM.eval('EyeCandyDB.minimap.angle') == 90, "a hidden minimap button stays hidden after reload")

# Presets and Backups tabs with the presets-backups API (fakes in the shared-plan shape)
API = """
CALLS = {}
local function rec(name) return function(...) local t = {} for i = 1, select("#", ...) do t[i] = tostring((select(i, ...))) end CALLS[#CALLS+1] = name .. ":" .. table.concat(t, ",") end end
for _, n in ipairs({"ApplyPresetById","SaveCurrentAsPreset","RenamePreset","DuplicatePreset","DeletePreset","CreateBackup","RestoreBackupById","DeleteBackup","ImportPreset"}) do NS[n] = rec(n) end
NS.ListPresets = function() return { builtin = { {id="t1", name="Performance", group="Tiers", builtin=true, desc="FPS first"}, {id="l4", name="Moody", group="Looks", builtin=true, desc="Dark"} }, user = { {id="u1", name="Raid night", group="Yours", builtin=false} } } end
NS.ExportPreset = function(id) return "!EC1!abc" .. id end
NS.PreviewImport = function(t) if t:find("^!EC1!") then return {ok=true, name="Moody", author="Sam", date="2026-11-15", gameVersion="1.60.1", changes=12, skipped={"chatStyle"}, clash=(t == "!EC1!clash")} end return {ok=false, err="Not an Eye Candy string."} end
NS.ListBackups = function() return { {id="b2", kind="auto", label="Before Moody", time="2026-11-15 21:40", character="Sam-Realm", values={}}, {id="b1", kind="original", label="Original settings", time="2026-11-01 10:00", values={}} } end
NS.CountBackupChanges = function(id) return id == "b2" and 47 or 3 end
function LASTCALL() return CALLS[#CALLS] end
function ACCEPT(text) if text then EyeCandyAskFrame.edit.text = text end EyeCandyAskFrame.accept.scripts.OnClick(EyeCandyAskFrame.accept) end
function CLICK(b) b.scripts.OnClick(b) end
"""
luaI = boot()
luaI.execute(API)
luaI.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY("")')
I = lambda e: luaI.eval(e)
P = 'EyeCandyMainFrame.pages.presets'
check(I(P + '.usesList') == True and I(P + '.rows[1].p.id') == "u1" and I(P + '.rows[2].p.id') == "t1" and I(P + '.rows[3].p.id') == "l4", "Presets tab lists yours, then quality levels, then Looks")
# The "..." menu (the game's MenuUtil is missing in the stubs, so the fallback list of buttons opens).
MENU = 'EyeCandyPresetMenu'
def menu(row):
    luaI.execute('CLICK(%s.rows[%d].more)' % (P, row))
    return [I('%s.buttons[%d].text' % (MENU, i)) for i in range(1, 5) if I('%s.buttons[%d] and %s.buttons[%d].shown' % (MENU, i, MENU, i))]
check("Performance" in I(P + '.rows[2].name.text') and menu(2) == ["Share", "Duplicate"], "built-ins can't be renamed or deleted")
check(menu(1)[2:] == ["Rename", "|cffff4040Delete|r"], "your presets can be renamed and deleted")
luaI.execute('CLICK(%s.rows[2].apply)' % P)
check(I('LASTCALL()') == "ApplyPresetById:t1", "Apply calls ApplyPresetById")
menu(3); luaI.execute('CLICK(%s.buttons[2])' % MENU)
check(I('LASTCALL()') == "DuplicatePreset:l4", "Duplicate works on a built-in")
menu(1); luaI.execute('CLICK(%s.buttons[1])' % MENU)
check(I('EyeCandyExportFrame.text') == "!EC1!abcu1" and "friend" in I('EyeCandyExportFrame.hint.text'), "Share shows the share string in the copy box")
menu(1); luaI.execute('CLICK(%s.buttons[3])' % MENU)
check(I('EyeCandyAskFrame.shown') == True and I('EyeCandyAskFrame.edit.text') == "Raid night", "Rename asks, with the old name filled in")
luaI.execute('ACCEPT("  Raid nights ")')
check(I('LASTCALL()') == "RenamePreset:u1,Raid nights", "Rename passes the new name, trimmed")
menu(1); luaI.execute('CLICK(%s.buttons[4])' % MENU)
check("can't be undone" in I('EyeCandyAskFrame.textFS.text') and I('LASTCALL()') == "RenamePreset:u1,Raid nights", "Delete asks first")
luaI.execute('ACCEPT()')
check(I('LASTCALL()') == "DeletePreset:u1", "Delete after yes")
luaI.execute('CLICK(%s.saveButton); ACCEPT("Goldshire")' % P)
check(I('LASTCALL()') == "SaveCurrentAsPreset:Goldshire", "Save current as preset asks for a name")
n = I('#CALLS')
luaI.execute('CLICK(%s.saveButton); ACCEPT("   ")' % P)
check(I('#CALLS') == n, "a blank name saves nothing")
# The Import strip on the Presets tab (the stub frames have no GetText, so give them one)
luaI.execute('local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index; mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end')
S = P + '.strip'
def paste(text):
    luaI.execute('%s.box.text = "%s"; NS.UpdateImportStrip(%s)' % (S, text, P))
paste("hello")
check("Can't read" in I(S + '.result.text') and I(S + '.import.shown') == False, "a bad string can't be imported")
paste("!EC1!ok")
pv = I(S + '.result.text')
check("Moody" in pv and "by Sam" in pv and "Changes 12 settings" in pv and "Skips 1" in pv and "chatStyle" in pv, "import preview: name, author, change count, skipped settings")
check(I(S + '.import.shown') == True and I(S + '.replace.shown') == False, "no name clash: one Import button")
luaI.execute('CLICK(%s.import)' % S)
check(I('LASTCALL()') == "ImportPreset:!EC1!ok,keep", "Import imports")
paste("!EC1!clash")
check(I(S + '.replace.shown') == True and I(S + '.keep.shown') == True and I(S + '.import.shown') == False, "name clash: Replace or Keep both")
luaI.execute('CLICK(%s.replace)' % S)
check(I('LASTCALL()') == "ImportPreset:!EC1!clash,replace", "Replace passes mode replace")
B = 'EyeCandyMainFrame.pages.backups'
luaI.execute('NS.ShowTab("backups")')
check(I(B + '.rows[2].name.text') == "Before Moody" and "47 settings differ" in I(B + '.rows[2].info.text') and "Sam" in I(B + '.rows[2].info.text'), "Backups list: label, change count, character")
check(I(B + '.rows[1].delete.shown') == False and I(B + '.rows[2].delete.shown') == True, "the Original is listed first and can't be deleted")
luaI.execute('CLICK(%s.rows[2].restore)' % B)
check(I('EyeCandyAskFrame.textFS.text').startswith("Restore 47 settings from 2026-11-15 21:40?"), "Restore asks with the count and date")
luaI.execute('ACCEPT()')
check(I('LASTCALL()') == "RestoreBackupById:b2", "Restore after yes")
luaI.execute('CLICK(%s.rows[2].delete); ACCEPT()' % B)
check(I('LASTCALL()') == "DeleteBackup:b2", "Delete a backup after yes")
luaI.execute('CLICK(EyeCandyMainFrame.createBackup); ACCEPT("Before raid")')
check(I('LASTCALL()') == "CreateBackup:manual,Before raid", "bottom bar Create backup asks for a name")
luaI.execute('CLICK(EyeCandyMainFrame.createBackup); ACCEPT("")')
check(I('LASTCALL()') == "CreateBackup:manual,nil", "a blank backup name lets the backups code pick the date")
# Undo points from the window (shared plan, step 4 contract)
luaI.execute('C_CVar.RegisterCVar("lodObjectCullDist", "30"); EyeCandyMainFrame:Hide(); SlashCmdList.EYECANDY(""); CALLS = {}; NS.SetStandard("vsync", "0"); NS.SetStandard("vsync", "1")')
check(I('#CALLS') == 0, "Standard changes take no automatic backup")
luaI.execute('NS.OriginalBackup = function() return { values = { lodObjectCullDist = "17" } } end; NS.db.advanced.lodObjectCullDist = "5"; SetCVar("lodObjectCullDist", "5"); NS.ShowTab("hidden"); CALLS = {}; local b = EyeCandyMainFrame.pages.hidden.resetAll; CLICK(b); CLICK(b)')
check(I('#CALLS') == 0, "Reset all dials takes no automatic backup (automatic backups are gone)")
check(I('GetCVar("lodObjectCullDist")') == "17" and I('NS.db.advanced.lodObjectCullDist') is None, "a reset dial goes back to the Original backup's value (read through OriginalBackup)")
luaI.execute('CALLS = {}; local b = EyeCandyMainFrame.pages.hidden.resetAll; CLICK(b); CLICK(b)')
check(I('#CALLS') == 0, "Reset all with nothing to reset takes no backup")
# A refused call says why (the API returns nil, "reason")
luaI.execute('NS.ShowTab("presets"); CHAT = {}; NS.SaveCurrentAsPreset = function() return nil, "Beautiful is a built-in name. Pick another." end; CLICK(%s.saveButton); ACCEPT("Beautiful")' % P)
check(I('EyeCandyAskFrame.shown') == True and "built-in name" in I('EyeCandyAskFrame.errFS.text') and not chat(luaI),
      "a refused save keeps the name box open and says why under it")
luaI.execute('EyeCandyAskFrame:Hide()')
luaI.execute('if EyeCandyExportFrame then EyeCandyExportFrame:Hide() end; NS.ExportPreset = function() return nil, "Sharing needs the game\'s encoding tools." end')
menu(1); luaI.execute('CLICK(%s.buttons[1])' % MENU)
check("encoding tools" in I(P + '.card.note.text') and not I('EyeCandyExportFrame and EyeCandyExportFrame.shown'), "a failed export says why and opens no empty box")
luaI.execute('NS.ImportPreset = function() return nil, "That code is from a newer Eye Candy." end')
paste("!EC1!ok")
luaI.execute('CLICK(%s.import)' % S)
check("newer Eye Candy" in I(S + '.result.text'), "a refused import says why, under the box")
paste("!EC1!ok")
check("doesn't save in presets" in I(S + '.result.text'), "the import preview says why settings were skipped")
# Without the backups list, the window doesn't promise automatic backups
check("Every apply can be undone" not in luaF.eval('EyeCandyMainFrame.pages.presets.status.text') or luaF.eval('NS.CreateBackup') is not None, "no undo promise when there are no automatic backups")

# Standard tab: the game's own Graphics menu
STD = """
local reg = { gxMonitor="0", gxMaximize="1", useUiScale="0", uiscale="1", LowLatencyMode="0", ffxAntiAliasingMode="4", cameraFov="90",
 graphicsQuality="5", gxMaxFrameLatency="3", gxapi="auto", physicsLevel="1", gxAdapter="", useMaxFPS="0", maxFPS="120",
 useMaxFPSBk="1", maxFPSBk="30", targetFPS="60", Contrast="50", Brightness="50", bloomUserMult="1",
 GxCompatOptionalGpuFeatures="1", GxCompatAsyncShaderCompilation="1", GxCompatCommandListMultiThreading="1", GxCompatWorkSubmitOptimizations="1" }
for k, v in pairs(reg) do C_CVar.RegisterCVar(k, v) end
function GetGraphicsAPIs() return "d3d11", "d3d12" end
function SettingsPanel:Open() self.shown = true end
function STDROW(cvar) for _, r in ipairs(NS.stdRows) do if r.def.cvar == cvar then return r end end end
function ROOT() local root = { radios = {} }
  function root:CreateRadio(text, isSel, setSel) local d = { text = text, isSel = isSel, setSel = setSel, enabled = true }
    function d:SetEnabled(e) self.enabled = e end; self.radios[#self.radios + 1] = d; return d end
  return root end
function MENU(cvar) local root = ROOT(); STDROW(cvar).menu(nil, root); return root.radios end
"""
luaS = boot()
luaS.execute(STD)
luaS.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("standard")')
S = lambda e: luaS.eval(e)
total = S('(function() local n = 0 for _, g in ipairs(NS.STANDARD) do n = n + #g.rows end return n end)()')
check(S('#NS.stdRows') == total and total >= 40, "Standard tab has a row per game setting (%s)" % total)
missing = S("""(function() local bad = {}
  for _, g in ipairs(NS.STANDARD) do if not NS.StandardText(g.name) then bad[#bad+1] = "group " .. g.key end
    for _, r in ipairs(g.rows) do if not NS.StandardText(r.label) then bad[#bad+1] = tostring(r.cvar) end
      if r.kind == "choice" and #NS.StandardOptions(r) == 0 then bad[#bad+1] = "options " .. r.cvar end end end
  return table.concat(bad, "; ") end)()""")
check(missing == "", "every Standard group and row has a label, every choice has options: " + missing)
check([S('NS.StandardText(NS.STANDARD[%d].name)' % i) for i in range(1, 5)] == ["Display", "Graphics Quality", "Advanced", "Compatibility Settings"], "Standard groups in the game's order")
luaS.execute('VIDEO_OPTIONS_MEDIUM = "Good (from the game)"')
check(S('NS.StandardOptions(NS.StandardRow("graphicsShadowQuality"))[3][2][1]') == "VIDEO_OPTIONS_MEDIUM" and S('NS.FormatStandard(NS.StandardRow("graphicsShadowQuality"), "2")') == "Good (from the game)", "option names come from the game's own strings")
# what presets and backups hold
saved = S('table.concat(NS.StandardCVars(), ",")').split(",")
check("ffxAntiAliasingMode" in saved and "graphicsShadowQuality" in saved and "RenderScale" in saved, "presets and backups hold the Standard settings that change the look")
check(not any(c in saved for c in ["gxapi", "gxAdapter", "gxMonitor", "gxMaximize", "useUiScale", "GxCompatOptionalGpuFeatures", "graphicsQuality"]), "never saved: PC setup, shown-only rows and the Base Game Quality slider")
check(not any(c in saved for c in ["maxFPS", "useMaxFPS", "targetFPS", "useTargetFPS", "maxFPSBk", "LowLatencyMode", "vsync", "gxMaxFrameLatency", "physicsLevel"]), "never saved: your own FPS limits, latency, vsync, buffering and physics, so an import can't reset them")
allm = S('table.concat(NS.AllManagedCVars(), ",")').split(",")
before = S('(function() local f = NS.StandardCVars; NS.StandardCVars = nil; local s = table.concat(NS.AllManagedCVars(), ","); NS.StandardCVars = f; return s end)()').split(",")
added = allm[len(before):]
check(allm[:len(before)] == before and "ffxAntiAliasingMode" in added and not any(c.lower() in set(b.lower() for b in before) for c in added) and len(added) == len(set(c.lower() for c in added)), "managed list adds the Standard settings it didn't already have, once each (%d)" % len(added))
# dropdown
radios = S('#MENU("graphicsShadowQuality")')
check(radios == 6, "Shadow Quality dropdown has the game's 6 levels (%s)" % radios)
luaS.execute('SUPPORTED_MAX.graphicsShadowQuality = 3; LAST = MENU("graphicsShadowQuality")')
check(S('LAST[4].enabled') == True and S('LAST[5].enabled') == False and S('LAST[6].enabled') == False, "levels this PC can't run are greyed out")
check(S('LAST[6].isSel()') == True, "the current level is ticked")
luaS.execute('wipe(EyeCandyDB.backups); LAST[2].setSel()')
check(S('GetCVar("graphicsShadowQuality")') == "1" and "Fair" in S('NS.FormatStandard(STDROW("graphicsShadowQuality").def, GetCVar("graphicsShadowQuality"))'), "picking a level sets it and shows it")
check(S('NS.OriginalBackup() ~= nil and NS.OriginalBackup().values.graphicsShadowQuality') == "5", "the first change backs up the old value")
check(S('STDROW("graphicsShadowQuality").dot.shown') == True and S('STDROW("graphicsProjectedTextures").dot.shown') == False, "dot on Standard settings changed from default")
cat = S('(function() for _, c in ipairs(NS.CATEGORIES) do for _, r in ipairs(c.cvars) do if r[1] == "graphicsSSAO" then return c.key end end end end)()')
luaS.execute('EyeCandyDB.tiers["%s"] = 3; MENU("graphicsSSAO")[2].setSel()' % cat)
check(S('EyeCandyDB.advanced.graphicsSSAO') == 1, "a Standard change to a tier's setting is kept as an override (tier %s)" % cat)
check(S('#MENU("graphicsParticleDensity")') == 5 and S('MENU("graphicsParticleDensity")[1].text') == "Low", "Particle Density uses the layout for PCs with secondary lighting")
check(S('#MENU("gxapi")') == 3 and S('MENU("gxapi")[1].isSel()') == True, "Graphics API lists auto plus the game's APIs, with auto ticked")
# toggle, slider, inverted slider, FPS box
luaS.execute('SetCVar("vsync", "0"); local r = STDROW("vsync"); r.check.scripts.OnClick(r.check)')
check(S('GetCVar("vsync")') == "1", "Vertical Sync checkbox sets it")
luaS.execute('EyeCandyDB.extras.renderScale = 1.25; local r = STDROW("RenderScale"); r.slider.scripts.OnValueChanged(r.slider, 1.5); RUNTIMERS()')
check(S('GetCVar("RenderScale")') == "1.5" and S('EyeCandyDB.extras.renderScale') == 1.5, "Render Scale slider sets it and keeps Eye Candy's own render scale in step")
luaS.execute('local r = STDROW("ResampleSharpness"); r.slider.scripts.OnValueChanged(r.slider, 1.5); RUNTIMERS()')
check(S('GetCVar("ResampleSharpness")') == "0.5", "Resample Sharpness bar runs like the game's: right is sharper (bar 1.5 = 0.5)")
luaS.execute('SetCVar("ResampleSharpness", "0.2"); STDROW("ResampleSharpness").slider:Refresh()')
check(abs(S('STDROW("ResampleSharpness").slider.current') - 1.8) < 1e-9, "the sharpness bar shows 0.2 at 1.8")
luaS.execute('local b = STDROW("maxFPS").checkBox; b.scripts.OnClick(b)')
check(S('GetCVar("useMaxFPS")') == "1", "Max Foreground FPS box turns the limit on")
check(S('NS.FormatStandard(NS.StandardRow("graphicsViewDistance"), "9")') == "10" and S('NS.FormatStandard(NS.StandardRow("maxFPS"), "120")') == "120 FPS", "values shown as the game does (View Distance 1 to 10, FPS)")
# Base Game Quality sets the rows below with the game's own values, rows first
luaS.execute('function GetGraphicsCVarValueForQualityLevel(cvar, level) return 0 end; SETLOG = {}; NS.SetStandard("graphicsQuality", 0)')
check(S('GetCVar("graphicsShadowQuality")') == "0" and S('GetCVar("graphicsParticleDensity")') == "1" and S('GetCVar("graphicsQuality")') == "0", "Base Game Quality sets each quality row (Particle Density stays at least 1, as the game does)")
check(S('SETLOG[#SETLOG]') == "graphicsQuality" and S('#SETLOG') > 5, "the rows are set before the master slider")
# info rows and the game's menu
check(S('STDROW("gxMaximize").valueText.text') == "Fullscreen (Windowed)" and S('NS.FormatStandard(NS.STANDARD[1].rows[3])') == "2560x1440", "Display Mode and Resolution show what the game is using")
check(S('STDROW("gxMaximize").control') is None and "game's Options menu" in S('NS.StandardTooltip(NS.StandardRow("gxMaximize"))'), "Monitor, Display Mode and Resolution are changed in the game's menu")
check("Not documented by Blizzard" in S('NS.StandardTooltip(NS.StandardRow("graphicsQuality"))') and "Game default: 6" in S('NS.StandardTooltip(NS.StandardRow("graphicsQuality"))'), "a tooltip without game text says so, and shows the default")
luaS.execute('SettingsPanel.shown = false; EyeCandyMainFrame.pages.standard.gameMenu.scripts.OnClick(EyeCandyMainFrame.pages.standard.gameMenu)')
check(S('SettingsPanel.shown') == True and S('EyeCandyMainFrame.shown') == False, "Open the game's menu button opens the game's Options and gets our window out of the way")
# A change made in the game's own menu is kept, not put back when the menu closes
luaS.execute('FIRE("PLAYER_ENTERING_WORLD", false, false); EyeCandyDB.keepApplied = true; EyeCandyDB.advanced.graphicsShadowQuality = 2; SetCVar("graphicsShadowQuality", "2")')
luaS.execute('SettingsPanel.hooks.OnShow(SettingsPanel); SetCVar("graphicsShadowQuality", "4"); SettingsPanel.hooks.OnHide(SettingsPanel); RUNTIMERS()')
check(S('GetCVar("graphicsShadowQuality")') == "4" and S('EyeCandyDB.advanced.graphicsShadowQuality') == 4, "a setting changed in the game's menu is kept as yours when it closes")
luaS.execute('SetCVar("graphicsShadowQuality", "1"); SettingsPanel.hooks.OnHide(SettingsPanel); RUNTIMERS()')
check(S('GetCVar("graphicsShadowQuality")') == "4", "a change made outside the game's menu is still put back (Keep my settings applied)")
luaS.execute('SlashCmdList.EYECANDY(""); NS.ShowTab("standard")')
# combat
luaS.execute('INCOMBAT = true')
check(S('(NS.SetStandard("vsync", "0"))') == False and S('GetCVar("vsync")') == "1", "Standard settings never change in combat")
luaS.execute('INCOMBAT = false')
# search covers the Standard tab
counts = luaS.eval('NS.SetSearch("shadow")')
check(counts["standard"] == 1 and S('STDROW("graphicsShadowQuality").shown') == True and S('STDROW("vsync").shown') == False, "search finds Standard settings (%s)" % counts["standard"])
luaS.execute('NS.SetSearch("")')

done()
