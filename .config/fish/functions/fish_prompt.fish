function fish_prompt
    set -l last_status $status

    # Path segment
    set_color blue
    echo -n $PWD | string replace $HOME '~'
    set_color normal
    echo -n ' '

    # Git segment
    if command -q git
        and test -d .git; or git rev-parse --git-dir >/dev/null 2>&1
        set -l git_branch (git symbolic-ref --short HEAD 2>/dev/null; or git rev-parse --short HEAD 2>/dev/null)
        set -l git_dirty (git status --porcelain 2>/dev/null)

        if test -n "$git_branch"
            set_color brblack # equivalent to your p:grey
            echo -n "$git_branch"

            # Show dirty state
            if test -n "$git_dirty"
                echo -n "*"
            end

            set_color normal
            echo -n ' '
        end
    end

    # Python virtual environment
    if set -q VIRTUAL_ENV
        set -l venv (basename "$VIRTUAL_ENV")
        set_color brblack
        echo -n "$venv "
        set_color normal
    end

    # New line before prompt character
    echo

    # Prompt character on new line
    if test $last_status -eq 0
        set_color magenta
    else
        set_color red
    end
    echo -n '❯'
    set_color normal
    echo -n ' '
end
