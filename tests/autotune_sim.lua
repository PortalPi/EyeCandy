-- A pretend PC for the Autotune checks (tests/test_autotune*.py). Load it after lib.boot():
--   lua.execute(open('tests/autotune_sim.lua').read())
-- Then SIM runs a whole tune on the pure logic, and GAME_SETUP() makes the run in the game playable.

AT = NS.Autotune
STATE = {}
-- FPS = BASE / (1 + the cost of every setting's level). COST[cvar][value] is the extra cost; settings not
-- listed cost nothing. Each check sets BASE and COST to shape the PC.
-- SPLIT, when set, is a PC whose CPU and graphics card each take time per frame (ms), and the slower one sets
-- FPS. The graphics card's time grows with the pixels drawn (render scale squared). CAP, when set, holds FPS
-- at a screen's refresh rate (Vertical Sync). SLOWF and LOWF, when set, give the slowest 5% and 1% of frames
-- from the average (an uneven PC); else the slowest 5% is left out and the 1% is 80% of the average.
function MODEL()
  if SPLIT then
    local s = tonumber(STATE.RenderScale or 1)
    local cpu, gpu = SPLIT.cpu, SPLIT.gpu
    for cvar, v in pairs(STATE) do
      local c = (SPLIT.cpuCost or {})[cvar]
      if c then cpu = cpu + (c[tostring(v)] or 0) end
      c = (SPLIT.gpuCost or {})[cvar]
      if c then gpu = gpu + (c[tostring(v)] or 0) end
    end
    return 1000 / math.max(cpu, gpu * s * s)
  end
  local load = 0
  for cvar, v in pairs(STATE) do
    local c = COST[cvar]
    if c then load = load + (c[tostring(v)] or 0) end
  end
  return BASE / (1 + load)
end
-- One measurement of the pretend PC, as AT.Stats would give it.
function MEASURE(n, opts)
  local fps = MODEL()
  if opts.noise then fps = fps * opts.noise(n) end
  local spread = 0.1
  if CAP and fps >= CAP then fps, spread = CAP, 0.004 end
  return { fps = fps, low = LOWF and LOWF(fps) or fps * 0.8, slow = SLOWF and SLOWF(fps) or nil,
    steady = true, spread = spread, frames = 400 }
end
-- COST shaped like AT.KNOBS' own cost guesses: each step adds its cost points x k.
function KNOBCOST(k)
  COST = {}
  for _, d in ipairs(AT.KNOBS) do
    local c = COST[d.cvar] or {}
    local sum = c[tostring(d.steps[1][1])] or 0
    for i, s in ipairs(d.steps) do
      if i > 1 then sum = sum + s[3] * k end
      c[tostring(s[1])] = sum
    end
    COST[d.cvar] = c
  end
end
-- Runs a whole tune with the pretend PC. Returns the last action, the list of tries, how many measurements
-- and the run. opts: current, exists, supported, noise, style (a way of tuning, AT.STYLES), from (a preset
-- to start from: { values, keep }).
function SIM(mode, goal, opts)
  opts = opts or {}
  STATE = {}
  for cvar, v in pairs(opts.current or {}) do STATE[cvar] = v end
  local run = AT.NewRun(mode, goal, {
    exists = opts.exists or function() return true end,
    supported = opts.supported or function() return true end,
    current = opts.current or {},
  }, opts.style, opts.from)
  local tries, n = {}, 0
  local action = AT.Step(run, nil)
  while not action.done do
    for cvar, v in pairs(action.set or {}) do STATE[cvar] = v end
    if action.try then tries[#tries + 1] = action.try end
    n = n + 1
    LASTM = MEASURE(n, opts)
    action = AT.Step(run, LASTM)
  end
  for cvar, v in pairs(action.set or {}) do STATE[cvar] = v end
  return action, tries, n, run
end

-- The run in the game: the pretend PC reads the game's settings, and frames arrive through the run's OnUpdate.
function GAME_SETUP()
  MOVING, FACING = false, 1.0
  function IsPlayerMoving() return MOVING end
  function GetPlayerFacing() return FACING end
  -- Where you stand, and the camera.
  ZOOM, MOUSELOOK, MOUSEDOWN = 15, false, false
  function GetCameraZoom() return ZOOM end
  function IsMouselooking() return MOUSELOOK end
  function IsMouseButtonDown() return MOUSEDOWN end
  function GetMouseFoci() return {} end -- over the world
  function GetRealZoneText() return "Stormwind City" end
  function GetSubZoneText() return "Trade District" end
  C_Map = { GetBestMapForUnit = function() return 84 end,
    GetPlayerMapPosition = function() return { GetXY = function() return 0.621, 0.704 end } end }
  C_CVar.RegisterCVar("cameraFov", "90")
  function GAMEFPS()
    local load = 0
    for cvar, c in pairs(COST) do load = load + (c[tostring(tonumber(GetCVar(cvar)))] or 0) end
    return BASE / (1 + load)
  end
  -- Plays frames until the run ends or n frames pass. at(i): something to do on frame i.
  function PLAY(n, at)
    local f = AT.frame
    PLAYTIME = 0
    for i = 1, n or 400000 do
      if not AT.IsRunning() then return i end
      if at then at(i) end
      local dt = (HITCHES and i % HITCHES == 0) and 0.3 or 1 / GAMEFPS()
      PLAYTIME = PLAYTIME + dt
      f.scripts.OnUpdate(f, dt)
    end
  end
  FIRE("PLAYER_LOGIN")
end
