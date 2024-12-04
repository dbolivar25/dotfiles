# Clear existing completions
complete -c sw -e

# Basic command setup
complete -c sw -f

# First argument completions
complete -c sw -n "test (count (commandline -opc)) -eq 1" -a "t tmux" -d "Switch tmux session (keep current)"
complete -c sw -n "test (count (commandline -opc)) -eq 1" -a "tk tmuxk" -d "Switch tmux session (kill current)"
complete -c sw -n "test (count (commandline -opc)) -eq 1" -a "a aws" -d "Switch AWS profile"

# Second argument completions
# For t/tmux - show all sessions except current
complete -c sw -n "test (count (commandline -opc)) -eq 2; and contains -- (commandline -opc)[2] t tmux" \
    -a "(__sw_tmux_all_sessions)" -d "Tmux session"

# For tk/tmuxk - show only unattached sessions
complete -c sw -n "test (count (commandline -opc)) -eq 2; and contains -- (commandline -opc)[2] tk tmuxk" \
    -a "(__sw_tmux_unattached_sessions)" -d "Unattached tmux session"

# For a/aws - show available AWS profiles
complete -c sw -n "test (count (commandline -opc)) -eq 2; and contains -- (commandline -opc)[2] a aws" \
    -a "(__sw_aws_profiles)" -d "AWS profile"
