"""Checks for moving, scaling and remembering the Eye Candy windows.
Run: python tests/test_window_scale.py"""
from lib import boot as lib_boot, check, done, GEO, near


def boot(svdb=None):
    lua = lib_boot(svdb=svdb)
    lua.execute(GEO)
    lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY("")')
    return lua


# The maths: the corner follows the cursor, top-left fixed, held to 60% to 130%.
lua = lib_boot()
E = lua.eval
check(near(E('NS.ScaleForCorner(100, 900, 780, 640, 100 + 780 * 1.2, 900 - 640 * 1.2)'), 1.2), "the scale puts the bottom-right corner under the cursor")
check(near(E('NS.ScaleForCorner(100, 900, 780, 640, 100 + 780 * 1.1, 900 - 640 * 0.7)'), 1.1), "the axis dragged further wins, so the corner never sits inside the window")
check(near(E('NS.ScaleForCorner(100, 900, 780, 640, 5000, -5000)'), 1.3), "the scale stops at 130%")
check(near(E('NS.ScaleForCorner(100, 900, 780, 640, 0, 1000)'), 0.6), "the scale stops at 60%")
check(E('NS.ScaleForCorner(nil, 900, 780, 640, 1, 1)') is None, "no scale when the window isn't placed yet")
check(near(E('NS.ClampWindowScale(1.234)'), 1.23) and near(E('NS.ClampWindowScale("x")'), 1), "scales round to whole percents, and junk reads as 100%")

# A window never moved opens centred at 100%.
lua = boot()
E, X = lua.eval, lua.execute
check(near(E('EyeCandyMainFrame.geo.s'), 1) and near(E('EyeCandyMainFrame.geo.l'), (1920 - 780) / 2), "a new window opens centred at 100%")
check(E('EyeCandyMainFrame.scaleGrip') is not None, "the main window has a size grip")

# Press the grip at its centre, about 9 units inside the corner (it is 14 x 14 at -2, 2).
IN = 9
x0, y0 = E('CORNER(EyeCandyMainFrame)')


def press(scale, w=780, h=640, frame='EyeCandyMainFrame'):
    X('G = %s.scaleGrip; CURSOR = { %r, %r }; G.scripts.OnMouseDown(G, "LeftButton")' % (frame, x0 + w * scale - IN, y0 - h * scale + IN))


def drag_to(scale, w=780, h=640):
    X('CURSOR = { %r, %r }; G.scripts.OnUpdate(G, 0.01)' % (x0 + w * scale - IN, y0 - h * scale + IN))


press(1)
check(E('G.scripts.OnUpdate') is not None, "pressing the grip starts the drag")
X('G.scripts.OnUpdate(G, 0.01)')
check(near(E('EyeCandyMainFrame.geo.s'), 1), "a press without moving leaves the size alone")
drag_to(1.2)
x1, y1 = E('CORNER(EyeCandyMainFrame)')
check(near(E('EyeCandyMainFrame.geo.s'), 1.2), "dragging the grip scales the window")
check(near(x1, x0) and near(y1, y0), "the top-left corner stays where it was while scaling")
check(E('EyeCandyMainFrame.geo.w') == 780 and E('EyeCandyMainFrame.geo.h') == 640, "the layout is untouched: the window keeps its size")
X('G.scripts.OnMouseUp(G, "LeftButton")')
check(E('G.scripts.OnUpdate') is None, "letting go ends the drag")
check(near(E('EyeCandyDB.windows.EyeCandyMainFrame.scale'), 1.2) and near(E('EyeCandyDB.windows.EyeCandyMainFrame.x'), x0), "letting go saves the scale and the spot")

# Right-button presses don't start a drag; right-click puts it back to 100%, top-left fixed.
X('G.scripts.OnMouseDown(G, "RightButton")')
check(E('G.scripts.OnUpdate') is None, "a right-button press doesn't start a drag")
X('G.scripts.OnClick(G, "RightButton")')
x2, y2 = E('CORNER(EyeCandyMainFrame)')
check(near(E('EyeCandyMainFrame.geo.s'), 1) and near(x2, x0) and near(y2, y0), "right-click on the grip goes back to 100% without moving the top-left")
check(near(E('EyeCandyDB.windows.EyeCandyMainFrame.scale'), 1), "the 100% is saved")

# Closing the window mid-drag ends the drag and keeps the size reached.
press(1)
drag_to(0.8)
X('G.scripts.OnHide(G)')
check(E('G.scripts.OnUpdate') is None and near(E('EyeCandyDB.windows.EyeCandyMainFrame.scale'), 0.8), "hiding mid-drag stops it and saves the size reached")

# Moving the window saves its spot, and doesn't leave it to the game's layout cache.
X('EyeCandyMainFrame.geo.l, EyeCandyMainFrame.geo.t = 50 / 0.8, 700 / 0.8; EyeCandyMainFrame.scripts.OnDragStop(EyeCandyMainFrame)')
check(near(E('EyeCandyDB.windows.EyeCandyMainFrame.x'), 50) and near(E('EyeCandyDB.windows.EyeCandyMainFrame.y'), 700), "moving the window saves where it is")
check(E('EyeCandyMainFrame.userPlaced') == False, "after a move the window is marked not user-placed, so the game's layout cache doesn't save it")

# A small window: a click alone used to shrink the ask window to about 94%.
X('NS.Ask({ title = "t", text = "x" })')
x0, y0 = E('CORNER(EyeCandyAskFrame)')
press(1, 420, 160, 'EyeCandyAskFrame')
X('G.scripts.OnUpdate(G, 0.01); G.scripts.OnMouseUp(G, "LeftButton")')
check(near(E('EyeCandyAskFrame.geo.s'), 1) and near(E('EyeCandyDB.windows.EyeCandyAskFrame.scale'), 1), "a click on the small ask window's grip leaves it at 100%")
check(E('EyeCandyAskFrame.userPlaced') == False, "a window is marked not user-placed when built, dropping any spot cached by older builds")

# After a reload it opens where it was, at its size. A saved scale out of range is held in range.
lua = boot('EyeCandyDB = { windows = { EyeCandyMainFrame = { x = 50, y = 700, scale = 0.8 }, EyeCandyExportFrame = { scale = 5 } } }')
E, X = lua.eval, lua.execute
x3, y3 = E('CORNER(EyeCandyMainFrame)')
check(near(x3, 50) and near(y3, 700) and near(E('EyeCandyMainFrame.geo.s'), 0.8), "after a reload the window opens where it was left, at its size")
X('NS.ShowText("hello")')
check(near(E('EyeCandyExportFrame.geo.s'), 1.3), "a saved scale above 130% opens at 130%")
check(near(E('EyeCandyExportFrame.geo.l'), (1920 / 1.3 - 640) / 2), "a window with only a saved size still opens centred")

# Every Eye Candy window drags, scales and remembers.
X('NS.Ask({ title = "t", text = "x" })')
for name in ["EyeCandyMainFrame", "EyeCandyExportFrame", "EyeCandyAskFrame"]:
    check(E('%s.scaleGrip ~= nil and %s.scripts.OnDragStop ~= nil and %s.windowName == "%s"' % (name, name, name, name)), name + " has the grip and remembers where it is moved")

done()
