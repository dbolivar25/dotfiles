function ls --wraps=eza --description "List directory contents"
    eza --color=always --group-directories-first --no-user --time-style=relative $argv
end
