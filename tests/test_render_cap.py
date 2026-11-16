"""The game's 100% hold on render scale (16 Nov 2026): Eye Candy clears it for the next start.
Run: python tests/test_render_cap.py"""
from lib import boot, chat, check, done

CVAR = "ClientSettings_HIGH_MEM_FEATURES_BY_API_MASK"
HOLD = "16001,0x0,0x0,0x1ff"
# The servers' line, and a game that holds render scale at 100% this session.
PRE = 'C_CVar.RegisterCVar(%r, ""); SetCVar(%r, %r); MAXSCALE = 1; function GetMaxRenderScale() return MAXSCALE end' % (CVAR, CVAR, HOLD)

lua = boot(PRE)
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(E("GetCVar(%r)" % CVAR) == HOLD, "nothing is cleared at once: the servers may still be sending it")
X("RUNTIMERS()")
check(E("GetCVar(%r)" % CVAR) == "", "a few seconds after a loading screen the hold is cleared for the next start")
X("SetCVar(%r, %r)" % (CVAR, HOLD))
X('FIRE("PLAYER_LOGOUT")')
check(E("GetCVar(%r)" % CVAR) == "", "written back during the session, it is cleared again at logout")
check(E("NS.RenderCap.Held()") is True, "the game holds 100% this session")

# What the player reads while it is held.
X("CHAT = {}; NS.ApplyShowcase()")
msgs = chat(lua)
check(any("Showcase on" in m and "restart" in m and "200%" in m for m in msgs), "Showcase says to restart the game for 200%% (%r)" % msgs)
check(any("Render scale" in m and "held at 100% until you restart the game" in m for m in msgs),
      "the note on render scale says it is held until a restart, not just the most the game allows (%r)" % msgs)
X("MAXSCALE = 2")
check(E("NS.RenderCap.Held()") is False, "after a restart, with 200% allowed, nothing says it is held")

# A game with no such line: nothing to clear, no error.
lua2 = boot("")
lua2.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); FIRE("PLAYER_LOGOUT")')
check(lua2.eval("ERRSEEN") == 0 and lua2.eval("NS.RenderCap.Clear()") is False, "with no such line there is nothing to clear, and no error")

done()
