function sw --description 'Universal switcher (tmux/aws)'
    if test (count $argv) -eq 0
        __sw_print_usage
        return 1
    end

    switch $argv[1]
        case t tmux tk tmuxk
            __sw_handle_tmux $argv
        case a aws
            __sw_handle_aws $argv
        case help --help
            __sw_print_usage
        case '*'
            __sw_print_usage
            return 1
    end
end

function __sw_print_usage
    echo "Usage:"
    echo "  sw <COMMAND> [target]"
    echo "Commands:"
    echo "  t,  tmux    - Switch tmux session (keep current)"
    echo "  tk, tmuxk   - Switch tmux session (kill current)"
    echo "  a,  aws     - Switch AWS profile"
end

function __sw_handle_tmux
    set -l action $argv[1]
    set -l current_session (tmux display-message -p '#S')

    # Handle direct session switch if provided
    if test (count $argv) -gt 1
        __sw_switch_to_tmux_session $action $current_session $argv[2]
        return $status
    end

    set -l sessions_data (__sw_get_filtered_sessions $action $current_session)
    if test $status -ne 0
        echo $sessions_data
        return 1
    end

    set -l selected_session (__sw_show_session_picker $action $sessions_data)
    if test -n "$selected_session"
        __sw_switch_to_tmux_session $action $current_session $selected_session
    else
        echo "No session selected"
        return 1
    end
end

function __sw_get_filtered_sessions
    set -l action $argv[1]
    set -l current_session $argv[2]

    set -l format_str '#{session_name}|#{session_attached}|#{session_windows}|#{t:session_created}|#{window_name}'
    set -l sessions (tmux list-sessions -F "$format_str" 2>/dev/null)

    if test -z "$sessions"
        echo "No tmux sessions found."
        return 1
    end

    set -l available_sessions
    set -l display_lines
    for session in $sessions
        set -l parts (string split '|' $session)
        set -l session_name $parts[1]
        set -l is_attached $parts[2]
        set -l window_count $parts[3]
        set -l created_at $parts[4]
        set -l current_window $parts[5]

        if begin
                test "$action" = tk -o "$action" = tmuxk -a "$is_attached" = 0 -a "$session_name" != "$current_session"
                or begin
                    test "$action" = t -o "$action" = tmux
                    and test "$session_name" != "$current_session"
                end
            end
            set -a available_sessions $session_name
            set -a display_lines (printf "%-20s%-10s%-20s%-20s" $session_name "[$window_count win]" "[$current_window]" "($created_at)")
        end
    end

    if test -z "$available_sessions"
        if test "$action" = tk -o "$action" = tmuxk
            echo "No other unattached tmux sessions found."
        else
            echo "No other tmux sessions found."
        end
        return 1
    end

    printf '%s\n' $display_lines
    return 0
end

function __sw_show_session_picker
    set -l action $argv[1]
    set -l sessions_data $argv[2..-1]

    printf '%s\n' $sessions_data | fzf \
        --tmux 46% \
        --reverse \
        --ansi \
        --header (test "$action" = tk -o "$action" = tmuxk; and echo 'Available Sessions (Select to switch and kill current)'; or echo 'Available Sessions (Select to switch)') \
        --header-lines 0 \
        | string split -f1 ' ' | string trim
end

function __sw_switch_to_tmux_session
    set -l action $argv[1]
    set -l current_session $argv[2]
    set -l target_session $argv[3]

    if not tmux has-session -t "$target_session" 2>/dev/null
        echo "Session '$target_session' does not exist."
        return 1
    end

    if test "$target_session" = "$current_session"
        echo "Already in session $target_session"
        return 1
    end

    tmux switch-client -t "$target_session"
    if test "$action" = tk -o "$action" = tmuxk
        tmux kill-session -t "$current_session"
    end
    return 0
end

function __sw_handle_aws
    if test (count $argv) -gt 1
        __sw_switch_to_aws_profile $argv[2]
        return $status
    end

    set -l profile (__sw_show_aws_picker)
    if test -n "$profile"
        __sw_switch_to_aws_profile $profile
    else
        echo "No profile selected"
        return 1
    end
end

function __sw_show_aws_picker
    aws configure list-profiles | fzf \
        --tmux 40% \
        --reverse \
        --header 'AWS Profiles (Select to switch)' \
        --prompt="Switch AWS Profile > "
end

function __sw_switch_to_aws_profile
    set -l profile $argv[1]

    if not contains "$profile" (aws configure list-profiles)
        echo "Profile '$profile' does not exist."
        return 1
    end

    set -gx AWS_PROFILE $profile
    aws sso login
    set -gx AWS_REGION (aws configure get region)
    set -gx AWS_DEFAULT_REGION $AWS_REGION
    echo "Switched to $AWS_PROFILE in region $AWS_REGION"
    return 0
end

function __sw_tmux_all_sessions
    set current (tmux display-message -p '#S')
    tmux list-sessions -F '#{session_name}' 2>/dev/null | while read -l session
        if test "$session" != "$current"
            echo $session
        end
    end
end

function __sw_tmux_unattached_sessions
    set current (tmux display-message -p '#S')
    tmux list-sessions -F '#{session_name}|#{session_attached}' 2>/dev/null | while read -l session
        set parts (string split '|' $session)
        if test $parts[2] = 0 -a $parts[1] != "$current"
            echo $parts[1]
        end
    end
end

function __sw_aws_profiles
    aws configure list-profiles
end
