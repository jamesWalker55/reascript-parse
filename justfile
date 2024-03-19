version := "v7.08"

run:
  rye run rs-parse "reascripthelp/{{version}}.html" "reaper_{{version}}.lua" &> "reaper_{{version}}.log"
