"""The chat line for a render scale the game won't take names the game's limit, not your PC.
The game sets the range (GetMinRenderScale, GetMaxRenderScale); a Forever patch in Nov 2026
capped the top at 100%.
Run: python tests/test_render_scale_words.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('C_CVar.RegisterCVar("RenderScale", "1"); GetMinRenderScale = function() return 0.33 end; GetMaxRenderScale = function() return 1 end')
X('function TRY(v) local r = { applied = 0, changed = {}, skipped = {} }; NS.ApplyOne("RenderScale", "Render scale", v, { scale = true }, r); return r.changed[1] end')

high = E('TRY(2)')
check(high is not None and "the most the game allows now" in high and "asked 2" in high, "above the game's top it says the most the game allows now (%r)" % high)
check("your setup" not in high and "max" not in high, "and it doesn't blame your PC (%r)" % high)
low = E('TRY(0.1)')
check(low is not None and "the least the game allows now" in low, "below the game's bottom it says the least (%r)" % low)
check(E('TRY(0.5)') is None and E('TRY(1)') is None, "a value in range, or right at the top, says nothing")

# A menu setting the game steps down (review of this fix): its own words, not render scale's.
X('C_CVar.RegisterCVar("graphicsParticleDensity", "1")')
X('function MENU(v) local r = { applied = 0, changed = {}, skipped = {} }; NS.ApplyOne("graphicsParticleDensity", "Particle density", v, { menu = true }, r); return r.changed[1] end')
menu = E('MENU(5)')
check(menu is not None and "the highest the game supports now" in menu and "asked 5" in menu, "a stepped-down menu setting says the highest the game supports now (%r)" % menu)
check("allows now" not in menu and "your setup" not in menu, "and not render scale's words (%r)" % menu)
check(E('MENU(3)') is None, "a supported menu value says nothing")
done()
