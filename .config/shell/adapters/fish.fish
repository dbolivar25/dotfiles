# Shared static environment for Fish. Interactive behavior remains native.
set -l dotfiles_shell_root $HOME/.config/shell

for value_file in $dotfiles_shell_root/environment.d/* $dotfiles_shell_root/secrets.d/*
    test -f $value_file; or continue
    set -l key (path basename $value_file)
    set -l value "$(string collect <$value_file)"
    set value "$(string replace -r '\n$' '' -- "$value")"
    set value "$(string replace -a '${HOME}' $HOME -- "$value")"
    set -gx $key $value
end

set -l managed_paths
while read -l entry
    string match -qr '^\s*(#|$)' -- $entry; and continue
    set entry (string replace -a '${HOME}' $HOME -- $entry)
    test -d $entry; and set -a managed_paths $entry
end <$dotfiles_shell_root/paths

set -l combined_paths $managed_paths $PATH
set -l unique_paths
for entry in $combined_paths
    contains -- $entry $unique_paths; or set -a unique_paths $entry
end
set -gx PATH $unique_paths

set -l editor_profile local
set -q SSH_CONNECTION; and set editor_profile ssh
set -l editor (string trim < $dotfiles_shell_root/behavior/editor/$editor_profile)
set -gx EDITOR $editor
set -gx VISUAL $editor

for integration in $dotfiles_shell_root/integrations/*/fish.fish
    test -f $integration; and source $integration
end

set -e dotfiles_shell_root editor_profile editor managed_paths combined_paths unique_paths
