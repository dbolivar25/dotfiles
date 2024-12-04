function pdf
    pandoc $argv[1] -H ~/.config/pandoc/disable_float.tex -o (string replace -r '\.[^.]*$' '.pdf' $argv[1])
end
