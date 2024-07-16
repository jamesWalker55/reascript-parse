# reascript-parse

Generated Lua definitions from REAPER v7.08:

- [**Download link**](https://github.com/jamesWalker55/rs-parse/releases/tag/initial)

A parser for ReaScript documentation files. These are generated by REAPER through the menu "Help" > "ReaScript documentation".

It is recommended to use `rye` to install this script.

```sh
rye sync
```

## Generating Lua Definitions

![REAPER intellisense for Lua in VSCode](docs/intellisense.png)

The action 'to-lua' generates a Lua declaration file containing all functions in the documentation:

```sh
# example usage:
reascript-parse to-lua reascripthelp.html reaper.lua
```

The generated file contains definitions like this:

````lua
---@diagnostic disable-next-line: lowercase-global
reaper = {
    --- ```
    --- MediaItem _ = reaper.AddMediaItemToTrack(MediaTrack tr)
    --- ```
    --- creates a new media item.
    ---@param tr MediaTrack
    ---@return MediaItem
    AddMediaItemToTrack = function(tr) end,

    -- ...

    --- ```
    --- boolean _ = reaper.AddTempoTimeSigMarker(ReaProject proj, number timepos, number bpm, integer timesig_num, integer timesig_denom, boolean lineartempochange)
    --- ```
    --- Deprecated. Use SetTempoTimeSigMarker with ptidx=-1.
    ---@param proj ReaProject
    ---@param timepos number
    ---@param bpm number
    ---@param timesig_num integer
    ---@param timesig_denom integer
    ---@param lineartempochange boolean
    ---@return boolean
    ---@deprecated
    AddTempoTimeSigMarker = function(proj, timepos, bpm, timesig_num, timesig_denom, lineartempochange) end,

    --- ```
    --- reaper.adjustZoom(number amt, integer forceset, boolean doupd, integer centermode)
    --- ```
    --- forceset=0,doupd=true,centermode=-1 for default
    ---@param amt number
    ---@param forceset integer
    ---@param doupd boolean
    ---@param centermode integer
    adjustZoom = function(amt, forceset, doupd, centermode) end,

    -- ...
````

The documentation is usually poorly formatted, so some functions may fail to parse. These functions are logged to the console then skipped:

```plain
[WARN] Skipping malformed Lua function in section 'lua_gfx.arc' - failed to find params: 'gfx.arc(x,y,r,ang1,ang2[,antialias])'
[WARN] Skipping malformed Lua function in section 'lua_gfx.blit' - failed to find params: 'gfx.blit(source[, scale, rotation, srcx, srcy, srcw, srch, destx, desty, destw, desth, rotxoffs, rotyoffs])'
[WARN] Skipping malformed Lua function in section 'lua_gfx.blitext' - malformed function parameter: 'gfx.blitext(source,coordinatelist,rotation)'
[WARN] Skipping malformed Lua function in section 'lua_gfx.blurto' - malformed function parameter: 'gfx.blurto(x,y)'
[WARN] Skipping malformed Lua function in section 'lua_gfx.circle' - failed to find params: 'gfx.circle(x,y,r[,fill,antialias])'
```

To parse the failed functions, you should manually fix the source HTML before parsing it.

## Generating TypeScript Definitions

The action 'to-ts' generates a TypeScript declaration file containing all functions in the documentation:

```sh
# example usage:
reascript-parse to-ts reascripthelp.html reaper.d.ts
```
