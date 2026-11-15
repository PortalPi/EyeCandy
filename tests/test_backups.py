"""Backups (1.0.0 step 4): the Original, manual and automatic backups, restore, migration from Vista 1.x.

Run alone: python tests/test_backups.py
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


luaU = boot()
luaU.execute(ADV)
check(luaU.eval('NS.OriginalBackup()') is None and luaU.eval('EyeCandyDB.backup') is None, "a fresh install has no Original until login settles")
luaU.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
evU = lambda s: luaU.eval(s)
gU = lambda n: luaU.eval('GetCVar("%s")' % n)
bl = lambda: lst(evU('NS.ListBackups()'))
kinds = lambda: [b['kind'] for b in bl()]
c = chat(luaU)
o = evU('NS.OriginalBackup()')
check(kinds() == ["original"] and o['label'] == "Original settings" and o['character'] == "Tester-Testrealm" and o['values']['groundEffectDensity'] == "48", "first login saves the Original, with the character")
check(any("/reload" in x for x in c), "first install asks for a /reload so the Original is saved")
check(o['time'] == "2026-11-06 10:40" and isinstance(o['stamp'], (int, float)), "backups have a date and a time stamp")
check(evU('NS.OriginalBackup().values.groundEffectDensity') == "48" and evU('rawget(EyeCandyDB, "backup")') is None, "the Original holds the value from before; no old Vista 1.x slot is saved")
luaU.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(kinds() == ["original"] and not any("/reload" in x for x in chat(luaU)), "the Original is made once, and asked about once")

# No backup row is ever made by itself (in test builds every apply and restore made one, and the list filled up).
# A preset keeps one "before" record for Back instead, outside the list.
luaU.execute('REFRESHES = 0; local old = NS.RefreshUI; NS.RefreshUI = function() REFRESHES = REFRESHES + 1; if old then old() end end')
luaU.execute('SlashCmdList.EYECANDY("preset cinematic"); CHAT = {}')
lb = lambda: evU('EyeCandyDB.lastBefore')
check(kinds() == ["original"], "a preset adds no backup row (%s)" % kinds())
check(lb()['name'] == "Cinematic" and lb()['label'] == "Before Cinematic" and lb()['values']['farclip'] == "7000" and lb()['id'] is None, "it keeps one 'before' record of its own, holding the old values")
luaU.execute('SlashCmdList.EYECANDY("apply")')
check(kinds() == ["original"] and lb()['name'] == "Cinematic", "Apply adds no backup row and leaves the preset's record alone")
luaU.execute('SetCVar("weatherDensity", 1); SlashCmdList.EYECANDY("apply")')
check(kinds() == ["original"], "a change, then Apply, adds no row either")
luaU.execute('NS.SetAdvanced("assaoRadius", 2); NS.SetAdvanced("assaoRadius", 2.5)')
check(kinds() == ["original"], "a dial change adds no row")
r = evU('{NS.CreateBackup("auto", "Before Apply")}')
check(r[1] is None and r[2] and kinds() == ["original"], "an automatic backup can't be made at all: %s" % r[2])
# review finding 1: the tier buttons change the choices before Apply; a backup keeps the choices in force
luaU.execute('for _, cat in ipairs(NS.CATEGORIES) do EyeCandyDB.tiers[cat.key] = 2 end')
tiered = evU('NS.CreateBackup("manual", "Tiered")')
check(tiered['state']['tiers']['clarity'] == 5 and tiered['values']['farclip'] == "10000" and tiered['state']['advanced']['assaoRadius'] == 2.5, "a backup holds the tiers that were applied, not the ones just clicked, and the dials as they are")
luaU.execute('SlashCmdList.EYECANDY("apply"); NS.RestoreBackupById(%d)' % tiered['id'])
check(evU('EyeCandyDB.tiers.clarity') == 5 and gU("farclip") == "10000", "restoring it puts the old tiers back with the old settings")
luaU.execute('NS.DeleteBackup(%d)' % tiered['id'])
luaU.execute('SlashCmdList.EYECANDY("look moody")')
check(lb()['name'] == "Moody", "a Look's record is named after it")
luaU.execute('SlashCmdList.EYECANDY("showcase")')
check(lb()['name'] == "Showcase" and kinds() == ["original"], "the next preset replaces it: one step back only, and still no rows")

# manual
m = evU('NS.CreateBackup("manual", "Before raid night")')
check(m['kind'] == "manual" and m['label'] == "Before raid night" and bl()[0]['id'] == m['id'], "manual backup with your own name, newest first")
check(evU('NS.CreateBackup("manual", "")')['label'].startswith("Backup "), "a manual backup with no name gets a dated name")
check(evU('NS.CreateBackup("manual", "|cffff0000Red|r")')['label'] == "Red", "colour codes are stripped from backup names")
r = evU('{NS.CreateBackup("original", "x")}')
check(r[1] is None and r[2] and len([k for k in kinds() if k == "original"]) == 1, "a second Original can't be made")
check(evU('REFRESHES') >= 3, "making a backup redraws the window (%d)" % evU('REFRESHES'))

# count, restore, and a named backup restores tiers and dials
luaU.execute('SlashCmdList.EYECANDY("preset cinematic"); NS.SetAdvanced("assaoRadius", 2.5); CHAT = {}')
mine = evU('NS.CreateBackup("manual", "Cinematic and a dial")')
nrows = len(bl())
cnt = evU('NS.CountBackupChanges(NS.OriginalBackup().id)')
check(cnt > 10, "change count for the Original (%d)" % cnt)
luaU.execute('CHAT = {}')
got = evU('NS.RestoreBackupById(NS.OriginalBackup().id)')
check(got == cnt and gU("farclip") == "7000" and gU("groundEffectDensity") == "48" and evU('next(EyeCandyDB.tiers)') is None and evU('next(EyeCandyDB.advanced)') is None, "restore puts the Original back, clears choices, and reports the change count")
check(len(bl()) == nrows and all(b['label'] != "Before restore" for b in bl()), "restore adds no backup row")
check(evU('EyeCandyDB.lastBefore') is None, "and clears Back's record, so Back never undoes a restore")
check(not any('estored' in x for x in chat(luaU)), "a restore from the window prints nothing to chat (the window shows it)")
check(evU('NS.RestoredLine(3, {label = "Raid", time = "today"})') == 'Restored 3 settings from "Raid" (today).' and evU('NS.RestoredLine(1, {label = "Raid", time = "today"})').startswith("Restored 1 setting from"), "the restore line counts settings, singular for one")
check(evU('NS.CountBackupChanges(NS.OriginalBackup().id)') == 0, "after a restore nothing differs from that backup")
luaU.execute('NS.RestoreBackupById(%d)' % mine['id'])
check(gU("farclip") == "10000" and evU('EyeCandyDB.tiers.clarity') == 5 and evU('EyeCandyDB.advanced.assaoRadius') == 2.5, "restoring a named backup puts its tiers and dials back too")
luaU.execute('INCOMBAT = true')
r = evU('{NS.RestoreBackupById(NS.OriginalBackup().id)}')
check(r[1] is None and gU("farclip") == "10000", "no restore in combat")
luaU.execute('INCOMBAT = false')
check(evU('{NS.RestoreBackupById(9999)}')[1] is None, "restoring an unknown backup is refused")
# review finding 4: a damaged entry is refused and changes nothing
luaU.execute('table.insert(EyeCandyDB.backups, { id = 777, kind = "manual", label = "Broken", time = "x", stamp = 1, state = { tiers = {} } })')
r = evU('{NS.RestoreBackupById(777)}')
check(r[1] is None and "damaged" in r[2] and evU('EyeCandyDB.tiers.clarity') == 5, "a damaged backup is refused and leaves your choices alone")
luaU.execute('NS.DeleteBackup(777)')

# Original never deleted
r = evU('{NS.DeleteBackup(NS.OriginalBackup().id)}')
check(r[1] is None and r[2] and evU('NS.OriginalBackup()') is not None, "the Original can't be deleted: %s" % r[2])
check(evU('NS.DeleteBackup(%d)' % m['id']) == True and all(b['id'] != m['id'] for b in bl()), "a manual backup can be deleted")
nman = kinds().count("manual")

# many presets in a row leave the list as it was
before = [b['id'] for b in bl()]
for i in range(30):
    luaU.execute('SlashCmdList.EYECANDY("preset %s")' % ("ultra" if i % 2 else "high"))
check([b['id'] for b in bl()] == before and kinds().count("manual") == nman, "30 presets add no rows; Original and manual untouched (%s)" % kinds())
luaU.execute('CHAT = {}; SlashCmdList.EYECANDY("restore")')
check(gU("farclip") == "7000" and [b['id'] for b in bl()] == before, "/ec restore still restores the Original, and adds no row")
said = chat(luaU)
check(len(said) == 1 and "Restored " in said[0] and "Original" in said[0], "/ec restore says once what it restored (%s)" % said)

# your own presets and imports keep the record too, and add no row
p = evU('NS.SaveCurrentAsPreset("Mine")')
luaU.execute('SlashCmdList.EYECANDY("preset ultra"); SetCVar("weatherDensity", 2)')
luaU.execute('NS.ApplyPresetById("%s")' % p['id'])
check(lb()['label'] == "Before Mine" and lb()['values']['weatherDensity'] == "2" and lb()['state']['tiers']['clarity'] == 4 and [b['id'] for b in bl()] == before, "applying your own preset records the settings and choices from just before, and adds no row")
s = evU('NS.ExportPreset("tier5")')
was = lb()
imp = evU('NS.ImportPreset("%s", "keep")' % s)
check([b['id'] for b in bl()] == before and lb()['name'] == was['name'], "an import only saves a preset: no row and no new before record")
luaU.execute('NS.ApplyPresetById("%s")' % imp['id'])
check(lb()['name'].startswith("Cinematic") and lb()['values']['farclip'] == "7000" and [b['id'] for b in bl()] == before, "applying an imported preset records it, and adds no row (%s)" % lb()['name'])

# slash
luaU.execute('CHAT = {}; SlashCmdList.EYECANDY("backup Raid Night"); SlashCmdList.EYECANDY("backups")')
c = chat(luaU)
raid = bl()[0]
check(raid['label'] == "Raid Night" and any(x.find("%d. " % raid['id']) >= 0 and "Raid Night" in x for x in c) and any("Original settings" in x for x in c), "/ec backup <name> and /ec backups (numbered by id)")
luaU.execute('CHAT = {}; SlashCmdList.EYECANDY("backups please")')
check(any("Raid Night" in x for x in chat(luaU)), "/ec backups with extra words still lists (review finding 6)")
luaU.execute('SlashCmdList.EYECANDY("backup")')
check(bl()[0]['label'].startswith("Backup ") and bl()[0]['kind'] == "manual", "/ec backup with no name")
# review finding 7: the number stays with its backup when another is added in between
luaU.execute('SlashCmdList.EYECANDY("preset ultra"); SlashCmdList.EYECANDY("preset high"); CHAT = {}; SlashCmdList.EYECANDY("restore %d")' % raid['id'])
check(any("Restored " in x and raid['label'] in x for x in chat(luaU)), "/ec restore <number> says what it restored")
luaU.execute('INCOMBAT = true; CHAT = {}; SlashCmdList.EYECANDY("restore %d"); INCOMBAT = false' % raid['id'])
said = chat(luaU)
check(len(said) == 1 and "Can't restore in combat" in said[0], "/ec restore in combat says why, once (%s)" % said)
check(gU("farclip") == raid['values']['farclip'] and evU('EyeCandyDB.tiers.clarity') == raid['state']['tiers']['clarity'] and bl()[0]['kind'] == "manual", "/ec restore <number> restores that backup, even after others were added, and adds no row")
luaU.execute('CHAT = {}; SlashCmdList.EYECANDY("restore 9999")')
check(any("no backup number" in x for x in chat(luaU)), "/ec restore with a bad number says so")

# migration from the Vista 1.x single backup
luaM = boot(svdb='EyeCandyDB = { tiers = { foliage = 5 }, keepApplied = true, backup = { time = "2026-11-01 09:00", values = { groundEffectDensity = "32", farclip = "6000" } } }')
om = luaM.eval('NS.OriginalBackup()')
check(om['values']['groundEffectDensity'] == "32" and om['time'] == "2026-11-01 09:00" and om['kind'] == "original", "the Vista 1.x backup becomes the Original")
check(luaM.eval('rawget(EyeCandyDB, "backup")') is None and luaM.eval('NS.OriginalBackup().values.farclip') == "6000", "the old slot is gone from saved data and became the Original")
check(not any("/reload" in x for x in chat(luaM)), "no /reload ask when the Original came from Vista 1.x")
luaM.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); SlashCmdList.EYECANDY("apply")')
check(luaM.eval('NS.OriginalBackup().values.doodadLodScale') is not None and luaM.eval('NS.OriginalBackup().values.farclip') == "6000", "settings the Vista 1.x backup didn't hold are merged in; its own values are kept")
luaM.execute('SlashCmdList.EYECANDY("restore")')
check(luaM.eval('GetCVar("groundEffectDensity")') == "32" and luaM.eval('GetCVar("farclip")') == "6000", "restoring the migrated Original works")
luaM2 = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true, backups = { { id = 1, kind = "original", label = "Original settings", time = "x", stamp = 5, character = "Other-Realm", values = { farclip = "6500" } } }, nextBackupId = 2, backup = { time = "y", values = { farclip = "1" } } }')
check(luaM2.eval('NS.OriginalBackup().values.farclip') == "6500" and luaM2.eval('#EyeCandyDB.backups') == 1 and luaM2.eval('rawget(EyeCandyDB, "backup")') is None, "an existing Original is never replaced by a leftover Vista 1.x backup")
luaM2.execute('NS.CreateBackup("manual", "Here"); SlashCmdList.EYECANDY("restore")')
check(luaM2.eval('GetCVar("farclip")') == "6500" and luaM2.eval('NS.ListBackups()[1].character') == "Tester-Testrealm" and luaM2.eval('NS.OriginalBackup().character') == "Other-Realm", "backups are account-wide: another character's backup restores here")
luaM3 = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true, backup = { time = "x", values = { doodadLodScale = "300", lodObjectFadeScale = "300", lodObjectCullSize = "7", terrainLodDist = "1000", TerrainLodDiv = "1024", wmoLodDist = "800", dynamicLod = "0" } } }')
check(luaM3.eval('NS.OriginalBackup().values.doodadLodScale') == "150" and any("corrected your Restore backup" in x for x in chat(luaM3)), "a Vista 1.x backup holding hand-tested Distant Detail values is still corrected")
luaR = boot(svdb='VistaDB = { tiers = {}, keepApplied = true, backup = { time = "old", values = { farclip = "6000" } } }')
check(luaR.eval('NS.OriginalBackup().time') == "old" and luaR.eval('NS.OriginalBackup().values.farclip') == "6000", "a Vista backup becomes the Original too")

# Automatic backups saved by test builds are removed at load. Back's old record pointed at one by id:
# its settings move into the record, so Back still works after the update.
OLD = ('EyeCandyDB = { tiers = {}, keepApplied = true, nextBackupId = 6, lastBefore = { id = 4, name = "Moody", after = {} }, backups = { "damaged",'
       ' { id = 1, kind = "original", label = "Original settings", time = "a", stamp = 1, character = "", values = { farclip = "6500" }, state = {} },'
       ' { id = 2, kind = "auto", label = "Before restore", time = "b", stamp = 2, character = "", values = { farclip = "1000" }, state = {} },'
       ' { id = 3, kind = "manual", label = "Raid night", time = "c", stamp = 3, character = "", values = { farclip = "5000" }, state = {} },'
       ' { id = 4, kind = "auto", label = "Before Moody", time = "d", stamp = 4, character = "", values = { farclip = "4321" }, state = { tiers = { clarity = 2 } } },'
       ' { id = 5, kind = "auto", label = "Before Apply", time = "e", stamp = 5, character = "", values = { farclip = "2000" }, state = {} } } }')
luaA = boot(svdb=OLD)
check([b['kind'] for b in lst(luaA.eval('NS.ListBackups()'))] == ["manual", "original"], "saved automatic backups (and a damaged entry) are removed; the Original and named backups stay")
check(any("removed 3 automatic backups" in x for x in chat(luaA)), "chat says how many were removed, once")
la = luaA.eval('EyeCandyDB.lastBefore')
check(la['values']['farclip'] == "4321" and la['state']['tiers']['clarity'] == 2 and la['label'] == "Before Moody" and la['id'] is None, "Back's record took the settings of the backup it pointed at")
check(luaA.eval('NS.LastPresetName()') == "Moody", "so Back is still offered after the update")
luaA.execute('SlashCmdList.EYECANDY("back")')
check(luaA.eval('GetCVar("farclip")') == "4321" and luaA.eval('EyeCandyDB.tiers.clarity') == 2 and luaA.eval('EyeCandyDB.lastBefore') is None, "and going back restores it, then clears it")
luaA2 = boot(svdb=OLD.replace('lastBefore = { id = 4,', 'lastBefore = { id = 99,'))
check(luaA2.eval('EyeCandyDB.lastBefore') is None and luaA2.eval('NS.LastPresetName()') is None, "a record pointing at a backup already gone is dropped")
luaA4 = boot(svdb=OLD.replace(', after = {} }', ' }'))
check(luaA4.eval('EyeCandyDB.lastBefore.values.farclip') == "4321" and luaA4.eval('NS.LastPresetName()') is None, "a folded record with no 'after' is kept for Compare, but doesn't offer Back")
luaA5 = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true, lastBefore = "junk" }')
check(luaA5.eval('EyeCandyDB.lastBefore') is None and luaA5.eval('NS.LastPresetName()') is None, "a damaged record is dropped at load")
luaA3 = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true }')
check(not any("automatic backups" in x for x in chat(luaA3)), "with none saved, nothing is said")

# review finding 2: choices but no Original (say the saved file was lost and the mirror brought the tiers back).
# The login re-apply must not run before the Original is saved, and settings the choices set are saved at the game default.
ALL5 = "{ " + ", ".join("%s = 5" % k for k in ["clarity", "lighting", "atmosphere", "water", "textures", "world", "distant", "foliage", "effects"]) + " }"
luaL = boot(svdb='EyeCandyDB = { tiers = %s, extras = {}, keepApplied = true }' % ALL5)
luaL.execute('SetCVar("farclip", "10000"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
ol = luaL.eval('NS.OriginalBackup()')
check(ol is not None and ol['values']['farclip'] == luaL.eval('GetCVarDefault("farclip")') and ol['values']['farclip'] != "10000", "an Original made while choices are in force saves the game default for what they set (%s)" % (ol and ol['values']['farclip']))
check(luaL.eval('#EyeCandyDB.backups') == 1, "only one Original, even with two login timers")

# the saved file: write EyeCandyDB the way the game does (real keys only), load it back
SER = """
function SER(v)
  if type(v) == "table" then
    local parts, k, x = {}, next(v)
    while k ~= nil do parts[#parts + 1] = "[" .. SER(k) .. "]=" .. SER(x); k, x = next(v, k) end
    return "{" .. table.concat(parts, ",") .. "}"
  elseif type(v) == "string" then return string.format("%q", v) end
  return tostring(v)
end
"""
luaU.execute(SER)
luaU.execute('SlashCmdList.EYECANDY("preset ultra")')
saved_before = evU('EyeCandyDB.lastBefore.values.farclip')
text = luaU.eval('SER(EyeCandyDB)')
check('["backup"]' not in text and '["backups"]' in text, "the saved file has the backups list and no old backup slot")
luaV = boot(svdb='EyeCandyDB = ' + text)
check(luaV.eval('#NS.ListBackups()') == len(bl()) and luaV.eval('NS.OriginalBackup().id') == evU('NS.OriginalBackup().id') and luaV.eval('NS.OriginalBackup().values.farclip') == "7000" and luaV.eval('EyeCandyDB.backup') is None, "after a reload the same backups are there, and the old Vista 1.x slot is gone")
check(luaV.eval('EyeCandyDB.lastBefore.name') == "Ultra" and luaV.eval('EyeCandyDB.lastBefore.values.farclip') == saved_before and not any("automatic backups" in x for x in chat(luaV)), "Back's record is saved with the file and survives a reload")
luaV.execute('SlashCmdList.EYECANDY("restore")')
check(luaV.eval('GetCVar("farclip")') == "7000", "the Original restores after a reload")

done()
