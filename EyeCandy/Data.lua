-- Eye Candy: tier definitions.
-- CVar names and menu index ranges are taken from Blizzard's own Forever UI source
-- (wow-ui-source "forever" branch, build 1.60.1.70790, Blizzard_SettingsDefinitions_Shared/Graphics.lua).
--
-- Each cvar row: { cvar, label, { Performance, Balanced, High, Ultra, Cinematic } }
--   nil in a tier slot = leave that CVar alone at that tier.
--   menu = true   -> a Graphics menu index; Eye Candy asks the client which values your GPU supports and steps down if needed.
--   hidden = true -> not in the Graphics menu; the menu can overwrite these, so Eye Candy can re-apply them.

local _, ns = ...

ns.TIERS = { "Performance", "Balanced", "High", "Ultra", "Cinematic" }

ns.TIER_COLOURS = {
	[0] = "ff9d9d9d", -- No change
	"ff7fbf7f",       -- Performance
	"ff9ad0ff",       -- Balanced
	"ffc8a2ff",       -- High
	"ffffc04d",       -- Ultra
	"ffff7b54",       -- Cinematic
}

ns.CATEGORIES = {
	{
		key = "clarity",
		name = "Resolution & Clarity",
		desc = "Render scale (supersampling), texture filtering, variable rate shading and sharpening.\nUltra asks for 125% render scale and Cinematic for 150%, or the most the game allows.\nHigh and above turn VRS off so every pixel is shaded at full rate.\nA new render scale may need a game restart.",
		cvars = {
			{ "RenderScale",           "Render scale",         { 0.9, 1, 1, 1.25, 1.5 }, scale = true },
			{ "textureFilteringMode",  "Texture filtering",    { 3, 4, 5, 5, 5 } },
			{ "vrsValar",              "Variable rate shading",{ 2, 1, 0, 0, 0 } },
			{ "ResampleAlwaysSharpen", "Always sharpen",       { nil, 1, 1, 1, 1 }, hidden = true },
		},
	},
	{
		key = "lighting",
		name = "Lighting & Shadows",
		desc = "Shadow quality, secondary lighting (Forever's new light bounce), SSAO and depth effects (soft edges where smoke and spells meet the world).\nSecondary Lighting High to Ultra is the single most expensive step in the game.",
		cvars = {
			{ "graphicsShadowQuality", "Shadow quality",       { 1, 3, 4, 5, 5 }, menu = true },
			{ "graphicsLightMode",     "Secondary lighting",   { 0, 1, 2, 3, 3 }, menu = true },
			{ "graphicsSSAO",          "SSAO",                 { 1, 2, 3, 4, 4 }, menu = true },
			{ "graphicsDepthEffects",  "Depth effects (soft particles)", { 1, 2, 3, 3, 3 }, menu = true },
		},
	},
	{
		key = "atmosphere",
		name = "Atmosphere & Weather",
		desc = "Compute Effects drives volumetric fog and the god rays that shine through it.\nWeather density controls rain/snow particle count.",
		cvars = {
			{ "graphicsComputeEffects", "Compute effects (fog, god rays)", { 1, 2, 3, 4, 4 }, menu = true },
			{ "weatherDensity",         "Weather density",                 { 1, 2, 3, 3, 3 }, hidden = true },
		},
	},
	{
		key = "water",
		name = "Water",
		desc = "Legacy and new physically based (PBR) water.",
		cvars = {
			{ "graphicsLiquidDetail",    "Legacy liquid detail", { 1, 2, 3, 3, 3 }, menu = true },
			{ "graphicsPBRLiquidDetail", "PBR liquid detail",    { 0, 1, 2, 2, 2 }, menu = true },
		},
	},
	{
		key = "textures",
		name = "Textures & Surfaces",
		desc = "Texture resolution and projected textures.\nProjected textures stay on at every level because they show ground-targeted combat effects.",
		cvars = {
			{ "graphicsTextureResolution", "Texture resolution", { 1, 2, 2, 2, 2 }, menu = true },
			{ "graphicsProjectedTextures", "Projected textures", { 1, 1, 1, 1, 1 }, menu = true },
		},
	},
	{
		key = "world",
		name = "View Distance & Horizon",
		desc = "How far terrain and objects draw.\nCinematic also pushes the far clip and horizon past the menu's maximum, and lets the camera zoom further out.",
		cvars = {
			{ "graphicsViewDistance",        "View distance",      { 3, 6, 8, 9, 9 }, menu = true },
			{ "graphicsEnvironmentDetail",   "Environment detail", { 3, 6, 8, 9, 9 }, menu = true },
			{ "farclip",                     "Far clip",           { nil, nil, nil, nil, 10000 }, hidden = true },
			{ "horizonClip",                 "Horizon clip",       { nil, nil, nil, nil, 10000 }, hidden = true },
			{ "horizonStart",                "Horizon start",      { nil, nil, nil, nil, 6000 }, hidden = true },
			{ "cameraDistanceMaxZoomFactor", "Max camera zoom",    { nil, nil, nil, 2.6, 4 }, hidden = true },
		},
	},
	{
		key = "distant",
		name = "Distant Detail (exp.)",
		desc = "How far trees, props, terrain and buildings keep full detail before they swap to simpler models or vanish.\nThe menu's View Distance and Environment Detail also set some of these. Eye Candy sets them again after you close Options.\nUnconfirmed: not checked by eye at long range.",
		cvars = {
			{ "doodadLodScale",     "Tree/prop detail distance",          { nil, nil, nil, 200, 300 },  hidden = true },
			{ "lodObjectFadeScale", "Small object fade distance",         { nil, nil, nil, 200, 300 },  hidden = true },
			{ "lodObjectCullSize",  "Small object cull size (lower = more)", { nil, nil, nil, 10, 7 }, hidden = true },
			{ "terrainLodDist",     "Terrain detail distance",            { nil, nil, nil, 800, 1000 }, hidden = true },
			{ "TerrainLodDiv",      "Terrain detail divisor",             { nil, nil, nil, nil, 1024 }, hidden = true },
			{ "wmoLodDist",         "Building detail distance",           { nil, nil, nil, 600, 800 },  hidden = true },
			{ "dynamicLod",         "Dynamic detail reduction (off)", { nil, nil, nil, nil, 0 },    hidden = true },
		},
	},
	{
		key = "foliage",
		name = "Grass & Foliage",
		desc = "How thick grass is and how far it reaches.\nUltra and Cinematic go past the menu's limits.\nCosts more FPS than you'd expect, so drop this first.",
		cvars = {
			{ "graphicsGroundClutter", "Ground clutter",  { 3, 6, 8, 9, 9 }, menu = true },
			{ "groundEffectDensity",   "Grass density",   { nil, nil, 96, 128, 256 }, hidden = true },
			{ "groundEffectDist",      "Grass distance",  { nil, nil, nil, 400, 500 }, hidden = true },
			{ "groundEffectFade",      "Grass fade",      { nil, nil, nil, 300, 370 }, hidden = true },
		},
	},
	{
		key = "effects",
		name = "Particles & Spells",
		desc = "Particle density (smoke, fire, sparks) and how many spell effects are drawn.",
		cvars = {
			{ "graphicsParticleDensity", "Particle density", { 1, 2, 3, 5, 5 }, menu = true },
			{ "graphicsSpellDensity",    "Spell density",    { 1, 2, 2, 2, 2 }, menu = true },
		},
	},
}

-- Extras: independent toggles, not tied to tiers. "Set all to" presets never touch them.
-- options: { value, label }; a nil value means leave the setting alone.
-- system: the Hidden tab group (ns.ADVANCED key) the Extra shows in.
-- slider: shown as a slider instead of a stepper ({ min, max, step, off, percent }; a scale Extra takes the
-- game's render scale limits). The options still name the common values and set the import range.
ns.EXTRAS = {
	{
		key = "renderScale", cvar = "RenderScale", name = "Render scale override", scale = true, system = "clarity",
		tipKey = "OPTION_TOOLTIP_RENDER_SCALE",
		desc = "Overrides the Resolution & Clarity level's render scale.\nAbove 100% the FPS cost climbs fast.\nA new render scale may need a game restart.",
		options = { { nil, "Use level" }, { 1.25, "125%" }, { 1.5, "150%" }, { 1.75, "175%" }, { 2, "200%" } },
		slider = { step = 0.01, percent = true },
	},
	{
		key = "resample", cvar = "ResampleQuality", name = "Resample filter", system = "clarity",
		tipKey = "OPTION_TOOLTIP_RESAMPLE_QUALITY",
		desc = "How the picture is scaled to your screen when render scale is below 100%.\nAbove 100% the game uses Bicubic, so this shows as ignored.\nFSR 1.0 is built for upscaling.",
		options = { { nil, "Leave as is" }, { 3, "FSR 1.0" }, { 2, "Bicubic" } },
	},
	{
		key = "sharpness", cvar = "ResampleSharpness", name = "Sharpness", system = "clarity",
		desc = "How much the picture is sharpened. |cffffd100Lower = sharper.|r\nOn the bar, right is sharper and Off is past the soft end.\nToo sharp makes grass and edges shimmer.\nOnly works while Always sharpen is on, or render scale isn't 100%.",
		options = { { nil, "Leave as is" }, { -1, "Off" }, { 0, "0 (sharpest)" }, { 0.2, "0.2 (default)" }, { 0.5, "0.5" }, { 1, "1.0 (soft)" }, { 2, "2.0 (softest)" } },
		-- The bar runs like the game's: soft on the left, Off past it, sharpest on the right.
		slider = { min = 0, max = 2, step = 0.05, off = -1, invert = true },
	},
	{
		key = "entityLod", cvar = "entityLodDist", name = "Character detail (exp.)", hidden = true, system = "distant",
		desc = "How far away characters and creatures keep their detail. Unconfirmed: higher looks like more detail.\nHigher costs more in crowded places.",
		options = { { nil, "Leave as is" }, { 5, "Lower (5)" }, { 10, "Default (10)" }, { 20, "Higher (20)" }, { 50, "50" }, { 100, "100" } },
		slider = { min = 5, max = 100, step = 1 },
	},
}

-- Extras the Showcase button picks on top of Cinematic everywhere.
-- 200% is an exact 2x2 downsample per screen pixel, so Bicubic is a safe filter for it.
-- Character detail at 20 is unconfirmed; it goes by the CVar's name.
ns.SHOWCASE_EXTRAS = { renderScale = 2, resample = 2, entityLod = 20 }

-- Looks: curated styles rather than "max everything". Each starts from a preset
-- (base: 5 = Cinematic, 6 = Showcase), then sets Extras and Advanced dials on top.
-- These are starting points chosen by eye and by what each setting does, not measured "best" values.
-- Every dial stays editable afterwards in the Advanced window.
ns.LOOKS = {
	{
		key = "beautiful", name = "Beautiful", base = 6,
		desc = "The happy medium. Showcase's view distance at 150% render scale, or the most the game allows, with softer sharpening, calmer grass, a little less bloom and a narrower view.",
		extras = { renderScale = 1.5, resample = 2, sharpness = 0.5, entityLod = 20 },
		dials = {
			groundEffectDensity = 160, groundEffectDist = 400, groundEffectFade = 300,
			assaoRadius = 1.6, assaoShadowMult = 1.0, assaoShadowPower = 1.34, assaoDetailShadowStrength = 0.3,
			Contrast = 55, Brightness = 50, Gamma = 1.0, bloomUserMult = 0.6, cameraFov = 80, graphicsDepthEffects = 3,
			weatherDensity = 2,
		},
	},
	{
		key = "painterly", name = "Painterly", base = 5,
		desc = "Leans into WoW's hand-painted art. Little sharpening, sparser grass so the ground textures show, and a slightly narrower view.",
		extras = { renderScale = 1.5, resample = 2, sharpness = 1, entityLod = 20 },
		dials = {
			groundEffectDensity = 128, groundEffectDist = 300, groundEffectFade = 250,
			assaoRadius = 1.4, assaoShadowMult = 0.8, assaoShadowPower = 1.2, assaoDetailShadowStrength = 0,
			Contrast = 50, Brightness = 52, Gamma = 1.0, bloomUserMult = 0.8, cameraFov = 85, graphicsDepthEffects = 3,
			CMAA2ExtraSharpness = 0, weatherDensity = 2,
		},
	},
	{
		key = "crisp", name = "Crisp", base = 6,
		desc = "Maximum clarity. The highest render scale the game allows, strong sharpening, depth effects off and the full 90 field of view.",
		extras = { renderScale = 2, resample = 2, sharpness = 0, entityLod = 20 },
		dials = {
			groundEffectDensity = 192, groundEffectDist = 450, groundEffectFade = 370,
			assaoRadius = 1.85, assaoShadowMult = 1.1, assaoShadowPower = 1.34, assaoDetailShadowStrength = 0.8, assaoSharpness = 1,
			Contrast = 55, Brightness = 50, Gamma = 1.0, bloomUserMult = 0.4, cameraFov = 90, graphicsDepthEffects = 0,
			CMAA2ExtraSharpness = 1,
		},
	},
	{
		key = "moody", name = "Moody", base = 6,
		desc = "Dark and dramatic. Higher contrast, full bloom and weather, deeper shading and a narrower view.",
		extras = { renderScale = 1.5, resample = 2, sharpness = 0.5, entityLod = 20 },
		dials = {
			groundEffectDensity = 192, groundEffectDist = 450, groundEffectFade = 300,
			assaoRadius = 2.2, assaoShadowMult = 1.3, assaoShadowPower = 1.6, assaoDetailShadowStrength = 0.5,
			Contrast = 62, Brightness = 45, Gamma = 0.9, bloomUserMult = 1, cameraFov = 75, graphicsDepthEffects = 3,
			weatherDensity = 3,
		},
	},
	{
		key = "classic", name = "Classic", base = 5,
		desc = "Closer to how WoW used to feel. Low bloom, sparse grass, light shading, depth effects off and the full field of view. Forever's new lighting and fog can't be turned off, so it's only close.",
		extras = { renderScale = 1.5, resample = 2, sharpness = 0.2, entityLod = 10 },
		dials = {
			groundEffectDensity = 64, groundEffectDist = 200, groundEffectFade = 150,
			assaoShadowMult = 0.8, assaoDetailShadowStrength = 0,
			Contrast = 50, Brightness = 50, Gamma = 1.0, bloomUserMult = 0.2, cameraFov = 90, graphicsDepthEffects = 0,
			weatherDensity = 2,
		},
	},
}

-- What the Graphics menu sets these to at View Distance and Environment Detail 10.
-- Used to correct Restore backups that were taken after hand-testing the LOD values.
ns.DISTANT_MENU_VALUES = {
	doodadLodScale = 150, lodObjectFadeScale = 150, lodObjectCullSize = 14, terrainLodDist = 650,
	TerrainLodDiv = 768, wmoLodDist = 400, dynamicLod = 1,
}

-- Extra CVars included in the export for context (read only).
ns.EXPORT_EXTRA = {
	"graphicsQuality", "graphicsOutlineMode", "RAIDsettingsEnabled",
	"ffxAntiAliasingMode", "MSAAQuality", "msaaAlphaTest", "ResampleQuality", "ResampleSharpness",
	"vrsValar", "shadowrt", "gxapi", "gxMaximize", "gxMonitor", "vsync", "LowLatencyMode",
	"maxFPS", "useMaxFPS", "maxFPSBk", "useMaxFPSBk", "targetFPS", "useTargetFPS",
	"cameraFov", "bloomUserMult", "Gamma", "Contrast", "Brightness", "physicsLevel",
	"useHighResTextures", "useUiScale", "uiscale",
	"GxCompatOptionalGpuFeatures", "GxCompatAsyncShaderCompilation",
	"GxCompatCommandListMultiThreading", "GxCompatWorkSubmitOptimizations",
	"volumeFog", "particleDensity", "RAIDparticleDensity",
}

-- Situations: built-in presets made for one job rather than a style.
-- Same shape as a Look (base preset, then Extras, then dials), listed under their own heading.
-- Starting points chosen from what each setting does, not measured. Menu values in the dials use the
-- same index the tiers use (graphicsParticleDensity 1 = what Performance sets; 0 = Disabled for SSAO
-- and Depth Effects, the first choice in the game's own menu).
ns.SITUATIONS = {
	{
		key = "raid", situation = true, name = "Raid & PvP", base = 3,
		desc = "Clear and steady for big fights. High on every system, with particles as low as Performance, no rain or snow, depth effects off, less glow, the widest view and a further camera zoom.\nIf the game's own Raid and Battleground settings are on, the game uses those in raids and battlegrounds instead.\nThe tick box under it switches to these in dungeons, raids, battlegrounds and arenas, and back when you leave.",
		dials = {
			graphicsParticleDensity = 1, graphicsDepthEffects = 0, weatherDensity = 0,
			bloomUserMult = 0.4, cameraFov = 90, cameraDistanceMaxZoomFactor = 2.6,
		},
		-- The switch by itself in a dungeon, raid, battleground or arena (Situations.lua, /ec instance):
		-- Raid & PvP's own values (High, then the dials above), only where yours are higher. Only settings
		-- that cost more when higher: not field of view or zoom, which Raid & PvP raises.
		auto = { test = "instance", caps = {
			graphicsShadowQuality = 4, graphicsLightMode = 2, graphicsSSAO = 3, graphicsDepthEffects = 0,
			graphicsComputeEffects = 3, weatherDensity = 0, graphicsViewDistance = 8, graphicsEnvironmentDetail = 8,
			graphicsGroundClutter = 8, groundEffectDensity = 96, graphicsParticleDensity = 1, bloomUserMult = 0.4,
		} },
	},
	{
		key = "laptop", situation = true, name = "Laptop", base = 1,
		desc = "Frames first, for a laptop or an older PC. Performance on every system, drawn at 75% render scale and scaled up with FSR 1.0, with ambient occlusion and depth effects off.",
		extras = { renderScale = 0.75, resample = 3, sharpness = 0.2 },
		dials = { graphicsSSAO = 0, graphicsDepthEffects = 0 },
	},
	{
		key = "screenshot", situation = true, name = "Screenshot", base = 6, back = true,
		desc = "Everything pushed for a screenshot. Showcase, the widest view and depth effects on high. Expect a big FPS drop.\nType /ec back when you're done.",
		dials = { cameraFov = 90, graphicsDepthEffects = 3 },
	},
	{
		-- Why: a crowded city is slow because of the crowd (the processor), not the graphics card. Players
		-- report view distance and environment detail as the big gain (above 7 is "very CPU intense"), and
		-- compute effects next. Shadows and SSAO are graphics card costs, so High keeps them.
		-- Reports from players and guides, not measured here. Measure in Stormwind or Orgrimmar.
		key = "city", situation = true, name = "Capital city", base = 3,
		desc = "Steadier frames in a busy city. High, with lower view distance, environment detail, fog and far-away character detail. Players say these help most in cities. Unconfirmed: not measured by Eye Candy.\nThe tick box under it lowers just those four in capital cities, and puts them back when you leave.",
		extras = { entityLod = 10 },
		dials = { graphicsViewDistance = 7, graphicsEnvironmentDetail = 7, graphicsComputeEffects = 2 },
		-- The switch by itself (Situations.lua): only these, only where yours are higher.
		auto = { test = "city", caps = { graphicsViewDistance = 7, graphicsEnvironmentDetail = 7, graphicsComputeEffects = 2, entityLodDist = 10 } },
	},
}
