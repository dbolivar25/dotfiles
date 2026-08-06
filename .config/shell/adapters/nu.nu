# Shared static environment for Nushell. Interactive behavior remains native.
let dotfiles_shell_root = ($env.HOME | path join ".config" "shell")

for value_file in (
    (glob ($dotfiles_shell_root | path join "environment.d" "*"))
    | append (glob ($dotfiles_shell_root | path join "secrets.d" "*"))
) {
    let key = ($value_file | path basename)
    let value = (
        open --raw $value_file
        | str trim --right
        | str replace --all '${HOME}' $env.HOME
    )
    load-env { $key: $value }
}

let managed_paths = (
    open --raw ($dotfiles_shell_root | path join "paths")
    | lines
    | where {|entry| not ($entry | str trim | is-empty) }
    | where {|entry| not ($entry | str trim | str starts-with "#") }
    | each {|entry| $entry | str replace --all '${HOME}' $env.HOME }
    | where {|entry| $entry | path exists }
)

$env.PATH = ($managed_paths | append $env.PATH | uniq)

let editor_profile = if (($env | get -i SSH_CONNECTION | default "") | is-empty) {
    "local"
} else {
    "ssh"
}
let editor = (
    open --raw ($dotfiles_shell_root | path join "behavior" "editor" $editor_profile)
    | str trim
)
$env.EDITOR = $editor
$env.VISUAL = $editor
