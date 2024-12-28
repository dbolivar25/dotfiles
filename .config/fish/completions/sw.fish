# Clear existing completions
complete -c sw -e

# Basic command setup
complete -c sw -f

# Add help option
complete -c sw -s h -l help -d "Show help message"

# For any position, offer AWS profiles as completions
complete -c sw -a "(aws configure list-profiles)" -d "AWS profile"
