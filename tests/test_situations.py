"""Situations: the Raid & PvP, Laptop, Screenshot and Capital city built-in presets, and /ec back.

Run alone: python tests/test_situations.py
"""
from lib import boot, chat, check, done

# Dials the three presets set that the stub client doesn't register by itself.
REG = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
"""


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)] if t is not None else []


lua = boot()
lua.execute(REG)
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
g = lambda n: lua.eval('GetCVar("%s")' % n)
ev = lambda s: lua.eval(s)

# Listed after the Looks, under their own group.
builtin = lst(ev('NS.ListPresets().builtin'))
sit = [p for p in builtin if p['group'] == "Situations"]
check([p['id'] for p in sit] == ["look:raid", "look:laptop", "look:screenshot", "look:city"], "four Situations listed: Raid & PvP, Laptop, Screenshot, Capital city")
check(all(p['builtin'] == True and p['desc'] for p in sit) and sit[0]['name'] == "Raid & PvP", "each is a described, read-only built-in")
check(len([p for p in builtin if p['group'] == "Looks"]) == 5, "the five Looks are still there")

# Raid & PvP: High base, particles and weather down, depth effects off.
lua.execute('SetCVar("weatherDensity", "2")')
check(ev('NS.ApplyPresetById("look:raid")') == True, "Raid & PvP applies")
check(g("graphicsShadowQuality") == "4" and g("graphicsParticleDensity") == "1" and g("graphicsDepthEffects") == "0", "Raid & PvP: High shadows, particles 1, depth effects off")
check(g("weatherDensity") == "0" and g("cameraDistanceMaxZoomFactor") == "2.6" and g("bloomUserMult") == "0.4", "Raid & PvP: no weather, zoom 2.6, bloom 0.4")
check(ev('EyeCandyDB.look') == "raid" and ev('NS.BackSteps()[1].name') == "Raid & PvP", "the preset is today's newest step, for Back")
check(any("Preset: Raid & PvP" in line for line in chat(lua)), "chat says the preset, not 'Look'")

# /ec back puts back what was there before.
lua.execute('SlashCmdList.EYECANDY("back")')
check(g("weatherDensity") == "2" and g("graphicsDepthEffects") != "0", "/ec back restores the settings from before Raid & PvP")
check(ev('#NS.BackSteps()') == 0, "after going back there is nothing left to go back to")
lua.execute('CHAT = {}; SlashCmdList.EYECANDY("back")')
check(any("Nothing to go back to" in line for line in chat(lua)), "a second /ec back says there is nothing to go back to")

# Laptop: Performance, 75% render scale with FSR, SSAO off.
check(ev('NS.ApplyPresetById("look:laptop")') == True, "Laptop applies")
check(g("RenderScale") == "0.75" and g("ResampleQuality") == "3" and g("graphicsSSAO") == "0", "Laptop: 75% render scale, FSR 1.0, SSAO off")
check(g("graphicsShadowQuality") == "1", "Laptop: Performance shadows")

# Screenshot: Showcase at 200%, and its chat line says how to get back.
lua.execute('CHAT = {}')
check(ev('NS.ApplyPresetById("look:screenshot")') == True and g("RenderScale") == "2", "Screenshot applies at 200% render scale")
check(any("/ec back" in line for line in chat(lua)), "Screenshot tells you how to get back")
lua.execute('SlashCmdList.EYECANDY("back")')
check(g("RenderScale") == "0.75", "/ec back after Screenshot returns to the Laptop settings")

# Capital city: from Beautiful (view distance 9, far characters at 20), the crowd costs come down
# and the graphics card costs stay at High.
lua.execute('NS.ApplyPresetById("look:beautiful")')
check(g("graphicsViewDistance") == "9" and g("entityLodDist") == "20", "set-up: Beautiful has view distance 9 and far characters at 20")
check(ev('NS.ApplyPresetById("look:city")') == True, "Capital city applies")
check(g("graphicsViewDistance") == "7" and g("graphicsEnvironmentDetail") == "7", "Capital city: view distance and environment detail at 7")
check(g("graphicsComputeEffects") == "2" and g("entityLodDist") == "10", "Capital city: compute effects 2, far characters back to the default 10")
check(g("graphicsShadowQuality") == "4" and g("graphicsSSAO") == "3" and g("graphicsParticleDensity") == "3", "Capital city: High shadows, SSAO and particles")
check(ev('EyeCandyDB.advanced.graphicsViewDistance') == 7 and ev('EyeCandyDB.extras.entityLod') == 10, "its dials and Extra are kept as your choices")
lua.execute('CHAT = {}; SlashCmdList.EYECANDY("back")')
check(g("graphicsViewDistance") == "9" and g("entityLodDist") == "20", "/ec back after Capital city returns to Beautiful")
lua.execute('SlashCmdList.EYECANDY("look city")')
check(ev('EyeCandyDB.look') == "city", "/ec look city applies Capital city")
lua.execute('SetCVar("graphicsViewDistance", "9"); SetCVar("entityLodDist", "20"); NS.ApplyAll(false, true)')
check(g("graphicsViewDistance") == "7" and g("entityLodDist") == "10", "a later Apply keeps 7 over High's 8, and far characters at 10")
lua.execute('SetCVar("graphicsComputeEffects", "4"); NS.ApplyAll(true, true)')
check(g("graphicsComputeEffects") == "2", "the quiet re-apply (login, closing Options) puts compute effects back to 2")
lua.execute('SlashCmdList.EYECANDY("back")')

# Moody (a Look, kept here with the other built-in values): 150% render scale, not 175%.
lua.execute('NS.ApplyPresetById("look:moody")')
check(g("RenderScale") == "1.5" and g("Gamma") == "0.9", "Moody draws at 150% render scale")
lua.execute('SlashCmdList.EYECANDY("back")')

# /ec look <key> works for them too.
lua.execute('SlashCmdList.EYECANDY("look raid")')
check(ev('EyeCandyDB.look') == "raid", "/ec look raid applies Raid & PvP")

# A share string of each reads back with nothing skipped (0.75 render scale and weather 0 are in range).
for pid in ("look:raid", "look:laptop", "look:screenshot", "look:city"):
    text = ev('NS.ExportPreset("%s")' % pid)
    prev = ev('NS.PreviewImport("%s")' % text) if text else None
    check(prev is not None and prev['ok'] == True and len(lst(prev['skipped'])) == 0, "%s shares and reads back with nothing skipped" % pid)

# A restore from the Backups tab is one of today's steps, so /ec back undoes the restore.
lua.execute('NS.ApplyPresetById("look:raid")')
orig = ev('NS.OriginalBackup().id')
lua.execute('NS.RestoreBackupById(%d); CHAT = {}' % orig)
check(ev('NS.BackSteps()[1].kind') == "restore" and ev('GetCVar("weatherDensity")') != "0", "a Backups-tab restore is today's newest step")
lua.execute('SlashCmdList.EYECANDY("back")')
check(ev('GetCVar("weatherDensity")') == "0" and any("Back to before you restored" in line for line in chat(lua)), "and /ec back undoes the restore, back to Raid & PvP")
# A change after a preset: /ec back undoes the change first, and keeps the preset.
lua.execute('NS.ApplyPresetById("look:raid"); SetCVar("weatherDensity", "3"); CHAT = {}')
lua.execute('SlashCmdList.EYECANDY("back")')
check(ev('GetCVar("weatherDensity")') == "0" and any("Back to before your own changes" in line for line in chat(lua)), "a change since the preset: /ec back undoes your own change")

# Today's steps are not backups, so deleting backups never takes one away.
lua.execute('NS.ApplyPresetById("look:laptop"); local b = NS.CreateBackup("manual", "Spare"); NS.DeleteBackup(b.id); CHAT = {}')
check(ev('NS.BackSteps()[1].name') == "Laptop", "deleting a backup leaves Laptop in today's steps")

# Your own preset is a step too.
p = ev('NS.SaveCurrentAsPreset("Mine")')
lua.execute('NS.ApplyPresetById("tier1")')
check(ev('NS.ApplyPresetById("%s")' % p['id']) == True and ev('NS.BackSteps()[1].name') == "Mine", "applying your own preset is a step for Back too")

done()
