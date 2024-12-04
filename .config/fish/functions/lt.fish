function lt --wraps=eza --description "List directory contents as a tree"
    eza --color=always --group-directories-first --git-ignore --tree $argv
end
