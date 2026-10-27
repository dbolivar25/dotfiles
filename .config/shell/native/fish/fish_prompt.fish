function fish_prompt
    set -l last_status $status

    # Path segment
    set_color blue
    echo -n $PWD | string replace $HOME '~'
    set_color normal
    echo -n ' '

    # set -l git_timeout
    #
    # if command -q gtimeout
    #     set git_timeout gtimeout
    # else if command -q timeout
    #     set git_timeout timeout
    # end
    #
    # if test -n "$git_timeout"
    #     if set -l git_lines (command $git_timeout -s KILL 0.050s git --no-optional-locks -c status.aheadBehind=false status --porcelain=v1 --branch --untracked-files=no 2>/dev/null)
    #         if set -q git_lines[1]
    #             set -l branch (string replace -r '^## (.*?)(\.\.\..*)?$' '$1' -- $git_lines[1])
    #
    #             set_color brblack
    #             echo -n "$branch"
    #
    #             if test (count $git_lines) -gt 1
    #                 echo -n '*'
    #             end
    #
    #             set_color normal
    #             echo -n ' '
    #         end
    #     end
    # end

    # Python virtual environment
    if set -q VIRTUAL_ENV
        set -l venv (basename "$VIRTUAL_ENV")
        set_color brblack
        echo -n "$venv "
        set_color normal
    end

    echo
    if test $last_status -eq 0
        set_color magenta
    else
        set_color red
    end
    echo -n '❯'
    set_color normal
    echo -n ' '
end
