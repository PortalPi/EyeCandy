"""Presets (1.0.0 step 3): built-ins, your presets, share strings, import safety.

Run alone: python tests/test_presets.py
"""
from lib import boot, chat, check, done

# The Advanced dials' CVars, registered so they exist in the stub client (same list as run.py).
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
"""


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)] if t is not None else []


luaS = boot()
luaS.execute(ADV)
luaS.execute('C_CVar.RegisterCVar("autoLootDefault", "0"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
# Import only saves a preset; these apply it after, to test what the preset holds.
luaS.execute('function IMPORT_APPLY(s, mode) local p, e = NS.ImportPreset(s, mode); if p then NS.ApplyPresetById(p.id) end; return p, e end')
gS = lambda n: luaS.eval('GetCVar("%s")' % n)
ev = lambda s: luaS.eval(s)

# built-ins
builtin = lst(ev('NS.ListPresets().builtin'))
check([p['id'] for p in builtin] == ["tier1", "tier2", "tier3", "tier4", "tier5", "tier6", "look:beautiful", "look:painterly", "look:crisp", "look:moody", "look:classic", "look:raid", "look:laptop", "look:screenshot", "look:city"], "built-ins: 6 tiers, 5 Looks, then the 4 Situations")
check(all(p['builtin'] == True and p['desc'] for p in builtin) and builtin[5]['name'] == "Showcase" and builtin[0]['group'] == "Tiers" and builtin[9]['group'] == "Looks" and builtin[9]['name'] == "Moody", "built-ins named, grouped, described, read-only")
check(len(lst(ev('NS.ListPresets().user'))) == 0, "no user presets on a fresh install")
check(ev('NS.ApplyPresetById("tier5")') == True and gS("farclip") == "10000" and ev('EyeCandyDB.tiers.clarity') == 5, "applying the Cinematic built-in sets Cinematic")
check(ev('NS.ApplyPresetById("look:moody")') == True and gS("Contrast") == "62" and ev('EyeCandyDB.look') == "moody", "applying a Look built-in sets the Look")
check(ev('NS.ApplyPresetById("nope")') in (None, False), "unknown preset id refused")

# save current
p = ev('NS.SaveCurrentAsPreset("  My Raid  ")')
check(p is not None and p['name'] == "My Raid" and p['builtin'] == False and p['group'] == "Yours", "save current settings as a named preset (name trimmed)")
pid = p['id']
check(p['values']['Contrast'] == "62" and p['values']['farclip'] == "10000" and p['values']['autoLootDefault'] is None, "saved preset holds managed settings only")
r = ev('{NS.SaveCurrentAsPreset("my raid")}')
check(r[1] is None and "already" in r[2], "saving a second preset with the same name is refused: %s" % r[2])
r = ev('{NS.SaveCurrentAsPreset("Moody")}')
check(r[1] is None and "built-in" in r[2], "a built-in's name is refused: %s" % r[2])
check(ev('{NS.SaveCurrentAsPreset("  ")}')[1] is None, "an empty name is refused")
check(ev('{NS.SaveCurrentAsPreset("\\200\\200\\255")}')[1] is None, "a name of broken UTF-8 bytes is refused (review finding 9)")
check(ev('NS.SaveCurrentAsPreset("Caf\\195\\169\\200!").name') == "Café!", "stray bytes dropped, real accented letters kept")
check(ev('NS.SaveCurrentAsPreset("|cffff0000Red|r " .. string.rep("x", 60))')['name'] == "Red " + "x" * 36, "colour codes stripped, name capped at 40 characters")

# rename, duplicate, delete
check(ev('NS.RenamePreset("%s", "Raid night")' % pid) == True and ev('NS.FindPreset("%s").name' % pid) == "Raid night", "rename a preset")
r = ev('{NS.RenamePreset("%s", "Moody")}' % pid)
check(r[1] in (None, False) and ev('NS.FindPreset("%s").name' % pid) == "Raid night", "rename to a built-in's name refused")
r = ev('{NS.RenamePreset("tier1", "Fast")}')
check(r[1] in (None, False) and ev('NS.FindPreset("tier1").name') == "Performance", "built-ins can't be renamed")
d = ev('NS.DuplicatePreset("%s")' % pid)
check(d['name'] == "Raid night (2)" and d['id'] != pid and d['values']['farclip'] == "10000", "duplicate a preset as 'Raid night (2)'")
dm = ev('NS.DuplicatePreset("look:moody")')
check(dm['name'] == "Moody (2)" and dm['builtin'] == False and dm['values']['Contrast'] == "62" and dm['values']['cameraFov'] == "75", "duplicating a built-in makes an editable copy with its values")
dp = ev('NS.DuplicatePreset("tier1")')
check(dp['values']['farclip'] == "7000" and dp['values']['TerrainLodDiv'] == "768" and dp['values']['cameraFov'] == "90" and dp['values']['Contrast'] == "57",
      "a copy of Performance made on Moody hands Cinematic-only and Look values back to yours, as applying it would (review finding 4)")
r = ev('{NS.DeletePreset("tier5")}')
check(r[1] in (None, False) and ev('NS.FindPreset("tier5")') is not None, "built-ins can't be deleted")
check(ev('NS.DeletePreset("%s")' % d['id']) == True and ev('NS.FindPreset("%s")' % d['id']) is None, "delete your own preset")
luaS.execute('NS.DeletePreset("%s")' % dp['id'])
# a preset's note (Autotune's says where it was tested) goes with a copy; a built-in's never does
luaS.execute('NS.FindPreset("%s").desc = "Tested in Stormwind City."' % pid)
dd = ev('NS.DuplicatePreset("%s")' % pid)
check(dd['desc'] == "Tested in Stormwind City.", "a copy of your preset keeps its note")
check(dm['desc'] is None, "a copy of a built-in has no note of its own")
luaS.execute('NS.DeletePreset("%s")' % dd['id'])

# applying your own preset
luaS.execute('SlashCmdList.EYECANDY("preset performance"); CHAT = {}')
check(gS("farclip") != "10000" and gS("ResampleAlwaysSharpen") == "0", "Performance moved away from the saved preset")
luaS.execute('SETLOG = {}')
check(ev('NS.ApplyPresetById("%s")' % pid) == True, "apply your own preset")
setlog = lst(ev('SETLOG'))
check(gS("farclip") == "10000" and gS("Contrast") == "62" and gS("cameraFov") == "75", "your preset puts every saved value back")
check(setlog.index("textureFilteringMode") < setlog.index("graphicsShadowQuality") < setlog.index("farclip"), "menu rows first, in category order, then hidden values (review finding 7)")
check(ev('next(EyeCandyDB.tiers)') is None and ev('next(EyeCandyDB.extras)') is None and ev('EyeCandyDB.look') is None, "your preset clears tiers, extras and Look so nothing re-applies over it")
check(ev('EyeCandyDB.advanced.cameraFov') == 75 and ev('EyeCandyDB.advanced.ResampleAlwaysSharpen') == 1, "hidden values that differ from default are kept applied, dial or not (review finding 5)")
luaS.execute('SetCVar("cameraFov", 90); SetCVar("ResampleAlwaysSharpen", 0); SettingsPanel.hooks.OnHide(); RUNTIMERS()')
check(gS("cameraFov") == "75" and gS("ResampleAlwaysSharpen") == "1", "your preset's hidden values survive closing Options")
luaS.execute('SlashCmdList.EYECANDY("preset performance"); CHAT = {}')
check(ev('EyeCandyDB.advanced.ResampleAlwaysSharpen') is None and gS("ResampleAlwaysSharpen") == "0", "a built-in drops your preset's no-dial values and hands them back")
luaS.execute('NS.ApplyPresetById("%s")' % pid)
luaS.execute('INCOMBAT = true')
check(ev('NS.ApplyPresetById("tier1")') in (None, False) and gS("farclip") == "10000", "no preset changes in combat")
luaS.execute('INCOMBAT = false')

# export
s = ev('NS.ExportPreset("%s")' % pid)
check(s.startswith("!EC1!") and 50 < len(s) < 4000, "export is !EC1! + Base64 (%d characters)" % len(s))
payload = ev('OPEN_SHARE("%s")' % s)
check(payload['name'] == "Raid night" and payload['author'] == "Tester-Testrealm" and payload['gameVersion'] == "1.60.1" and payload['date'] == "2026-11-06 10:40" and payload['v'] == 1, "share string holds name, author, date, game version, format version")
check(payload['values']['farclip'] == "10000" and payload['values']['bloomUserMult'] is None and payload['values']['Gamma'] == "0.9", "share string holds only settings that differ from game defaults")
check(payload['desc'] == "Tested in Stormwind City.", "share code holds your preset's note")
check(ev('OPEN_SHARE(NS.ExportPreset("look:crisp")).desc') is None, "a built-in's share code has no note")
check(ev('NS.ExportPreset("look:crisp")').startswith("!EC1!"), "built-ins can be shared too")
check(ev('{NS.ExportPreset("nope")}')[1] is None, "exporting an unknown id fails cleanly")

# import round trip
luaS.execute('SlashCmdList.EYECANDY("preset performance"); CHAT = {}')
pv = ev('NS.PreviewImport("  %s\\n")' % s)
check(pv['ok'] == True and pv['name'] == "Raid night" and pv['author'] == "Tester-Testrealm" and pv['gameVersion'] == "1.60.1" and pv['date'] == "2026-11-06 10:40", "preview shows name, author, date, game version (spaces and new lines ignored)")
check(pv['changes'] > 5 and len(lst(pv['skipped'])) == 0 and pv['clash'] == True, "preview counts changes (%s), nothing skipped (%s), name clash flagged" % (pv['changes'], lst(pv['skipped'])))
n_user = len(lst(ev('NS.ListPresets().user')))
k = ev('NS.ImportPreset("%s", "keep")' % s)
check(k['name'] == "Raid night (2)" and len(lst(ev('NS.ListPresets().user'))) == n_user + 1, "Keep both saves the import as 'Raid night (2)'")
check(gS("farclip") != "10000" and gS("Contrast") != "62", "import only saves the preset: no setting changes")
luaS.execute('NS.ApplyPresetById("%s")' % k['id'])
check(gS("farclip") == "10000" and gS("Contrast") == "62", "the imported preset applies when you press Apply on it")
rp = ev('NS.ImportPreset("%s", "replace")' % s)
check(rp['id'] == pid and len(lst(ev('NS.ListPresets().user'))) == n_user + 1, "Replace overwrites the preset with the same name")
check(k['desc'] == "Tested in Stormwind City." and rp['desc'] == "Tested in Stormwind City.", "an imported preset keeps the note, Keep both and Replace alike")
nd = ev('NS.ImportPreset(MAKE_SHARE({ v = 1, name = "Raid night", values = { farclip = "10000" } }), "replace")')
check(nd['id'] == pid and nd['desc'] is None, "Replace with a code that has no note drops the old note")
dirty = ev('NS.ImportPreset(MAKE_SHARE({ v = 1, name = "Dirty note", desc = "|cffff0000Red|r line\\nnext |Hitem:1|h " .. string.rep("a", 600), values = { farclip = "9000" } }), "keep")')
check(dirty['desc'].startswith("Red line next Hitem:1h a") and len(dirty['desc']) <= 400, "a note from a code loses colours and new lines, and is cut to 400 characters (%d)" % len(dirty['desc']))
check(ev('NS.ImportPreset(MAKE_SHARE({ v = 1, name = "Odd note", desc = { 1 }, values = {} }), "keep").desc') is None, "a note that is not text is dropped")
ext = ev('NS.PreviewImport(MAKE_SHARE({ v = 1, name = "Thing", values = { farclip = "9000" } }))')
check(ext['ok'] == True and ext['clash'] == False and (ext['author'] or "") == "", "a string with no author still previews, no clash")
# settings a string leaves out are the game default, so it is the same preset the sharer had
luaS.execute('IMPORT_APPLY(MAKE_SHARE({ v = 1, name = "Only farclip", values = { farclip = "9000" } }), "keep")')
check(gS("farclip") == "9000" and gS("Contrast") == "57" and gS("groundEffectDensity") == "16", "settings a string leaves out go to the game default")

# whitelist: nothing outside the addon's graphics list is ever touched
bad = ev('MAKE_SHARE({ v = 1, name = "Sneaky", values = { farclip = "8000", autoLootDefault = "1", SET_BINDING = "x", [5] = "1", Contrast = { nested = 1 }, Gamma = "1; reload", cameraFov = string.rep("9", 40) } })')
pv = ev('NS.PreviewImport("%s")' % bad)
sk = sorted(lst(pv['skipped']))
check(pv['ok'] == True and "autoLootDefault" in sk and "SET_BINDING" in sk, "settings off the graphics list are skipped and listed: %s" % sk)
check("Contrast" in sk and "Gamma" in sk and "cameraFov" in sk and "5" in sk, "bad values and keys are skipped and listed")
luaS.execute('SETLOG = {}')
ev('IMPORT_APPLY("%s", "keep")' % bad)
setlog = lst(ev('SETLOG'))
check(gS("autoLootDefault") == "0" and "autoLootDefault" not in setlog and "SET_BINDING" not in setlog, "a shared string can't change settings off the graphics list")
check(gS("farclip") == "8000", "the whitelisted part still imports")
# values out of range are skipped: a huge menu index used to hang the game (review findings 1 and 2)
huge = ev('MAKE_SHARE({ v = 1, name = "Huge", values = { graphicsShadowQuality = "99999999999999999999", graphicsSSAO = "1000000000", graphicsLightMode = "2.5", '
          'terrainLodDist = "99999999999999999999", animFrameSkipLOD = "-1", TerrainLodDiv = "1000", RenderScale = "9", entityLodDist = "500", '
          'graphicsLiquidDetail = "2", assaoRadius = "2", TerrainLodDiv2 = "1" } })')
pv = ev('NS.PreviewImport("%s")' % huge)
sk = sorted(lst(pv['skipped']))
check(sk == sorted(["graphicsShadowQuality", "graphicsSSAO", "graphicsLightMode", "terrainLodDist", "animFrameSkipLOD", "TerrainLodDiv", "RenderScale", "entityLodDist", "TerrainLodDiv2"]),
      "huge, negative, fractional, off-list and off-choice values skipped: %s" % sk)
ev('IMPORT_APPLY("%s", "keep")' % huge)
check(gS("graphicsLiquidDetail") == "2" and abs(float(gS("assaoRadius")) - 2) < 1e-9 and gS("graphicsShadowQuality") == "3", "in-range values import; the rest go to default")
check(ev('NS.ResolveMenuValue("graphicsShadowQuality", 1e20)') == 20, "a huge menu index is capped before the supported-value loop")

# tampered and foreign strings
mid = len(s) // 2
tampered = s[:mid] + ("A" if s[mid] != "A" else "B") + s[mid + 1:]
for label, text in [("tampered", tampered), ("cut short", s[:len(s) - 9]), ("foreign (WeakAuras)", "!WA:2!abcdefgh"), ("plain text", "hello"), ("empty", ""),
                    ("not Base64", "!EC1!@@@@"), ("Base64 of nonsense", "!EC1!aGVsbG8gd29ybGQ="), ("not a table", ev('MAKE_SHARE("just text")')),
                    ("no name", ev('MAKE_SHARE({ v = 1, values = {} })')), ("no values", ev('MAKE_SHARE({ v = 1, name = "x" })')),
                    ("no format version", ev('MAKE_SHARE({ name = "x", values = {} })')), ("format version as text", ev('MAKE_SHARE({ v = "1", name = "x", values = {} })')),
                    ("format version 0", ev('MAKE_SHARE({ v = 0, name = "x", values = {} })')), ("too long", "!EC1!" + "A" * 20000)]:
    pv = ev('NS.PreviewImport("%s")' % text)
    check(pv['ok'] == False and pv['err'], "%s string refused: %s" % (label, pv['err']))
pv = ev('NS.PreviewImport(MAKE_SHARE({ v = 2, name = "Future", values = {} }, "!EC2!"))')
check(pv['ok'] == False and "newer" in pv['err'], "a string from a newer Eye Candy says to update: %s" % pv['err'])
r = ev('{NS.ImportPreset("%s", "keep")}' % tampered)
check(r[1] is None and r[2], "importing a tampered string changes nothing and says why")
check(ev('{NS.PreviewImport(nil)}')[1]['ok'] == False, "nil text handled")
# the real decoders may return nothing, or a CBOR array, instead of raising (review finding 11)
for label, stub in [("decompress returns nothing", 'C_EncodingUtil.DecompressString = function() return nil end'),
                    ("base64 decode returns nothing", 'C_EncodingUtil.DecodeBase64 = function() end'),
                    ("CBOR returns nothing", 'C_EncodingUtil.DeserializeCBOR = function() return nil end'),
                    ("CBOR returns a number", 'C_EncodingUtil.DeserializeCBOR = function() return 5 end')]:
    luaS.execute('local saved = {}; for k, v in pairs(C_EncodingUtil) do saved[k] = v end; SAVED_ENC = saved; ' + stub)
    pv = ev('NS.PreviewImport("%s")' % s)
    luaS.execute('for k, v in pairs(SAVED_ENC) do C_EncodingUtil[k] = v end')
    check(pv['ok'] == False and pv['err'], "%s: refused cleanly" % label)
arr = ev('NS.PreviewImport(MAKE_SHARE({ v = 1, name = "Array", values = { "10000", "62", "1" } }))')
check(arr['ok'] == True and len(lst(arr['skipped'])) == 3, "values that arrive as an array are all skipped")
# a built-in's name never gets replaced
mo = ev('NS.ImportPreset(MAKE_SHARE({ v = 1, name = "Moody", values = { farclip = "9000" } }), "replace")')
check(mo['name'] == "Moody (3)" and ev('NS.FindPreset("look:moody").builtin') == True, "Replace never overwrites a built-in: saved as 'Moody (3)' (2 is taken)")
# combat
n_user = len(lst(ev('NS.ListPresets().user')))
luaS.execute('INCOMBAT = true; SETLOG = {}')
r = ev('{NS.ImportPreset("%s", "keep")}' % s)
check(r[1] is not None and len(lst(ev('NS.ListPresets().user'))) == n_user + 1 and len(lst(ev('SETLOG'))) == 0, "an import in combat saves the preset and changes no setting")
luaS.execute('INCOMBAT = false')

# saved across reloads
luaS2 = boot(svdb='EyeCandyDB = { tiers = {}, extras = {}, advanced = {}, keepApplied = true, presets = { { id = "u7", name = "Kept", group = "Yours", builtin = false, values = { farclip = "9000" } } }, nextPresetId = 8 }')
check(luaS2.eval('NS.FindPreset("u7").name') == "Kept" and luaS2.eval('NS.SaveCurrentAsPreset("New").id') == "u8", "your presets come back after a reload; ids never reused")

# slash commands for testing in game
luaS.execute('CHAT = {}; SlashCmdList.EYECANDY("save Slash Test")')
check(ev('NS.FindPresetByName("slash test").name') == "Slash Test", "/ec save <name> keeps the name's capitals")
luaS.execute('CHAT = {}; SlashCmdList.EYECANDY("share slash test")')
c = chat(luaS)
check(ev('EyeCandyExportFrame.text').startswith("!EC1!") and any("reads back" in x for x in c), "/ec share <name> shows the string and checks it reads back: %s" % c)
luaS.execute('SlashCmdList.EYECANDY("presets")')
c = chat(luaS)
check(any("Slash Test" in x for x in c) and any("Moody" in x for x in c), "/ec presets lists built-ins and yours")
luaS.execute('SlashCmdList.EYECANDY("share nothing here")')
check(any("no preset" in x.lower() for x in chat(luaS)), "/ec share with an unknown name says so")
luaS.execute('SlashCmdList.EYECANDY("use slash test")')
check(any("applied your preset" in x for x in chat(luaS)), "/ec use <name> applies it")
# the window redraws after every change
luaS.execute('REFRESHES = 0; local old = NS.RefreshUI; NS.RefreshUI = function() REFRESHES = REFRESHES + 1; if old then old() end end')
luaS.execute('local p = NS.SaveCurrentAsPreset("Redraw"); NS.RenamePreset(p.id, "Redraw 2"); NS.DuplicatePreset(p.id); NS.DeletePreset(p.id)')
check(ev('REFRESHES') >= 4, "save, rename, duplicate and delete each redraw the window (%d)" % ev('REFRESHES'))

done()
