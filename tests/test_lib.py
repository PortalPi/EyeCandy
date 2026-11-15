"""Checks for tests/lib.py itself."""
from lib import boot, check, done, toc_files

core_files = [f for f in toc_files() if f in ('Data.lua', 'Core.lua', 'UI.lua', 'Advanced.lua')]
check(core_files == ['Data.lua', 'Core.lua', 'UI.lua', 'Advanced.lua'], "lib reads the .toc file list in order")
lua = boot()
lua.execute('SlashCmdList.EYECANDY("")')
check(lua.eval('EyeCandyMainFrame.shown') == True, "lib boots the addon and the window opens")
done()
