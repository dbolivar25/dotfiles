# Commands that must mutate Nushell or preserve structured output.
def --env load_env [file: path = ".env"] {
    if not ($file | path exists) {
        error make {msg: $"load_env: ($file): file not found"}
    }

    for line in (open --raw $file | lines) {
        let clean = ($line | str trim)
        if ($clean | is-empty) or ($clean | str starts-with "#") {
            continue
        }
        let equals = ($line | str index-of "=")
        if $equals == -1 {
            continue
        }
        let key = ($line | str substring 0..<$equals)
        if not ($key =~ '^[A-Za-z_][A-Za-z0-9_]*$') {
            error make {msg: $"load_env: invalid name: ($key)"}
        }
        load-env {($key): ($line | str substring ($equals + 1)..)}
    }
}

def --env mkcd [dirname: string, ...rest: string] {
    mkdir $dirname
    cd $dirname
}

def --env up [levels: string = "1", ...rest: string] {
    if not ($levels =~ '^[0-9]+$') {
        error make {msg: "Usage: up [levels]"}
    }
    let count = ($levels | into int)
    if $count == 0 {
        cd $env.HOME
    } else {
        cd (0..<$count | each {|_| "../" } | str join)
    }
}

alias venv = overlay use .venv/bin/activate.nu

def --wrapped fenv [...rest: string] {
    ^env | ^rg ...$rest
}

# Nushell keeps structured ls and uses native directory-scoped editor commands.
alias rc = do { cd ~/.config/shell; nvim; cd - }
alias nrc = do { cd ~/.config/nvim; nvim init.lua; cd - }
alias trc = do { cd ~/.config/ghostty; nvim config; cd - }
alias src = do { cd ~/.ssh; nvim config; cd - }
