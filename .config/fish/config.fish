if status is-interactive
    # fish config
    fish_config theme choose "Rosé Pine"

    # zoxide
    zoxide init fish --cmd cd | source

    # direnv
    direnv hook fish | source
end
