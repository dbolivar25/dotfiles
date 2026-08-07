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

# Shared environment and behavior contracts.
source ~/.config/shell/adapters/nu.nu

# Nushell cannot evaluate activation output inline, so build mise's native
# module outside the tracked dotfiles tree before config.nu is parsed.
let mise_module_dir = ($nu.cache-dir | path join "dotfiles")
mkdir $mise_module_dir
# Mise 2025.10.7 can emit duplicate hides during deactivation.
^mise activate nu
| str replace --all 'hide-env $var.name' 'hide-env --ignore-errors $var.name'
| save ($mise_module_dir | path join "mise.nu") --force
$env.NU_LIB_DIRS = ($env.NU_LIB_DIRS | prepend $mise_module_dir | uniq)
