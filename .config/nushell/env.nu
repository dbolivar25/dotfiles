# Nushell Environment Config File
#
# version = "0.99.1"

use std "path add"

def create_left_prompt [] {
    # Initialize segments
    mut segments = []

    # Path segment with home directory replacement
    let dir = ($env.PWD | str replace $nu.home-path "~")
    let path_segment = $"(ansi blue)($dir)(ansi reset)"
    $segments = ($segments | append $path_segment)

    # Git segment
    if (do -s { git rev-parse --is-inside-work-tree } | complete | get exit_code) == 0 {
        let git_branch = (do -s { git symbolic-ref --short HEAD } | complete | get stdout | str trim)
        let branch = if ($git_branch | is-empty) {
            do -s { git rev-parse --short HEAD } | complete | get stdout | str trim
        } else {
            $git_branch
        }

        if not ($branch | is-empty) {
            let is_dirty = not (do -s { git status --porcelain } | complete | get stdout | is-empty)
            let dirty_marker = if $is_dirty { "*" } else { "" }
            let git_segment = $"(ansi grey)($branch)($dirty_marker)(ansi reset)"
            $segments = ($segments | append $git_segment)
        }
    }

    # Python virtual environment segment
    if not ($env | get -i VIRTUAL_ENV | is-empty) {
        let venv = ($env.VIRTUAL_ENV | path basename)
        let venv_segment = $"(ansi grey)($venv)(ansi reset)"
        $segments = ($segments | append $venv_segment)
    }

    # Join all segments with spaces
    let prompt = ($segments | str join " ")

    $"($prompt)\n\n"
}

def create_right_prompt [] {}

def prompt_char [] {
    let last_exit_code = $env.LAST_EXIT_CODE
    if $last_exit_code == 0 {
        $"(ansi magenta)❯(ansi reset) "
    } else {
        $"(ansi red)❯(ansi reset) "
    }
}

$env.PROMPT_COMMAND = {|| create_left_prompt }
$env.PROMPT_COMMAND_RIGHT = {|| create_right_prompt }

# The prompt indicators are environmental variables that represent
# the state of the prompt
$env.PROMPT_INDICATOR = {|| prompt_char }
$env.PROMPT_INDICATOR_VI_INSERT = {|| prompt_char }
$env.PROMPT_INDICATOR_VI_NORMAL = {|| prompt_char }
$env.PROMPT_MULTILINE_INDICATOR = {|| prompt_char }

# Specifies how environment variables are:
# - converted from a string to a value on Nushell startup (from_string)
# - converted from a value back to a string when running external commands (to_string)
# Note: The conversions happen *after* config.nu is loaded
$env.ENV_CONVERSIONS = {
    "PATH": {
        from_string: { |s| $s | split row (char esep) | path expand --no-symlink }
        to_string: { |v| $v | path expand --no-symlink | str join (char esep) }
    }
    "Path": {
        from_string: { |s| $s | split row (char esep) | path expand --no-symlink }
        to_string: { |v| $v | path expand --no-symlink | str join (char esep) }
    }
}

# Directories to search for scripts when calling source or use
# The default for this is $nu.default-config-dir/scripts
$env.NU_LIB_DIRS = [
    ($nu.default-config-dir | path join 'scripts') # add <nushell-config-dir>/scripts
    ($nu.data-dir | path join 'completions') # default home for nushell completions
]

# Directories to search for plugin binaries when calling register
# The default for this is $nu.default-config-dir/plugins
$env.NU_PLUGIN_DIRS = [
    ($nu.default-config-dir | path join 'plugins') # add <nushell-config-dir>/plugins
]

# Environment variables
$env.EDITOR = "nvim"
$env.VISUAL = "nvim"

# Config directory
$env.XDG_CONFIG_HOME = ($env.HOME | path join ".config")

# Ruby exports
$env.LDFLAGS = "-L/opt/homebrew/opt/ruby/lib"
$env.CPPFLAGS = "-I/opt/homebrew/opt/ruby/include"

# Key and Token exports
source ~/.config/nushell/secrets.nu

# FZF Configuration
$env.FZF_DEFAULT_OPTS = "
        --tmux 70%
        --color=fg:#908caa,bg:#191724,hl:#ebbcba
        --color=fg+:#e0def4,bg+:#26233a,hl+:#ebbcba
        --color=border:#403d52,header:#31748f,gutter:#191724
        --color=spinner:#f6c177,info:#9ccfd8
        --color=pointer:#c4a7e7,marker:#eb6f92,prompt:#908caa"

# Bat Configuration
$env.BAT_THEME = "base16"

# Other Configuration
$env.USER = "daniel"
$env.VIRTUAL_ENV_DISABLE_PROMPT = 1
$env.NODE_OPTIONS = "--max-old-space-size=8192"

# Path configuration
$env.PATH = ($env.PATH | split row (char esep))

path add ($env.HOME | path join ".local" "bin")
path add "/opt/homebrew/bin"
path add "/usr/local/sbin"
path add ($env.HOME | path join ".cargo" "bin")
path add ($env.HOME | path join ".ghcup" "bin")
path add ($env.HOME | path join ".cabal" "bin")
path add ($env.HOME | path join ".modular" "bin")
path add "/Library/TeX/texbin"
path add "/opt/homebrew/opt/ruby/bin"
path add ($env.HOME | path join ".dotnet" "tools")
path add "/usr/local/share/dotnet"

$env.PATH = ($env.PATH | uniq)

zoxide init nushell --cmd cd | save ~/.config/nushell/zoxide.nu --force
