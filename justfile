version := "v7.08"

run:
  rye run rs-parse "reascripthelp/{{version}}.html" "temp/reaper_{{version}}.lua" &> "temp/reaper_{{version}}.log"
