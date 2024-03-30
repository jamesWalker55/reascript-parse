version := "v7.08"

run:
  rye run reascript-parse "reascripthelp/{{version}}.html" "temp/reaper_{{version}}.lua" &> "temp/reaper_{{version}}.log"
