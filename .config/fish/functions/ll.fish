function ll --wraps=eza --description "List directory contents with long format"
    eza --color=always --group-directories-first --no-user --git --git-repos --links $argv
end
