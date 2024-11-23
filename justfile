version := "v7.08"

run:
  rye run reascript-parse to-ts "reascripthelp/{{version}}.html" "temp/reaper_{{version}}.ts" &> "temp/reaper_{{version}}.log"

run-appdata:
  rye run reascript-parse to-ts "C:/Users/James/AppData/Local/Temp/reascripthelp.html" "temp/reaper_appdata.d.ts" &> "temp/reaper_appdata.log"
