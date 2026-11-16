-- Eye Candy: the Standard tab. Mirrors the game's own Graphics menu (Base quality only), with the game's
-- own labels and tooltip strings, so it reads like the menu and translates itself.
-- Facts per setting (CVar, label and tooltip global strings, option values) are from Blizzard's Forever
-- UI source (Blizzard_SettingsDefinitions_Shared/Graphics.lua); the labels, tooltips and defaults below are read from there.
--
-- Row fields:
--   cvar     the CVar it reads and writes (nil for Resolution, which has none)
--   label    { GLOBAL_STRING, "English fallback" }, or a function returning one
--   tip      { GLOBAL_STRING, "English fallback" }, or a function returning one
--   kind     "choice" (named levels), "toggle" (on/off), "range" (slider), "info" (shown, changed in the game's menu)
--   options  choice: { { value, { GLOBAL_STRING, "fallback" } }, ... }, or a function returning that
--   min, max, step   range: CVar units (min and max may be functions)
--   percent  show value x 100 with a % sign; suffix: text after the value; plusOne: show value + 1 (the game's 1 to 10)
--   invert   range: the bar runs the other way (the game's Resample Sharpness: right = sharper = lower value)
--   check    range: a CVar for an on/off box in front of the slider (Max FPS and Target FPS)
--   on, off  toggle: the CVar values for on and off (default "1" and "0")
--   shown    a function; the row is left out when it returns false (hardware the game also checks)
--   read     info: a function returning the text to show
--   master   Base Game Quality: moving it sets every quality row below, as the game's slider does
--   device = true   your PC's own setup (monitor, GPU, API): never saved in presets or backups
--   own = true      your own choice (FPS limits, latency, vsync, buffering, physics): never saved in presets or
--                   backups either, because an imported preset sets everything it leaves out to the game default
--   restart = true  takes effect after a game restart

local _, ns = ...

local function G(global, fallback) return { global, fallback } end
local function Call(f, ...)
	if type(f) ~= "function" then return nil end
	local ok, a, b, c = pcall(f, ...)
	if ok then return a, b, c end
	return nil
end
local function Has(f) return type(f) ~= "function" or Call(f) ~= false end
local VO = function(name) return C_VideoOptions and C_VideoOptions[name] end

local OFFON = { { "0", G("VIDEO_OPTIONS_DISABLED", "Disabled") }, { "1", G("VIDEO_OPTIONS_ENABLED", "Enabled") } }
local LOW, FAIR, GOOD, HIGH, ULTRA = G("VIDEO_OPTIONS_LOW", "Low"), G("VIDEO_OPTIONS_FAIR", "Fair"),
	G("VIDEO_OPTIONS_MEDIUM", "Good"), G("VIDEO_OPTIONS_HIGH", "High"), G("VIDEO_OPTIONS_ULTRA", "Ultra")
local DISABLED = G("VIDEO_OPTIONS_DISABLED", "Disabled")

local function Levels(...)
	local list = {}
	for i = 1, select("#", ...) do list[i] = { tostring(i - 1), (select(i, ...)) } end
	return list
end

local function GraphicsAPIs()
	local list = { { "auto", G("GXAPI_AUTO", "Auto Detect") } }
	local r = { pcall(GetGraphicsAPIs) }
	local apis = {}
	if r[1] then
		if type(r[2]) == "table" then apis = r[2] else for i = 2, #r do apis[#apis + 1] = r[i] end end
	end
	for _, api in ipairs(apis) do
		api = tostring(api):lower()
		if api ~= "auto" then list[#list + 1] = { api, G("GXAPI_" .. api:upper(), api) } end
	end
	return list
end

local function GraphicsCards()
	local list = { { "", G("GX_ADAPTER_AUTO_DETECT", "Auto Detect") } }
	for _, a in ipairs(Call(VO("GetGxAdapterInfo")) or {}) do
		local fmt = (a.isExternal and (GX_ADAPTER_EXTERNAL or "%s (External)")) or (a.isLowPower and (GX_ADAPTER_LOW_POWER or "%s (Low Power)")) or "%s"
		list[#list + 1] = { a.name, { nil, fmt:format(a.name) } }
	end
	return list
end

ns.STANDARD = {
	{
		key = "display", name = G("DISPLAY_LABEL", "Display"),
		rows = {
			{ cvar = "gxMonitor", kind = "info", device = true, label = G("PRIMARY_MONITOR", "Monitor"),
				tip = G("OPTION_TOOLTIP_PRIMARY_MONITOR", "Allows you to change the primary monitor used by the display."),
				read = function()
					local v = tonumber((ns.GetInfo("gxMonitor"))) or 0
					if v == 0 then return VIDEO_OPTIONS_MONITOR_PRIMARY or "Primary" end
					return Call(GetMonitorName, v + 1) or (VIDEO_OPTIONS_MONITOR or "Monitor %d"):format(v)
				end },
			{ cvar = "gxMaximize", kind = "info", device = true, label = G("DISPLAY_MODE", "Display Mode"),
				tip = G("OPTION_TOOLTIP_DISPLAY_MODE", "Set the game to run in Fullscreen or Windowed mode."),
				read = function()
					if ns.Same(ns.GetInfo("gxMaximize"), "1") then return VIDEO_OPTIONS_WINDOWED_FULLSCREEN or "Fullscreen (Windowed)" end
					return VIDEO_OPTIONS_WINDOWED or "Windowed"
				end },
			{ key = "resolution", kind = "info", device = true, label = G("WINDOW_SIZE", "Resolution"),
				tip = G("OPTION_TOOLTIP_WINDOW_SIZE", "Adjust the resolution of the game"),
				read = function()
					local size = Call(VO("GetCurrentGameWindowSize"))
					if type(size) == "table" and size.x then return math.floor(size.x) .. "x" .. math.floor(size.y) end
					return "n/a"
				end },
			{ cvar = "RenderScale", kind = "range", percent = true, step = 0.01,
				min = function() return Call(GetMinRenderScale) or 0.33 end, max = function() return Call(GetMaxRenderScale) or 2 end,
				label = G("RENDER_SCALE", "Render Scale"),
				tip = G("OPTION_TOOLTIP_RENDER_SCALE", "Changes the resolution for rendering the 3D World. Lowering the render scale below 100% reduces the GPU workload and can greatly improve frame rate in some cases. Render scale above 100% is for supersampled anti-aliasing (SSAA). SSAA is very expensive for the GPU and only recommended if you are unsatisfied with the other anti-aliasing options offered.") },
			{ cvar = "useUiScale", kind = "info", device = true, label = G("USE_UISCALE", "Use UI Scale"),
				tip = G("OPTION_TOOLTIP_USE_UISCALE", "Check to use the UI Scale Slider, uncheck to use the system default scale."),
				read = function()
					if not ns.Same(ns.GetInfo("useUiScale"), "1") then return "Off" end
					local s = tonumber((ns.GetInfo("uiscale")))
					return "On" .. (s and (", " .. math.floor(s * 100 + 0.5) .. "%") or "")
				end },
			{ cvar = "vsync", own = true, kind = "toggle", label = G("VERTICAL_SYNC", "Vertical Sync"),
				tip = G("OPTION_TOOLTIP_VERTICAL_SYNC", "Synchronizes your framerate to some fraction of your monitor's refresh rate. Enable this if you see excessive screen tearing in game.") },
			{ cvar = "LowLatencyMode", own = true, kind = "choice", label = G("LOW_LATENCY_MODE", "Low Latency Mode"),
				tip = G("OPTION_TOOLTIP_LOW_LATENCY_MODE", "Allows the game to use various techniques to reduce input latency"),
				options = Levels(G("GX_ADAPTER_AUTO_DETECT", "Auto Detect"), DISABLED, G("VIDEO_OPTIONS_BUILTIN", "Built-in"),
					G("VIDEO_OPTIONS_NVIDIA_REFLEX", "NVIDIA Reflex"), G("VIDEO_OPTIONS_NVIDIA_REFLEX_BOOST", "NVIDIA Reflex + Boost"), G("VIDEO_OPTIONS_INTEL_XELL", "Intel XeLL")) },
			{ cvar = "ffxAntiAliasingMode", kind = "choice", label = G("FXAA_CMAA_LABEL", "Image-Based Techniques"),
				tip = G("OPTION_TOOLTIP_ANTIALIASING_IB", "Anti-aliasing techniques using only the existing full-screen renders"),
				options = Levels(G("VIDEO_OPTIONS_NONE", "None"), G("ANTIALIASING_FXAA_LOW", "FXAA Low"), G("ANTIALIASING_FXAA_HIGH", "FXAA High"),
					G("ANTIALIASING_CMAA", "CMAA"), G("ANTIALIASING_CMAA2", "CMAA 2")) },
			{ cvar = "cameraFov", kind = "range", step = 1,
				min = function() local _, lo = Call(GetCameraFOVDefaults); return lo or 50 end,
				max = function() local _, _, hi = Call(GetCameraFOVDefaults); return hi or 90 end,
				label = G("CAMERA_FOV", "Camera FOV"), tip = G("OPTION_TOOLTIP_CAMERA_FOV", "Adjust the camera field of view") },
		},
	},
	{
		key = "quality", name = G("GRAPHICS_QUALITY", "Graphics Quality"),
		note = "Base settings. The game's Raid and Battleground set isn't shown here.",
		rows = {
			{ cvar = "graphicsQuality", kind = "range", min = 0, max = 9, step = 1, plusOne = true, master = true,
				label = G("BASE_GRAPHICS_QUALITY", "Base Game Quality"), tip = G("OPTION_TOOLTIP_GRAPHICS_QUALITY", nil) },
			{ cvar = "graphicsShadowQuality", kind = "choice", label = G("SHADOW_QUALITY", "Shadow Quality"),
				tip = G("OPTION_TOOLTIP_SHADOW_QUALITY", "Controls both the method and quality of shadows. Decreasing this may greatly improve performance."),
				options = Levels(LOW, FAIR, GOOD, HIGH, ULTRA, G("VIDEO_OPTIONS_ULTRA_HIGH", "Ultra High")) },
			{ cvar = "graphicsLiquidDetail", kind = "choice",
				label = function() return Call(VO("IsPBRWaterSupported")) and G("LEGACY_LIQUID_DETAIL", "Legacy Liquid Detail") or G("LIQUID_DETAIL", "Liquid Detail") end,
				tip = function() return Call(VO("IsPBRWaterSupported")) and G("OPTION_TOOLTIP_LEGACY_LIQUID_DETAIL", "Controls the rendering quality of older liquids.")
					or G("OPTION_TOOLTIP_LIQUID_DETAIL", "Controls the rendering quality of liquid. Decreasing this may improve performance.") end,
				options = Levels(LOW, FAIR, GOOD, HIGH) },
			{ cvar = "graphicsPBRLiquidDetail", kind = "choice", shown = function() return Has(VO("IsPBRWaterSupported")) end,
				label = G("PBR_LIQUID_DETAIL", "PBR Liquid Detail"),
				tip = G("OPTION_TOOLTIP_PBR_LIQUID_DETAIL", "Controls the rendering quality of new, Physically Based, liquids."),
				options = Levels(LOW, HIGH, ULTRA) },
			{ cvar = "graphicsParticleDensity", kind = "choice", minQuality = 1, label = G("PARTICLE_DENSITY", "Particle Density"),
				tip = G("OPTION_TOOLTIP_PARTICLE_DENSITY", "Controls the number of particles used in effects caused by spells, fires, etc. Decrease to improve performance."),
				-- The game uses two layouts, picked by whether secondary lighting is supported.
				options = function()
					if Call(VO("IsSecondaryLightingSupported")) then return Levels(LOW, FAIR, GOOD, HIGH, ULTRA) end
					return Levels(DISABLED, LOW, FAIR, GOOD, HIGH, ULTRA)
				end },
			{ cvar = "graphicsSSAO", kind = "choice", label = G("SSAO_LABEL", "SSAO"),
				tip = G("OPTION_TOOLTIP_SSAO", "Controls the rendering quality of the advanced lighting effects. Decreasing this may greatly improve performance."),
				options = Levels(DISABLED, LOW, GOOD, HIGH, ULTRA) },
			{ cvar = "graphicsDepthEffects", kind = "choice", label = G("DEPTH_EFFECTS", "Depth Effects"),
				tip = G("OPTION_TOOLTIP_DEPTH_EFFECTS", "Controls the rendering of depth-based particle effects.  Decreasing this may improve performance."),
				options = Levels(DISABLED, LOW, GOOD, HIGH) },
			{ cvar = "graphicsComputeEffects", kind = "choice", label = G("COMPUTE_EFFECTS", "Compute Effects"),
				tip = G("OPTION_TOOLTIP_COMPUTE_EFFECTS", "Controls the quality of Compute-based effects such as Volumetric Fog and some particle effects. Compute-based effects may be more expensive for older graphics cards."),
				options = Levels(LOW, FAIR, GOOD, HIGH, ULTRA) },
			{ cvar = "graphicsTextureResolution", kind = "choice", label = G("TEXTURE_DETAIL", "Texture Resolution"),
				tip = G("OPTION_TOOLTIP_TEXTURE_DETAIL", "Controls the level of all texture detail. Decreasing this may slightly improve performance."),
				options = Levels(LOW, FAIR, HIGH) },
			{ cvar = "graphicsSpellDensity", kind = "choice", shown = function() return Has(IsSpellVisualDensitySystemSupported) end,
				label = G("SPELL_DENSITY", "Spell Density"), tip = G("OPTION_TOOLTIP_SPELL_DENSITY", "Controls visibility of non-essential spells."),
				options = Levels(G("VIDEO_OPTIONS_SFX_DENSITY_MIN", "Essential"), G("VIDEO_OPTIONS_SFX_DENSITY_REDUCED", "Reduced"), G("VIDEO_OPTIONS_SFX_DENSITY_FULL", "Everything")) },
			{ cvar = "graphicsProjectedTextures", kind = "toggle", label = G("PROJECTED_TEXTURES", "Projected Textures"),
				tip = G("OPTION_TOOLTIP_PROJECTED_TEXTURES", "Enables the projecting of textures to the environment. Disabling this may improve performance.") },
			{ cvar = "graphicsLightMode", kind = "choice", shown = function() return Has(VO("IsSecondaryLightingSupported")) end,
				label = G("LIGHTING_MODE", "Secondary Lighting"), tip = G("OPTION_TOOLTIP_LIGHTING_MODE", "Controls the detail level of secondary lighting effects"),
				options = Levels(FAIR, GOOD, HIGH, ULTRA) },
			{ cvar = "graphicsViewDistance", kind = "range", min = 0, max = 9, step = 1, plusOne = true, label = G("FARCLIP", "View Distance"),
				tip = G("OPTION_TOOLTIP_FARCLIP", "View distance controls how far you can see. Larger view distances require more memory and a faster processor.") },
			{ cvar = "graphicsEnvironmentDetail", kind = "range", min = 0, max = 9, step = 1, plusOne = true, label = G("ENVIRONMENT_DETAIL", "Environment Detail"),
				tip = G("OPTION_TOOLTIP_ENVIRONMENT_DETAIL", "Controls how far you can see objects. Decrease to improve performance.") },
			{ cvar = "graphicsGroundClutter", kind = "range", min = 0, max = 9, step = 1, plusOne = true, label = G("GROUND_CLUTTER", "Ground Clutter"),
				tip = G("OPTION_TOOLTIP_GROUND_CLUTTER", "Controls the density and the distance at which ground clutter items, like grass and foliage, are placed. Decrease to improve performance.") },
		},
	},
	{
		key = "advanced", name = G("ADVANCED_LABEL", "Advanced"),
		rows = {
			{ cvar = "gxMaxFrameLatency", own = true, kind = "toggle", on = "3", off = "2", restart = true, label = G("TRIPLE_BUFFER", "Triple Buffering"),
				tip = G("OPTION_TOOLTIP_TRIPLE_BUFFER", "Triple buffering evens out frame rate spikes but may slightly increase input latency on slower GPUs.\nEnabled: Triple Buffering\nDisabled: Double Buffering") },
			{ cvar = "textureFilteringMode", kind = "choice", label = G("ANISOTROPIC", "Texture Filtering"),
				tip = G("OPTION_TOOLTIP_ANISOTROPIC", "Increases texture sharpness, particularly for textures viewed at an angle."),
				options = Levels(G("VIDEO_OPTIONS_BILINEAR", "Bilinear"), G("VIDEO_OPTIONS_TRILINEAR", "Trilinear"), G("VIDEO_OPTIONS_2XANISOTROPIC", "2x Anisotropic"),
					G("VIDEO_OPTIONS_4XANISOTROPIC", "4x Anisotropic"), G("VIDEO_OPTIONS_8XANISOTROPIC", "8x Anisotropic"), G("VIDEO_OPTIONS_16XANISOTROPIC", "16x Anisotropic")) },
			-- Above 100% render scale the game uses Bicubic whatever this says (its own tooltip), so it greys out.
			{ cvar = "ResampleQuality", kind = "choice", label = G("RESAMPLE_QUALITY", "Resample Quality"),
				ignoredWhen = function() return ns.RenderScaleAbove100() end,
				ignoredNote = "Ignored now: render scale is above 100%, so the game uses Bicubic.",
				tip = G("OPTION_TOOLTIP_RESAMPLE_QUALITY", "When using a Render Scale that is not 100%, this adjusts the quality of the upscale/downscale. Note: Point and FidelityFX Super Resolution are only used for upscaling. If Render Scale is above 100%, Bicubic is used for SSAA instead."),
				options = Levels(G("RESAMPLE_QUALITY_POINT", "Point"), G("RESAMPLE_QUALITY_BILINEAR", "Bilinear"), G("RESAMPLE_QUALITY_BICUBIC", "Bicubic"), G("RESAMPLE_QUALITY_FSR", "FidelityFX Super Resolution 1.0")) },
			{ cvar = "vrsValar", kind = "choice", label = G("VRS_MODE", "VRS Mode"),
				tip = G("OPTION_TOOLTIP_VRS_MODE", "Controls intensity of Variable Rate Shading (VRS) features. VRS is a GPU hardware feature that reduces the GPU workload without significantly reducing visual quality. Enabling this feature on supported hardware may improve FPS."),
				options = Levels(DISABLED, G("VIDEO_OPTIONS_STANDARD", "Standard"), G("VIDEO_OPTIONS_AGGRESSIVE", "Aggressive")) },
			{ cvar = "gxapi", kind = "choice", lower = true, device = true, restart = true, label = G("GXAPI", "Graphics API"),
				tip = G("OPTION_TOOLTIP_GXAPI", "Select the graphics API."), options = GraphicsAPIs },
			{ cvar = "physicsLevel", own = true, kind = "choice", restart = true, label = G("PHYSICS_INTERACTION", "Physics Interactions"),
				tip = G("OPTION_PHYSICS_OPTIONS", "Select physics interactions with the environment."),
				options = Levels(G("NO_ENVIRONMENT_INTERACTION", "None"), G("PLAYER_ONLY_INTERACTION", "Player Only"), G("PLAYER_AND_NPC_INTERACTION", "Player and NPC")) },
			{ cvar = "gxAdapter", kind = "choice", device = true, restart = true, label = G("GRAPHICS_CARD", "Graphics Card"),
				tip = G("OPTION_TOOLTIP_GRAPHICS_CARD", "Select which graphics card you want to use."), options = GraphicsCards },
			{ cvar = "maxFPS", own = true, check = "useMaxFPS", kind = "range", min = 8, max = 200, step = 1, suffix = " FPS", label = G("MAXFPS", "Max Foreground FPS"),
				tip = G("OPTION_MAXFPS_CHECK", "Enable this option to limit the foreground framerate") },
			{ cvar = "maxFPSBk", own = true, check = "useMaxFPSBk", kind = "range", min = 8, max = 200, step = 1, suffix = " FPS", label = G("MAXFPSBK", "Max Background FPS"),
				tip = G("OPTION_MAXFPSBK_CHECK", "Enable this option to limit the background framerate") },
			{ cvar = "targetFPS", own = true, check = "useTargetFPS", kind = "range", min = 8, max = 200, step = 1, suffix = " FPS", label = G("TARGETFPS", "Target FPS"),
				tip = G("OPTION_TARGETFPS_CHECK", "Enable this option to dynamically reduce graphics quality if you fall below a specific framerate.") },
			-- off: Blizzard's help text says -1 turns sharpening off; it sits left of the bar, the softest end.
			{ cvar = "ResampleSharpness", kind = "range", min = 0, max = 2, step = 0.05, invert = true, off = -1, label = G("RESAMPLE_SHARPNESS", "Resample Sharpness"),
				tip = G("OPTION_TOOLTIP_SHARPNESS", "Adjusts the strength of the FidelityFX Super Resolution sharpness effect. 0 is full strength.") },
			{ cvar = "Contrast", kind = "range", min = 0, max = 100, step = 1, suffix = "%", label = G("OPTION_CONTRAST", "Contrast"),
				tip = G("OPTION_TOOLTIP_CONTRAST", "Controls the Contrast of the game.") },
			{ cvar = "Brightness", kind = "range", min = 0, max = 100, step = 1, suffix = "%", label = G("OPTIONS_BRIGHTNESS", "Brightness"),
				tip = G("OPTION_TOOLTIP_BRIGHTNESS", "Controls the Brightness of the game.") },
			{ cvar = "Gamma", kind = "range", min = 0.3, max = 2.8, step = 0.05, label = G("GAMMA", "Gamma"),
				tip = G("OPTION_TOOLTIP_GAMMA", "Controls the Gamma of the game.") },
			{ cvar = "bloomUserMult", kind = "range", min = 0, max = 1, step = 0.05, shown = function() return Has(VO("IsLinearEnabledOnStart")) end,
				label = G("BLOOM_MULT", "Bloom Intensity"), tip = G("OPTION_TOOLTIP_BLOOM_MULT", "Controls the intensity of the bloom effect.") },
		},
	},
	{
		key = "compat", name = G("COMPATIBILITY_SETTINGS", "Compatibility Settings"),
		note = "Only for working round crashes or graphics bugs. Turning these off usually costs FPS.",
		rows = {
			{ cvar = "GxCompatOptionalGpuFeatures", kind = "toggle", device = true, restart = true, label = G("COMPAT_SETTING_OPTIONAL_GPU_FEATURES", "Optional GPU Features"),
				tip = G("OPTION_TOOLTIP_COMPAT_SETTING_OPTIONAL_GPU_FEATURES", "Allows the use of newer GPU features. When disabled, the game will act as if the GPU only supports the minimum required features. Various graphical features will be disabled and the visual quality of the game will likely be reduced. This may help work around driver bugs or other issues with newer GPU features.") },
			{ cvar = "GxCompatAsyncShaderCompilation", kind = "toggle", device = true, restart = true, label = G("COMPAT_SETTING_DEVICE_MULTITHREADING", "Async Resource Creation"),
				tip = G("OPTION_TOOLTIP_COMPAT_SETTING_DEVICE_MULTITHREADING", "Allows asynchronously creating GPU resources such as textures and shaders. Disabling this will likely introduce hitching but could help work around crashes or visual issues on very old drivers or hardware.") },
			{ cvar = "GxCompatCommandListMultiThreading", kind = "toggle", device = true, restart = true, label = G("COMPAT_SETTING_CMDLIST_MULTITHREADING", "Multithreaded Rendering"),
				tip = G("OPTION_TOOLTIP_COMPAT_SETTING_CMDLIST_MULTITHREADING", "Allows the game to use multiple CPU threads to render the game. Disabling this will likely greatly reduce framerate, but could work around crashes or visual bugs in some cases.") },
			{ cvar = "GxCompatWorkSubmitOptimizations", kind = "toggle", device = true, restart = true, label = G("COMPAT_SETTING_ADV_WORK_SUBMIT", "Advanced Work Submit"),
				tip = G("OPTION_TOOLTIP_COMPAT_SETTING_ADV_WORK_SUBMIT", "Allows more complex code paths for submitting work to the GPU. Disabling this may cause less consistent or lower framerate but could help avoid some kinds of crashes for certain hardware, driver and OS combinations.") },
		},
	},
}

-- The plain line under Blizzard's words in each row's tooltip (the tooltip rule in CONTRIBUTING.md).
-- Info rows and the Base Game Quality slider get theirs from RowTooltip.
local PLAIN = {
	RenderScale = "Below 100% draws fewer pixels for more FPS. Above 100% is the sharpest picture and the most expensive.",
	vsync = "Stops screen tearing by holding the frame rate to your screen. It can add a little input delay.",
	LowLatencyMode = "Cuts the delay between a key press and the screen. NVIDIA Reflex needs an NVIDIA card.",
	ffxAntiAliasingMode = "Smooths jagged edges cheaply, after the picture is drawn. FXAA can soften the picture a little.",
	cameraFov = "How wide the camera sees. Higher shows more at the sides; lower looks closer.",
	graphicsShadowQuality = "Better shadows cost FPS. Blizzard says lowering this can help a lot.",
	graphicsLiquidDetail = "How good water and other liquids look. Lower for some FPS.",
	graphicsPBRLiquidDetail = "How good the newer, more realistic water looks.",
	graphicsParticleDensity = "How many sparks, smoke and spell bits you see. Lower helps FPS in busy fights.",
	graphicsSSAO = "Soft shadows in corners and where things meet. Blizzard says lowering this can help a lot.",
	graphicsDepthEffects = "Soft particles: smoke and spell effects fade where they meet the ground, instead of a hard line. Not depth of field.",
	graphicsComputeEffects = "Volumetric fog and some particle effects. Blizzard says they may cost more on older graphics cards.",
	graphicsTextureResolution = "How detailed surfaces look up close. Higher uses more video memory.",
	graphicsSpellDensity = "How many non-essential spell effects you see. Essential shows only the ones that matter.",
	graphicsProjectedTextures = "Textures cast onto the ground and walls, such as some spell effects. Off may help FPS.",
	graphicsLightMode = "Forever's new light bounce. High to Ultra is the single most expensive step in the game.",
	graphicsViewDistance = "How far away the world is drawn. Higher costs FPS and memory.",
	graphicsEnvironmentDetail = "How far away objects such as trees and buildings are drawn. Lower helps FPS.",
	graphicsGroundClutter = "How much grass and small plants there are, and how far out. Lower helps FPS.",
	gxMaxFrameLatency = "A steadier frame rate. Blizzard says it may add a little input delay on slower graphics cards.",
	textureFilteringMode = "Keeps the ground and walls sharp when seen at an angle. Higher is sharper.",
	ResampleQuality = "How the picture is scaled to your screen when render scale is below 100%. Above 100% the game uses Bicubic whatever this says.",
	vrsValar = "Draws less detail where you won't notice it, for more FPS. Needs a graphics card that supports it.",
	gxapi = "Which graphics system the game uses. Change it only if the game has problems.",
	physicsLevel = "Whether the world reacts when you move through it: nobody, just you, or you and NPCs.",
	gxAdapter = "Which graphics card draws the game. On a laptop, pick the main card.",
	maxFPS = "Caps the frame rate while the game is in front. Saves power and heat.",
	maxFPSBk = "Caps the frame rate while you're in another window. Low saves power.",
	targetFPS = "When FPS drops below this, the game lowers its quality to keep up.",
	ResampleSharpness = "How much the picture is sharpened after scaling. Right is sharper; Off turns it off.",
	Contrast = "The difference between light and dark.",
	Brightness = "How bright the whole picture is.",
	Gamma = "How bright the middle tones are, without changing pure black or white.",
	bloomUserMult = "How strong the glow around bright light is.",
	GxCompatOptionalGpuFeatures = "Leave it on. Turn it off only to work round a crash or a graphics bug; the game looks worse.",
	GxCompatAsyncShaderCompilation = "Leave it on. Turn it off only to work round a crash; Blizzard says it will likely stutter.",
	GxCompatCommandListMultiThreading = "Leave it on. Turn it off only to work round a crash; Blizzard says FPS will likely drop a lot.",
	GxCompatWorkSubmitOptimizations = "Leave it on. Turn it off only to work round a crash; FPS may be less steady.",
}
for _, group in ipairs(ns.STANDARD) do
	for _, row in ipairs(group.rows) do
		row.plain = row.plain or PLAIN[row.cvar or row.key]
	end
end

local byCVar = {}
local function Index()
	wipe(byCVar)
	for _, group in ipairs(ns.STANDARD) do
		for _, row in ipairs(group.rows) do
			row.group = group
			if row.cvar then byCVar[row.cvar] = row end
		end
	end
end
Index()

function ns.StandardRow(cvar)
	return byCVar[cvar]
end

-- Standard CVars that presets and backups may hold. Left out: your PC's own setup (device), your own choices
-- like FPS limits (own), shown-only rows, and Base Game Quality (its rows are saved instead, so a restore
-- never fights the master slider).
function ns.StandardCVars()
	local list = {}
	for _, group in ipairs(ns.STANDARD) do
		for _, row in ipairs(group.rows) do
			if row.cvar and not row.device and not row.own and not row.master and row.kind ~= "info" then
				list[#list + 1] = row.cvar
				if row.check then list[#list + 1] = row.check end
			end
		end
	end
	return list
end

local function Text(pair)
	if type(pair) == "function" then pair = pair() end
	if not pair then return nil end
	local s = pair[1] and _G[pair[1]]
	if type(s) == "string" and s ~= "" then return (s:gsub("%s+$", "")) end
	return pair[2]
end
ns.StandardText = Text

local function Options(row)
	if type(row.options) == "function" then return row.options() end
	return row.options or {}
end
ns.StandardOptions = Options

local function Num(x) if type(x) == "function" then return x() end return x end

local function Current(row)
	local v = ns.GetInfo(row.cvar)
	if row.lower and type(v) == "string" then v = v:lower() end
	return v
end

-- An Extra, a dial override or a chosen tier that owns this CVar keeps the new value,
-- so "Keep my settings applied" holds it instead of putting the old one back. True if anything kept it.
local function Keep(cvar, value)
	local n = tonumber(value)
	local kept = false
	for _, ex in ipairs(ns.EXTRAS) do
		if ex.cvar == cvar then
			-- Applied at once, so backups count it as applied. Called for every Extra on this setting:
			-- one set to "Use tier" but not yet applied is still in force (Backups.lua decides).
			if ns.NoteAppliedExtra then ns.NoteAppliedExtra(ex.key, n or value) end
			if ns.db.extras[ex.key] ~= nil then
				ns.db.extras[ex.key] = n or value
				ns.SaveMirror()
				kept = true
			end
		end
	end
	if ns.db.advanced[cvar] ~= nil or (ns.TierValueFor and ns.TierValueFor(cvar) ~= nil) then
		ns.db.advanced[cvar] = n or value
		kept = true
	end
	return kept
end

-- Render scale above 100%: the value set now, or (useExtra) what Apply will set: the render scale Extra,
-- else the Resolution & Clarity tier's value, else the value set now.
function ns.RenderScaleAbove100(useExtra)
	local v = useExtra and ns.db and ns.db.extras and ns.db.extras.renderScale
	if v == nil and useExtra and ns.TierValueFor then v = ns.TierValueFor("RenderScale") end
	if v == nil then v = tonumber((ns.GetInfo("RenderScale"))) end
	return (tonumber(v) or 1) > 1.0001
end

local function SetOne(cvar, value)
	Keep(cvar, value)
	SetCVar(cvar, value)
end

-- The game's own Options window. Eye Candy re-applies its settings when it closes (Core.lua),
-- so a Standard setting changed there is kept as your value first, or it would be put back.
local menuBefore
function ns.SnapshotGameMenu()
	menuBefore = {}
	for _, cvar in ipairs(ns.StandardCVars()) do
		if ns.Exists(cvar) then menuBefore[cvar] = GetCVar(cvar) end
	end
end

function ns.KeepGameMenuChanges()
	if not menuBefore then return 0 end
	local n = 0
	for cvar, before in pairs(menuBefore) do
		local now = GetCVar(cvar)
		if now ~= nil and now ~= before and Keep(cvar, now) then n = n + 1 end
	end
	menuBefore = nil
	return n
end

-- Set a Standard setting the way the game's menu does: straight away.
-- An Extra, a dial or a tier that already owns this CVar keeps the new value too.
-- Base Game Quality also sets each quality row to the game's own value for that level, rows first, as the game does.
function ns.SetStandard(cvar, value)
	if InCombatLockdown() then
		-- The row says it when the window is open (rule 6, docs/ui-rules.md); chat only when it isn't.
		local win = _G.EyeCandyMainFrame
		local page = win and win.pages and win.pages.standard
		if not (win and win:IsShown() and page and page:IsShown()) then ns.Print("can't change settings in a fight. Try again after it.") end
		return false, "not changed in a fight"
	end
	if not ns.Exists(cvar) then return false end
	ns.TakeBackup(false)
	local row = byCVar[cvar]
	if row and row.master and type(GetGraphicsCVarValueForQualityLevel) == "function" then
		local level = tonumber(value)
		for _, sub in ipairs(row.group.rows) do
			if not sub.master and ns.Exists(sub.cvar) then
				local v = Call(GetGraphicsCVarValueForQualityLevel, sub.cvar, level, false)
				if v ~= nil then
					if sub.minQuality and tonumber(v) and tonumber(v) < sub.minQuality then v = sub.minQuality end
					SetOne(sub.cvar, v)
				end
			end
		end
	end
	SetOne(cvar, value)
	return true
end

-- Display text for a row's value.
function ns.FormatStandard(row, value)
	if row.kind == "info" then return row.read() end
	if value == nil then return "n/a" end
	if row.kind == "toggle" then
		return ns.Same(value, row.on or "1") and "On" or "Off"
	elseif row.kind == "choice" then
		if row.lower and type(value) == "string" then value = value:lower() end
		for _, opt in ipairs(Options(row)) do
			if ns.Same(opt[1], value) then return Text(opt[2]) end
		end
		return tostring(value)
	end
	local n = tonumber(value)
	if not n then return tostring(value) end
	if row.off ~= nil and n == row.off then return "Off" end
	if row.percent then return math.floor(n * 100 + 0.5) .. "%" end
	if row.plusOne then return tostring(math.floor(n + 0.5) + 1) end
	if row.suffix then return math.floor(n + 0.5) .. row.suffix end
	return ns.FormatNumber(n)
end

----------------------------------------------------------------------
-- Tab
----------------------------------------------------------------------

local ROW_H = 26
local stdRows = {}
ns.stdRows = stdRows
local stdPage

-- The game's own tooltip text, quoted, then the plain line (if any), then the game default (tooltip rule in UI.lua).
-- shown: the row's frame, so an info row's value (cut to its width, never wrapped) can be given in full.
local function RowTooltip(row, shown)
	local plain = row.plain
	if row.master then
		plain = "Moving this sets every Graphics Quality row below to the game's own values for that level."
	elseif row.kind == "info" then
		plain = "Change this in the game's Options menu. It can move or resize the window."
	end
	local default = row.cvar and select(2, ns.GetInfo(row.cvar))
	local more = {}
	if shown and row.kind == "info" and row.read then
		local ok, now = pcall(row.read)
		if ok and now and now ~= "" then more[#more + 1] = "Now: " .. tostring(now) end
	end
	if row.ignoredWhen and row.ignoredNote and row.ignoredWhen() == true then more[#more + 1] = "|cffffd100" .. row.ignoredNote .. "|r" end
	if row.restart then more[#more + 1] = "|cffffd100Takes effect after you restart the game.|r" end
	if row.device then more[#more + 1] = "|cff9d9d9dNot saved in presets or backups.|r" end
	if row.own then more[#more + 1] = "|cff9d9d9dPresets never change it. Backups don't save it.|r" end
	if row.master then more[#more + 1] = "|cff9d9d9dPresets and backups save the rows below, not this slider.|r" end
	return ns.SettingTip({
		quote = Text(row.tip), plain = plain,
		default = (row.kind ~= "info" and default ~= nil) and ns.FormatStandard(row, default) or nil,
		more = more, cvar = row.cvar and (row.cvar .. (row.check and (" + " .. row.check) or "")),
	})
end
ns.StandardTooltip = RowTooltip

-- A Standard row's menu tooltip text (the game's string, or the English copy here), for other tabs to quote.
function ns.StandardTipText(cvar)
	local row = byCVar[cvar]
	return row and Text(row.tip) or nil
end

local function RefreshStdRow(r)
	local row = r.def
	if row.kind == "info" then
		r.valueText:SetText(row.read())
		r.dot:SetShown(row.cvar ~= nil and ns.IsChanged(row.cvar) == true)
		return
	end
	local value = Current(row)
	if value == nil then
		r.valueText:SetText("|cff9d9d9dnot in this game|r")
		if r.control then r.control:Hide(); r.control:SetAlpha(1) end
		r.dot:Hide()
		r.ignored = false
		return
	end
	-- The dropdown, box or checkbox already shows the value, so the text beside it stays empty unless it adds something.
	r.valueText:SetText("")
	if row.ignoredWhen then
		local ignored = row.ignoredWhen() == true
		-- Faded, not locked: it can still be set ready for a render scale below 100%.
		if r.control then r.control:SetAlpha(ignored and 0.45 or 1) end
		if ignored then r.valueText:SetText("|cff9d9d9d(ignored above 100%)|r") end
		r.ignored = ignored
	end
	-- A change refused in a fight stays said on the row until the fight ends. Fights only: out of
	-- one the mark goes at once, so a refusal for any other reason would need its own clear.
	if r.refused then
		if InCombatLockdown() then r.valueText:SetText("|cffff4040" .. r.refused .. "|r") else r.refused = nil end
	end
	r.dot:SetShown(ns.IsChanged(row.cvar) == true or (row.check ~= nil and ns.IsChanged(row.check) == true))
	if r.Update then r:Update(value) end
end

function ns.RefreshStandard()
	if not (stdPage and stdPage:IsShown()) then return end
	for _, r in ipairs(stdRows) do RefreshStdRow(r) end
end
ns.TAB_REFRESH.standard = ns.RefreshStandard

-- When the fight ends, the "not changed in a fight" lines (here and on the Hidden tab) go.
local regen = CreateFrame("Frame")
regen:RegisterEvent("PLAYER_REGEN_ENABLED")
regen:SetScript("OnEvent", function()
	if stdPage and stdPage.gameMenuMsg then stdPage.gameMenuMsg:SetText("") end
	-- Every row's mark goes, not just the front tab's, so the next fight doesn't show an old one.
	for _, r in ipairs(stdRows) do r.refused = nil end
	for _, r in ipairs(ns.advRows or {}) do r.refused = nil end
	if ns.RefreshUI then ns.RefreshUI() end
end)

-- A refused change (in a fight) is said in red beside the row's control, until the fight ends
-- (RefreshStdRow keeps it through other refreshes).
local function Refused(r, err)
	r.refused = err
	if err then r.valueText:SetText("|cffff4040" .. err .. "|r") end
end

local function Commit(r, value)
	local ok, err = ns.SetStandard(r.def.cvar, value)
	if r.def.master then
		ns.RefreshStandard()
	else
		RefreshStdRow(r)
	end
	if not ok then Refused(r, err) end
end

local function ChoiceControl(r)
	local row = r.def
	local function IsSelected(value) return ns.Same(Current(row), value) end
	local function Generator(_, root)
		for _, opt in ipairs(Options(row)) do
			local d = root:CreateRadio(Text(opt[2]), function() return IsSelected(opt[1]) end, function() Commit(r, opt[1]) end)
			-- The game greys out quality levels this PC can't run (same check as the game's menu).
			if d and d.SetEnabled and row.group.key == "quality" and tonumber(opt[1]) and not ns.IsSupported(row.cvar, tonumber(opt[1])) then d:SetEnabled(false) end
		end
	end
	r.menu = Generator
	local ok, dd = pcall(CreateFrame, "DropdownButton", nil, r, "WowStyle1DropdownTemplate")
	if ok and dd and dd.SetupMenu then
		dd:SetWidth(170)
		dd:SetupMenu(Generator)
		r.Update = function() if dd.GenerateMenu then dd:GenerateMenu() end end
		return dd
	end
	-- No modern dropdown in this client: a "< value >" stepper instead.
	local f = CreateFrame("Frame", nil, r)
	f:SetSize(170, 24)
	local function Step(dir)
		local opts = Options(row)
		local now, idx = Current(row), 1
		for i, opt in ipairs(opts) do if ns.Same(opt[1], now) then idx = i end end
		idx = math.min(math.max(idx + dir, 1), #opts)
		if opts[idx] then Commit(r, opts[idx][1]) end
	end
	local minus = ns.Button(f, "<", 24, function() Step(-1) end)
	minus:SetPoint("LEFT")
	local plus = ns.Button(f, ">", 24, function() Step(1) end)
	plus:SetPoint("RIGHT")
	r.Step = Step
	return f
end

local function ToggleControl(r)
	local row = r.def
	local check = CreateFrame("CheckButton", nil, r, "UICheckButtonTemplate")
	check:SetSize(24, 24)
	check:SetScript("OnClick", function(self)
		Commit(r, self:GetChecked() and (row.on or "1") or (row.off or "0"))
	end)
	r.check = check
	r.Update = function(_, value) check:SetChecked(ns.Same(value, row.on or "1")) end
	return check
end

local function RangeControl(r)
	local row = r.def
	local lo, hi = Num(row.min), Num(row.max)
	local off = row.off -- a value meaning "off", shown left of the bar's low end
	local holder = CreateFrame("Frame", nil, r)
	holder:SetSize(240, 24)
	local s
	local width = 120
	if row.check then
		local box = CreateFrame("CheckButton", nil, holder, "UICheckButtonTemplate")
		box:SetSize(24, 24)
		box:SetPoint("LEFT", -4, 0)
		box:SetScript("OnClick", function(self)
			local ok, err = ns.SetStandard(row.check, self:GetChecked() and "1" or "0")
			RefreshStdRow(r)
			if not ok then Refused(r, err) end
		end)
		r.checkBox = box
		width = 96
	end
	s = ns.Slider(holder, {
		-- invert: the bar runs like the game's Resample Sharpness bar (soft on the left, Off past it).
		min = lo, max = hi, step = row.step, width = width, off = off, invert = row.invert,
		get = function() return tonumber((ns.GetInfo(row.cvar))) end,
		set = function(v) Commit(r, v) end,
		default = function() local _, d = ns.GetInfo(row.cvar); return tonumber(d) end,
		-- The box shows what the game's menu shows (View Distance 1 to 10, 150 for 150%), without the unit.
		format = function(v) return (ns.FormatStandard(row, v):gsub("[^%d%.%-]", "")) end,
		parse = function(text)
			if off ~= nil and text:lower():find("off") then return off end
			local n = tonumber(text:match("%-?[%d%.]+"))
			if not n then return nil end
			if row.percent then n = n / 100 end
			if row.plusOne then n = n - 1 end
			return n
		end,
	})
	s:SetPoint("LEFT", row.check and 46 or 20, 0)
	r.slider = s
	r.Update = function()
		s:Refresh()
		if r.checkBox then r.checkBox:SetChecked(ns.Same(ns.GetInfo(row.check), "1")) end
	end
	return holder
end

local function BuildStdRow(content, def, index)
	local r = CreateFrame("Frame", nil, content)
	r:SetSize(ns.ROW_W, ROW_H - 2)
	r.def = def
	local bg = r:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(1, 1, 1, (index % 2 == 0) and 0.04 or 0.0)
	r.dot = ns.Dot(r)
	r.label = ns.Label(r, Text(def.label), "GameFontHighlightSmall")
	r.label:SetPoint("LEFT", 12, 0)
	r.label:SetWidth(220)
	r.label:SetWordWrap(false) -- rule 16: a fixed-height row never wraps; the full label is in the tooltip
	if def.kind == "info" then
		-- Not a control: grey, and says where it is changed.
		r.label:SetTextColor(0.62, 0.62, 0.62)
		r.hint = ns.Label(r, "|cff9d9d9dchange in the game menu|r", "GameFontHighlightSmall")
		r.hint:SetPoint("LEFT", 470, 0)
		r.hint:SetWidth(160)
		r.hint:SetWordWrap(false)
	end
	if def.kind == "choice" then
		r.control = ChoiceControl(r)
	elseif def.kind == "toggle" then
		r.control = ToggleControl(r)
	elseif def.kind == "range" then
		r.control = RangeControl(r)
	end
	if r.control then r.control:SetPoint("LEFT", 240, 0) end
	r.valueText = ns.Label(r, "", "GameFontHighlight")
	-- A range row's value is in its typed box; valueText only says when the setting is missing.
	r.valueText:SetPoint("LEFT", def.kind == "info" and 240 or (def.kind == "range" and 486 or 430), 0)
	r.valueText:SetWidth(def.kind == "info" and 220 or 150)
	r.valueText:SetWordWrap(false)
	r:EnableMouse(true)
	ns.Tooltip(r, Text(def.label), function() return RowTooltip(def, r) end)
	stdRows[#stdRows + 1] = r
	return r
end

-- The game's own Options window (for Monitor, Display Mode, Resolution and UI scale).
function ns.OpenGameOptions()
	local page = stdPage
	if page and page.gameMenuMsg then page.gameMenuMsg:SetText("") end
	if InCombatLockdown() then
		-- Said under the button (rule 6, docs/ui-rules.md); chat only when the Standard tab isn't in front.
		if page and page:IsShown() and page.gameMenuMsg then
			page.gameMenuMsg:SetText("|cffff4040Can't open it in a fight.|r")
		else
			ns.Print("can't open the game's options in a fight. Try again after it.")
		end
		return
	end
	-- Our window sits above the game's Options; get out of its way.
	local main = _G.EyeCandyMainFrame
	if main and main:IsShown() then main:Hide() end
	if SettingsPanel and SettingsPanel.Open then
		SettingsPanel:Open()
	elseif SettingsPanel then
		ShowUIPanel(SettingsPanel)
	end
end

ns.TAB_BUILD.standard = function(page)
	stdPage = page
	local intro = ns.Label(page, "The game's Graphics settings, in one place. They apply straight away.", "GameFontNormalSmall")
	intro:SetPoint("TOPLEFT", 4, -6)
	intro:SetWidth(ns.PAGE_W - 260)
	intro:SetWordWrap(false) -- the legend sits right under it
	page.gameMenu = ns.Button(page, "Open the game's Graphics menu", 220, ns.OpenGameOptions)
	page.gameMenu:SetPoint("TOPRIGHT", -4, 0)
	-- Why the button did nothing (in a fight), under it. It goes when you leave the tab.
	page.gameMenuMsg = ns.Label(page, "", "GameFontHighlightSmall")
	page.gameMenuMsg:SetPoint("TOPRIGHT", -4, -26)
	page.gameMenuMsg:SetWidth(260)
	page.gameMenuMsg:SetJustifyH("RIGHT")
	page.gameMenuMsg:SetWordWrap(false)
	page:HookScript("OnHide", function(self) self.gameMenuMsg:SetText("") end)
	page.legend = ns.Label(page, "|TInterface\\Buttons\\WHITE8X8:6:6:0:0:8:8:0:8:0:8:255:209:0|t = changed from the game default", "GameFontNormalSmall")
	page.legend:SetPoint("TOPLEFT", 4, -22)
	local content = ns.ScrollPage(page, -40)
	local list = ns.NewList(content)
	ns.TAB_LIST.standard = list
	local index = 0
	for _, group in ipairs(ns.STANDARD) do
		local header, h = ns.Header(content, Text(group.name), group.note)
		local headerItem = list:Add(header, h, Text(group.name))
		for _, def in ipairs(group.rows) do
			if not def.shown or def.shown() then
				index = index + 1
				local r = BuildStdRow(content, def, index)
				list:Add(r, ROW_H, Text(def.label) .. " " .. (def.cvar or "") .. " " .. (def.check or ""), headerItem)
			end
		end
	end
end
