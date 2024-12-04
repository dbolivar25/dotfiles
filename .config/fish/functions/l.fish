function l --wraps=eza --description "List directory contents with short format"
    eza --color=always --group-directories-first --classify $argv
end
