import lupa.lua51 as L, sys, os
base=os.path.dirname(os.path.abspath(__file__))+os.sep
addon=os.path.join(base,'..','EyeCandy')+os.sep
def boot(svdb=None, mirror=None):
    lua = L.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(open(base+'harness.lua', encoding='utf-8').read())
    lua.execute("""ALLFRAMES = {}; local cf = CreateFrame
      function CreateFrame(...) local f = cf(...); ALLFRAMES[#ALLFRAMES+1] = f; return f end
      function FIRE(ev, ...) for _, f in ipairs(ALLFRAMES) do if f.scripts.OnEvent then f.scripts.OnEvent(f, ev, ...) end end end
      function RUNTIMERS() local t = TIMERS; TIMERS = {}; for _, f in ipairs(t) do f() end end
      NS = {}
      -- EditBox text: GetText returns what SetText stored.
      local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
      mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end""")
    if svdb: lua.execute(svdb)
    if mirror: lua.execute('C_CVar.RegisterCVar("eyeCandyMirror", ""); C_CVar.SetCVar("eyeCandyMirror", %r)' % mirror)
    loader = lua.eval('function(src, name) local f, e = loadstring(src, name); if not f then error(e) end; return f end')
    # Load the files the game loads, in the .toc's order.
    toc = [l.strip() for l in open(addon+'EyeCandy.toc', encoding='utf-8') if l.strip() and not l.startswith('#')]
    for f in toc:
        loader(open(addon+f, encoding='utf-8').read(), f)('EyeCandy', lua.eval('NS'))
    lua.execute('FIRE("ADDON_LOADED", "EyeCandy")')
    return lua

def chat(lua):
    out = list(lua.eval('CHAT').values()); lua.execute('CHAT = {}'); return out

ok = True
def check(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg); ok = ok and cond

# 1. Fresh install, Cinematic everywhere via slash
lua = boot()
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
lua.execute('SlashCmdList.EYECANDY("preset cinematic")')
c = chat(lua); print("\n".join(c))
g = lambda n: lua.eval('GetCVar("%s")' % n)
check(g("RenderScale") == "1.5", "render scale 150%")
check(g("useTargetFPS") == "1", "target FPS left alone"); check(g("ResampleAlwaysSharpen") == "1", "always sharpen on at Cinematic"); check(g("vrsValar") == "0", "VRS disabled at Cinematic")
check(g("groundEffectDensity") == "256" and g("groundEffectDist") == "500", "grass 256 / 500")
check(g("farclip") == "10000", "farclip 10000")
check(g("graphicsParticleDensity") == "4", "particle density stepped down to supported max (4)")
check(any("not in this game" in x and "Horizon start" in x for x in c), "missing horizonStart reported, not set")
check(any("the game kept 2.6" in x for x in c), "zoom clamp reported")
check(lua.eval('NS.OriginalBackup() ~= nil and NS.OriginalBackup().values.groundEffectDensity') == "48", "backup holds pre-apply grass value")

# 2. Graphics menu overwrites grass, then Options closes -> hidden re-applied
lua.execute('SetCVar("groundEffectDensity", 48); SetCVar("graphicsShadowQuality", 2)')
lua.execute('SettingsPanel.hooks.OnHide(); RUNTIMERS()')
check(g("groundEffectDensity") == "256", "grass re-applied after Options closes")
check(g("graphicsShadowQuality") == "2", "menu choice (shadows) NOT overridden by re-apply")

# 3. Combat queueing
lua.execute('INCOMBAT = true; SetCVar("weatherDensity", 1); SlashCmdList.EYECANDY("apply")')
check(g("weatherDensity") == "1", "nothing applied during combat")
lua.execute('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(g("weatherDensity") == "3", "queued apply runs after combat")
chat(lua)

# 4. Export
lua.execute('SlashCmdList.EYECANDY("export")')
txt = lua.eval('EyeCandyExportFrame.text')
check("RTX 3090" in txt and "Experience preset: Enhanced" in txt and "Render scale range: 0.33 to 2" in txt, "export header (GPU, preset, render range)")
check("horizonStart" in txt and "(not in this game)" in txt, "export flags missing CVars")
check("--- Changed graphics CVars" in txt, "export includes changed-CVar scan")
print("---- export sample ----"); print("\n".join(txt.split("\n")[:22]))

# 5. UI window builds and refreshes
lua.execute('SlashCmdList.EYECANDY("")')
check(lua.eval('EyeCandyMainFrame.shown') == True, "main window opens")

# 6. Restore
lua.execute('SlashCmdList.EYECANDY("restore")')
check(g("RenderScale") == "1" and g("groundEffectDensity") == "48", "restore puts original values back")
check(lua.eval('next(EyeCandyDB.tiers)') is None, "tiers cleared after restore")

# 7. SavedVariables bug fallback: SV empty, mirror present
lua2 = boot(svdb=None, mirror="foliage=5,lighting=4;keep=1")
check(lua2.eval('EyeCandyDB.tiers.foliage') == 5 and lua2.eval('EyeCandyDB.tiers.lighting') == 4, "tiers recovered from CVar mirror")
lua2.execute('SetCVar("groundEffectDensity", 16); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(lua2.eval('GetCVar("groundEffectDensity")') == "256", "login re-applies hidden values from recovered tiers")


# 8. /ec find
lua3 = boot()
lua3.execute('local orig = ConsoleGetAllCommands; function ConsoleGetAllCommands() local t = orig(); for _, c in ipairs(t) do if c.command == "groundEffectDist" then c.help = "Ground effect view distance" end end; return t end')
lua3.execute('SlashCmdList.EYECANDY("find groundeffect")')
ft = lua3.eval('EyeCandyExportFrame.text')
print(ft)
check('groundEffectDist = 320 (default 100)  *changed' in ft and 'Ground effect view distance' in ft and '(no description)' in ft, "find shows value, default, help text")
lua3.execute('SlashCmdList.EYECANDY("find")')
check('Usage' in lua3.eval('EyeCandyExportFrame.text'), "find with no word shows usage")

# 9. Distant Detail row at Cinematic, and backup merge for an older Original
lua4 = boot(svdb='EyeCandyDB = { tiers = { clarity = 5 }, keepApplied = true, nextBackupId = 2, backups = { { id = 1, kind = "original", label = "Original settings", time = "old", stamp = 5, character = "", values = { RenderScale = "1" } } } }')
lua4.execute('SlashCmdList.EYECANDY("preset cinematic")')
g4 = lambda n: lua4.eval('GetCVar("%s")' % n)
check(g4("doodadLodScale") == "300" and g4("lodObjectCullSize") == "7" and g4("TerrainLodDiv") == "1024" and g4("dynamicLod") == "0" and g4("maxLightDist") == "2048", "Distant Detail Cinematic values applied, maxLightDist left alone")
check(lua4.eval('NS.OriginalBackup().values.doodadLodScale') == "150" and lua4.eval('NS.OriginalBackup().values.RenderScale') == "1" and lua4.eval('NS.OriginalBackup().time') == "old", "an older Original is kept, and new CVars are merged in with pre-apply values")
lua4.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SetCVar("terrainLodDist", 650); SettingsPanel.hooks.OnHide(); RUNTIMERS()')
check(g4("terrainLodDist") == "1000", "terrain LOD re-applied after Options closes")
lua4.execute('SlashCmdList.EYECANDY("restore")')
check(g4("doodadLodScale") == "150" and g4("maxLightDist") == "2048", "restore reverts Distant Detail")

# 10. Extras
lua5 = boot()
lua5.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
lua5.execute('EyeCandyDB.tiers.clarity = 5; EyeCandyDB.extras.renderScale = 2; EyeCandyDB.extras.resample = 2; EyeCandyDB.extras.entityLod = 20; SETLOG = {}')
lua5.execute('SlashCmdList.EYECANDY("apply")')
c5 = chat(lua5); print("\n".join(c5))
g5 = lambda n: lua5.eval('GetCVar("%s")' % n)
check(g5("RenderScale") == "2", "render scale override 200% wins over Cinematic 150%")
rs_sets = [x for x in lua5.eval('SETLOG').values() if x == "RenderScale"]
check(len(rs_sets) == 1, "RenderScale set once, not twice (%d)" % len(rs_sets))
check(g5("ResampleQuality") == "2", "resample set to Bicubic")
check(g5("entityLodDist") == "20", "character detail set to 20")
lua5.execute('SetCVar("entityLodDist", 10); SettingsPanel.hooks.OnHide(); RUNTIMERS()')
check(g5("entityLodDist") == "20", "character detail re-applied after Options closes")
check(lua5.eval('NS.OriginalBackup().values.ResampleQuality') == "3" and lua5.eval('NS.OriginalBackup().values.entityLodDist') == "10", "extras backed up with pre-change values")
lua5.execute('SlashCmdList.EYECANDY("export")')
t5 = lua5.eval('EyeCandyExportFrame.text')
check("--- Eye Candy extras ---" in t5 and "Bicubic" in t5 and "200%" in t5 and "Higher (20)" in t5, "export lists extras")
lua5.execute('SlashCmdList.EYECANDY("")')
check(lua5.eval('EyeCandyMainFrame.shown') == True, "main window builds with extras section")
lua5.execute('EyeCandyDB.extras.renderScale = nil; SlashCmdList.EYECANDY("apply")')
check(g5("RenderScale") == "1.5", "'Use tier' hands render scale back to the Clarity tier")
# mirror round trip with extras
lua5.execute('NS.SaveMirror()')
mirror = lua5.eval('GetCVar("eyeCandyMirror")')
print("mirror:", mirror)
lua6 = boot(mirror=mirror)
check(lua6.eval('EyeCandyDB.extras.resample') == 2 and lua6.eval('EyeCandyDB.extras.entityLod') == 20 and lua6.eval('EyeCandyDB.tiers.clarity') == 5, "extras and tiers recovered from new mirror format")
lua5.execute('SlashCmdList.EYECANDY("restore")')
check(g5("ResampleQuality") == "3" and g5("entityLodDist") == "10" and lua5.eval('next(EyeCandyDB.extras)') is None, "restore reverts extras and clears them")
lua5.execute('SlashCmdList.EYECANDY("preset ultra")')
check(lua5.eval('next(EyeCandyDB.extras)') is None, "presets never touch extras")

# 11. Backup fix for a tester's case: backup captured hand-tested LOD values
lua7 = boot(svdb='EyeCandyDB = { tiers = { distant = 5 }, keepApplied = true, nextBackupId = 2, backups = { { id = 1, kind = "original", label = "Original settings", time = "x", stamp = 5, character = "", values = { RenderScale = "1.5", doodadLodScale = "300", lodObjectFadeScale = "300", lodObjectCullSize = "7", terrainLodDist = "1000", TerrainLodDiv = "1024", wmoLodDist = "800", dynamicLod = "0", maxLightDist = "4096" } } } }')
bv = lambda n: lua7.eval('NS.OriginalBackup().values.%s' % n)
check([bv(k) for k in ["doodadLodScale","lodObjectFadeScale","lodObjectCullSize","terrainLodDist","TerrainLodDiv","wmoLodDist","dynamicLod"]] == ["150","150","14","650","768","400","1"], "backup corrected to Graphics-menu values")
check(bv("RenderScale") == "1.5", "unrelated backup values untouched")
check(any("corrected your Restore backup" in x for x in chat(lua7)), "user told about the correction")
lua8 = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true, nextBackupId = 2, backups = { { id = 1, kind = "original", label = "Original settings", time = "x", stamp = 5, character = "", values = { doodadLodScale = "150" } } } }')
check(not any("corrected" in x for x in chat(lua8)), "no message when the backup is already fine")

# 12. Showcase
lua9 = boot()
lua9.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("")')
lua9.execute('SlashCmdList.EYECANDY("showcase")')
c9 = chat(lua9); print("\n".join(c9))
g9 = lambda n: lua9.eval('GetCVar("%s")' % n)
check(all(lua9.eval('EyeCandyDB.tiers.%s' % k) == 5 for k in ["clarity","lighting","atmosphere","water","textures","world","distant","foliage","effects"]), "showcase sets every row to Cinematic")
check(g9("RenderScale") == "2" and g9("ResampleQuality") == "2" and g9("entityLodDist") == "20", "showcase extras applied (200%, Bicubic, 20)")
check(g9("doodadLodScale") == "500" and g9("vrsValar") == "0" and g9("groundEffectDensity") == "256", "showcase tier values applied")
check(any("Render scale changed" in x for x in c9), "showcase warns about FPS after a render scale change")
lua9.execute('SlashCmdList.EYECANDY("restore")')
check(g9("RenderScale") == "1" and g9("ResampleQuality") == "3" and g9("entityLodDist") == "10", "restore undoes showcase")

# 13. Sharpness extra
lua10 = boot()
lua10.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
lua10.execute('EyeCandyDB.extras.sharpness = 0.6; SlashCmdList.EYECANDY("apply")')
check(lua10.eval('GetCVar("ResampleSharpness")') == "0.6", "sharpness set to 0.6")
lua10.execute('EyeCandyDB.extras.sharpness = 0; SlashCmdList.EYECANDY("apply")')
check(lua10.eval('GetCVar("ResampleSharpness")') == "0", "sharpness 0 applied (0 is not treated as unset)")
lua10.execute('EyeCandyDB.extras.sharpness = 0.4; NS.SaveMirror()')
m = lua10.eval('GetCVar("eyeCandyMirror")'); print("mirror:", m)
lua11 = boot(mirror=m)
check(abs(lua11.eval('EyeCandyDB.extras.sharpness') - 0.4) < 1e-9, "decimal sharpness survives mirror round trip")
lua10.execute('SlashCmdList.EYECANDY("export")')
check("Sharpness" in lua10.eval('EyeCandyExportFrame.text') and "0.4" in lua10.eval('EyeCandyExportFrame.text'), "export lists sharpness")
lua10.execute('SlashCmdList.EYECANDY("showcase")')
check(abs(lua10.eval('EyeCandyDB.extras.sharpness') - 0.4) < 1e-9, "showcase leaves your sharpness choice alone")
lua10.execute('SlashCmdList.EYECANDY("restore")')
check(lua10.eval('GetCVar("ResampleSharpness")') == "0.2", "restore puts sharpness back to 0.2")

# 14. Advanced dials
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
function DRAG(cvar, v) local r = FINDROW(cvar); r.slider.scripts.OnValueChanged(r.slider, v) end
"""
# data sanity
luaD = boot()
bad = luaD.eval("""function()
  local bad, seen, extra = {}, {}, {}
  for _, ex in ipairs(NS.EXTRAS) do extra[ex.cvar] = true end
  for _, g in ipairs(NS.ADVANCED) do for _, d in ipairs(g.rows) do
    if seen[d[1]] then bad[#bad+1] = "dup " .. d[1] end
    seen[d[1]] = true
    if extra[d[1]] then bad[#bad+1] = "extra clash " .. d[1] end
    if d.kind == "choice" then
      for i = 2, #d.values do if d.values[i] <= d.values[i-1] then bad[#bad+1] = "choice order " .. d[1] end end
    elseif d.kind ~= "toggle" then
      if not (d[3] < d[4] and d[5] > 0) then bad[#bad+1] = "range " .. d[1] end
      local n = (d[4] - d[3]) / d[5]
      if math.abs(n - math.floor(n + 0.5)) > 1e-6 then bad[#bad+1] = "step " .. d[1] end
    end
    if not d.note then bad[#bad+1] = "note " .. d[1] end
  end end
  return table.concat(bad, "; ")
end""")()
check(bad == "", "advanced data sane (no dupes, clean ranges, notes): " + bad)
print("advanced dials:", luaD.eval('#NS.AdvancedCVars()'))

luaA = boot(svdb='EyeCandyDB = { tiers = { foliage = 5 }, extras = {}, keepApplied = true }')
luaA.execute(ADV)
luaA.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("apply"); CHAT = {}')
gA = lambda n: luaA.eval('GetCVar("%s")' % n)
check(gA("groundEffectDensity") == "256", "tier sets grass 256 before override")
luaA.execute('SlashCmdList.EYECANDY("adv")')
check(luaA.eval('EyeCandyMainFrame.shown') == True and luaA.eval('EyeCandyMainFrame.tab') == "hidden" and luaA.eval('#NS.advRows') == luaA.eval('#NS.AdvancedCVars()'), "/ec adv opens the Hidden tab with a row per dial")
check("not in client" in luaA.eval('FINDROW("horizonStart").status.text'), "missing CVar shown as not in client")
check("level" in luaA.eval('FINDROW("groundEffectDensity").status.text'), "level-managed dial labelled level")
# drag + snap + debounce
luaA.execute('SETLOG = {}; DRAG("groundEffectDensity", 120); DRAG("groundEffectDensity", 131.7)')
check(gA("groundEffectDensity") == "256", "nothing applied mid-drag (debounced)")
luaA.execute('RUNTIMERS()')
gsets = [x for x in luaA.eval('SETLOG').values() if x == "groundEffectDensity"]
check(gA("groundEffectDensity") == "132" and len(gsets) == 1, "drag settles: snapped to 132 (step 1), set once (%d)" % len(gsets))
check(luaA.eval('EyeCandyDB.advanced.groundEffectDensity') == 132 and "custom" in luaA.eval('FINDROW("groundEffectDensity").status.text'), "override saved and labelled custom")
# override beats tier, survives Options close
luaA.execute('SlashCmdList.EYECANDY("apply")')
check(gA("groundEffectDensity") == "132", "Apply keeps the override over the Cinematic tier")
luaA.execute('SetCVar("groundEffectDensity", 48); SettingsPanel.hooks.OnHide(); RUNTIMERS()')
check(gA("groundEffectDensity") == "132", "override re-applied after Options closes")
# float snapping
luaA.execute('DRAG("assaoSharpness", 0.333); DRAG("assaoShadowPower", 1.351); RUNTIMERS()')
check(gA("assaoSharpness") == "0.335" and gA("assaoShadowPower") == "1.35", "decimal dials snap cleanly to steps 0.005 and 0.01 (%s, %s)" % (gA("assaoSharpness"), gA("assaoShadowPower")))
check(luaA.eval('NS.OriginalBackup().values.assaoSharpness') == ".98", "backup kept the pre-change ASSAO value")
# toggle
luaA.execute('local r = FINDROW("animFrameSkipLOD"); r.check.scripts.OnClick(r.check)')
check(gA("animFrameSkipLOD") == "1" and luaA.eval('EyeCandyDB.advanced.animFrameSkipLOD') == 1, "toggle commits immediately")
# reset: tier-managed -> tier value; plain -> value from before Eye Candy
luaA.execute('NS.ResetAdvanced("groundEffectDensity"); NS.ResetAdvanced("assaoSharpness")')
check(gA("groundEffectDensity") == "256" and luaA.eval('EyeCandyDB.advanced.groundEffectDensity') is None, "Reset hands grass back to the tier (256)")
check(abs(float(gA("assaoSharpness")) - 0.98) < 1e-9, "Reset puts a non-tier dial back to its value from before Eye Candy")
# combat
luaA.execute('INCOMBAT = true; DRAG("assaoRadius", 3); RUNTIMERS(); INCOMBAT = false')
check(gA("assaoRadius") == "1.85" and luaA.eval('EyeCandyDB.advanced.assaoRadius') is None, "no changes in combat")
# export
luaA.execute('SlashCmdList.EYECANDY("export")')
tA = luaA.eval('EyeCandyExportFrame.text')
check("--- Eye Candy advanced overrides ---" in tA and "assaoShadowPower" in tA and "1.35" in tA, "export lists advanced overrides")
# main window still builds with the Advanced button
luaA.execute('SlashCmdList.EYECANDY("")')
check(luaA.eval('EyeCandyMainFrame.shown') == False, "/ec closes the open window")
luaA.execute('SlashCmdList.EYECANDY("")')
check(luaA.eval('EyeCandyMainFrame.shown') == True and luaA.eval('EyeCandyMainFrame.tab') == "presets", "/ec opens it again on Presets")
# restore
luaA.execute('SlashCmdList.EYECANDY("restore")')
check(luaA.eval('next(EyeCandyDB.advanced)') is None and gA("assaoShadowPower") == "1.34" and gA("animFrameSkipLOD") == "0", "restore clears dials and reverts them")
# login re-apply from SavedVariables
luaB = boot(svdb='EyeCandyDB = { tiers = {}, extras = {}, advanced = { assaoRadius = 2.5, dynamicLod = 0 }, keepApplied = true }')
luaB.execute(ADV)
luaB.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(luaB.eval('GetCVar("assaoRadius")') == "2.5" and luaB.eval('GetCVar("dynamicLod")') == "0", "dials re-applied at login")
# old SavedVariables without an advanced table
luaC = boot(svdb='EyeCandyDB = { tiers = { clarity = 5 }, keepApplied = true }')
check(luaC.eval('type(EyeCandyDB.advanced)') == "table", "older saved data upgraded with an advanced table")

# 15. Extras-only and dials-only users also get re-applied after Options closes
luaE = boot(svdb='EyeCandyDB = { tiers = {}, extras = { entityLod = 20 }, advanced = {}, keepApplied = true }')
luaE.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(luaE.eval('GetCVar("entityLodDist")') == "20", "extras-only setup re-applied at login")

# 16. Presets drive the Advanced dials
luaP = boot()
bad = luaP.eval("""function()
  local bad = {}
  for _, g in ipairs(NS.ADVANCED) do for _, d in ipairs(g.rows) do
    if d.p then for i = 1, 6 do local v = d.p[i]
      if v ~= nil then
        if d.kind == "toggle" then if v ~= 0 and v ~= 1 then bad[#bad+1] = d[1] .. " toggle " .. i end
        elseif d.kind == "choice" then if NS.SnapAdvanced(d, v) ~= v then bad[#bad+1] = d[1] .. " not a choice at " .. i end
        else
          if v < d[3] or v > d[4] then bad[#bad+1] = d[1] .. " out of range at " .. i end
          if NS.SnapAdvanced(d, v) ~= v then bad[#bad+1] = d[1] .. " off-step at " .. i end
        end
      end
    end end
  end end
  return table.concat(bad, "; ")
end""")()
check(bad == "", "preset values in range and on-step: " + bad)

# A tester's maxed-out dials (from an export), then Cinematic
MAXED = "EyeCandyDB = { tiers = { clarity=5, lighting=5, atmosphere=5, water=5, textures=5, world=5, distant=5, foliage=5, effects=5 }, extras = { renderScale = 2, resample = 2, entityLod = 20 }, keepApplied = true, advanced = { animFrameSkipLOD=1, assaoAdaptiveQualityLimit=1, assaoBlurPassCount=6, assaoDetailShadowStrength=5, assaoFadeOutFrom=500, assaoFadeOutTo=1000, assaoHorizonAngleThresh=1, assaoRadius=4, assaoShadowMult=2.5, assaoShadowPower=3, assaoSharpness=1, cameraDistanceMaxZoomFactor=4, CMAA2ExtraSharpness=1, doodadLodScale=500, entityLodOffset=50, entityShadowFadeScale=200, groundEffectFade=500, lodObjectCullDist=100, lodObjectCullSize=30, lodObjectFadeScale=500, lodObjectMinSize=40, lodObjectSizeScale=3, preloadStreamingDistObject=256, preloadStreamingDistTerrain=1024, terrainLodDist=1500, TerrainLodDiv=2048, wmoDoodadDist=5000, wmoLodDist=1500, wmoLodDistScale=3 }, nextBackupId = 2, backups = { { id = 1, kind = 'original', label = 'Original settings', time = 'x', stamp = 5, character = '', values = { assaoRadius='1.85', assaoShadowMult='1.1', assaoShadowPower='1.34', assaoSharpness='.98', assaoBlurPassCount='2', assaoDetailShadowStrength='0', assaoHorizonAngleThresh='0.4', assaoAdaptiveQualityLimit='.45', entityLodOffset='10', lodObjectMinSize='20', animFrameSkipLOD='0', groundEffectFade='370', doodadLodScale='150', lodObjectFadeScale='150', lodObjectCullSize='14', terrainLodDist='650', TerrainLodDiv='768', wmoLodDist='400' } } } }"
luaD2 = boot(svdb=MAXED)
luaD2.execute(ADV)
luaD2.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
g = lambda n: luaD2.eval('GetCVar("%s")' % n)
num = lambda n: float(g(n))
check(g("lodObjectCullSize") == "30" and g("assaoRadius") == "4", "maxed dials active before the preset")
luaD2.execute('SlashCmdList.EYECANDY("preset cinematic")')
check(g("lodObjectCullSize") == "7", "Cinematic: cull size back to the tier's 7")
check(g("animFrameSkipLOD") == "0", "Cinematic: animation frame skipping off")
check(abs(num("assaoRadius") - 1.85) < 1e-9 and abs(num("assaoShadowPower") - 1.34) < 1e-9 and abs(num("assaoHorizonAngleThresh") - 0.4) < 1e-9, "Cinematic: AO shape dials back to value from before Eye Candys")
check(g("assaoFadeOutFrom") == "100" and g("assaoFadeOutTo") == "500", "Cinematic: AO fade 100 to 500")
check(g("entityLodOffset") == "10", "Cinematic: unknown-direction dials handed back")
check(g("lodObjectMinSize") == "5" and g("assaoAdaptiveQualityLimit") == "0.7", "Cinematic: min size 5, AO adaptive quality 0.7")
check(abs(float(g("assaoDetailShadowStrength")) - 0) < 1e-9, "Cinematic: AO fine detail back to default")
check(g("groundEffectFade") == "370" and g("doodadLodScale") == "300" and g("terrainLodDist") == "1000", "Cinematic: tier-managed dials back to tier values")
check(g("wmoDoodadDist") == "4000" and g("lodObjectSizeScale") == "2" and g("wmoLodDistScale") == "2" and g("entityShadowFadeScale") == "150", "Cinematic: dial values applied")
check(g("preloadStreamingDistObject") == "128" and g("preloadStreamingDistTerrain") == "512" and g("CMAA2ExtraSharpness") == "1", "Cinematic: streaming and CMAA values")
check(g("RenderScale") == "2" and g("entityLodDist") == "20", "Cinematic preset leaves Extras alone")
keys = sorted(luaD2.eval('EyeCandyDB.advanced').keys())
check("assaoRadius" not in keys and "lodObjectCullSize" not in keys and "doodadLodScale" not in keys, "only preset-defined dials remain as overrides")

luaD2.execute('SlashCmdList.EYECANDY("showcase")')
check(g("doodadLodScale") == "500" and g("TerrainLodDiv") == "1024" and g("wmoLodDist") == "1500" and g("terrainLodDist") == "1500", "Showcase: furthest LOD values, terrain divisor at documented max 1024")
check(g("wmoDoodadDist") == "5000" and g("lodObjectSizeScale") == "3" and g("lodObjectCullDist") == "100" and g("assaoFadeOutTo") == "800", "Showcase: dial values applied")
check(g("lodObjectCullSize") == "5" and g("lodObjectMinSize") == "1" and g("groundEffectFade") == "370", "Showcase: cull size 5, min size 1, grass fade from tier")
check(g("assaoAdaptiveQualityLimit") == "1" and g("assaoDetailShadowStrength") == "0.5", "Showcase: AO adaptive quality 1, fine detail 0.5")

luaD2.execute('SlashCmdList.EYECANDY("preset performance")')
check(g("animFrameSkipLOD") == "1" and g("wmoDoodadDist") == "1000" and g("lodObjectSizeScale") == "0.8" and g("entityShadowFadeScale") == "30", "Performance: lighter dial values")
check(g("doodadLodScale") == "150" and g("TerrainLodDiv") == "768", "Performance: Showcase LOD maxes handed back to value from before Eye Candys")

luaD2.execute('INCOMBAT = true; SlashCmdList.EYECANDY("preset ultra")')
check(luaD2.eval('EyeCandyDB.tiers.clarity') == 1, "no preset changes in combat")
luaD2.execute('INCOMBAT = false')

# 17. Research-driven changes
luaR = boot()
luaR.execute(ADV)
luaR.execute('C_CVar.RegisterCVar("TerrainLodDiv", "768"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("adv")')
gR = lambda n: luaR.eval('GetCVar("%s")' % n)
luaR.execute('DRAG("TerrainLodDiv", 4.4); RUNTIMERS()')
check(gR("TerrainLodDiv") == "1024", "terrain divisor slider picks from the choice list (position 4 = 1024)")
luaR.execute('DRAG("TerrainLodDiv", 5); RUNTIMERS()')
check(gR("TerrainLodDiv") == "2048", "terrain divisor last position = 2048")
check(luaR.eval('FINDROW("TerrainLodDiv").valueText.text') == "2048", "choice dial shows the real value, not the position")
luaR.execute('NS.ResetAdvanced("TerrainLodDiv")')
check(gR("TerrainLodDiv") == "768", "terrain divisor Reset back to default")
luaR.execute('DRAG("SkyCloudLOD", 3); RUNTIMERS()')
check(gR("SkyCloudLOD") == "1", "cloud smoothing capped at 1 (2 and 3 would disable it)")
luaR.execute('DRAG("farclip", 19600); RUNTIMERS()')
check(gR("farclip") == "19600", "far clip slider reaches 19600")
luaR.execute('DRAG("groundEffectFade", 510); RUNTIMERS()')
check(gR("groundEffectFade") == "510", "grass fade can go past max distance (no-fade setting)")
opts = luaR.eval('(function() for _, ex in ipairs(NS.EXTRAS) do if ex.key == "entityLod" then local t = {} for _, o in ipairs(ex.options) do t[#t+1] = tostring(o[1]) end return table.concat(t, ",") end end end)()')
check(opts == "nil,5,10,20,50,100", "character detail offers 50 and 100 (%s)" % opts)
tip = luaR.eval('(function() local r = FINDROW("TerrainLodDiv"); return r.scripts.OnEnter and "ok" or "none" end)()')
check(tip == "ok", "choice dial has a tooltip")

# 18. Lower presets don't keep higher presets' hidden values
luaL = boot()
luaL.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
gL = lambda n: luaL.eval('GetCVar("%s")' % n)
before = {k: gL(k) for k in ["farclip", "groundEffectDensity", "TerrainLodDiv", "dynamicLod", "doodadLodScale"]}
luaL.execute('SlashCmdList.EYECANDY("preset cinematic")')
check(gL("farclip") == "10000" and gL("TerrainLodDiv") == "1024" and gL("dynamicLod") == "0", "Cinematic hidden values set")
luaL.execute('SlashCmdList.EYECANDY("preset performance")')
check(all(gL(k) == v for k, v in before.items() if k != "groundEffectDensity"), "Performance puts Cinematic-only hidden values back: %s" % {k: gL(k) for k in before})
luaL.execute('SetCVar("graphicsShadowQuality", 2); SlashCmdList.EYECANDY("preset performance")')
check(gL("graphicsShadowQuality") == "1", "menu settings still follow the tier (not the backup)")

# 19. Looks
luaK = boot()
bad = luaK.eval("""function()
  local bad = {}
  for _, look in ipairs(NS.LOOKS) do
    if look.base ~= 5 and look.base ~= 6 then bad[#bad+1] = look.key .. " base" end
    for cvar, v in pairs(look.dials) do
      local d = NS.ADVANCED_BY_CVAR[cvar]
      if not d then bad[#bad+1] = look.key .. " unknown dial " .. cvar
      elseif d.kind == "toggle" then if v ~= 0 and v ~= 1 then bad[#bad+1] = look.key .. " toggle " .. cvar end
      elseif d.kind ~= "choice" then
        if v < d[3] or v > d[4] then bad[#bad+1] = look.key .. " range " .. cvar end
        if NS.SnapAdvanced(d, v) ~= v then bad[#bad+1] = look.key .. " off-step " .. cvar end
      end
    end
    for key, v in pairs(look.extras) do
      local found = false
      for _, ex in ipairs(NS.EXTRAS) do if ex.key == key then for _, o in ipairs(ex.options) do if o[1] == v then found = true end end end end
      if not found then bad[#bad+1] = look.key .. " extra " .. key .. "=" .. tostring(v) end
    end
  end
  return table.concat(bad, "; ")
end""")()
check(bad == "", "every Look value is a valid dial/extra option: " + bad)
print("looks:", luaK.eval('#NS.LOOKS'))

luaK = boot(svdb=MAXED)
luaK.execute(ADV)
luaK.execute('C_CVar.RegisterCVar("TerrainLodDiv", "768"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("showcase"); CHAT = {}')
g = lambda n: luaK.eval('GetCVar("%s")' % n)
luaK.execute('SlashCmdList.EYECANDY("look beautiful")')
c = chat(luaK); print("\n".join(c[-2:]))
check(g("RenderScale") == "1.5" and g("ResampleSharpness") == "0.5" and g("ResampleQuality") == "2", "Beautiful: 150%, sharpness 0.5, Bicubic")
check(g("groundEffectDensity") == "160" and g("groundEffectDist") == "400" and g("groundEffectFade") == "300", "Beautiful: grass 160 / 400 / fade 300")
check(g("Contrast") == "55" and g("bloomUserMult") == "0.6" and g("cameraFov") == "80" and g("graphicsDepthEffects") == "3", "Beautiful: contrast 55, bloom 0.6, FOV 80, depth of field on")
check(g("doodadLodScale") == "500" and g("lodObjectCullSize") == "5" and g("assaoAdaptiveQualityLimit") == "1", "Beautiful keeps Showcase's LOD and AO quality")
check(g("assaoRadius") == "1.6" and g("assaoDetailShadowStrength") == "0.3", "Beautiful: natural AO")
check(luaK.eval('EyeCandyDB.look') == "beautiful", "current look saved")
luaK.execute('SetCVar("groundEffectDensity", 48); SettingsPanel.hooks.OnHide(); RUNTIMERS()')
check(g("groundEffectDensity") == "160", "Look's grass survives closing Options")
luaK.execute('SlashCmdList.EYECANDY("export")')
check("Look: Beautiful" in luaK.eval('EyeCandyExportFrame.text'), "export shows the Look")

luaK.execute('SlashCmdList.EYECANDY("look crisp")')
check(g("graphicsDepthEffects") == "0" and g("ResampleSharpness") == "0" and g("RenderScale") == "2" and g("cameraFov") == "90", "Crisp: no depth of field, sharpest, 200%, FOV 90")
luaK.execute('SlashCmdList.EYECANDY("apply")')
check(g("graphicsDepthEffects") == "0", "Crisp's depth-of-field override beats the Lighting tier on Apply")
luaK.execute('SlashCmdList.EYECANDY("look moody")')
check(g("Contrast") == "62" and g("Gamma") == "0.9" and g("cameraFov") == "75" and g("RenderScale") == "1.5", "Moody: contrast 62, gamma 0.9, FOV 75, 150%")
luaK.execute('SlashCmdList.EYECANDY("look classic")')
check(g("bloomUserMult") == "0.2" and g("groundEffectDensity") == "64" and g("entityLodDist") == "10" and g("graphicsDepthEffects") == "0", "Classic: low bloom, sparse grass, default character LOD, no DoF")
check(g("doodadLodScale") == "300", "Classic is built on Cinematic, not Showcase")
luaK.execute('SlashCmdList.EYECANDY("look painterly")')
check(g("ResampleSharpness") == "1" and g("groundEffectDensity") == "128" and g("assaoShadowMult") == "0.8", "Painterly: soft, sparse grass, light AO")

luaK.execute('SlashCmdList.EYECANDY("preset cinematic")')
check(luaK.eval('EyeCandyDB.look') is None, "picking a preset clears the Look")
check(g("Contrast") == "57" and g("cameraFov") == "90" and g("bloomUserMult") == "1" and g("groundEffectDensity") == "256", "preset hands colour/FOV back to your own values and grass to the tier")
luaK.execute('SlashCmdList.EYECANDY("look nonsense")')
check(any("unknown look" in x for x in chat(luaK)), "unknown look name handled")
luaK.execute('SlashCmdList.EYECANDY("look moody"); SlashCmdList.EYECANDY("restore")')
check(luaK.eval('EyeCandyDB.look') is None and g("Contrast") == "57" and g("cameraFov") == "90", "Restore clears the Look and colour settings")
luaK.execute('SlashCmdList.EYECANDY("")')
check(luaK.eval('EyeCandyMainFrame.shown') == True, "main window builds with the Looks row")
luaK.execute('INCOMBAT = true; SlashCmdList.EYECANDY("look crisp"); INCOMBAT = false')
check(luaK.eval('EyeCandyDB.look') is None, "no Look changes in combat")
# Slash commands, numbered with no gap (the game stops reading at the first missing number)
luaR3 = boot()
check(luaR3.eval('SLASH_EYECANDY1') == "/ec" and luaR3.eval('SLASH_EYECANDY2') == "/graphics" and luaR3.eval('SLASH_EYECANDY3') == "/eyecandy" and luaR3.eval('SLASH_EYECANDY4') is None, "slash commands /ec, /graphics and the spare /eyecandy, with no gap")
luaR3.execute('SlashCmdList.EYECANDY("")')
check(luaR3.eval('EyeCandyMainFrame.shown') == True and "Eye Candy" in luaR3.eval('EyeCandyMainFrame.titleText.text'), "main window opens under the new name")

print("\nALL PASS" if ok else "\nSOME FAILED")
