-- Minimal WoW API stubs
local cvars = {
  RenderScale={"1","1"}, useTargetFPS={"1","0"}, textureFilteringMode={"5","3"}, ResampleAlwaysSharpen={"0","0"},
  graphicsShadowQuality={"5","3"}, graphicsLightMode={"3","1"}, graphicsSSAO={"4","2"}, graphicsDepthEffects={"3","2"},
  graphicsComputeEffects={"4","2"}, weatherDensity={"2","2"}, graphicsLiquidDetail={"3","2"}, graphicsPBRLiquidDetail={"2","1"},
  graphicsTextureResolution={"2","2"}, graphicsProjectedTextures={"1","1"}, graphicsViewDistance={"9","5"},
  graphicsEnvironmentDetail={"9","5"}, farclip={"7000","5000"}, horizonClip={"5000","5000"},
  cameraDistanceMaxZoomFactor={"1.9","1.9"}, graphicsGroundClutter={"9","5"}, groundEffectDensity={"48","16"},
  groundEffectDist={"320","100"}, groundEffectFade={"70","70"}, graphicsParticleDensity={"4","3"}, graphicsSpellDensity={"2","1"},
  vsync={"1","0"}, Gamma={"1","1"}, vrsValar={"1","0"}, doodadLodScale={"150","100"}, lodObjectFadeScale={"150","100"}, lodObjectCullSize={"14","15"}, terrainLodDist={"650","400"}, TerrainLodDiv={"768","768"}, wmoLodDist={"400","300"}, dynamicLod={"1","1"}, maxLightDist={"2048","2048"}, ResampleQuality={"3","3"}, ResampleSharpness={"0.2","0.2"}, entityLodDist={"10","10"},
}
-- horizonStart deliberately missing to test "not in this client"
CLAMP = { cameraDistanceMaxZoomFactor = 2.6 } -- client clamps zoom
SUPPORTED_MAX = { graphicsParticleDensity = 4 } -- index 5 illegal when secondary lighting is on
SETLOG = {}
function GetCVar(n) return cvars[n] and cvars[n][1] end
function GetCVarDefault(n) return cvars[n] and cvars[n][2] end
function GetCVarBool(n) return GetCVar(n) == "1" end
function SetCVar(n, v)
  if not cvars[n] then return false end
  local x = tonumber(v)
  if CLAMP[n] and x and x > CLAMP[n] then x = CLAMP[n] end
  cvars[n][1] = x and (x == math.floor(x) and tostring(math.floor(x)) or tostring(x)) or tostring(v)
  SETLOG[#SETLOG+1] = n
  return true
end
C_CVar = {
  GetCVarInfo = function(n) if cvars[n] then return cvars[n][1], cvars[n][2] end end,
  SetCVar = function(n, v) cvars[n] = cvars[n] or {"",""}; cvars[n][1] = tostring(v); return true end,
  RegisterCVar = function(n, d) cvars[n] = cvars[n] or {d, d} end,
}
function IsGraphicsSettingValueSupported(cvar, v) if SUPPORTED_MAX[cvar] and v > SUPPORTED_MAX[cvar] then return 1 end return 0 end
function GetMinRenderScale() return 0.33 end
function GetMaxRenderScale() return 2 end
function GetBuildInfo() return "1.60.1", "70790", "Nov 4 2026", 16001 end
function InCombatLockdown() return INCOMBAT or false end
function IsShiftKeyDown() return false end
function date(f) return "2026-11-06 10:40" end
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
tinsert = table.insert
UISpecialFrames = {}
CHAT = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) CHAT[#CHAT+1] = m end }
TIMERS = {}
C_Timer = { After = function(_, f) TIMERS[#TIMERS+1] = f end }
C_VideoOptions = {
  GetGxAdapterInfo = function() return { { name = "NVIDIA GeForce RTX 3090", isLowPower = false } } end,
  GetCurrentGameWindowSize = function() return { x = 2560, y = 1440 } end,
  IsPBRWaterSupported = function() return true end, IsSecondaryLightingSupported = function() return true end,
  IsOutlineModeSupported = function() return true end, IsLinearEnabledOnStart = function() return true end,
  AreHighResTexturesAvailable = function() return false end,
}
Enum = { ForeverExperiencePreset = { Classic = 0, Enhanced = 1 }, ConsoleCategory = { Graphics = 1 }, ConsoleCommandType = { Cvar = 0 } }
C_GameRules = { GetForeverExperiencePreset = function() return 1 end }
function ConsoleGetAllCommands() local t = {} for k in pairs(cvars) do t[#t+1] = { command = k, category = 1, commandType = 0 } end return t end
-- Generic frame stub: every method returns nil, scripts stored
local FrameMT = {}
FrameMT.__index = function(t, k)
  if k == "SetScript" then return function(self, ev, fn) self.scripts[ev] = fn end end
  if k == "HookScript" then return function(self, ev, fn) self.hooks[ev] = fn end end
  if k == "GetChecked" then return function() return true end end
  if k == "IsShown" then return function(self) return self.shown end end
  if k == "SetShown" then return function(self, s) self.shown = s; if s and self.scripts.OnShow then self.scripts.OnShow(self) end end end
  if k == "Show" then return function(self) self.shown = true end end
  if k == "Hide" then return function(self) self.shown = false end end
  if k == "SetText" then return function(self, s) self.text = s end end
  if k == "CreateFontString" or k == "CreateTexture" then return function() return setmetatable({ scripts = {}, hooks = {} }, FrameMT) end end
  if type(k) == "string" and k:match("^%u") then return function() end end
  return nil
end
function CreateFrame(kind, name, parent, template)
  local f = setmetatable({ scripts = {}, hooks = {}, kind = kind }, FrameMT)
  if name then _G[name] = f end
  return f
end
SettingsPanel = CreateFrame("Frame")
GameTooltip = CreateFrame("Frame")
ChatFontNormal = {}
SlashCmdList = {}
function GameTooltip_Hide() end

-- Error handler, stack and add-on metadata (used by Report.lua)
ERRSEEN = 0
local errorHandler = function(msg) ERRSEEN = ERRSEEN + 1 end
function geterrorhandler() return errorHandler end
function seterrorhandler(f) errorHandler = f end
DEBUGSTACK = ""
function debugstack() return DEBUGSTACK end
function GetAddOnMetadata(addon, field) if addon == "EyeCandy" and field == "Version" then return "1.0.0-test" end end

function DUMP(n) return GetCVar(n) end

-- Presets and backups (1.0.0 steps 3 and 4)
function UnitName(unit) return "Tester" end
function GetRealmName() return "Testrealm" end
CLOCK = 1763200000
function time() CLOCK = CLOCK + 60; return CLOCK end

-- C_EncodingUtil stand-in. Base64 is real (RFC 4648 standard alphabet). Compression and CBOR are
-- not the real formats, but they round-trip faithfully and, like the game's, error on bad input
-- (DecompressString is documented to raise an error on invalid data; the CBOR decoder here also
-- errors, so callers must pcall every decode).
do
  local B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  local idx = {}
  for i = 1, 64 do idx[B64:sub(i, i)] = i - 1 end

  local function encode64(s)
    local out = {}
    for i = 1, #s, 3 do
      local a, b, c = s:byte(i, i + 2)
      local n = a * 65536 + (b or 0) * 256 + (c or 0)
      local c1 = math.floor(n / 262144) % 64
      local c2 = math.floor(n / 4096) % 64
      local c3 = math.floor(n / 64) % 64
      local c4 = n % 64
      out[#out + 1] = B64:sub(c1 + 1, c1 + 1) .. B64:sub(c2 + 1, c2 + 1)
        .. (b and B64:sub(c3 + 1, c3 + 1) or "=") .. (c and B64:sub(c4 + 1, c4 + 1) or "=")
    end
    return table.concat(out)
  end

  local function decode64(s)
    s = s:gsub("%s", "")
    if #s % 4 ~= 0 then return nil end
    local out = {}
    for i = 1, #s, 4 do
      local chunk = s:sub(i, i + 3)
      local pad = select(2, chunk:gsub("=", ""))
      if chunk:find("=[^=]") then return nil end
      local n = 0
      for j = 1, 4 do
        local ch = chunk:sub(j, j)
        local v = (ch == "=") and 0 or idx[ch]
        if v == nil then return nil end
        n = n * 64 + v
      end
      local bytes = string.char(math.floor(n / 65536) % 256, math.floor(n / 256) % 256, n % 256)
      out[#out + 1] = bytes:sub(1, 3 - pad)
    end
    return table.concat(out)
  end

  local function checksum(s)
    local a, b = 1, 0
    for i = 1, #s do a = (a + s:byte(i)) % 65521; b = (b + a) % 65521 end
    return b * 65536 + a
  end

  local function ser(v, out, depth)
    if depth > 100 then error("SerializeCBOR: too deep") end
    local t = type(v)
    if t == "string" then out[#out + 1] = "s" .. #v .. ":" .. v
    elseif t == "number" then local s = string.format("%.17g", v); out[#out + 1] = "n" .. #s .. ":" .. s
    elseif t == "boolean" then out[#out + 1] = v and "T" or "F"
    elseif t == "nil" then out[#out + 1] = "N"
    elseif t == "table" then
      out[#out + 1] = "{"
      for k, x in pairs(v) do ser(k, out, depth + 1); ser(x, out, depth + 1) end
      out[#out + 1] = "}"
    else error("SerializeCBOR: unsupported type " .. t) end
  end

  local function des(s, pos, depth)
    if depth > 100 then error("DeserializeCBOR: too deep") end
    local tag = s:sub(pos, pos)
    if tag == "s" or tag == "n" then
      local len, rest = s:match("^(%d+):()", pos + 1)
      if not len then error("DeserializeCBOR: bad length") end
      len = tonumber(len)
      local body = s:sub(rest, rest + len - 1)
      if #body ~= len then error("DeserializeCBOR: truncated") end
      if tag == "n" then
        local n = tonumber(body)
        if not n then error("DeserializeCBOR: bad number") end
        return n, rest + len
      end
      return body, rest + len
    elseif tag == "T" then return true, pos + 1
    elseif tag == "F" then return false, pos + 1
    elseif tag == "N" then return nil, pos + 1
    elseif tag == "{" then
      local t = {}
      pos = pos + 1
      while s:sub(pos, pos) ~= "}" do
        if pos > #s then error("DeserializeCBOR: unterminated map") end
        local k, v
        k, pos = des(s, pos, depth + 1)
        v, pos = des(s, pos, depth + 1)
        if k == nil then error("DeserializeCBOR: nil key") end
        t[k] = v
      end
      return t, pos + 1
    end
    error("DeserializeCBOR: unknown item")
  end

  C_EncodingUtil = {
    EncodeBase64 = function(s) return encode64(s) end,
    DecodeBase64 = function(s) return decode64(s) end,
    CompressString = function(s) return "DFL" .. checksum(s) .. ":" .. s end,
    DecompressString = function(s)
      local sum, body = s:match("^DFL(%d+):(.*)$")
      if not sum or tonumber(sum) ~= checksum(body) then error("DecompressString: invalid data") end
      return body
    end,
    SerializeCBOR = function(v) local out = {}; ser(v, out, 0); return table.concat(out) end,
    DeserializeCBOR = function(s)
      local v, pos = des(s, 1, 0)
      if pos ~= #s + 1 then error("DeserializeCBOR: trailing data") end
      return v
    end,
  }
  -- Test helpers: build a share string from any Lua value, and open one back up.
  function MAKE_SHARE(v, prefix)
    return (prefix or "!EC1!") .. C_EncodingUtil.EncodeBase64(C_EncodingUtil.CompressString(C_EncodingUtil.SerializeCBOR(v)))
  end
  function OPEN_SHARE(s)
    return C_EncodingUtil.DeserializeCBOR(C_EncodingUtil.DecompressString(C_EncodingUtil.DecodeBase64(s:sub(6))))
  end
end

-- Window stubs (minimap button, Options > AddOns entry)
Minimap = CreateFrame("Frame")
function GetCursorPosition() return 0, 0 end
function HideUIPanel(f) if f then f.shown = false end end
SETTINGS_CATEGORIES = {}
Settings = {
  RegisterCanvasLayoutCategory = function(frame, name) local c = { frame = frame, name = name }; return c end,
  RegisterAddOnCategory = function(c) SETTINGS_CATEGORIES[#SETTINGS_CATEGORIES+1] = c end,
}
