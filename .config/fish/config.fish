if status is-interactive
    # fish config
    fish_config theme choose "Rosé Pine"

    # zoxide
    zoxide init fish --cmd cd | source

    # direnv
    direnv hook fish | source

    # if set -q SSH_TTY; and not set -q TMUX; and test "$SSH_DEVICE" = phone
    #     exec tmux new-session -A -s phone
    # end
end
