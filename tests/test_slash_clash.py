"""When another addon also claims /ec (Easy Controller Forever does), WoW picks one of the two at
random, so Eye Candy says once at login that /eyecandy always opens it. With no other /ec, it
says nothing. Run: python tests/test_slash_clash.py"""
from lib import boot, check, done


def lines(lua):
    return [lua.eval('CHAT[%d]' % i) for i in range(1, lua.eval('#CHAT') + 1)]


def clash_lines(lua):
    return [l for l in lines(lua) if "/eyecandy" in l]


# No other addon: nothing is said at login, and help names only /ec.
lua = boot()
X = lua.execute
X('CHAT = {}; FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(clash_lines(lua) == [], "with no other /ec, login says nothing about it (%r)" % lines(lua))
X('CHAT = {}; SlashCmdList.EYECANDY("help")')
check(clash_lines(lua) == [], "with no other /ec, help names only /ec")

# Another addon's /ec, in capitals: one line at login, naming /eyecandy.
lua = boot()
X = lua.execute
X('SLASH_EASYCONTROLLER1 = "/EC"; SLASH_EASYCONTROLLER2 = "/easycontroller"')
X('CHAT = {}; FIRE("PLAYER_ENTERING_WORLD", true, false)')
said = clash_lines(lua)
check(len(said) == 1, "another /ec gives one line at login (%r)" % lines(lua))
check(said and "another addon" in said[0] and "/ec" in said[0], "the line says another addon uses /ec (%r)" % said)

# A reload or a zone change does not say it again.
X('CHAT = {}; FIRE("PLAYER_ENTERING_WORLD", false, true); FIRE("PLAYER_ENTERING_WORLD", false, false)')
check(clash_lines(lua) == [], "a reload or zone change says nothing more (%r)" % lines(lua))

# Help names /eyecandy too while the clash is there.
X('CHAT = {}; SlashCmdList.EYECANDY("help")')
check(len(clash_lines(lua)) == 1, "help names /eyecandy once while another addon has /ec (%r)" % lines(lua))

# A different command such as /ecx is no clash. (Eye Candy's own /ec is the first block.)
lua = boot()
X = lua.execute
X('SLASH_OTHER1 = "/ecx"; SLASH_OTHER2 = 5')
X('CHAT = {}; FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(clash_lines(lua) == [], "a different command such as /ecx is no clash (%r)" % lines(lua))
done()
